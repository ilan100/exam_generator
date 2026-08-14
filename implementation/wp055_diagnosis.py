"""WP-055 diagnostic reconstruction for the Globus Pallidus classification-
ambiguity investigation.

NOT production code. Prototype-only, offline-first, imported by nothing in
``src/``. Makes NO LLM/API calls - it only:

  1. Deterministically reconstructs the exact retrieval evidence and
     QuestionTarget the WP-054 live verification used for Globus Pallidus
     (retrieval is deterministic TF-IDF; target construction is the same
     deterministic `refine_concept_inventory()`/`anchor_concept_evidence()`
     pipeline `wp054_verification.py` already used) - so the real evidence
     text behind the three recorded WP-054 failures can be inspected
     without spending a new API call.
  2. Deterministically recomputes `extract_relationship()` and
     `discover_competitors()` for that exact target/evidence - again, no
     LLM call, these are pure application logic.
  3. Deterministically re-runs the existing, unmodified
     `_validate_target_answer_identity()` pre-validator check
     (`generation/generator.py`, WP-047) against a synthetic response
     carrying the exact historical WP-045-round-3 accepted answer text, to
     prove (not merely assert) whether that previously-successful
     property-based answer shape would be accepted or rejected under the
     current, unmodified architecture.
  4. Greps the reconstructed evidence text for the specific distinguishing
     facts WP-050/WP-053 each separately reported finding for Globus
     Pallidus, to confirm (or refute) that they are still reachable in the
     evidence generation actually receives today.

Everything else in this WP's completion report (the three recorded WP-054
attempts, the historical WP-045/046/049 Globus Pallidus rounds, the
grounding-validator reasons) comes directly from already-recorded JSON
under `evaluation/live_outputs/` - no new generation or validation call of
any kind was made for this diagnostic.
"""

from __future__ import annotations

import json

from exam_generator.generation.competitors import discover_competitors
from exam_generator.generation.generator import _validate_target_answer_identity
from exam_generator.generation.relationship import extract_relationship
from exam_generator.models import DistractorArchetype, DistractorDesign, GeneratedQuestionResponse, QuestionBlueprint, QuestionDifficulty, QuestionTarget
from exam_generator.planning.concept_anchor import anchor_concept_evidence, refine_concept_inventory
from exam_generator.retrieval import build_category_resolver, build_student_summary_retrieval_index, retrieve_for_category

CATEGORY = "גרעיני הבסיס"
TARGET_TOPIC = "Globus Pallidus"

# The exact accepted correct-answer text from the WP-045 pilot's own round 3
# (evaluation/live_outputs/wp045_pilot_records.json, round 3, attempt 2) -
# a genuine, evidence-supported functional/property description, accepted
# under the pre-WP-047 architecture.
HISTORICAL_PROPERTY_ANSWER_TEXT = "מדכא את התלמוס ומפחית תנועה"


def _build_target(*, canonical_category: str, concept_name: str, source_evidence, chunk_text_by_id) -> QuestionTarget:
    inventory = refine_concept_inventory(source_evidence)
    concept_item = next(c for c in inventory if c.concept == concept_name)
    chunk_text = chunk_text_by_id[concept_item.evidence_chunk_id]
    factual_focus = anchor_concept_evidence(
        chunk_text=chunk_text, concept=concept_item.concept, source_line_indices=concept_item.source_line_indices
    )
    return QuestionTarget(
        target_id=1,
        category=canonical_category,
        topic=concept_item.concept,
        factual_focus=factual_focus,
        supporting_evidence_chunk_ids=(concept_item.evidence_chunk_id,),
        named_entity_target=True,
    )


def _blueprint() -> QuestionBlueprint:
    distractor = DistractorDesign(
        archetype=DistractorArchetype.SIBLING_STRUCTURE,
        plausibility_reason="diagnostic-only synthetic distractor",
        incorrectness_reason="diagnostic-only synthetic distractor",
        evidence_checked=True,
    )
    return QuestionBlueprint(
        knowledge_target="diagnostic-only",
        tested_relationship="diagnostic-only",
        question_style="diagnostic-only",
        intended_difficulty=QuestionDifficulty.MEDIUM,
        correct_answer_role="diagnostic-only",
        distractors=[distractor, distractor, distractor],
    )


def main() -> None:
    category_resolver = build_category_resolver()
    student_summary_index = build_student_summary_retrieval_index()
    canonical_category = category_resolver.resolve(CATEGORY)

    retrieval_results = retrieve_for_category(canonical_category, category_resolver, student_summary_index)
    source_evidence = tuple(r.chunk for r in retrieval_results)
    chunk_text_by_id = {c.chunk_id: c.text for c in source_evidence}

    print("=" * 80)
    print(f"RETRIEVAL: {len(source_evidence)} chunks for category {canonical_category!r}")
    print("=" * 80)
    for chunk in source_evidence:
        print(f"\n--- chunk_id={chunk.chunk_id} source={chunk.source_file} page={chunk.page} ---")
        print(chunk.text)

    target = _build_target(
        canonical_category=canonical_category, concept_name=TARGET_TOPIC,
        source_evidence=source_evidence, chunk_text_by_id=chunk_text_by_id,
    )
    relationship = extract_relationship(target)
    competitors = discover_competitors(target=target, relationship=relationship, source_evidence=source_evidence)

    print("\n" + "=" * 80)
    print("RECONSTRUCTED GLOBUS PALLIDUS TARGET")
    print("=" * 80)
    print("topic:", target.topic)
    print("factual_focus:", repr(target.factual_focus))
    print("supporting_evidence_chunk_ids:", target.supporting_evidence_chunk_ids)
    print("relationship_type:", relationship.relationship_type)
    print("competitors:", [(c.concept, c.relationship_relevance) for c in competitors])

    print("\n" + "=" * 80)
    print("EVIDENCE-TEXT SEARCH FOR PREVIOUSLY-REPORTED DISTINGUISHING FACTS")
    print("=" * 80)
    full_evidence_text = "\n\n".join(c.text for c in source_evidence)
    for needle, source in [
        ("תלמוס", "WP-050: thalamus-suppression property (GPi)"),
        ("מדכא", "WP-045 accepted answer: suppresses ('מדכא')"),
        ("ממוקם", "WP-053: location-based property ('ממוקם')"),
    ]:
        present = needle in full_evidence_text
        print(f"  {source}: substring {needle!r} present in full retrieved evidence = {present}")

    print("\n" + "=" * 80)
    print("DETERMINISTIC PRE-VALIDATOR CHECK: would the WP-045 historical")
    print("property-only answer now be rejected by WP-047's")
    print("_validate_target_answer_identity()? (no LLM call - pure function)")
    print("=" * 80)
    synthetic_response = GeneratedQuestionResponse(
        blueprint=_blueprint(),
        question="diagnostic-only synthetic question",
        answers=[HISTORICAL_PROPERTY_ANSWER_TEXT, "b", "c", "d"],
        correct_answer=1,
        evidence_refs=[],
        historical_reference_id=None,
    )
    try:
        _validate_target_answer_identity(synthetic_response, target=target)
        print(f"  RESULT: ACCEPTED - {HISTORICAL_PROPERTY_ANSWER_TEXT!r} passes the identity check")
    except Exception as exc:  # noqa: BLE001 - diagnostic-only, want to see any exception
        print(f"  RESULT: REJECTED - {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
