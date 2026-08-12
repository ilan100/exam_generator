from exam_generator.planning.target_role import detect_source_evidence_role, extract_source_relationship_entity


def test_real_corpus_basillar_artery_is_detected_as_source_role():
    # The exact real corpus shape (WP-042's own diagnostic finding):
    # "Basillar artery" is immediately preceded by the Hebrew "source:"
    # label, since it is the labeled source value for a different,
    # separately-described artery (Superior Cerebellar Artery).
    chunk_text = "Superior cerebellar artery\no\n מקור :\nBasillar artery\no\n אזור אספקת דם :המשטח העליון"
    assert detect_source_evidence_role(chunk_text, "Basillar artery") is True


def test_real_corpus_superior_cerebellar_artery_is_not_detected_as_source_role():
    # The sibling entity in the same passage - the subject of its own
    # sentence, not a labeled source value - must not be misclassified.
    chunk_text = ":עורקים מספקים דם לצרבלום \n\nSuperior cerebellar artery\no\n מקור :\nBasillar artery"
    assert detect_source_evidence_role(chunk_text, "Superior cerebellar artery") is False


def test_cue_phrase_far_away_does_not_trigger_detection():
    # The window is small and local by design - a source label many
    # characters away must not be associated with an unrelated concept.
    far_prefix = "מקור :" + ("א" * 200)
    chunk_text = far_prefix + "\nUnrelated Concept"
    assert detect_source_evidence_role(chunk_text, "Unrelated Concept") is False


def test_missing_concept_returns_false_never_guesses():
    assert detect_source_evidence_role("some text without the concept", "Nonexistent Concept") is False


def test_concept_with_no_preceding_text_returns_false():
    assert detect_source_evidence_role("Concept At The Very Start", "Concept At The Very Start") is False


def test_unrelated_hebrew_prefix_without_the_cue_phrase_is_not_detected():
    chunk_text = "תיאור כללי של המבנה\nConcept Name"
    assert detect_source_evidence_role(chunk_text, "Concept Name") is False


def test_no_llm_or_embedding_call_in_target_role_module():
    import inspect

    import exam_generator.planning.target_role as target_role_module

    source = inspect.getsource(target_role_module.detect_source_evidence_role)
    assert "generate_structured" not in source
    assert "embedding" not in source.lower()
    assert "import" not in source  # no dynamic imports of an LLM/embedding client


# ---------------------------------------------------------------------------
# extract_source_relationship_entity (WP-044 Part B)
# ---------------------------------------------------------------------------


def test_real_corpus_basillar_artery_downstream_entity_is_identified():
    # The exact real corpus shape (WP-044's own investigation, re-verified
    # against the real corpus chunk): "Superior cerebellar artery" is the
    # nearest preceding candidate-concept heading line before the "מקור :"
    # cue and its "Basillar artery" value.
    chunk_text = "Superior cerebellar artery\no\n מקור :\nBasillar artery\no\n אזור אספקת דם :המשטח העליון"
    assert extract_source_relationship_entity(chunk_text, "Basillar artery") == "Superior cerebellar artery"


def test_missing_concept_returns_none_never_guesses():
    assert extract_source_relationship_entity("some text without the concept", "Nonexistent Concept") is None


def test_concept_with_no_preceding_candidate_line_returns_none():
    chunk_text = "תיאור כללי בלבד ללא כותרת מובנית\no\n מקור :\nBasillar artery"
    assert extract_source_relationship_entity(chunk_text, "Basillar artery") is None


def test_downstream_entity_beyond_the_bounded_scan_returns_none():
    # The downstream heading is genuinely too far away (more filler lines
    # than the bounded backward scan will ever inspect) - never guessed,
    # never extended past the fixed bound.
    filler = "\n".join(f"filler line {i}" for i in range(10))
    chunk_text = f"Real Heading\n{filler}\nBasillar artery"
    assert extract_source_relationship_entity(chunk_text, "Basillar artery") is None


def test_second_artery_in_same_passage_has_its_own_correct_downstream_entity():
    # WP-044 section 24's own second example: a different sibling in the
    # same passage, sharing the same "מקור :" shape but with its own,
    # different downstream heading immediately above it.
    chunk_text = (
        "Anterior Inferior Cerebellar Artery (AICA)\no\n מקור :\nBasillar Artery\no\n אזור אספקת דם :example"
    )
    assert extract_source_relationship_entity(chunk_text, "Basillar Artery") == (
        "Anterior Inferior Cerebellar Artery (AICA)"
    )


def test_no_llm_or_embedding_call_in_extract_source_relationship_entity():
    import inspect

    import exam_generator.planning.target_role as target_role_module

    source = inspect.getsource(target_role_module.extract_source_relationship_entity)
    assert "generate_structured" not in source
    assert "embedding" not in source.lower()
