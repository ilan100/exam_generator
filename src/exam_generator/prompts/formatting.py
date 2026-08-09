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
    CategoryCoverage,
    CompetitorCandidate,
    ExamQuestion,
    HistoricalStyleReference,
    QuestionTarget,
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

QUESTION_TARGET_BEGIN = "--- BEGIN ASSIGNED QUESTION TARGET (REQUIRED FOCUS) ---"
QUESTION_TARGET_END = "--- END ASSIGNED QUESTION TARGET (REQUIRED FOCUS) ---"

COMPETITOR_CONCEPTS_BEGIN = "--- BEGIN POSSIBLE COMPETING CONCEPTS (INFORMATION ONLY) ---"
COMPETITOR_CONCEPTS_END = "--- END POSSIBLE COMPETING CONCEPTS (INFORMATION ONLY) ---"
NO_COMPETITOR_CONCEPTS_TEXT = (
    "No candidate competing concepts were found in the supplied evidence besides the assigned target's own."
)

ALREADY_TESTED_BEGIN = "--- BEGIN ALREADY-TESTED KNOWLEDGE IN THIS CATEGORY (INFORMATION ONLY) ---"
ALREADY_TESTED_END = "--- END ALREADY-TESTED KNOWLEDGE IN THIS CATEGORY (INFORMATION ONLY) ---"
NO_ALREADY_TESTED_TEXT = (
    "No questions have been generated for this category yet - there is nothing to avoid overlapping with."
)


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


def format_question_target(target: QuestionTarget) -> str:
    """Deterministically format an assigned WP-025 ``QuestionTarget`` for
    the generation prompt.

    Contains only the topic/factual-focus information already present on
    the target - never the target's ``supporting_evidence_chunk_ids``
    (those are canonical provenance already established during planning,
    not something the generation prompt needs restated), and the target
    itself is never modified.
    """
    body = f"Topic: {target.topic}\nFactual Focus: {target.factual_focus}"
    return f"{QUESTION_TARGET_BEGIN}\n{body}\n{QUESTION_TARGET_END}"


def format_competitors(competitors: Sequence[CompetitorCandidate]) -> str:
    """Deterministically format WP-031's deterministically-discovered
    competitor candidates for the generation prompt.

    Caller-supplied order is preserved exactly (already the discovery
    function's own deterministic ranking - see
    ``exam_generator.generation.competitors.discover_competitors()``).
    An empty sequence is explicitly allowed and renders an honest
    "none found" sentinel rather than omitting the section - the same
    fail-honest pattern already used for historical references and
    course-book evidence.
    """
    if not competitors:
        return f"{COMPETITOR_CONCEPTS_BEGIN}\n{NO_COMPETITOR_CONCEPTS_TEXT}\n{COMPETITOR_CONCEPTS_END}"

    entries = "\n".join(
        f"[Competitor {position}] (relationship: {competitor.relationship_relevance}) {competitor.concept}"
        for position, competitor in enumerate(competitors, start=1)
    )
    return f"{COMPETITOR_CONCEPTS_BEGIN}\n{entries}\n{COMPETITOR_CONCEPTS_END}"


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


def format_category_coverage(coverage: CategoryCoverage) -> str:
    """Deterministically format WP-034's ``CategoryCoverage`` for the
    target-planning prompt - information only, never an instruction to
    reject anything (WP-034 section 6: "coverage does NOT become another
    validator").

    An empty coverage (no existing questions yet, or no coverage could be
    determined) renders an honest "nothing tested yet" sentinel rather
    than omitting the section - the same fail-honest pattern already used
    for historical references, course-book evidence, and competitor
    concepts.
    """
    if not coverage.tested_concepts and not coverage.tested_relationship_types:
        return f"{ALREADY_TESTED_BEGIN}\n{NO_ALREADY_TESTED_TEXT}\n{ALREADY_TESTED_END}"

    lines: list[str] = []
    if coverage.tested_concepts:
        lines.append("Already-tested concepts (the correct answer of each question already generated for this category):")
        lines.extend(f"- {concept}" for concept in coverage.tested_concepts)
    if coverage.tested_relationship_types:
        lines.append("Already-tested relationship types:")
        lines.extend(f"- {relationship_type}" for relationship_type in coverage.tested_relationship_types)

    body = "\n".join(lines)
    return f"{ALREADY_TESTED_BEGIN}\n{body}\n{ALREADY_TESTED_END}"


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
