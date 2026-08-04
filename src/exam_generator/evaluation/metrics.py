"""Pure, deterministic aggregate-metric functions over evaluation records
(WP-017 sections 8/9/13). No I/O, no LLM calls - every function here is a
plain transformation of already-collected data, independently testable
with synthetic records."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Sequence

from exam_generator.evaluation.models import CandidateAttemptRecord, CategoryEvaluationResult, RetrievalEvalResult


def group_attempts_by_question(
    attempts: Sequence[CandidateAttemptRecord],
) -> dict[int, list[CandidateAttemptRecord]]:
    """Group attempts by the planned question they belong to
    (``question_position``), preserving attempt order within each group."""
    groups: dict[int, list[CandidateAttemptRecord]] = defaultdict(list)
    for attempt in attempts:
        groups[attempt.question_position].append(attempt)
    return dict(groups)


def candidate_acceptance_rate(attempts: Sequence[CandidateAttemptRecord]) -> float:
    """accepted candidates / generated candidates (WP-017 section 8)."""
    if not attempts:
        return 0.0
    accepted = sum(1 for attempt in attempts if attempt.accepted)
    return accepted / len(attempts)


def first_attempt_acceptance_rate(attempts: Sequence[CandidateAttemptRecord]) -> float:
    """questions accepted on attempt 1 / successfully produced questions."""
    accepted = [attempt for attempt in attempts if attempt.accepted]
    if not accepted:
        return 0.0
    first_attempt = sum(1 for attempt in accepted if attempt.attempt_number == 1)
    return first_attempt / len(accepted)


def attempts_per_accepted_question_stats(attempts: Sequence[CandidateAttemptRecord]) -> dict[str, float]:
    """mean/median/min/max attempt count, over only the questions that
    were ultimately accepted."""
    groups = group_attempts_by_question(attempts)
    counts = sorted(len(group) for group in groups.values() if any(a.accepted for a in group))
    if not counts:
        return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "n": 0}

    n = len(counts)
    mean = sum(counts) / n
    mid = n // 2
    median = float(counts[mid]) if n % 2 == 1 else (counts[mid - 1] + counts[mid]) / 2
    return {"mean": mean, "median": median, "min": float(counts[0]), "max": float(counts[-1]), "n": n}


def exhaustion_rate(attempts: Sequence[CandidateAttemptRecord]) -> float:
    """Fraction of planned questions (that produced at least one attempt)
    where no attempt was ever accepted."""
    groups = group_attempts_by_question(attempts)
    if not groups:
        return 0.0
    exhausted = sum(1 for group in groups.values() if not any(a.accepted for a in group))
    return exhausted / len(groups)


def validator_failure_counts(attempts: Sequence[CandidateAttemptRecord]) -> dict[str, object]:
    """Counts/rates of each primary validator failing, over rejected
    candidates only. A candidate may fail more than one validator, so
    rates need not sum to 100% (WP-017 section 9)."""
    rejected = [attempt for attempt in attempts if not attempt.accepted]
    total = len(rejected)

    def _rate(count: int) -> float:
        return count / total if total else 0.0

    grounding_failures = sum(1 for attempt in rejected if not attempt.grounding_passed)
    mcq_failures = sum(1 for attempt in rejected if not attempt.mcq_valid)
    category_failures = sum(1 for attempt in rejected if not attempt.category_valid)
    quality_failures = sum(1 for attempt in rejected if not attempt.quality_valid)

    return {
        "total_rejected": total,
        "grounding": {"count": grounding_failures, "rate": _rate(grounding_failures)},
        "mcq": {"count": mcq_failures, "rate": _rate(mcq_failures)},
        "category": {"count": category_failures, "rate": _rate(category_failures)},
        "quality": {"count": quality_failures, "rate": _rate(quality_failures)},
    }


def textbook_status_distribution(attempts: Sequence[CandidateAttemptRecord]) -> dict[str, int]:
    """Counts of each ``TextbookCheckStatus`` value across all attempts."""
    counts = Counter(attempt.textbook_status.value for attempt in attempts)
    return dict(counts)


def build_category_results(
    plan: Sequence[tuple[str, object, int]],
    attempts: Sequence[CandidateAttemptRecord],
    operational_failures: Sequence[object],
) -> tuple[CategoryEvaluationResult, ...]:
    """Per-category rollup (WP-017 section 10) from the evaluation plan
    plus observed attempt/failure records."""
    requested_per_category: dict[str, int] = defaultdict(int)
    category_order: list[str] = []
    for category, _mode, _position in plan:
        if category not in requested_per_category:
            category_order.append(category)
        requested_per_category[category] += 1

    attempts_by_category: dict[str, list[CandidateAttemptRecord]] = defaultdict(list)
    for attempt in attempts:
        attempts_by_category[attempt.category].append(attempt)

    failures_by_category: dict[str, int] = defaultdict(int)
    for failure in operational_failures:
        failures_by_category[failure.category] += 1

    results = []
    for category in category_order:
        category_attempts = attempts_by_category.get(category, [])
        groups = group_attempts_by_question(category_attempts)
        produced = sum(1 for group in groups.values() if any(a.accepted for a in group))
        exhausted = sum(1 for group in groups.values() if not any(a.accepted for a in group))
        accepted = sum(1 for attempt in category_attempts if attempt.accepted)
        rejected = sum(1 for attempt in category_attempts if not attempt.accepted)
        results.append(
            CategoryEvaluationResult(
                category=category,
                requested_questions=requested_per_category[category],
                produced_questions=produced,
                candidate_attempts=len(category_attempts),
                accepted_candidates=accepted,
                rejected_candidates=rejected,
                exhausted_units=exhausted,
                operational_failures=failures_by_category.get(category, 0),
            )
        )
    return tuple(results)


def recall_at_k(retrieval_results: Sequence[RetrievalEvalResult], k: int) -> float:
    """Fraction of retrieval-evaluation queries where at least one
    expected-relevant chunk appeared within the top ``k`` results."""
    field = {3: "hit_at_3", 5: "hit_at_5", 8: "hit_at_8"}[k]
    if not retrieval_results:
        return 0.0
    hits = sum(1 for result in retrieval_results if getattr(result, field))
    return hits / len(retrieval_results)


def retrieval_misses(retrieval_results: Sequence[RetrievalEvalResult]) -> tuple[RetrievalEvalResult, ...]:
    """Queries that missed even at the widest evaluated K (8)."""
    return tuple(result for result in retrieval_results if not result.hit_at_8)
