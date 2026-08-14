"""WP-053 controlled experiment: identity-first generation.

NOT production code. Uses the real, unmodified QuestionProducer/
QuestionGenerator/all five real validators against the real OpenAI API,
for exactly two conditions:

  CONTROL: unmodified production prompt repository (byte-identical to
      prompts/generation/question.txt on disk).
  EXPERIMENTAL: the same production prompt text, with one small,
      isolated "IDENTITY-FIRST" instruction block appended in-memory
      only (never written to prompts/generation/question.txt) - built by
      constructing a new PromptTemplate and a new PromptRepository, per
      the existing, already-designed-for-this injection points
      (PromptRepository.__init__ takes an explicit templates mapping;
      QuestionGenerator takes an explicit prompt_repository).

The experimental repository is used ONLY for Caudate Nucleus/Nucleus
Accumbens rounds. Globus Pallidus always uses the unmodified control
repository - by construction, not by a runtime conditional - so it
cannot be contaminated by the experimental instruction.

Targets are constructed directly (mirroring the WP-050/051 probes'
established pattern) rather than via automatic coverage-based planning,
to test exactly the three named concepts this experiment concerns.

One fresh live pilot. No reruns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from exam_generator.config import load_app_config, load_llm_config
from exam_generator.generation.competitors import discover_competitors
from exam_generator.generation.errors import InvalidGeneratedOutputError
from exam_generator.generation.generator import QuestionGenerator
from exam_generator.generation.relationship import extract_relationship
from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.llm import build_llm_provider
from exam_generator.models import GenerationMode, QuestionTarget
from exam_generator.planning.concept_anchor import anchor_concept_evidence, refine_concept_inventory
from exam_generator.production.errors import QuestionAttemptsExhaustedError
from exam_generator.production.models import QuestionProductionResult
from exam_generator.production.producer import QuestionProducer
from exam_generator.prompts import PromptId, PromptRepository
from exam_generator.prompts.models import PromptTemplate
from exam_generator.retrieval import build_category_resolver, build_student_summary_retrieval_index, retrieve_for_category
from exam_generator.validation import CategoryValidator, GroundingValidator, MCQValidator, QualityValidator, TextbookValidator

CATEGORY = "גרעיני הבסיס"
EXPERIMENTAL_TARGETS = {"Caudate Nucleus", "Nucleus Accumbens"}
SAFETY_CONTROL_TARGET = "Globus Pallidus"
OUTPUT_PATH = Path("evaluation/live_outputs/wp053_experiment_records.json")

_EXPERIMENTAL_INSTRUCTION_BLOCK = (
    "\n\n--- EXPERIMENTAL INSTRUCTION (WP-053, IDENTITY-FIRST, PROTOTYPE-ONLY - "
    "NOT PART OF THE PERMANENT PROMPT) ---\n"
    "For this generation attempt, prefer constructing the question so that the "
    "correct answer is determined by TARGET CONCEPT's own identity/name (for "
    "example, \"which of the following is TARGET CONCEPT\" or an equivalent "
    "identity-establishing phrasing), rather than by a distinguishing "
    "functional, locational, or classificatory property. Only fall back to a "
    "property-based question if an identity-based question genuinely cannot "
    "be constructed from the supplied evidence at all. This does not relax, "
    "replace, or override any other requirement stated above.\n"
    "--- END EXPERIMENTAL INSTRUCTION ---\n"
)


def _build_experimental_prompt_repository(control: PromptRepository) -> PromptRepository:
    original = control.get(PromptId.QUESTION_GENERATION)
    experimental_text = original.text + _EXPERIMENTAL_INSTRUCTION_BLOCK
    experimental_template = PromptTemplate(
        prompt_id=PromptId.QUESTION_GENERATION,
        text=experimental_text,
        required_variables=original.required_variables,
        version="WP-053-EXPERIMENTAL-IDENTITY-FIRST",
    )
    templates = {prompt_id: control.get(prompt_id) for prompt_id in control.prompt_ids}
    templates[PromptId.QUESTION_GENERATION] = experimental_template
    return PromptRepository(templates)


def _build_producer(*, prompt_repository: PromptRepository, category_resolver, student_summary_index, historical_repository, llm_provider, max_attempts) -> QuestionProducer:
    generator = QuestionGenerator(
        category_resolver=category_resolver,
        student_summary_index=student_summary_index,
        historical_repository=historical_repository,
        prompt_repository=prompt_repository,
        llm_provider=llm_provider,
    )
    return QuestionProducer(
        generator=generator,
        grounding_validator=GroundingValidator.from_default_configuration(),
        mcq_validator=MCQValidator.from_default_configuration(),
        category_validator=CategoryValidator.from_default_configuration(),
        quality_validator=QualityValidator.from_default_configuration(),
        textbook_validator=TextbookValidator.from_default_configuration(),
        max_attempts=max_attempts,
    )


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


def _run_round(*, producer: QuestionProducer, category: str, target: QuestionTarget, condition: str) -> dict:
    print(f"--- round start: target={target.topic!r} condition={condition} ---", flush=True)
    try:
        result: QuestionProductionResult = producer.produce_question(
            category=category, generation_mode=GenerationMode.INDEPENDENT, target=target
        )
        record = {
            "target": target.topic,
            "condition": condition,
            "accepted": True,
            "attempt_count": len(result.attempts),
            "attempts": [_attempt_record(a) for a in result.attempts],
        }
    except QuestionAttemptsExhaustedError as exc:
        record = {
            "target": target.topic,
            "condition": condition,
            "accepted": False,
            "attempt_count": len(exc.attempts),
            "attempts": [_attempt_record(a) for a in exc.attempts],
        }
    print(f"--- round end: target={target.topic!r} condition={condition} accepted={record['accepted']} attempts={record['attempt_count']} ---", flush=True)
    return record


def main() -> None:
    category_resolver = build_category_resolver()
    student_summary_index = build_student_summary_retrieval_index()
    historical_repository = HistoricalQuestionRepository.from_default_location()
    llm_provider = build_llm_provider(load_llm_config())
    max_attempts = load_app_config().generation.max_generation_attempts

    control_prompt_repository = PromptRepository.from_default_location()
    experimental_prompt_repository = _build_experimental_prompt_repository(control_prompt_repository)

    control_producer = _build_producer(
        prompt_repository=control_prompt_repository, category_resolver=category_resolver,
        student_summary_index=student_summary_index, historical_repository=historical_repository,
        llm_provider=llm_provider, max_attempts=max_attempts,
    )
    experimental_producer = _build_producer(
        prompt_repository=experimental_prompt_repository, category_resolver=category_resolver,
        student_summary_index=student_summary_index, historical_repository=historical_repository,
        llm_provider=llm_provider, max_attempts=max_attempts,
    )

    canonical_category = category_resolver.resolve(CATEGORY)
    retrieval_results = retrieve_for_category(canonical_category, category_resolver, student_summary_index)
    source_evidence = tuple(r.chunk for r in retrieval_results)
    chunk_text_by_id = {c.chunk_id: c.text for c in source_evidence}

    targets = {
        name: _build_target(
            canonical_category=canonical_category, concept_name=name,
            source_evidence=source_evidence, chunk_text_by_id=chunk_text_by_id,
        )
        for name in ("Caudate Nucleus", "Nucleus Accumbens", "Globus Pallidus")
    }

    records = []
    # Experimental condition - Caudate Nucleus, Nucleus Accumbens only.
    records.append(_run_round(producer=experimental_producer, category=canonical_category, target=targets["Caudate Nucleus"], condition="EXPERIMENTAL"))
    records.append(_run_round(producer=experimental_producer, category=canonical_category, target=targets["Nucleus Accumbens"], condition="EXPERIMENTAL"))
    # Current control condition - same two targets, unmodified prompt.
    records.append(_run_round(producer=control_producer, category=canonical_category, target=targets["Caudate Nucleus"], condition="CURRENT_CONTROL"))
    records.append(_run_round(producer=control_producer, category=canonical_category, target=targets["Nucleus Accumbens"], condition="CURRENT_CONTROL"))
    # Safety/control target - Globus Pallidus, always unmodified prompt.
    records.append(_run_round(producer=control_producer, category=canonical_category, target=targets["Globus Pallidus"], condition="CURRENT_CONTROL"))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print(f"WP-053 EXPERIMENT COMPLETE - wrote {len(records)} round(s) to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
