"""Human-readable Markdown rendering of an ``EvaluationReport`` (WP-017
section 21). Pure formatting only - no metric computation happens here
(that is ``metrics.py``'s job), and no LLM calls are made."""

from __future__ import annotations

from exam_generator.evaluation import metrics
from exam_generator.evaluation.models import EvaluationReport


def render_markdown_report(
    report: EvaluationReport,
    *,
    human_quality_notes: str = "",
    exam_level_observations: str = "",
    recommendations: str = "",
) -> str:
    attempts = report.candidate_attempts
    lines: list[str] = []

    lines.append("# WP-017 Evaluation Report")
    lines.append("")
    lines.append("## Run Summary")
    lines.append("")
    lines.append(f"- Generated at: {report.generated_at.isoformat()}")
    lines.append(f"- Baseline type: **{report.config.baseline_type}**")
    lines.append(f"- Provider/model: `{report.config.provider}` / `{report.config.model}`")
    lines.append(
        f"- Categories evaluated: {len(report.config.evaluated_categories)} of "
        f"{len(report.config.canonical_categories)} canonical categories"
    )
    lines.append(f"- Questions requested per category: {report.config.questions_per_category_requested}")
    lines.append(f"- Total candidate attempts recorded: {len(attempts)}")
    lines.append(f"- Total operational failures recorded: {len(report.operational_failures)}")
    lines.append("")

    lines.append("## Acceptance Metrics")
    lines.append("")
    lines.append(f"- Candidate acceptance rate: {metrics.candidate_acceptance_rate(attempts):.1%}")
    lines.append(f"- First-attempt acceptance rate: {metrics.first_attempt_acceptance_rate(attempts):.1%}")
    stats = metrics.attempts_per_accepted_question_stats(attempts)
    lines.append(
        f"- Attempts per accepted question: mean={stats['mean']:.2f}, median={stats['median']:.2f}, "
        f"min={stats['min']:.0f}, max={stats['max']:.0f} (n={stats['n']})"
    )
    lines.append(f"- Exhaustion rate: {metrics.exhaustion_rate(attempts):.1%}")
    lines.append("")

    lines.append("## Validator Failure Metrics")
    lines.append("")
    failure_counts = metrics.validator_failure_counts(attempts)
    lines.append(f"- Total rejected candidates: {failure_counts['total_rejected']}")
    for name in ("grounding", "mcq", "category", "quality"):
        entry = failure_counts[name]
        lines.append(f"  - {name.capitalize()}: {entry['count']} ({entry['rate']:.1%} of rejections)")
    lines.append("")
    lines.append("Textbook status distribution (all attempts):")
    for status, count in metrics.textbook_status_distribution(attempts).items():
        lines.append(f"  - {status}: {count}")
    lines.append("")

    lines.append("## Category Results")
    lines.append("")
    lines.append("| Category | Requested | Produced | Attempts | Accepted | Rejected | Exhausted | Op. Failures |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for category_result in report.category_results:
        lines.append(
            f"| {category_result.category} | {category_result.requested_questions} | "
            f"{category_result.produced_questions} | {category_result.candidate_attempts} | "
            f"{category_result.accepted_candidates} | {category_result.rejected_candidates} | "
            f"{category_result.exhausted_units} | {category_result.operational_failures} |"
        )
    lines.append("")

    lines.append("## Retrieval Metrics")
    lines.append("")
    if report.retrieval_results:
        lines.append(f"- Recall@3: {metrics.recall_at_k(report.retrieval_results, 3):.1%}")
        lines.append(f"- Recall@5: {metrics.recall_at_k(report.retrieval_results, 5):.1%}")
        lines.append(f"- Recall@8: {metrics.recall_at_k(report.retrieval_results, 8):.1%}")
        misses = metrics.retrieval_misses(report.retrieval_results)
        lines.append(f"- Queries missed at K=8: {len(misses)} of {len(report.retrieval_results)}")
        for miss in misses:
            lines.append(f"  - {miss.query!r} (expected term {miss.expected_literal_term!r})")
    else:
        lines.append("- No retrieval evaluation results in this report.")
    lines.append("")

    lines.append("## Operational/Provenance Failures")
    lines.append("")
    if report.operational_failures:
        for failure in report.operational_failures:
            lines.append(
                f"- [{failure.category} / {failure.generation_mode.value}] "
                f"{failure.failure_type}: {failure.message}"
            )
    else:
        lines.append("- None recorded.")
    lines.append("")

    lines.append("## Human Quality Observations")
    lines.append("")
    lines.append(human_quality_notes or "_Not recorded._")
    lines.append("")

    lines.append("## Exam-Level Quality Observations")
    lines.append("")
    lines.append(exam_level_observations or "_Not recorded._")
    lines.append("")

    lines.append("## Recommended Next Actions")
    lines.append("")
    lines.append(recommendations or "_Not recorded._")
    lines.append("")

    return "\n".join(lines)
