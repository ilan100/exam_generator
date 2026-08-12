from exam_generator.models import SourceEvidenceChunk, SourceType
from exam_generator.planning.concept_anchor import (
    _attempt_leading_reconstruction,
    _is_likely_category_self_restatement,
    _looks_leading_truncated,
    anchor_concept_evidence,
    detect_enumeration_member_shape,
    is_enumeration_evidence_insufficient,
    is_factual_focus_sufficient,
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


# ---------------------------------------------------------------------------
# WP-039: trailing-fragment truncation recovery
#
# Every test in this section reproduces the actual multi-line structural
# shape observed in the real corpus (WP-039 section 5: "do not merely add
# tests that call a repair function with two strings... test the actual
# extraction path") - each runs the real evidence text through
# refine_concept_inventory() end-to-end, exactly as production does.
# ---------------------------------------------------------------------------


def test_clean_concept_is_never_touched_by_trailing_repair():
    chunk = _chunk("Caudate Nucleus\n \nNucleus Accumbens")
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "Caudate Nucleus" in concepts
    assert not any("WP-039" in c.extraction_reason for c in refined if c.concept == "Caudate Nucleus")


def test_real_corpus_case_corpos_str_reconstructs_to_corpos_striatum():
    # The exact live WP-036/037/038 shape: bidi text extraction placed
    # the word's trailing fragments on the two lines immediately before
    # the truncated concept's own line.
    chunk = _chunk(
        " גרעיני הבסיס:מכילים מספר תתי מבנים \n"
        "\n \ntum\nia\nCorpos Str\n \no\n \nCaudate Nucleus"
    )
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "Corpos Striatum" in concepts
    assert "Corpos Str" not in concepts
    repaired = next(c for c in refined if c.concept == "Corpos Striatum")
    assert "WP-039" in repaired.extraction_reason


def test_real_corpus_case_anterior_corticospinal_t_reconstructs_to_tract():
    # The exact live WP-038 shape: a single trailing fragment ("ract") on
    # the line immediately before the truncated concept's own line.
    chunk = _chunk("מסילות יורדות  :\n      \n \nract\nAnterior Corticospinal T\n                     ")
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "Anterior Corticospinal Tract" in concepts
    assert "Anterior Corticospinal T" not in concepts


def test_real_corpus_case_forward_direction_single_letter_suffix():
    # "Interna" + "l" = "Internal" - the completing fragment is on the
    # line AFTER the concept, not before (real corpus shape, mirroring
    # WP-037's own leading-truncation check of both directions).
    chunk = _chunk(" Y\n Interna\nl\n Medullary Lamin")
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "Internal" in concepts
    assert "Interna" not in concepts


def test_sibling_chain_shares_single_letter_boundary_lines_correctly():
    # The real corpus "Globus Pallidu"/"Putame"/"Lentifor" chain: three
    # separate truncated concepts, each completed by exactly the one
    # single-letter line between it and its neighbor. This is the test
    # that exercises consumed-line tracking across concepts.
    chunk = _chunk(
        ",מראה,\nGlobus Pallidu\ns\nPutame\nn\n Lentifor\nm\n.\nחלוקה שמתאימה יותר"
    )
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "Globus Pallidus" in concepts
    assert "Putamen" in concepts
    assert "Lentiform" in concepts
    assert "Globus Pallidu" not in concepts
    assert "Putame" not in concepts
    assert "Lentifor" not in concepts


def test_consumed_boundary_line_is_not_reused_by_a_different_concept():
    # Regression test for a real bug found during WP-039 development:
    # when a reconstruction attempt discovers fragment lines but fails
    # (ambiguous/malformed), those lines must still be marked consumed -
    # otherwise a different, unrelated concept can wrongly absorb them
    # into an equally invalid, differently-ordered "reconstruction." This
    # reproduces the real corpus case: "Substantia Nigra P"'s own
    # (correctly rejected) attempt discovers "a" and "rs Reticulata (";
    # without consuming them, "NSp.)" would wrongly absorb both.
    chunk = _chunk(
        "ת \nSubstantia Nigra P\na\nrs Reticulata (\nNSp.)\nם"
    )
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "Substantia Nigra P" not in concepts
    # "NSp.)" may legitimately remain unrepaired (its only neighbor
    # fragment was consumed by "Substantia Nigra P"'s own failed
    # attempt) - the invariant under test is that it is never wrongly
    # merged with that neighbor's own discarded fragments.
    assert "NSp.)rs Reticulata (a" not in concepts
    assert not any(c.startswith("Substantia Nigra P") and c != "Substantia Nigra P" for c in concepts)


def test_unbalanced_parentheses_after_reconstruction_is_excluded():
    # A reconstruction that stops mid-parenthetical is untrustworthy -
    # never used partially.
    chunk = _chunk("ת \nSubstantia Nigra P\na\nrs Reticulata (\nNSp.)")
    refined = refine_concept_inventory((chunk,))
    assert not any(c.concept.startswith("Substantia Nigra Pars") for c in refined)


def test_ambiguous_both_directions_have_fragments_is_excluded():
    chunk = _chunk(", globus pallidus \ninetnrus \n(GiP )\nrN .\nאמנם ")
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "(GiP )" not in concepts
    assert not any("GiP" in c for c in concepts)  # no partial repair either


def test_no_adjacent_evidence_leaves_a_genuinely_unrecoverable_fragment_unchanged():
    # "Medullary Lamin" has no safely-usable adjacent evidence (its only
    # neighbor fragment is consumed by "Interna", and its forward
    # neighbor is Hebrew-fused) - it must be left unchanged, never
    # excluded, since absence of evidence is not evidence of exclusion.
    chunk = _chunk(" Y\n Interna\nl\n Medullary Lamin\na. ,לטרליי")
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "Medullary Lamin" in concepts


def test_fragment_fused_with_hebrew_text_is_never_used_as_a_continuation():
    # A line mixing a lowercase-starting fragment with Hebrew prose on
    # the same physical line must never be treated as pure continuation
    # text (WP-039 section 11: no general text correction).
    chunk = _chunk(" נקראים גםlia\nThe Basal Gang\n , אך מושג זה שגוי")
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "The Basal Ganglia" not in concepts


def test_trailing_period_is_stripped_from_a_reconstructed_concept():
    chunk = _chunk(",המוטורית,\nNeuromuscular Junctio\nn.")
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "Neuromuscular Junction" in concepts
    assert "Neuromuscular Junction." not in concepts


def test_reconstructed_duplicate_of_an_already_complete_concept_is_deduplicated():
    # "Neurom" (backward: "u" + "scular Junction") reconstructs to the
    # same normalized text as an already-complete "Neuromuscular
    # Junction" extracted elsewhere in the same evidence - only one
    # survives (first occurrence wins, the established convention).
    chunk = _chunk(
        "Neuromuscular Junction\n \nscular Junction\nu\nNeurom\n –\ninal Common Pathway \nF"
    )
    refined = refine_concept_inventory((chunk,))
    normalized = [c.concept.strip().lower() for c in refined]
    assert normalized.count("neuromuscular junction") == 1


def test_short_legitimate_abbreviation_is_not_arbitrarily_expanded():
    # False-positive protection: a genuine short abbreviation surrounded
    # by ordinary Hebrew prose (no adjacent continuation-fragment shape)
    # must not be "expanded" into anything.
    chunk = _chunk("חלק מהתלמוס נקרא \nVL\n ומכיל תאים")
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "VL" in concepts


def test_related_concepts_are_never_merged_by_trailing_repair():
    # False-positive protection: two genuinely distinct, already-complete
    # concepts on adjacent lines must never be merged into one.
    chunk = _chunk("Anterior Spinal Artery\n \nPosterior Spinal Arteries")
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "Anterior Spinal Artery" in concepts
    assert "Posterior Spinal Arteries" in concepts
    assert "Anterior Spinal ArteryPosterior Spinal Arteries" not in concepts


def test_two_possible_completions_is_ambiguous_and_excludes():
    # Synthetic: a concept genuinely has a plausible completion in BOTH
    # directions - WP-039's own explicit ambiguity test requirement
    # (section 17: "two possible completions").
    chunk = _chunk("tail\nAmbiguous Concep\nture")
    refined = refine_concept_inventory((chunk,))
    concepts = [c.concept for c in refined]
    assert "Ambiguous Concep" not in concepts
    assert "Ambiguous Conceptail" not in concepts
    assert "Ambiguous Concepture" not in concepts


def test_reconstructed_concept_via_trailing_repair_preserves_genuine_evidence_chunk_id():
    chunk = _chunk("ract\nAnterior Corticospinal T", chunk_id="STUDENT_SUMMARY:s2.pdf:0106:0001")
    refined = refine_concept_inventory((chunk,))
    repaired = next(c for c in refined if c.concept == "Anterior Corticospinal Tract")
    assert repaired.evidence_chunk_id == "STUDENT_SUMMARY:s2.pdf:0106:0001"


def test_malformed_and_blank_heavy_evidence_does_not_crash_trailing_repair():
    chunk = _chunk("\n\n\n   \nCorpos Str\n\n\n")
    refine_concept_inventory((chunk,))  # must not raise


def test_no_llm_or_embedding_call_in_trailing_repair_functions():
    import inspect

    import exam_generator.planning.concept_anchor as concept_anchor_module

    source = inspect.getsource(concept_anchor_module._repair_trailing_truncations)
    source += inspect.getsource(concept_anchor_module._attempt_trailing_reconstruction)
    assert "generate_structured" not in source
    assert "embedding" not in source.lower()


# ---------------------------------------------------------------------------
# WP-043 Part A: anchoring span-fix for trailing-reconstructed concepts,
# and deterministic evidence-sufficiency + broader fallback
# ---------------------------------------------------------------------------


def test_source_line_indices_locate_a_trailing_reconstructed_concepts_true_span():
    # The exact real corpus shape: "Corpos Str" + "ia" + "tum" reconstructs
    # to "Corpos Striatum", which never appears verbatim as one raw line -
    # before WP-043, anchoring could not find it at all and silently fell
    # back to the bare name. source_line_indices lets it locate the real span.
    chunk = _chunk("מכילים מספר תתי מבנים \ntum\nia\nCorpos Str\n \nCaudate Nucleus")
    refined = refine_concept_inventory((chunk,))
    concept = next(c for c in refined if c.concept == "Corpos Striatum")
    assert concept.source_line_indices != ()

    focus = anchor_concept_evidence(
        chunk_text=chunk.text, concept=concept.concept, source_line_indices=concept.source_line_indices
    )
    assert focus != "Corpos Striatum"
    assert "מכילים מספר תתי מבנים" in focus
    assert "Caudate Nucleus" not in focus  # never crosses into a sibling concept


def test_without_source_line_indices_a_trailing_reconstructed_concept_anchors_bare():
    # Documents the exact WP-043 root-cause finding: omitting
    # source_line_indices reproduces the pre-fix bare-fallback behavior,
    # since no single raw line ever equals the reconstructed text verbatim.
    chunk = _chunk("מכילים מספר תתי מבנים \ntum\nia\nCorpos Str\n \nCaudate Nucleus")
    focus = anchor_concept_evidence(chunk_text=chunk.text, concept="Corpos Striatum")
    assert focus == "Corpos Striatum"


def test_is_factual_focus_sufficient_false_for_bare_concept():
    assert is_factual_focus_sufficient(factual_focus="Corpos Striatum", concept="Corpos Striatum") is False


def test_is_factual_focus_sufficient_true_with_any_real_context():
    assert (
        is_factual_focus_sufficient(factual_focus="something\nCorpos Striatum", concept="Corpos Striatum") is True
    )


def test_is_factual_focus_sufficient_normalizes_whitespace_and_case():
    assert is_factual_focus_sufficient(factual_focus="  corpos   striatum  ", concept="Corpos Striatum") is False


def test_real_corpus_isolated_concept_stays_insufficient_even_broad():
    # The exact real corpus shape for "Anterior Corticospinal Tract": its
    # own line is immediately bounded by two consecutive blank lines on
    # each side - a genuine paragraph boundary broadening must never
    # cross - so it honestly remains insufficient even with broad=True,
    # confirmed live during this WP's own investigation (WP-043
    # completion report).
    chunk = _chunk(
        "מסילות יורדות  :\n      \n \nract\nAnterior Corticospinal T\n                     \n          "
    )
    refined = refine_concept_inventory((chunk,))
    concept = next(c for c in refined if c.concept == "Anterior Corticospinal Tract")
    narrow = anchor_concept_evidence(
        chunk_text=chunk.text, concept=concept.concept, source_line_indices=concept.source_line_indices
    )
    assert is_factual_focus_sufficient(factual_focus=narrow, concept=concept.concept) is False
    broad = anchor_concept_evidence(
        chunk_text=chunk.text, concept=concept.concept, source_line_indices=concept.source_line_indices, broad=True
    )
    assert is_factual_focus_sufficient(factual_focus=broad, concept=concept.concept) is False


def test_broad_fallback_provides_richer_context_than_narrow_for_the_real_corpos_striatum_case():
    # Real corpus finding (see WP-043 completion report): once narrow
    # already finds some genuine context (via the source_line_indices
    # span-fix), broad's widened max_lines/raw-scan bounds provide
    # strictly more of it, still within the same paragraph boundary -
    # richer evidence for generation, even though it cannot and does not
    # need to flip the insufficient/sufficient determination itself.
    chunk = _chunk(
        ", אך מושג זה שגוי משום שגנגליה מתאר צבר גופי תאים במערכת\n"
        ".העצבים ההיקפית, בעוד גרעיני הבסיס הם חלק ממערכת העצבים המרכזית \n"
        " גרעיני הבסיס:מכילים מספר תתי מבנים \n\ntum\nia\nCorpos Str\n \no"
    )
    refined = refine_concept_inventory((chunk,))
    concept = next(c for c in refined if c.concept == "Corpos Striatum")
    narrow = anchor_concept_evidence(
        chunk_text=chunk.text, concept=concept.concept, source_line_indices=concept.source_line_indices
    )
    broad = anchor_concept_evidence(
        chunk_text=chunk.text, concept=concept.concept, source_line_indices=concept.source_line_indices, broad=True
    )
    assert is_factual_focus_sufficient(factual_focus=narrow, concept=concept.concept) is True
    assert len(broad) > len(narrow)
    assert narrow in broad or all(line in broad for line in narrow.splitlines())


def test_broad_fallback_can_never_flip_insufficient_to_sufficient_when_immediately_boundary_blocked():
    # Documents a real, deliberate design property (see WP-043 completion
    # report's own honest discussion): when the concept's immediate
    # neighbor in a direction is already a paragraph boundary (two
    # consecutive blanks) or a sibling concept line, narrow and broad
    # both stop at exactly the same point, since neither ever relaxes
    # those two rules - widening only affects how much is collected once
    # collection has already started, never whether it starts at all.
    chunk = _chunk("Header Line One\n\n\nIsolated Concept\n\n\nFooter Line One")
    narrow = anchor_concept_evidence(chunk_text=chunk.text, concept="Isolated Concept")
    broad = anchor_concept_evidence(chunk_text=chunk.text, concept="Isolated Concept", broad=True)
    assert narrow == broad == "Isolated Concept"


def test_broad_fallback_never_crosses_a_genuine_paragraph_boundary():
    # Two consecutive blank lines remain a hard stop even in broad mode -
    # broadening only widens how much may be collected within one
    # paragraph, never how far a real paragraph break may be crossed.
    chunk = _chunk("Unrelated Document Header\n\n\nConcept Name\n\n\nUnrelated Trailing Text")
    broad = anchor_concept_evidence(chunk_text=chunk.text, concept="Concept Name", broad=True)
    assert "Unrelated Document Header" not in broad
    assert "Unrelated Trailing Text" not in broad


def test_broad_fallback_still_stops_before_a_sibling_concept_line():
    chunk = _chunk("Some context line\nConcept Name\nSibling Concept Line Here")
    broad = anchor_concept_evidence(chunk_text=chunk.text, concept="Concept Name", broad=True)
    assert "Sibling Concept Line Here" not in broad


def test_genuinely_isolated_concept_remains_insufficient_even_after_broad_fallback():
    # No real content anywhere nearby - broad widening must never invent
    # or manufacture content; the honest result is still insufficient.
    chunk = _chunk("Header Line One\n\n\nIsolated Concept\n\n\nFooter Line One")
    focus = anchor_concept_evidence(chunk_text=chunk.text, concept="Isolated Concept", broad=True)
    assert is_factual_focus_sufficient(factual_focus=focus, concept="Isolated Concept") is False


# ---------------------------------------------------------------------------
# Enumeration-shaped evidence (WP-044 Part A)
# ---------------------------------------------------------------------------


def test_real_corpus_corpos_striatum_is_enumeration_insufficient():
    # WP-044 section 23 Test 1/3: the exact real corpus shape (WP-043's
    # own live pilot finding) - the anchored evidence is only ever the
    # shared "basal nuclei contain several sub-structures" intro plus a
    # bare bullet-marker fragment, never anything specific to Corpos
    # Striatum itself. This is exactly the case WP-044 section 11 says
    # must prefer "missing" over a known-ambiguous generic membership
    # question.
    chunk = _chunk(
        ", אך מושג זה שגוי משום שגנגליה מתאר צבר גופי תאים במערכת\n"
        ".העצבים ההיקפית, בעוד גרעיני הבסיס הם חלק ממערכת העצבים המרכזית \n"
        " גרעיני הבסיס:מכילים מספר תתי מבנים \n\ntum\nia\nCorpos Str\n \no"
    )
    refined = refine_concept_inventory((chunk,))
    concept = next(c for c in refined if c.concept == "Corpos Striatum")
    focus = anchor_concept_evidence(
        chunk_text=chunk.text, concept=concept.concept, source_line_indices=concept.source_line_indices
    )
    assert is_enumeration_evidence_insufficient(factual_focus=focus, concept=concept.concept) is True


def test_enumeration_with_unique_distinguishing_property_is_not_insufficient():
    # WP-044 section 23 Test 2: the same enumeration-intro shape, but this
    # member's own forward context carries a real, concept-specific
    # distinguishing fact - generation should remain possible.
    focus = (
        " גרעיני הבסיס:מכילים מספר תתי מבנים \n"
        "Corpos Striatum\n"
        "אחראי על תפקוד ייחודי ומובחן מבין תתי המבנים"
    )
    assert is_enumeration_evidence_insufficient(factual_focus=focus, concept="Corpos Striatum") is False
    assert detect_enumeration_member_shape(factual_focus=focus, concept="Corpos Striatum") is True


def test_no_enumeration_cue_is_never_flagged_insufficient_by_this_check():
    # A concept anchored to genuinely concept-specific prose (no shared
    # list-intro cue phrase at all) is not this function's concern - the
    # existing is_factual_focus_sufficient() already covers plain sparse
    # evidence; this check is narrowly about the enumeration shape only.
    focus = "X is characterized by a unique distinguishing property.\nConcept Name"
    assert is_enumeration_evidence_insufficient(factual_focus=focus, concept="Concept Name") is False
    assert detect_enumeration_member_shape(factual_focus=focus, concept="Concept Name") is False


def test_enumeration_cue_present_but_bare_concept_alone_is_insufficient():
    # No forward content whatsoever (concept is the very last line) -
    # still insufficient, the same "nothing distinguishing" shape.
    focus = "X contains several sub-structures:\nConcept Name"
    assert is_enumeration_evidence_insufficient(factual_focus=focus, concept="Concept Name") is True
    assert detect_enumeration_member_shape(factual_focus=focus, concept="Concept Name") is True


def test_enumeration_member_shape_true_even_when_insufficient():
    # detect_enumeration_member_shape() only reports shape, never
    # sufficiency - the planner is responsible for skipping an
    # insufficient concept before this would ever be surfaced on a real
    # QuestionTarget (see planning.planner), but the function itself must
    # not conflate the two questions.
    focus = "X contains several sub-structures:\nConcept Name\no"
    assert is_enumeration_evidence_insufficient(factual_focus=focus, concept="Concept Name") is True
    assert detect_enumeration_member_shape(factual_focus=focus, concept="Concept Name") is True


def test_enumeration_cue_far_from_concept_falls_outside_backward_context():
    # The cue phrase must actually appear within the anchored backward
    # context - a concept whose own anchoring never reached back far
    # enough to include the cue is correctly not flagged as enumeration-
    # shaped, since that anchored evidence genuinely does not contain it.
    focus = "Some unrelated nearby line\nConcept Name\nSome specific distinguishing fact"
    assert is_enumeration_evidence_insufficient(factual_focus=focus, concept="Concept Name") is False
    assert detect_enumeration_member_shape(factual_focus=focus, concept="Concept Name") is False


def test_english_enumeration_cue_phrases_are_also_detected():
    focus = "The vertebral column consists of the following segments:\nConcept Name"
    assert detect_enumeration_member_shape(factual_focus=focus, concept="Concept Name") is True


def test_no_llm_or_embedding_call_in_enumeration_functions():
    import inspect

    import exam_generator.planning.concept_anchor as concept_anchor_module

    source = inspect.getsource(concept_anchor_module.is_enumeration_evidence_insufficient) + inspect.getsource(
        concept_anchor_module.detect_enumeration_member_shape
    )
    assert "generate_structured" not in source
    assert "embedding" not in source.lower()
