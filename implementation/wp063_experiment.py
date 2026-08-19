"""WP-063 controlled generation experiment: first single-category
post-WP-060 deterministic target-planning pilot.

NOT production code. Uses the real, unmodified CategoryQuestionSetService/
QuestionTargetPlanner/QuestionProducer/all five real validators against the
real OpenAI API, for exactly two conditions on the same category
(``המערכת הלימבית``, selected in ``implementation/WP-063_CATEGORY_SELECTION.md``):

  BASELINE: QuestionTargetPlanner constructed with the pre-WP-063
      pilot_categories set (explicitly excludes המערכת הלימבית) - the
      unmodified LLM-based free-text target-planning path, exactly as it
      behaved for this category before this WP.
  PILOT: QuestionTargetPlanner constructed with no override - the real,
      now-updated production PILOT_CATEGORIES default (includes
      המערכת הלימבית) - the new zero-LLM-call deterministic
      concept-inventory target-planning path.

The principal independent variable is exactly the target-planning
mechanism (WP-063 section 16) - category, source corpus, generation
configuration, validation configuration, and question count are held
constant across both conditions. Each condition runs 4 sequential
CategoryQuestionSetService.generate_next() calls (mirroring WP-036's own
"four sequential questions per pilot category" evaluation shape,
implementation/WP-036_COMPLETION_REPORT.md), each call's
existing_questions accumulating the previously-accepted questions from
that same condition so category-coverage-based diversity behaves exactly
as it would in real production use.

Retrieval, generation, validation, and output are never bypassed. No
manual repair of any generated question. No prompt modification of any
kind during the experiment (WP-063 section 23).

One fresh live pilot. No reruns.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from exam_generator.category_generation.models import CategoryQuestionSetRequest
from exam_generator.category_generation.service import CategoryQuestionSetService
from exam_generator.config import load_app_config, load_llm_config
from exam_generator.llm import LLMMessage, LLMProfile, LLMProvider, build_llm_provider
from exam_generator.models import ExamQuestion, GenerationMode
from exam_generator.planning import QuestionTargetPlanner
from exam_generator.production import QuestionProducer
from exam_generator.prompts import PromptRepository
from exam_generator.retrieval import build_category_resolver, build_student_summary_retrieval_index

CATEGORY = "המערכת הלימבית"
PRE_WP063_PILOT_CATEGORIES = frozenset({"אספקת דם", "מסילות עצביות", "גרעיני הבסיס"})
QUESTIONS_PER_CONDITION = 4
OUTPUT_PATH = Path("evaluation/live_outputs/wp063_experiment_records.json")


class _CountingLLMProvider(LLMProvider):
    """Thin, transparent wrapper around a real LLMProvider that counts
    every ``generate_structured`` call, broken down by profile - the only
    change from the wrapped provider's own real behavior. Never alters,
    caches, or short-circuits any call."""

    def __init__(self, wrapped: LLMProvider) -> None:
        self._wrapped = wrapped
        self.call_count = 0
        self.calls_by_profile: dict[str, int] = {}

    @property
    def provider_name(self) -> str:
        return self._wrapped.provider_name

    @property
    def model_name(self) -> str:
        return self._wrapped.model_name

    def generate_structured(self, *, messages: Sequence[LLMMessage], response_model, profile: LLMProfile):
        self.call_count += 1
        self.calls_by_profile[profile.value] = self.calls_by_profile.get(profile.value, 0) + 1
        return self._wrapped.generate_structured(messages=messages, response_model=response_model, profile=profile)


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
        "category": attempt.candidate.category,
        "validations": {
            "grounding": {"passed": v.grounding.passed, "reason": v.grounding.reason},
            "mcq": {"valid": v.mcq.valid, "reason": v.mcq.reason},
            "category": {"valid": v.category.valid, "reason": v.category.reason},
            "quality": {"valid": v.quality.valid, "reason": v.quality.reason},
            "textbook": {"status": v.textbook.status.value},
        },
    }


def _run_condition(*, service: CategoryQuestionSetService, target_planner: QuestionTargetPlanner, condition: str) -> list[dict]:
    records: list[dict] = []
    existing_questions: tuple[ExamQuestion, ...] = ()
    for round_number in range(1, QUESTIONS_PER_CONDITION + 1):
        print(f"--- {condition} round {round_number} start ---", flush=True)
        history_before = len(target_planner.plan_history)
        response = service.generate_next(
            CategoryQuestionSetRequest(
                category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, existing_questions=existing_questions
            )
        )
        planned_targets = []
        if len(target_planner.plan_history) > history_before:
            _, targets = target_planner.plan_history[-1]
            planned_targets = [
                {
                    "topic": t.topic,
                    "factual_focus": t.factual_focus,
                    "named_entity_target": t.named_entity_target,
                    "supporting_evidence_chunk_ids": list(t.supporting_evidence_chunk_ids),
                    "is_source_role": t.is_source_role,
                    "is_enumeration_member": t.is_enumeration_member,
                }
                for t in targets
            ]
        record = {
            "condition": condition,
            "round": round_number,
            "planned_targets": planned_targets,
            "accepted": response.accepted,
            "attempts": response.attempts,
            "duplicate_replacement_attempts": response.duplicate_replacement_attempts,
        }
        if response.accepted:
            record["question"] = response.question.question
            record["answers"] = [response.question.answer1, response.question.answer2, response.question.answer3, response.question.answer4]
            record["correct_answer_position"] = response.question.correct_answer
            record["production_attempts"] = [_attempt_record(a) for a in response.production.attempts]
            existing_questions = existing_questions + (response.question,)
        else:
            record["failure_type"] = response.failure_type
            record["failure_message"] = response.failure_message
            record["failure_attempts"] = [_attempt_record(a) for a in response.failure_attempts]
        print(
            f"--- {condition} round {round_number} end: accepted={response.accepted} "
            f"attempts={response.attempts} targets={[t['topic'] for t in planned_targets]} ---",
            flush=True,
        )
        records.append(record)
    return records


def main() -> None:
    category_resolver = build_category_resolver()
    max_duplicate_replacement_attempts = load_app_config().generation.max_duplicate_replacement_attempts
    max_generation_attempts = load_app_config().generation.max_generation_attempts

    student_summary_index = build_student_summary_retrieval_index()
    prompt_repository = PromptRepository.from_default_location()

    baseline_llm_provider = _CountingLLMProvider(build_llm_provider(load_llm_config()))
    pilot_llm_provider = _CountingLLMProvider(build_llm_provider(load_llm_config()))

    baseline_target_planner = QuestionTargetPlanner(
        category_resolver=build_category_resolver(),
        student_summary_index=student_summary_index,
        prompt_repository=prompt_repository,
        llm_provider=baseline_llm_provider,
        pilot_categories=PRE_WP063_PILOT_CATEGORIES,
    )
    pilot_target_planner = QuestionTargetPlanner(
        category_resolver=build_category_resolver(),
        student_summary_index=student_summary_index,
        prompt_repository=prompt_repository,
        llm_provider=pilot_llm_provider,
    )

    baseline_producer = QuestionProducer.from_default_configuration()
    pilot_producer = QuestionProducer.from_default_configuration()

    baseline_service = CategoryQuestionSetService(
        category_resolver=category_resolver,
        target_planner=baseline_target_planner,
        producer=baseline_producer,
        max_duplicate_replacement_attempts=max_duplicate_replacement_attempts,
    )
    pilot_service = CategoryQuestionSetService(
        category_resolver=category_resolver,
        target_planner=pilot_target_planner,
        producer=pilot_producer,
        max_duplicate_replacement_attempts=max_duplicate_replacement_attempts,
    )

    all_records: list[dict] = []
    all_records += _run_condition(service=baseline_service, target_planner=baseline_target_planner, condition="BASELINE_LLM_PLANNING")
    all_records += _run_condition(service=pilot_service, target_planner=pilot_target_planner, condition="PILOT_DETERMINISTIC_PLANNING")

    output = {
        "category": CATEGORY,
        "questions_per_condition": QUESTIONS_PER_CONDITION,
        "max_generation_attempts": max_generation_attempts,
        "max_duplicate_replacement_attempts": max_duplicate_replacement_attempts,
        "baseline_llm_call_count": baseline_llm_provider.call_count,
        "baseline_llm_calls_by_profile": baseline_llm_provider.calls_by_profile,
        "pilot_llm_call_count": pilot_llm_provider.call_count,
        "pilot_llm_calls_by_profile": pilot_llm_provider.calls_by_profile,
        "records": all_records,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"WP-063 EXPERIMENT COMPLETE - wrote {len(all_records)} round(s) to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
