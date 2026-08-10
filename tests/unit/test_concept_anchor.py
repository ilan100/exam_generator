from exam_generator.models import SourceEvidenceChunk, SourceType
from exam_generator.planning.concept_anchor import (
    _attempt_leading_reconstruction,
    _is_likely_category_self_restatement,
    _looks_leading_truncated,
    anchor_concept_evidence,
    refine_concept_inventory,
)


def _chunk(text: str, *, chunk_id: str = "STUDENT_SUMMARY:s1.pdf:0001:0001") -> SourceEvidenceChunk:
    return SourceEvidenceChunk(
        chunk_id=chunk_id, source_type=SourceType.STUDENT_SUMMARY, source_file="s1.pdf", page=1, text=text
    )


# ---------------------------------------------------------------------------
# Concept anchoring (WP-037 section 22)
# ---------------------------------------------------------------------------


def test_concept_alone_on_its_own_line():
    text = "Superior Cerebellar Artery"
    assert anchor_concept_evidence(chunk_text=text, concept="Superior Cerebellar Artery") == text


def test_concept_with_context_on_multiple_surrounding_lines():
    text = "אספקת הדם:\nSuperior Cerebellar Artery\nמקור:\nBasilar Artery"
    anchored = anchor_concept_evidence(chunk_text=text, concept="Superior Cerebellar Artery")
    assert "Superior Cerebellar Artery" in anchored
    assert "אספקת הדם" in anchored


def test_anchoring_stops_before_a_competing_salient_entity():
    # The exact WP-036 live-pilot failure shape: a concept ("Basilar
    # Artery") extracted from a passage whose main subject is a
    # different, more salient entity ("Superior Cerebellar Artery") must
    # not have that entity's own name pulled into its anchored evidence.
    text = "Superior Cerebellar Artery\nמקור:\nBasilar Artery\nאזור:\nהמשטח העליון"
    anchored = anchor_concept_evidence(chunk_text=text, concept="Basilar Artery")
    assert "Superior Cerebellar Artery" not in anchored
    assert "Basilar Artery" in anchored


def test_concept_at_the_beginning_of_evidence():
    text = "Spinothalamic Tract\nמעבירה תחושות כאב"
    anchored = anchor_concept_evidence(chunk_text=text, concept="Spinothalamic Tract")
    assert "Spinothalamic Tract" in anchored


def test_concept_at_the_end_of_evidence():
    text = "מעבירה תחושות כאב\nSpinothalamic Tract"
    anchored = anchor_concept_evidence(chunk_text=text, concept="Spinothalamic Tract")
    assert "Spinothalamic Tract" in anchored


def test_missing_concept_falls_back_to_the_concept_itself():
    anchored = anchor_concept_evidence(chunk_text="completely unrelated text", concept="Nonexistent Concept")
    assert anchored == "Nonexistent Concept"


def test_malformed_empty_lines_do_not_crash():
    text = "\n\n\nSuperior Cerebellar Artery\n\n\n"
    anchored = anchor_concept_evidence(chunk_text=text, concept="Superior Cerebellar Artery")
    assert "Superior Cerebellar Artery" in anchored


def test_a_single_blank_line_is_not_treated_as_a_boundary():
    # The exact bug found and fixed during this WP's own development: a
    # single blank line (used liberally in this corpus as visual
    # spacing, not a paragraph boundary) must not immediately stop the
    # walk and strip a concept of all context.
    text = "אספקת הדם:\n \nSuperior Cerebellar Artery"
    anchored = anchor_concept_evidence(chunk_text=text, concept="Superior Cerebellar Artery")
    assert "אספקת הדם" in anchored


def test_two_consecutive_blank_lines_are_a_boundary():
    text = "Unrelated Prior Concept\n\n\nSuperior Cerebellar Artery"
    anchored = anchor_concept_evidence(chunk_text=text, concept="Superior Cerebellar Artery")
    assert "Unrelated Prior Concept" not in anchored


def test_hebrew_english_mixed_multiline_evidence():
    text = "מבנה המוח– אספקת הדם\n2020-2021\n\nSuperior Cerebellar Artery\nמקור:\nBasilar Artery"
    anchored = anchor_concept_evidence(chunk_text=text, concept="Superior Cerebellar Artery")
    assert "Superior Cerebellar Artery" in anchored
    assert "מקור" in anchored


def test_anchoring_uses_the_reconstructed_concept_text_not_the_raw_truncated_line():
    text = "M\nedial Lemniscus Tract\nמעבירה תחושות"
    anchored = anchor_concept_evidence(chunk_text=text, concept="Medial Lemniscus Tract")
    assert "Medial Lemniscus Tract" in anchored
    # The raw truncated line must not appear as a *separate* line from
    # the corrected one - only as a substring of the corrected text.
    lines = anchored.splitlines()
    assert "edial Lemniscus Tract" not in lines
    # The consumed orphan letter must not also appear as separate context.
    assert anchored.count("M") == 1


# ---------------------------------------------------------------------------
# Extraction artifacts (WP-037 sections 10/11)
# ---------------------------------------------------------------------------


def test_clean_concept_passes_through_unchanged():
    chunk = _chunk("Superior Cerebellar Artery")
    refined = refine_concept_inventory((chunk,))
    assert [c.concept for c in refined] == ["Superior Cerebellar Artery"]


def test_obviously_truncated_concept_is_reconstructed_when_unambiguous():
    chunk = _chunk("M\nedial Lemniscus Tract")
    refined = refine_concept_inventory((chunk,))
    assert [c.concept for c in refined] == ["Medial Lemniscus Tract"]


def test_leading_truncation_detection():
    assert _looks_leading_truncated("edial Lemniscus Tract") is True
    assert _looks_leading_truncated("Medial Lemniscus Tract") is False
    assert _looks_leading_truncated("MCA") is False


def test_ambiguous_fragment_with_no_reconstruction_candidate_is_excluded():
    # No adjacent single-uppercase-letter orphan line exists anywhere
    # near the truncated concept - nothing to unambiguously reconstruct
    # from, so it must be excluded rather than guessed at.
    chunk = _chunk("edial Lemniscus Tract\nCaudate Nucleus")
    refined = refine_concept_inventory((chunk,))
    assert "edial Lemniscus Tract" not in [c.concept for c in refined]
    assert "Medial Lemniscus Tract" not in [c.concept for c in refined]


def test_ambiguous_fragment_with_two_candidate_letters_is_excluded():
    # Both neighbors are lone uppercase letters - genuinely ambiguous
    # which one (if either) completes the word; never guess.
    chunk = _chunk("A\nedial Lemniscus Tract\nB")
    reconstructed = _attempt_leading_reconstruction(chunk.text, "edial Lemniscus Tract")
    assert reconstructed is None


def test_category_self_restatement_is_excluded():
    # A realistic amount of separating text between the naming statement
    # and the next, unrelated, genuine sub-concept (mirroring the real
    # corpus's own spacing) - not artificially compressed.
    chunk = _chunk(
        "גרעיני הבסיס נקראים גם\nThe Basal Ganglia\n"
        "אך מושג זה שגוי משום שגנגליה מתאר צבר גופי תאים במערכת העצבים ההיקפית\n"
        "גרעיני הבסיס מכילים מספר תתי מבנים\n\nCaudate Nucleus"
    )
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "The Basal Ganglia" not in concepts
    assert "Caudate Nucleus" in concepts


def test_naming_cue_detection_is_a_local_deterministic_text_check():
    text = "נקראים גם\nThe Basal Ganglia"
    assert _is_likely_category_self_restatement(text, "The Basal Ganglia") is True
    assert _is_likely_category_self_restatement("Caudate Nucleus", "Caudate Nucleus") is False


def test_naming_cue_far_away_does_not_trigger_exclusion():
    # The naming-cue phrase must be locally adjacent, not merely present
    # anywhere earlier in a long chunk.
    far_prefix = "x" * 200
    text = f"נקראים גם{far_prefix}\nCaudate Nucleus"
    assert _is_likely_category_self_restatement(text, "Caudate Nucleus") is False


# ---------------------------------------------------------------------------
# Planner integration (WP-037 section 22) - see also test_planning.py
# ---------------------------------------------------------------------------


def test_refine_concept_inventory_preserves_genuine_evidence_chunk_id():
    chunk = _chunk("Superior Cerebellar Artery", chunk_id="STUDENT_SUMMARY:s2.pdf:0128:0001")
    refined = refine_concept_inventory((chunk,))
    assert refined[0].evidence_chunk_id == "STUDENT_SUMMARY:s2.pdf:0128:0001"


def test_reconstructed_concept_preserves_genuine_evidence_chunk_id():
    chunk = _chunk("M\nedial Lemniscus Tract", chunk_id="STUDENT_SUMMARY:s2.pdf:0108:0001")
    refined = refine_concept_inventory((chunk,))
    assert refined[0].evidence_chunk_id == "STUDENT_SUMMARY:s2.pdf:0108:0001"


def test_no_llm_or_embedding_call_in_concept_anchor_module():
    import inspect

    import exam_generator.planning.concept_anchor as concept_anchor_module

    source = inspect.getsource(concept_anchor_module)
    assert "generate_structured" not in source
    assert "vector" not in source.lower()
