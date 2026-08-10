from exam_generator.planning.concept_identity import (
    ConceptIdentity,
    build_concept_identity,
    concept_identities_for_inventory,
    concept_identity_matches_text,
)
from exam_generator.planning.concept_inventory import InventoryConcept


def _concept(text: str, *, chunk_id: str = "c1") -> InventoryConcept:
    return InventoryConcept(concept=text, evidence_chunk_id=chunk_id, factual_focus="x", extraction_reason="r")


# ---------------------------------------------------------------------------
# Normalization (WP-038 section 15 "Normalization")
# ---------------------------------------------------------------------------


def test_whitespace_normalization():
    identity = build_concept_identity(_concept("Superior   Cerebellar\tArtery"), chunk_text="")
    assert concept_identity_matches_text(identity, "Superior Cerebellar Artery")


def test_case_normalization():
    identity = build_concept_identity(_concept("Superior Cerebellar Artery"), chunk_text="")
    assert concept_identity_matches_text(identity, "superior cerebellar artery")
    assert concept_identity_matches_text(identity, "SUPERIOR CEREBELLAR ARTERY")


def test_punctuation_normalization():
    identity = build_concept_identity(
        _concept("Anterior Inferior Cerebellar Artery (AICA)"), chunk_text=""
    )
    assert concept_identity_matches_text(identity, "Anterior Inferior Cerebellar Artery AICA")


def test_unicode_nfkc_normalization():
    # U+FB01 LATIN SMALL LIGATURE FI decomposes under NFKC to "fi" - a
    # harmless compatibility-equivalence, never a semantic judgment.
    identity = build_concept_identity(_concept("ﬁber tract"), chunk_text="")
    assert concept_identity_matches_text(identity, "fiber tract")


def test_normalized_forms_are_deduplicated():
    identity = build_concept_identity(_concept("GPe"), chunk_text="")
    assert len(identity.normalized_forms) == len(set(identity.normalized_forms))


def test_unsupported_orthographic_variant_does_not_match():
    # A genuinely different spelling that is NOT a deterministic
    # normalization of the canonical form (e.g. a transliteration
    # variance) must not be treated as the same form - only whitespace/
    # case/punctuation/Unicode-compatibility differences are safe.
    identity = build_concept_identity(_concept("Spinothalamic Tract"), chunk_text="")
    assert not concept_identity_matches_text(identity, "Spinotalamic Tract")


# ---------------------------------------------------------------------------
# Identity (WP-038 section 15 "Identity")
# ---------------------------------------------------------------------------


def test_identical_concept_matches_itself():
    identity = build_concept_identity(_concept("Basilar artery"), chunk_text="")
    assert concept_identity_matches_text(identity, "Basilar artery")


def test_explicitly_paired_bilingual_form_is_recognized():
    # The WP-038 section 8 "Preferred Principle: Evidence-Derived
    # Identity" case: the source evidence itself explicitly pairs the
    # concept with a Hebrew form via adjacent parenthetical notation.
    chunk_text = "Superior cerebellar artery (עורק צרבלרי עליון)\nמקור: Basilar artery"
    identity = build_concept_identity(_concept("Superior cerebellar artery"), chunk_text=chunk_text)
    assert identity.explicitly_supported_language_forms == ("עורק צרבלרי עליון",)
    assert concept_identity_matches_text(identity, "עורק צרבלרי עליון")


def test_explicitly_paired_bilingual_form_reverse_order():
    chunk_text = "(עורק צרבלרי עליון) Superior cerebellar artery\nמקור: Basilar artery"
    identity = build_concept_identity(_concept("Superior cerebellar artery"), chunk_text=chunk_text)
    assert identity.explicitly_supported_language_forms == ("עורק צרבלרי עליון",)


def test_explicitly_paired_bilingual_form_on_adjacent_line():
    chunk_text = "Superior cerebellar artery\n(עורק צרבלרי עליון)\nמקור: Basilar artery"
    identity = build_concept_identity(_concept("Superior cerebellar artery"), chunk_text=chunk_text)
    assert identity.explicitly_supported_language_forms == ("עורק צרבלרי עליון",)


def test_unrelated_concepts_remain_separate():
    a = build_concept_identity(_concept("Basilar artery"), chunk_text="")
    b = build_concept_identity(_concept("Vertebral Artery"), chunk_text="")
    assert not concept_identity_matches_text(a, "Vertebral Artery")
    assert not concept_identity_matches_text(b, "Basilar artery")


def test_related_but_non_identical_concepts_remain_separate():
    a = build_concept_identity(_concept("Anterior Spinal Artery"), chunk_text="")
    b = build_concept_identity(_concept("Posterior Spinal Arteries"), chunk_text="")
    assert not concept_identity_matches_text(a, "Posterior Spinal Arteries")
    assert not concept_identity_matches_text(b, "Anterior Spinal Artery")


def test_ambiguous_form_is_never_extracted():
    # No explicit adjacent parenthetical Hebrew pairing exists here - the
    # Hebrew text is ordinary prose elsewhere in the chunk, the exact real
    # corpus shape found for "קורפוס סטריאטום" during WP-038's own
    # investigation (see the module docstring). Must not be guessed at.
    chunk_text = (
        "Corpus Striatum\no\nניתן לחלק את הקורפוס סטריאטום לתתי מבנים לפי חלוקות שונות"
    )
    identity = build_concept_identity(_concept("Corpus Striatum"), chunk_text=chunk_text)
    assert identity.explicitly_supported_language_forms == ()
    assert not concept_identity_matches_text(identity, "קורפוס סטריאטום")


def test_parenthetical_with_english_content_is_not_treated_as_a_language_form():
    chunk_text = "Anterior Inferior Cerebellar Artery (AICA)\nמקור: Basilar Artery"
    identity = build_concept_identity(_concept("Anterior Inferior Cerebellar Artery"), chunk_text=chunk_text)
    assert identity.explicitly_supported_language_forms == ()


# ---------------------------------------------------------------------------
# Coverage (WP-038 section 15 "Coverage")
# ---------------------------------------------------------------------------


def test_selected_concept_recognized_from_same_language_answer():
    identity = build_concept_identity(_concept("Spinothalamic Tract"), chunk_text="")
    assert concept_identity_matches_text(identity, "Spinothalamic Tract")


def test_selected_concept_recognized_from_supported_alternate_language_answer():
    chunk_text = "Spinothalamic Tract (מסילה ספינותלמית)\nמעבירה תחושות כאב"
    identity = build_concept_identity(_concept("Spinothalamic Tract"), chunk_text=chunk_text)
    assert concept_identity_matches_text(identity, "מסילה ספינותלמית")


def test_unsupported_alternate_representation_remains_unmatched():
    # The exact live WP-037 regression case: no evidence-derived pairing
    # exists for this concept in this corpus (verified directly against
    # the real retrieved evidence during WP-038's investigation), so the
    # Hebrew answer generation actually produced must honestly remain
    # unrecognized - never guessed at via transliteration.
    chunk_text = "3 \n:עורקים מספקים דם לצרבלום \n\nSuperior cerebellar artery\no\n מקור :"
    identity = build_concept_identity(_concept("Superior cerebellar artery"), chunk_text=chunk_text)
    assert identity.explicitly_supported_language_forms == ()
    assert not concept_identity_matches_text(identity, "עורק סופריור צרבלרי")


def test_semantically_related_but_different_concept_remains_unmatched():
    identity = build_concept_identity(_concept("Superior cerebellar artery"), chunk_text="")
    assert not concept_identity_matches_text(identity, "arterial supply of the cerebellum")


def test_concept_identities_for_inventory_builds_one_identity_per_concept():
    inventory = (
        _concept("Superior cerebellar artery", chunk_id="c1"),
        _concept("Basilar artery", chunk_id="c1"),
    )
    identities = concept_identities_for_inventory(
        inventory, chunk_text_by_id={"c1": "Superior cerebellar artery\nBasilar artery"}
    )
    assert set(identities) == {"Superior cerebellar artery", "Basilar artery"}
    assert all(isinstance(identity, ConceptIdentity) for identity in identities.values())


# ---------------------------------------------------------------------------
# Safety (WP-038 section 15 "Safety") - related concepts must never collapse
# ---------------------------------------------------------------------------


def test_structure_and_function_do_not_become_equivalent():
    structure = build_concept_identity(_concept("Corpus Striatum"), chunk_text="")
    assert not concept_identity_matches_text(
        structure, "להגביר תנועה על ידי הפעלת מסלולי תנועה"
    )  # "increase movement by activating movement pathways" - a function, not the structure


def test_source_and_destination_do_not_become_equivalent():
    source = build_concept_identity(_concept("Vertebral Artery"), chunk_text="")
    assert not concept_identity_matches_text(source, "משטח תחתון ואחורי של הצרבלום")  # a supplied area, not the source


def test_pathway_and_general_system_do_not_become_equivalent():
    pathway = build_concept_identity(_concept("Spinothalamic Tract"), chunk_text="")
    assert not concept_identity_matches_text(pathway, "מסילות עולות")  # the ascending-tract system generally


def test_two_concepts_sharing_a_naming_cue_context_still_do_not_collapse():
    # Even when a naming-cue phrase is present in the chunk (WP-037's own
    # self-restatement signal), it must not cause an unrelated later
    # concept's Hebrew description to be attributed to this concept.
    chunk_text = (
        "גרעיני הבסיס נקראים גם\nThe Basal Ganglia\n"
        "גרעיני הבסיס מכילים מספר תתי מבנים\n\nCaudate Nucleus\no\nגרעין הזנב"
    )
    identity = build_concept_identity(_concept("Caudate Nucleus"), chunk_text=chunk_text)
    assert identity.explicitly_supported_language_forms == ()
    assert not concept_identity_matches_text(identity, "גרעין הזנב")


# ---------------------------------------------------------------------------
# ConceptIdentity is an internal-only model - no public contract change
# ---------------------------------------------------------------------------


def test_concept_identity_model_is_frozen_and_forbids_extra_fields():
    identity = ConceptIdentity(canonical_form="X", normalized_forms=("x",))
    assert identity.model_config.get("frozen") is True
    assert identity.model_config.get("extra") == "forbid"
