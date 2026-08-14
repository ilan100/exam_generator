"""WP-051 prototype-only signal probe.

NOT production code. Reuses the real, unmodified production functions
(retrieve_for_category, refine_concept_inventory, anchor_concept_evidence,
extract_relationship, is_enumeration_evidence_insufficient,
is_factual_focus_sufficient, keywords_for) against real retrieved
evidence for גרעיני הבסיס, plus a purely additive, read-only
full-evidence keyword-proximity scan (reusing the existing
_RELATIONSHIP_KEYWORDS vocabulary via keywords_for(), never a new
vocabulary), to test whether any candidate deterministic
evidence-sufficiency signal actually discriminates Globus Pallidus from
Caudate Nucleus / Nucleus Accumbens. Zero LLM calls, zero new production
logic, never imported by src/.
"""

from exam_generator.generation.relationship import (
    UNSPECIFIED_RELATIONSHIP_TYPE,
    _RELATIONSHIP_KEYWORDS,
    extract_relationship,
    keywords_for,
)
from exam_generator.models import QuestionTarget
from exam_generator.planning.concept_anchor import (
    anchor_concept_evidence,
    detect_enumeration_member_shape,
    is_enumeration_evidence_insufficient,
    is_factual_focus_sufficient,
    refine_concept_inventory,
)
from exam_generator.retrieval import build_category_resolver, build_student_summary_retrieval_index, retrieve_for_category

CATEGORY = "גרעיני הבסיס"
PRIMARY_TARGETS = {"Caudate Nucleus", "Nucleus Accumbens", "Globus Pallidus"}
_PROXIMITY_WINDOW_CHARS = 80

resolver = build_category_resolver()
index = build_student_summary_retrieval_index()
canonical = resolver.resolve(CATEGORY)
results = retrieve_for_category(canonical, resolver, index)
source_evidence = tuple(r.chunk for r in results)
chunk_text_by_id = {c.chunk_id: c.text for c in source_evidence}

inventory = refine_concept_inventory(source_evidence)


def full_evidence_keyword_proximity(concept: str) -> list[tuple[str, str]]:
    """Read-only: scan every retrieved chunk's FULL text (not just the
    concept's own narrow/broad anchor) for occurrences of `concept`
    (or any word thereof, min 4 chars, to tolerate PDF line-splitting)
    within _PROXIMITY_WINDOW_CHARS of a known relationship keyword.
    Reuses the existing keywords_for() vocabulary across all 10 families -
    no new keyword table. Returns [(relationship_type, snippet), ...].
    """
    hits: list[tuple[str, str]] = []
    concept_words = [w for w in concept.split() if len(w) >= 4]
    for chunk in source_evidence:
        text = chunk.text
        lowered = text.lower()
        for rel_type, keywords in _RELATIONSHIP_KEYWORDS:
            for kw in keywords:
                idx = 0
                lowered_kw = kw.lower()
                while True:
                    kpos = lowered.find(lowered_kw, idx)
                    if kpos == -1:
                        break
                    idx = kpos + 1
                    window_start = max(0, kpos - _PROXIMITY_WINDOW_CHARS)
                    window_end = min(len(text), kpos + len(kw) + _PROXIMITY_WINDOW_CHARS)
                    window = text[window_start:window_end]
                    lowered_window = window.lower()
                    for cw in concept_words:
                        if cw.lower() in lowered_window:
                            hits.append((rel_type, window.replace("\n", " ").strip()))
                            break
    return hits


for concept_item in inventory:
    if concept_item.concept not in PRIMARY_TARGETS:
        continue
    print(f"\n########## TARGET: {concept_item.concept} ##########")
    chunk_text = chunk_text_by_id[concept_item.evidence_chunk_id]

    narrow = anchor_concept_evidence(
        chunk_text=chunk_text, concept=concept_item.concept, source_line_indices=concept_item.source_line_indices
    )
    broad = anchor_concept_evidence(
        chunk_text=chunk_text, concept=concept_item.concept,
        source_line_indices=concept_item.source_line_indices, broad=True,
    )

    sig_E_narrow = is_factual_focus_sufficient(factual_focus=narrow, concept=concept_item.concept)
    sig_E_broad = is_factual_focus_sufficient(factual_focus=broad, concept=concept_item.concept)
    sig_A_narrow = not is_enumeration_evidence_insufficient(factual_focus=narrow, concept=concept_item.concept)
    sig_A_broad = not is_enumeration_evidence_insufficient(factual_focus=broad, concept=concept_item.concept)
    enum_shape_narrow = detect_enumeration_member_shape(factual_focus=narrow, concept=concept_item.concept)
    enum_shape_broad = detect_enumeration_member_shape(factual_focus=broad, concept=concept_item.concept)

    target_narrow = QuestionTarget(
        target_id=1, category=canonical, topic=concept_item.concept,
        factual_focus=narrow, supporting_evidence_chunk_ids=(concept_item.evidence_chunk_id,),
        named_entity_target=True,
    )
    rel_narrow = extract_relationship(target_narrow)
    target_broad = target_narrow.model_copy(update={"factual_focus": broad})
    rel_broad = extract_relationship(target_broad)

    print(f"narrow factual_focus: {narrow!r}")
    print(f"broad factual_focus:  {broad!r}")
    print(f"Signal E (narrow factual_focus 'sufficient'): {sig_E_narrow}")
    print(f"Signal E (broad factual_focus 'sufficient'):  {sig_E_broad}")
    print(f"Signal A (narrow: not enumeration-insufficient): {sig_A_narrow}")
    print(f"Signal A (broad: not enumeration-insufficient):  {sig_A_broad}")
    print(f"is_enumeration_member (narrow): {enum_shape_narrow}")
    print(f"is_enumeration_member (broad):  {enum_shape_broad}")
    print(f"Signal F (narrow relationship != UNSPECIFIED): {rel_narrow.relationship_type != UNSPECIFIED_RELATIONSHIP_TYPE} ({rel_narrow.relationship_type})")
    print(f"Signal F (broad relationship != UNSPECIFIED):  {rel_broad.relationship_type != UNSPECIFIED_RELATIONSHIP_TYPE} ({rel_broad.relationship_type})")

    hits = full_evidence_keyword_proximity(concept_item.concept)
    print(f"Full-evidence keyword-proximity hits (own concept name near any of the 10 existing relationship keywords, anywhere in full retrieved evidence): {len(hits)}")
    for rel_type, snippet in hits[:5]:
        print(f"   [{rel_type}] ...{snippet}...")
