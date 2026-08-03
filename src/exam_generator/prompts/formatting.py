"""Deterministic, non-LLM formatting of already-selected domain objects into
prompt text.

Formatting only: this module never retrieves, ranks, filters, sorts, or
deduplicates evidence/references - callers supply exactly what should
appear, in the order it should appear, and that order is preserved exactly.
"""

from __future__ import annotations

from typing import Sequence

from exam_generator.models import (
    CandidateQuestion,
    ExamQuestion,
    HistoricalStyleReference,
    SourceEvidenceChunk,
    SourceType,
)
from exam_generator.prompts.errors import PromptContextError

FACTUAL_EVIDENCE_BEGIN = "--- BEGIN FACTUAL EVIDENCE (STUDENT SUMMARY - AUTHORITATIVE) ---"
FACTUAL_EVIDENCE_END = "--- END FACTUAL EVIDENCE (STUDENT SUMMARY - AUTHORITATIVE) ---"

COURSE_BOOK_EVIDENCE_BEGIN = "--- BEGIN COURSE-BOOK EVIDENCE (SECONDARY - NOT PRIMARY GROUNDING) ---"
COURSE_BOOK_EVIDENCE_END = "--- END COURSE-BOOK EVIDENCE (SECONDARY - NOT PRIMARY GROUNDING) ---"
NO_COURSE_BOOK_EVIDENCE_TEXT = "No course-book evidence was supplied for this check."

HISTORICAL_REFERENCE_BEGIN = "--- BEGIN HISTORICAL STYLE REFERENCE (NOT FACTUAL EVIDENCE) ---"
HISTORICAL_REFERENCE_END = "--- END HISTORICAL STYLE REFERENCE (NOT FACTUAL EVIDENCE) ---"
NO_HISTORICAL_REFERENCE_TEXT = "No historical style reference is supplied for this generation mode."


def _format_answers(answers: Sequence[str]) -> str:
    return "\n".join(
        f"Answer {position}: {answer}" for position, answer in enumerate(answers, start=1)
    )


def _format_evidence_chunk(chunk: SourceEvidenceChunk, position: int) -> str:
    return (
        f"[Evidence {position}]\n"
        f"Source: {chunk.source_file}\n"
        f"Page: {chunk.page}\n"
        f"Chunk: {chunk.chunk_id}\n"
        f"Text:\n{chunk.text}"
    )


def _format_evidence_section(
    chunks: Sequence[SourceEvidenceChunk],
    *,
    expected_source_type: SourceType,
    begin_marker: str,
    end_marker: str,
    empty_text: str | None,
) -> str:
    if not chunks:
        if empty_text is None:
            raise PromptContextError(
                f"At least one {expected_source_type.value} evidence chunk is required, got none"
            )
        return f"{begin_marker}\n{empty_text}\n{end_marker}"

    for chunk in chunks:
        if chunk.source_type != expected_source_type:
            raise PromptContextError(
                f"Expected {expected_source_type.value} evidence, got "
                f"{chunk.source_type.value} chunk {chunk.chunk_id!r}"
            )

    body = "\n\n".join(
        _format_evidence_chunk(chunk, position) for position, chunk in enumerate(chunks, start=1)
    )
    return f"{begin_marker}\n{body}\n{end_marker}"


def format_student_summary_evidence(chunks: Sequence[SourceEvidenceChunk]) -> str:
    """Format already-selected student-summary evidence chunks.

    Caller-supplied order is preserved exactly. At least one chunk is
    required - student-summary evidence is mandatory for question
    generation and grounding validation (WP-008 section 43); an empty
    sequence fails clearly here rather than producing a hollow
    "(none)" section that later reaches an LLM call.
    """
    return _format_evidence_section(
        chunks,
        expected_source_type=SourceType.STUDENT_SUMMARY,
        begin_marker=FACTUAL_EVIDENCE_BEGIN,
        end_marker=FACTUAL_EVIDENCE_END,
        empty_text=None,
    )


def format_course_book_evidence(chunks: Sequence[SourceEvidenceChunk]) -> str:
    """Format already-selected course-book evidence chunks.

    Caller-supplied order is preserved exactly. Unlike student-summary
    evidence, an empty sequence is explicitly allowed: future textbook
    retrieval may legitimately find nothing for a given question (WP-008
    section 43), so this renders an explicit "no evidence" sentinel instead
    of failing.
    """
    return _format_evidence_section(
        chunks,
        expected_source_type=SourceType.COURSE_BOOK,
        begin_marker=COURSE_BOOK_EVIDENCE_BEGIN,
        end_marker=COURSE_BOOK_EVIDENCE_END,
        empty_text=NO_COURSE_BOOK_EVIDENCE_TEXT,
    )


def format_historical_reference(reference: HistoricalStyleReference | None) -> str:
    """Format an already-selected historical style reference, or ``None``
    for ``INDEPENDENT`` generation (an explicit "no reference supplied"
    sentinel is rendered instead of fabricating one).

    Always explicitly labeled as a style reference, never as factual
    evidence.
    """
    if reference is None:
        return (
            f"{HISTORICAL_REFERENCE_BEGIN}\n"
            f"{NO_HISTORICAL_REFERENCE_TEXT}\n"
            f"{HISTORICAL_REFERENCE_END}"
        )

    body = (
        "STYLE REFERENCE - NOT FACTUAL EVIDENCE\n"
        f"Historical Reference ID: {reference.historical_question_id}\n"
        f"Category: {reference.category}\n"
        f"Question: {reference.question}\n"
        f"{_format_answers(reference.answers)}\n"
        f"Correct Answer Position: {reference.correct_answer}"
    )
    return f"{HISTORICAL_REFERENCE_BEGIN}\n{body}\n{HISTORICAL_REFERENCE_END}"


def format_candidate_question(candidate: CandidateQuestion) -> str:
    """Deterministically format a ``CandidateQuestion`` for validator prompts.

    Includes only information already present on the candidate - no hidden
    facts, and the candidate itself is never modified.
    """
    return (
        f"Question: {candidate.question}\n"
        f"{_format_answers(candidate.answers)}\n"
        f"Intended Correct Answer Position: {candidate.correct_answer}\n"
        f"Category: {candidate.category}\n"
        f"Generation Mode: {candidate.generation_mode.value}"
    )


def format_exam_question(question: ExamQuestion) -> str:
    """Deterministically format a clean ``ExamQuestion``, reusing the same
    answer-formatting helper as ``format_candidate_question`` rather than
    introducing a subtly different representation."""
    answers = [question.answer1, question.answer2, question.answer3, question.answer4]
    return (
        f"Question: {question.question}\n"
        f"{_format_answers(answers)}\n"
        f"Intended Correct Answer Position: {question.correct_answer}\n"
        f"Category: {question.category}"
    )
