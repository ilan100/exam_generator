"""WP-054 real end-to-end verification.

NOT production code. Uses the real, unmodified, now-permanent production
path (``QuestionGenerator``/``QuestionProducer``/all five real validators)
against the real OpenAI API, for the three targets WP-053's experiment
covered:

    Caudate Nucleus     - approved, expect IDENTITY_FIRST
    Nucleus Accumbens   - approved, expect IDENTITY_FIRST
    Globus Pallidus     - explicit exclusion, expect DEFAULT (unaffected)

Unlike WP-053's own experiment script, no separate experimental prompt
repository is constructed here - the strategy preference is now a
permanent part of the real ``PromptRepository.from_default_location()``
production path, resolved automatically by
``exam_generator.generation.strategy.resolve_strategy_preference()``
inside the real, unmodified ``QuestionGenerator``.

Targets are constructed directly (mirroring WP-053's own established
pattern), since coverage-based automatic planning is out of scope for this
verification. One fresh live pilot. No reruns.
"""

from __future__ import annotations

import json
from pathlib import Path

from exam_generator.config import load_app_config, load_llm_config
from exam_generator.generation.strategy import resolve_strategy_preference
from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.llm import build_llm_provider
from exam_generator.models import GenerationMode, GenerationStrategyPreference, QuestionTarget
from exam_generator.planning.concept_anchor import anchor_concept_evidence, refine_concept_inventory
from exam_generator.production.errors import QuestionAttemptsExhaustedError
from exam_generator.production.models import QuestionProductionResult
from exam_generator.production.producer import QuestionProducer
from exam_generator.generation.generator import QuestionGenerator
from exam_generator.prompts import PromptRepository
from exam_generator.retrieval import build_category_resolver, build_student_summary_retrieval_index, retrieve_for_category
from exam_generator.validation import CategoryValidator, GroundingValidator, MCQValidator, QualityValidator, TextbookValidator

CATEGORY = "גרעיני הבסיס"
TARGET_NAMES = ("Caudate Nucleus", "Nucleus Accumbens", "Globus Pallidus")
OUTPUT_PATH = Path("evaluation/live_outputs/wp054_verification_records.json")


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


def _attempt_record(attempt) -> dict:
    if attempt.is_generation_contract_failure:
        return {
            "attempt_number": attempt.attempt_number,
            "accepted": False,
            "generation_failure_type": attempt.generation_failure_type,
            "generation_failure_message": attempt.generation_failure_message,
        }
    v = attempt.validations
    return {
        "attempt_number": attempt.attempt_number,
        "accepted": attempt.accepted,
        "question": attempt.candidate.question,
        "answers": list(attempt.candidate.answers),
        "correct_answer_position": attempt.candidate.correct_answer,
        "correct_answer_text": attempt.candidate.answers[attempt.candidate.correct_answer - 1],
        "validations": {
            "grounding": {"passed": v.grounding.passed, "reason": v.grounding.reason},
            "mcq": {"valid": v.mcq.valid, "reason": v.mcq.reason},
            "category": {"valid": v.category.valid, "reason": v.category.reason},
            "quality": {"valid": v.quality.valid, "reason": v.quality.reason},
            "textbook": {"status": v.textbook.status.value},
        },
    }


def main() -> None:
    category_resolver = build_category_resolver()
    student_summary_index = build_student_summary_retrieval_index()
    historical_repository = HistoricalQuestionRepository.from_default_location()
    llm_provider = build_llm_provider(load_llm_config())
    max_attempts = load_app_config().generation.max_generation_attempts
    prompt_repository = PromptRepository.from_default_location()

    generator = QuestionGenerator(
        category_resolver=category_resolver,
        student_summary_index=student_summary_index,
        historical_repository=historical_repository,
        prompt_repository=prompt_repository,
        llm_provider=llm_provider,
    )
    producer = QuestionProducer(
        generator=generator,
        grounding_validator=GroundingValidator.from_default_configuration(),
        mcq_validator=MCQValidator.from_default_configuration(),
        category_validator=CategoryValidator.from_default_configuration(),
        quality_validator=QualityValidator.from_default_configuration(),
        textbook_validator=TextbookValidator.from_default_configuration(),
        max_attempts=max_attempts,
    )

    canonical_category = category_resolver.resolve(CATEGORY)
    retrieval_results = retrieve_for_category(canonical_category, category_resolver, student_summary_index)
    source_evidence = tuple(r.chunk for r in retrieval_results)
    chunk_text_by_id = {c.chunk_id: c.text for c in source_evidence}

    records = []
    for name in TARGET_NAMES:
        target = _build_target(
            canonical_category=canonical_category, concept_name=name,
            source_evidence=source_evidence, chunk_text_by_id=chunk_text_by_id,
        )
        resolved_strategy = resolve_strategy_preference(category=canonical_category, topic=target.topic)
        print(f"--- round start: target={name!r} resolved_strategy={resolved_strategy.value} ---", flush=True)
        try:
            result: QuestionProductionResult = producer.produce_question(
                category=canonical_category, generation_mode=GenerationMode.INDEPENDENT, target=target
            )
            record = {
                "target": name,
                "resolved_strategy": resolved_strategy.value,
                "accepted": True,
                "attempt_count": len(result.attempts),
                "attempts": [_attempt_record(a) for a in result.attempts],
            }
        except QuestionAttemptsExhaustedError as exc:
            record = {
                "target": name,
                "resolved_strategy": resolved_strategy.value,
                "accepted": False,
                "attempt_count": len(exc.attempts),
                "attempts": [_attempt_record(a) for a in exc.attempts],
            }
        print(
            f"--- round end: target={name!r} accepted={record['accepted']} attempts={record['attempt_count']} ---",
            flush=True,
        )
        records.append(record)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print(f"WP-054 VERIFICATION COMPLETE - wrote {len(records)} round(s) to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
