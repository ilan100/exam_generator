"""WP-056 controlled experiment: reverse-framed identity generation for
Globus Pallidus.

NOT production code. Uses the real, unmodified QuestionProducer/
QuestionGenerator/all five real validators against the real OpenAI API,
for exactly two conditions:

  CONTROL: unmodified production prompt repository (byte-identical to
      prompts/generation/question.txt on disk) - current DEFAULT
      behavior for Globus Pallidus.
  EXPERIMENT: the same production prompt text, with one small, isolated
      "REVERSE-FRAMED IDENTITY" instruction block appended in-memory
      only (never written to prompts/generation/question.txt) - built
      via the same, already-established injection points WP-053 used
      (PromptRepository.__init__ takes an explicit templates mapping;
      QuestionGenerator takes an explicit prompt_repository).

The target is constructed directly (mirroring WP-053/WP-054/WP-055's own
established pattern) rather than via automatic coverage-based planning,
to test exactly the one named concept this experiment concerns:
Globus Pallidus, in גרעיני הבסיס, only.

3 independent CONTROL rounds + 3 independent EXPERIMENT rounds (the
sample size WP-056 section 18 explicitly recommends), each with the
existing, unmodified 3-attempt production budget. No round is rerun; no
condition is run until it succeeds.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from exam_generator.config import load_app_config, load_llm_config
from exam_generator.generation.generator import QuestionGenerator
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
TARGET_TOPIC = "Globus Pallidus"
ROUNDS_PER_CONDITION = 3
OUTPUT_PATH = Path("evaluation/live_outputs/wp056_experiment_records.json")

_EXPERIMENTAL_INSTRUCTION_BLOCK = (
    "\n\n--- EXPERIMENTAL INSTRUCTION (WP-056, REVERSE-FRAMED IDENTITY, "
    "PROTOTYPE-ONLY - NOT PART OF THE PERMANENT PROMPT) ---\n"
    "For this generation attempt, prefer a reverse-framed identity question "
    "that asks which answer choice IS TARGET CONCEPT itself - for example, "
    "\"Which of the following IS TARGET CONCEPT?\" or an equivalent "
    "identity-establishing phrasing that names TARGET CONCEPT within the "
    "question text and as the correct answer.\n"
    "Do NOT use a broader category-membership question such as \"Which "
    "structure is part of the basal nuclei?\" or \"Which of the following "
    "is part of X?\" - this framing has repeatedly failed grounding for "
    "this exact target, because the same membership property is equally "
    "true of every sibling structure.\n"
    "This identity framing is a preference, not an unconditional validity "
    "override: it does not relax, replace, or override any other "
    "requirement stated above (grounding, uniqueness, target-answer "
    "identity, category, quality, or any other existing constraint).\n"
    "--- END EXPERIMENTAL INSTRUCTION ---\n"
)

# ---------------------------------------------------------------------------
# Deterministic question-shape classifier (WP-056 section 13/23) - a small,
# explicit, keyword-based rule over the generated question TEXT only, in the
# same spirit as WP-052's own PROPERTY/IDENTITY classifier
# (implementation/wp052_strategy_probe.py) but refined to specifically
# distinguish reverse-framed identity ("which of the following IS X",
# target named INSIDE the question) from bare membership ("which structure
# is part of X", target named only among the answer choices, never in the
# question text itself) - the exact distinction WP-056 section 13 requires.
# Never an LLM judgment; never imported by src/.
# ---------------------------------------------------------------------------

_MEMBERSHIP_MARKERS = [
    "חלק מ", "מהווה חלק", "שייך ל", "שייכת ל", "נמצא בתוך", "נמצאת בתוך",
]
_COPULA_PATTERNS = ["הוא ", "היא "]
_NAMING_CUE = ["הנקרא", "הנקראת", "מוכר גם כ", "ידוע גם כ", "הידוע כ"]
_PROPERTY_MARKERS = ["תפקיד", "מקור", "משפיע", "ממוקם", "משויך", "מאפשר", "מדכא", "מפעיל", "תורם", "אחראי"]


def classify_question_shape(question: str, target_topic: str) -> str:
    target_words = [w for w in re.split(r"\s+", target_topic) if len(w) >= 4]
    question_names_target = any(w.lower() in question.lower() for w in target_words)
    has_membership_marker = any(m in question for m in _MEMBERSHIP_MARKERS)
    has_copula_or_naming = any(c in question for c in _COPULA_PATTERNS) or any(n in question for n in _NAMING_CUE)
    has_property_marker = any(p in question for p in _PROPERTY_MARKERS)

    if question_names_target and has_copula_or_naming and not has_membership_marker:
        return "VALID_IDENTITY_SHAPE"
    if has_membership_marker:
        return "MEMBERSHIP_CLASSIFICATION"
    if has_property_marker:
        return "PROPERTY"
    return "OTHER"


def _self_check_classifier() -> None:
    """Deterministic, offline verification of the classifier above against
    already-recorded real examples (WP-054's three fresh failures; two real
    historical successes) - run before any LLM call, per WP-056 section 39's
    'add deterministic tests for the prototype itself' instruction. Fails
    loudly (AssertionError) rather than silently mis-scoring the live run.
    """
    cases = [
        ("איזה מבנה הוא חלק מגרעיני הבסיס ומסייע בוויסות תנועות מוטוריות?", "MEMBERSHIP_CLASSIFICATION"),
        ("איזה מבנה מהווה חלק מגרעיני הבסיס?", "MEMBERSHIP_CLASSIFICATION"),
        ("איזה מהבאים הוא גרעין הנמצא בתוך הגרעינים הבסיסיים?", "MEMBERSHIP_CLASSIFICATION"),
        ("איזה מהגרעינים הבסיסיים הוא Globus Pallidus?", "VALID_IDENTITY_SHAPE"),
        ("איזה מבין הגרעינים הבאים הוא Globus Pallidus?", "VALID_IDENTITY_SHAPE"),
        ("מהו תפקידו של ה-Globus Pallidus במערכת גרעיני הבסיס?", "PROPERTY"),
    ]
    for question, expected in cases:
        actual = classify_question_shape(question, TARGET_TOPIC)
        assert actual == expected, f"classifier self-check FAILED: {question!r} -> {actual}, expected {expected}"
    print(f"classifier self-check: PASSED ({len(cases)}/{len(cases)} known cases)", flush=True)


def _self_check_experimental_isolation(control: PromptRepository, experimental: PromptRepository) -> None:
    """WP-056 section 39: verify control has no reverse-identity
    instruction, experiment does, and both use the identical target/
    category - before spending any API call."""
    control_text = control.get(PromptId.QUESTION_GENERATION).text
    experimental_text = experimental.get(PromptId.QUESTION_GENERATION).text
    assert "REVERSE-FRAMED IDENTITY" not in control_text, "control repository must not carry the experimental instruction"
    assert "REVERSE-FRAMED IDENTITY" in experimental_text, "experimental repository must carry the experimental instruction"
    assert control_text == PromptRepository.from_default_location().get(PromptId.QUESTION_GENERATION).text, (
        "control template must be byte-identical to the real production template"
    )
    assert TARGET_TOPIC == "Globus Pallidus"
    assert CATEGORY == "גרעיני הבסיס"
    print("experimental isolation self-check: PASSED", flush=True)


def _build_experimental_prompt_repository(control: PromptRepository) -> PromptRepository:
    original = control.get(PromptId.QUESTION_GENERATION)
    experimental_text = original.text + _EXPERIMENTAL_INSTRUCTION_BLOCK
    experimental_template = PromptTemplate(
        prompt_id=PromptId.QUESTION_GENERATION,
        text=experimental_text,
        required_variables=original.required_variables,
        version="WP-056-EXPERIMENTAL-REVERSE-FRAMED-IDENTITY",
    )
    templates = {prompt_id: control.get(prompt_id) for prompt_id in control.prompt_ids}
    templates[PromptId.QUESTION_GENERATION] = experimental_template
    return PromptRepository(templates)


def _build_producer(*, prompt_repository, category_resolver, student_summary_index, historical_repository, llm_provider, max_attempts) -> QuestionProducer:
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


def _build_target(*, canonical_category: str, source_evidence, chunk_text_by_id) -> QuestionTarget:
    inventory = refine_concept_inventory(source_evidence)
    concept_item = next(c for c in inventory if c.concept == TARGET_TOPIC)
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
            "question": None,
            "answers": None,
            "correct_answer_text": None,
            "question_shape": None,
            "generation_failure_type": attempt.generation_failure_type,
            "generation_failure_message": attempt.generation_failure_message,
            "target_answer_identity_failure": attempt.generation_failure_type == "InvalidGeneratedOutputError",
        }
    v = attempt.validations
    question = attempt.candidate.question
    shape = classify_question_shape(question, TARGET_TOPIC)
    return {
        "attempt_number": attempt.attempt_number,
        "accepted": attempt.accepted,
        "question": question,
        "answers": list(attempt.candidate.answers),
        "correct_answer_position": attempt.candidate.correct_answer,
        "correct_answer_text": attempt.candidate.answers[attempt.candidate.correct_answer - 1],
        "question_shape": shape,
        "validations": {
            "grounding": {"passed": v.grounding.passed, "reason": v.grounding.reason},
            "mcq": {"valid": v.mcq.valid, "reason": v.mcq.reason},
            "category": {"valid": v.category.valid, "reason": v.category.reason},
            "quality": {"valid": v.quality.valid, "reason": v.quality.reason},
            "textbook": {"status": v.textbook.status.value},
        },
        "target_answer_identity_failure": False,
    }


def _run_round(*, producer: QuestionProducer, category: str, target: QuestionTarget, condition: str, round_number: int) -> dict:
    print(f"--- round start: condition={condition} round={round_number} target={target.topic!r} ---", flush=True)
    try:
        result: QuestionProductionResult = producer.produce_question(
            category=category, generation_mode=GenerationMode.INDEPENDENT, target=target
        )
        record = {
            "condition": condition,
            "round": round_number,
            "target": target.topic,
            "accepted": True,
            "attempt_count": len(result.attempts),
            "attempts": [_attempt_record(a) for a in result.attempts],
        }
    except QuestionAttemptsExhaustedError as exc:
        record = {
            "condition": condition,
            "round": round_number,
            "target": target.topic,
            "accepted": False,
            "attempt_count": len(exc.attempts),
            "attempts": [_attempt_record(a) for a in exc.attempts],
        }
    print(
        f"--- round end: condition={condition} round={round_number} accepted={record['accepted']} "
        f"attempts={record['attempt_count']} ---",
        flush=True,
    )
    return record


def main() -> None:
    _self_check_classifier()

    category_resolver = build_category_resolver()
    student_summary_index = build_student_summary_retrieval_index()
    historical_repository = HistoricalQuestionRepository.from_default_location()
    llm_provider = build_llm_provider(load_llm_config())
    max_attempts = load_app_config().generation.max_generation_attempts

    control_prompt_repository = PromptRepository.from_default_location()
    experimental_prompt_repository = _build_experimental_prompt_repository(control_prompt_repository)
    _self_check_experimental_isolation(control_prompt_repository, experimental_prompt_repository)

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
    target = _build_target(canonical_category=canonical_category, source_evidence=source_evidence, chunk_text_by_id=chunk_text_by_id)

    records = []
    for round_number in range(1, ROUNDS_PER_CONDITION + 1):
        records.append(_run_round(producer=control_producer, category=canonical_category, target=target, condition="CONTROL", round_number=round_number))
    for round_number in range(1, ROUNDS_PER_CONDITION + 1):
        records.append(_run_round(producer=experimental_producer, category=canonical_category, target=target, condition="EXPERIMENT", round_number=round_number))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print(f"WP-056 EXPERIMENT COMPLETE - wrote {len(records)} round(s) to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
