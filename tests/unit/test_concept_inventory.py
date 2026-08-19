from exam_generator.models import CategoryCoverage, SourceEvidenceChunk, SourceType
from exam_generator.planning.concept_inventory import (
    PILOT_CATEGORIES,
    InventoryConcept,
    extract_concept_inventory,
    normalize_concept_text,
)
from exam_generator.planning.planner import _select_remaining_concepts

CATEGORY = "אספקת דם"


def _chunk(text: str, *, chunk_id: str = "STUDENT_SUMMARY:s1.pdf:0001:0001") -> SourceEvidenceChunk:
    return SourceEvidenceChunk(
        chunk_id=chunk_id, source_type=SourceType.STUDENT_SUMMARY, source_file="s1.pdf", page=1, text=text
    )


# ---------------------------------------------------------------------------
# Inventory extraction (WP-036 section 3/9)
# ---------------------------------------------------------------------------


def test_extracts_a_clean_capitalized_english_line():
    # Mirrors the real corpus's own line-splitting shape (WP-035/036):
    # a Hebrew label on its own line, the English concept name on the
    # next - never merged onto a single mixed-language line, since a
    # mixed line is exactly the shape most often corrupted by the source
    # PDFs' bidi text extraction (see the module's own documented
    # rationale for requiring a pure-ASCII line).
    chunk = _chunk("אספקת הדם:\nSuperior Cerebellar Artery\nמקור:\nBasilar Artery")
    inventory = extract_concept_inventory((chunk,))
    concepts = [c.concept for c in inventory]
    assert "Superior Cerebellar Artery" in concepts
    assert "Basilar Artery" in concepts


def test_extraction_is_deterministic():
    chunk = _chunk("Superior Cerebellar Artery\nAnterior Inferior Cerebellar Artery")
    assert extract_concept_inventory((chunk,)) == extract_concept_inventory((chunk,))


def test_concept_records_its_genuine_source_chunk_id():
    chunk = _chunk("Superior Cerebellar Artery", chunk_id="STUDENT_SUMMARY:s2.pdf:0099:0001")
    inventory = extract_concept_inventory((chunk,))
    assert inventory[0].evidence_chunk_id == "STUDENT_SUMMARY:s2.pdf:0099:0001"


def test_first_occurrence_order_is_preserved_across_chunks():
    chunk1 = _chunk("Superior Cerebellar Artery", chunk_id="c1")
    chunk2 = _chunk("Basilar Artery", chunk_id="c2")
    inventory = extract_concept_inventory((chunk1, chunk2))
    assert [c.concept for c in inventory] == ["Superior Cerebellar Artery", "Basilar Artery"]


# ---------------------------------------------------------------------------
# Malformed / noisy evidence (section 9)
# ---------------------------------------------------------------------------


def test_pure_hebrew_prose_contributes_nothing():
    chunk = _chunk("זהו טקסט עברי רגיל ללא שום מבנה או מונחים באנגלית כלל.")
    assert extract_concept_inventory((chunk,)) == ()


def test_single_stray_letters_are_not_extracted():
    # A PDF line-wrap artifact leaving one capital letter alone on a line
    # must not be treated as a concept (see the module's own documented
    # rationale for _MIN_ALPHA_CHARS).
    chunk = _chunk("A\nM\nP\nSuperior Cerebellar Artery")
    concepts = [c.concept for c in extract_concept_inventory((chunk,))]
    assert "A" not in concepts
    assert "M" not in concepts
    assert "P" not in concepts
    assert "Superior Cerebellar Artery" in concepts


def test_pure_digit_lines_are_not_extracted():
    chunk = _chunk("9\n11\nSuperior Cerebellar Artery")
    concepts = [c.concept for c in extract_concept_inventory((chunk,))]
    assert "9" not in concepts
    assert "11" not in concepts


def test_overly_long_ascii_lines_are_not_extracted():
    long_line = "This Is A Very Long Line That Should Not Be Treated As A Concept Name At All"
    chunk = _chunk(f"{long_line}\nSuperior Cerebellar Artery")
    concepts = [c.concept for c in extract_concept_inventory((chunk,))]
    assert long_line not in concepts
    assert "Superior Cerebellar Artery" in concepts


def test_short_uppercase_abbreviations_are_still_extracted():
    # Real corpus abbreviations (MCA, ACA, VL, LD) must survive despite
    # being short - only single letters are excluded, not short acronyms.
    chunk = _chunk("MCA\nACA\nVL")
    concepts = [c.concept for c in extract_concept_inventory((chunk,))]
    assert concepts == ["MCA", "ACA", "VL"]


def test_no_evidence_yields_empty_inventory():
    assert extract_concept_inventory(()) == ()


# ---------------------------------------------------------------------------
# Inventory filtering: deduplication (section 9 "inventory filtering")
# ---------------------------------------------------------------------------


def test_the_same_concept_repeated_across_chunks_is_extracted_once():
    chunk1 = _chunk("Superior Cerebellar Artery", chunk_id="c1")
    chunk2 = _chunk("Superior Cerebellar Artery", chunk_id="c2")
    inventory = extract_concept_inventory((chunk1, chunk2))
    assert len(inventory) == 1
    assert inventory[0].evidence_chunk_id == "c1"  # first occurrence wins


def test_deduplication_is_case_and_whitespace_insensitive():
    chunk = _chunk("Superior Cerebellar Artery\nsuperior   cerebellar artery")
    inventory = extract_concept_inventory((chunk,))
    assert len(inventory) == 1


def test_normalize_concept_text_matches_established_normalization_shape():
    assert normalize_concept_text("  Superior   Cerebellar Artery  ") == normalize_concept_text(
        "superior cerebellar artery"
    )


# ---------------------------------------------------------------------------
# Coverage filtering (WP-034 reuse, exact match only - section 6/9)
# ---------------------------------------------------------------------------


def _concept(text: str, *, chunk_id: str = "c1") -> InventoryConcept:
    return InventoryConcept(concept=text, evidence_chunk_id=chunk_id, factual_focus=text, extraction_reason="test")


def test_tested_concepts_are_excluded_by_exact_match():
    inventory = (_concept("Superior Cerebellar Artery"), _concept("Basilar Artery"))
    coverage = CategoryCoverage(tested_concepts=("Superior Cerebellar Artery",))
    remaining = _select_remaining_concepts(inventory, coverage=coverage, count=2, chunk_text_by_id={})
    assert [c.concept for c in remaining] == ["Basilar Artery"]


def test_coverage_exclusion_is_case_and_whitespace_insensitive():
    inventory = (_concept("Superior Cerebellar Artery"),)
    coverage = CategoryCoverage(tested_concepts=("superior   cerebellar artery",))
    remaining = _select_remaining_concepts(inventory, coverage=coverage, count=1, chunk_text_by_id={})
    assert remaining == []


def test_no_synonym_matching_a_differently_worded_tested_concept_is_not_excluded():
    # WP-036 section 6: exact matching only - "SCA" is not recognized as
    # the same concept as "Superior Cerebellar Artery" even though a
    # human would know they refer to the same thing.
    inventory = (_concept("SCA"),)
    coverage = CategoryCoverage(tested_concepts=("Superior Cerebellar Artery",))
    remaining = _select_remaining_concepts(inventory, coverage=coverage, count=1, chunk_text_by_id={})
    assert [c.concept for c in remaining] == ["SCA"]


def test_selection_respects_count():
    inventory = (_concept("A1"), _concept("A2"), _concept("A3"))
    remaining = _select_remaining_concepts(inventory, coverage=CategoryCoverage(), count=2, chunk_text_by_id={})
    assert [c.concept for c in remaining] == ["A1", "A2"]


def test_selection_returns_empty_when_inventory_is_fully_tested():
    inventory = (_concept("Superior Cerebellar Artery"),)
    coverage = CategoryCoverage(tested_concepts=("Superior Cerebellar Artery",))
    remaining = _select_remaining_concepts(inventory, coverage=coverage, count=1, chunk_text_by_id={})
    assert remaining == []


# ---------------------------------------------------------------------------
# Pilot category set
# ---------------------------------------------------------------------------


def test_pilot_categories_are_exactly_four():
    # WP-063 added המערכת הלימבית as the first single-category post-WP-060
    # pilot, alongside the original three WP-036 pilot categories.
    assert PILOT_CATEGORIES == {"אספקת דם", "מסילות עצביות", "גרעיני הבסיס", "המערכת הלימבית"}


def test_no_llm_or_embedding_call_in_concept_inventory_module():
    import inspect

    import exam_generator.planning.concept_inventory as concept_inventory_module

    source = inspect.getsource(concept_inventory_module)
    assert "generate_structured" not in source
    assert "vector" not in source.lower()
