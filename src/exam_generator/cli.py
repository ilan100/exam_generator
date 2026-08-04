"""The WP-016 command-line adapter around the already-complete exam
generation pipeline.

    request.json
         v
    ExamOrchestrator.from_default_configuration()   (WP-006..WP-014)
         v
    ExamGenerationResult
         v
    build_exam_output_bundle()                       (WP-015)
         v
    exam.json + audit.json

This module is a thin adapter only: it parses arguments, reads/validates
the request file, invokes the existing orchestration/output boundary
exactly as already built, and translates the resulting success or known
failure into console output/exit code. It introduces no new generation,
validation, retrieval, or acceptance policy of any kind.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from exam_generator.config import ConfigError, load_app_config, load_llm_config
from exam_generator.generation import GenerationError
from exam_generator.llm import LLMConfigurationError, LLMError
from exam_generator.models import ExamRequest
from exam_generator.orchestration import ExamOrchestrator, QuestionProductionFailedError
from exam_generator.output import AuditConsistencyError, build_exam_output_bundle, serialize_audit_json, serialize_exam_json
from exam_generator.production import QuestionAttemptsExhaustedError
from exam_generator.prompts import PromptError
from exam_generator.retrieval import CategoryResolutionError, RetrievalError
from exam_generator.validation import GroundingValidationError, TextbookValidationError

EXIT_SUCCESS = 0
EXIT_GENERATION_FAILURE = 1
EXIT_USAGE_ERROR = 2

DEFAULT_EXAM_OUTPUT_PATH = "exam.json"
DEFAULT_AUDIT_OUTPUT_PATH = "exam_audit.json"


class CliUsageError(Exception):
    """A CLI-level usage problem (bad request file, existing output
    without ``--force``) - always maps to ``EXIT_USAGE_ERROR``."""


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="exam-generator", description="Generate a Hebrew neuroanatomy exam from a request file."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Generate an exam from a request file.")
    generate_parser.add_argument("--request", required=True, help="Path to a UTF-8 JSON exam request file.")
    generate_parser.add_argument(
        "--exam-output",
        default=DEFAULT_EXAM_OUTPUT_PATH,
        help=f"Path to write the clean exam JSON (default: {DEFAULT_EXAM_OUTPUT_PATH}).",
    )
    generate_parser.add_argument(
        "--audit-output",
        default=DEFAULT_AUDIT_OUTPUT_PATH,
        help=f"Path to write the audit JSON (default: {DEFAULT_AUDIT_OUTPUT_PATH}).",
    )
    generate_parser.add_argument("--force", action="store_true", help="Overwrite existing output files.")

    return parser


def _load_exam_request(path: Path) -> ExamRequest:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CliUsageError(f"Request file not found: {path}") from exc
    except OSError as exc:
        raise CliUsageError(f"Could not read request file {path}: {exc}") from exc

    try:
        raw_data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CliUsageError(f"Request file is not valid JSON: {path} ({exc})") from exc

    try:
        return ExamRequest.model_validate(raw_data)
    except ValidationError as exc:
        raise CliUsageError(f"Invalid exam request in {path}:\n{exc}") from exc


def _check_output_targets(exam_output: Path, audit_output: Path, *, force: bool) -> None:
    if force:
        return
    existing = [str(path) for path in (exam_output, audit_output) if path.exists()]
    if existing:
        raise CliUsageError(
            f"Output file(s) already exist: {', '.join(existing)} (use --force to overwrite)"
        )


def _atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` via a same-directory temp file plus
    ``os.replace()``, so a failure mid-write never leaves a truncated or
    partially-written target file."""
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def _run_generate(args: argparse.Namespace) -> int:
    exam_output = Path(args.exam_output)
    audit_output = Path(args.audit_output)

    # Fail fast on cheap, local checks before touching the network/API key.
    _check_output_targets(exam_output, audit_output, force=args.force)

    print("Loading request...")
    request = _load_exam_request(Path(args.request))

    print("Initializing exam generator...")
    orchestrator = ExamOrchestrator.from_default_configuration()

    print("Generating exam...")
    generation_result = orchestrator.generate_exam(request)

    generated_at = datetime.now(timezone.utc)
    bundle = build_exam_output_bundle(
        generation_result,
        exam_id=f"exam-{generated_at.strftime('%Y%m%dT%H%M%SZ')}",
        generated_at=generated_at,
        llm_config=load_llm_config(),
        diversity_target=load_app_config().generation.initial_diversity_target,
    )

    # Serialize both outputs before writing either, so a serialization
    # failure in one never leaves the other written alone.
    exam_json = serialize_exam_json(bundle.exam)
    audit_json = serialize_audit_json(bundle.audit)

    print("Writing exam output...")
    _atomic_write_text(exam_output, exam_json)

    print("Writing audit output...")
    _atomic_write_text(audit_output, audit_json)

    print("Done.")
    print(f"Exam generated successfully: {len(bundle.exam.questions)} question(s)")
    print(f"  Exam output:  {exam_output}")
    print(f"  Audit output: {audit_output}")

    return EXIT_SUCCESS


def _classify_error(exc: Exception) -> tuple[int, str] | None:
    """Map a known, expected application/CLI exception to
    ``(exit_code, message)``. Returns ``None`` for anything not
    recognized, so ``main()`` lets a genuinely unexpected exception
    propagate with its traceback rather than hiding it."""
    if isinstance(exc, CliUsageError):
        return EXIT_USAGE_ERROR, str(exc)
    if isinstance(exc, LLMConfigurationError):
        return EXIT_USAGE_ERROR, f"LLM configuration error: {exc}"
    if isinstance(exc, ConfigError):
        return EXIT_USAGE_ERROR, f"Configuration error: {exc}"
    if isinstance(exc, CategoryResolutionError):
        return EXIT_USAGE_ERROR, f"Invalid category in request: {exc}"
    if isinstance(exc, OSError):
        return EXIT_USAGE_ERROR, f"Output write failed: {exc}"
    if isinstance(exc, QuestionAttemptsExhaustedError):
        return EXIT_GENERATION_FAILURE, f"Exam generation failed: {exc}"
    if isinstance(exc, QuestionProductionFailedError):
        return EXIT_GENERATION_FAILURE, f"Exam generation failed: {exc}"
    if isinstance(exc, AuditConsistencyError):
        return EXIT_GENERATION_FAILURE, f"Internal output-consistency check failed: {exc}"
    if isinstance(exc, GenerationError):
        return EXIT_GENERATION_FAILURE, f"Generation failed: {exc}"
    if isinstance(exc, GroundingValidationError):
        return EXIT_GENERATION_FAILURE, f"Grounding validation failed: {exc}"
    if isinstance(exc, TextbookValidationError):
        return EXIT_GENERATION_FAILURE, f"Textbook validation failed: {exc}"
    if isinstance(exc, RetrievalError):
        return EXIT_GENERATION_FAILURE, f"Retrieval failed: {exc}"
    if isinstance(exc, PromptError):
        return EXIT_GENERATION_FAILURE, f"Prompt processing failed: {exc}"
    if isinstance(exc, LLMError):
        return EXIT_GENERATION_FAILURE, f"LLM provider error: {exc}"
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    try:
        return _run_generate(args)
    except Exception as exc:
        classified = _classify_error(exc)
        if classified is None:
            raise
        exit_code, message = classified
        print(f"Error: {message}", file=sys.stderr)
        return exit_code


if __name__ == "__main__":
    sys.exit(main())
