"""WP-017 evaluation-run driver.

NOT part of the automated pytest suite. Exercises the real corpus/retrieval
layer (no API key needed) and, optionally, the real generation/validation
pipeline (requires ``OPENAI_API_KEY``) across a caller-controlled subset of
canonical categories, then writes a machine-readable JSON report plus a
human-readable Markdown report - kept entirely separate from normal exam/
audit output (WP-015's contracts are never touched).

Sequential only - no concurrency, no automatic reruns of operational
failures, per WP-017 sections 16/23.

Usage:
    # Retrieval evaluation only (offline, no API key needed):
    .venv/bin/python scripts/run_evaluation.py --skip-generation

    # Reduced baseline (a specific category subset):
    .venv/bin/python scripts/run_evaluation.py \\
        --categories "אמבריולוגיה,טופוגרפיה של ההמיספרות" \\
        --questions-per-category 2 --baseline-type REDUCED

    # Full baseline (every canonical category):
    .venv/bin/python scripts/run_evaluation.py --questions-per-category 2 --baseline-type FULL
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from exam_generator.chunking import build_student_summary_corpus
from exam_generator.config import load_app_config, load_llm_config
from exam_generator.evaluation import (
    RETRIEVAL_EVAL_QUERIES,
    CandidateEvaluationRunner,
    EvaluationConfig,
    EvaluationReport,
    RetrievalEvaluationRunner,
    build_evaluation_plan,
    metrics,
    render_markdown_report,
)
from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.production import QuestionProducer
from exam_generator.retrieval import build_student_summary_retrieval_index


def _build_config(*, categories: list[str], questions_per_category: int, baseline_type: str) -> EvaluationConfig:
    app_config = load_app_config()
    llm_config = load_llm_config()
    repository = HistoricalQuestionRepository.from_default_location()
    return EvaluationConfig(
        provider=llm_config.provider,
        model=llm_config.model,
        generation_temperature=llm_config.generation.temperature,
        generation_max_tokens=llm_config.generation.max_tokens,
        validation_temperature=llm_config.validation.temperature,
        validation_max_tokens=llm_config.validation.max_tokens,
        chunk_size=app_config.chunking.chunk_size,
        chunk_overlap=app_config.chunking.chunk_overlap,
        retrieval_top_k=app_config.retrieval.top_k,
        retrieval_ngram_min=app_config.retrieval.ngram_min,
        retrieval_ngram_max=app_config.retrieval.ngram_max,
        max_generation_attempts=app_config.generation.max_generation_attempts,
        max_duplicate_replacement_attempts=app_config.generation.max_duplicate_replacement_attempts,
        canonical_categories=repository.canonical_categories,
        evaluated_categories=tuple(categories),
        questions_per_category_requested=questions_per_category,
        baseline_type=baseline_type,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a WP-017 evaluation pass.")
    parser.add_argument("--categories", default="", help="Comma-separated category subset; empty = all canonical categories.")
    parser.add_argument("--questions-per-category", type=int, default=2)
    parser.add_argument("--baseline-type", default="REDUCED", choices=["FULL", "REDUCED"])
    parser.add_argument("--skip-generation", action="store_true", help="Run retrieval evaluation only - no API key needed.")
    parser.add_argument("--output-dir", default="evaluation")
    args = parser.parse_args()

    repository = HistoricalQuestionRepository.from_default_location()
    all_categories = list(repository.canonical_categories)
    categories = [c.strip() for c in args.categories.split(",") if c.strip()] or all_categories

    config = _build_config(
        categories=categories, questions_per_category=args.questions_per_category, baseline_type=args.baseline_type
    )

    print(f"Evaluating {len(categories)} of {len(all_categories)} canonical categories.")

    print("Running retrieval evaluation (real corpus, no API key needed)...")
    corpus = build_student_summary_corpus()
    index = build_student_summary_retrieval_index()
    retrieval_runner = RetrievalEvaluationRunner(index=index, corpus=corpus)
    retrieval_results = retrieval_runner.run(RETRIEVAL_EVAL_QUERIES)
    print(f"  Recall@3={metrics.recall_at_k(retrieval_results, 3):.1%}  "
          f"Recall@5={metrics.recall_at_k(retrieval_results, 5):.1%}  "
          f"Recall@8={metrics.recall_at_k(retrieval_results, 8):.1%}")

    candidate_attempts: list = []
    operational_failures: list = []
    category_results: tuple = ()

    if not args.skip_generation:
        print("Running candidate generation/validation evaluation (real OpenAI API)...")
        producer = QuestionProducer.from_default_configuration()
        candidate_runner = CandidateEvaluationRunner(producer=producer)
        plan = build_evaluation_plan(categories, args.questions_per_category)
        print(f"  Plan: {len(plan)} planned question(s).")
        candidate_attempts, operational_failures = candidate_runner.run(plan)
        category_results = metrics.build_category_results(plan, candidate_attempts, operational_failures)
        print(f"  {len(candidate_attempts)} attempt(s) recorded, {len(operational_failures)} operational failure(s).")
    else:
        print("Skipping generation/validation evaluation (--skip-generation).")

    report = EvaluationReport(
        config=config,
        generated_at=datetime.now(timezone.utc),
        candidate_attempts=tuple(candidate_attempts),
        operational_failures=tuple(operational_failures),
        category_results=category_results,
        retrieval_results=tuple(retrieval_results),
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "evaluation_report.json"
    md_path = output_dir / "evaluation_report.md"

    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(render_markdown_report(report), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
