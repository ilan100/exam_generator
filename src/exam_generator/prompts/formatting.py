"""Deterministic, non-LLM formatting of already-selected domain objects into
prompt text.

Formatting only: this module never retrieves, ranks, filters, sorts, or
deduplicates evidence/references - callers supply exactly what should
appear, in the order it should appear, and that order is preserved exactly.
"""

from __future__ import annotations

import re
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


_NO_NAMED_ENTITY_REQUIREMENT_TEXT = (
    "No additional answer-identity requirement applies to this target - the correct answer "
    "may describe any evidence-supported aspect of it (its function, a property, a "
    "relationship, or the entity itself), exactly per the general instructions above."
)


def format_target_answer_requirement(target: QuestionTarget) -> str:
    """WP-040: deterministically format the answer-identity requirement
    for ``target``, based only on ``target.named_entity_target`` -
    information already decided by planning (never re-derived here, never
    an LLM judgment). Honestly renders
    ``_NO_NAMED_ENTITY_REQUIREMENT_TEXT`` (never silently omits the
    section) when ``target`` is not known to be a named entity - matching
    this project's established fail-honest-sentinel convention (e.g.
    ``format_category_coverage()``'s "nothing tested yet").

    When ``target.named_entity_target`` is true, states the target
    concept's own text as the required answer identity and explicitly
    prohibits the specific substitution shapes WP-039's live pilot
    actually observed (a functional description, a property, a related
    or sibling structure, a neighboring entity, or the broader system/
    category) - never a language requirement of any kind (WP-040 section
    16: "the key requirement is identity of the target, not a particular
    language" - the correct answer may be phrased in whichever language
    generation judges natural, exactly as before this WP).
    """
    if not target.named_entity_target:
        return _NO_NAMED_ENTITY_REQUIREMENT_TEXT

    topic = target.topic
    return (
        f"TARGET CONCEPT = {topic}\n\n"
        f"The correct answer must identify TARGET CONCEPT ({topic}) itself - not merely "
        "describe it. Do not use, as the correct answer, a description of its function, an "
        "effect it causes, a property it has, a related or sibling structure, a neighboring "
        "anatomical entity, or the broader system/category it belongs to - even if that "
        "description is itself factually true and evidence-supported.\n"
        f"The question may still test any evidence-supported aspect of {topic} (its role, "
        "location, connections, or distinguishing characteristics) - the requirement is only "
        f"that the correct ANSWER choice itself names {topic}, not a description of it."
    )


#: WP-041: a deterministic "is this text already expressible in Latin/
#: ASCII script" check - intentionally a separate, simpler definition
#: from ``planning.concept_inventory._CANDIDATE_LINE_PATTERN`` (which
#: additionally gates extraction-candidate-line detection with a
#: narrower charset) rather than importing it: ``exam_generator.planning``
#: already imports from ``exam_generator.prompts`` (established since
#: WP-034's ``CategoryCoverage`` precedent), so importing the reverse
#: direction here would create a circular import. The two checks serve
#: different purposes and do not need to be byte-identical - this one
#: only asks whether ``text`` can be represented without any non-ASCII
#: (i.e. non-Latin/non-Hebrew-only) character, which is exactly the
#: WP-041 question ("is an English representation available").
_ASCII_PATTERN = re.compile(r"^[\x00-\x7f]+$")


def _is_english_representable(text: str) -> bool:
    """WP-041 section 7: true if ``text`` is already fully expressible in
    Latin/ASCII script - never a translation judgment, purely whether the
    text as given already IS an English/Latin representation. For every
    real pilot-category ``named_entity_target=True`` target, this is true
    by construction (``target.topic`` is always the concept's own
    structurally-extracted, pure-ASCII text - the same invariant WP-040's
    ``named_entity_target`` itself already relies on) - this function
    re-derives it explicitly anyway, rather than trusting the invariant
    blindly, so it degrades honestly rather than crashing or guessing if
    ever called with a hypothetical non-ASCII target."""
    stripped = text.strip()
    return bool(stripped) and bool(_ASCII_PATTERN.match(stripped))


_NO_TARGET_LANGUAGE_REQUIREMENT_TEXT = (
    "No additional target-language requirement applies to this target - follow the general "
    "Hebrew-language instructions above."
)


def format_target_language_requirement(target: QuestionTarget) -> str:
    """WP-041: deterministically format the English-first target-language
    requirement for ``target``, based only on ``target.named_entity_target``
    and whether ``target.topic`` is already English-representable - never
    a bilingual-pairing search, never a translation, never an LLM
    judgment (section 5's explicit prohibition on fuzzy/semantic/
    transliteration matching, and section 9's "if such an association
    cannot be established safely, do not guess").

    Honestly renders ``_NO_TARGET_LANGUAGE_REQUIREMENT_TEXT`` (never
    silently omits the section) when ``target`` is not known to be a
    named entity - the same fail-honest-sentinel convention
    ``format_target_answer_requirement()`` already established.

    When ``target`` is a named entity with an English-representable
    topic (true for every real pilot-category target, by construction -
    see ``_is_english_representable()``), states the requirement
    explicitly: use the target's own English text verbatim, for both the
    correct answer and any reference to the target within the question
    itself, never translating or transliterating it into Hebrew - this
    is the deterministic fix for the exact live-observed WP-040 case
    (``Corpos Striatum`` correctly identified, but in Hebrew,
    ``קורפוס סטריאטום``, which WP-038's coverage matching could not
    recognize against the English-stored concept).

    When ``target`` is a named entity whose topic is NOT English-
    representable (never actually produced by the current pilot-category
    extraction path, which only ever extracts pure-ASCII text - but
    handled honestly rather than assumed impossible), states that Hebrew
    is permitted and explicitly forbids inventing an English translation
    that is not already present in the evidence.
    """
    if not target.named_entity_target:
        return _NO_TARGET_LANGUAGE_REQUIREMENT_TEXT

    topic = target.topic
    if _is_english_representable(topic):
        return (
            f"TARGET LANGUAGE = English\n\n"
            f"An English representation of TARGET CONCEPT is available: {topic}. Use it. The "
            "question itself may still be written in Hebrew per the general instructions above, "
            f"but wherever you reference TARGET CONCEPT by name within the question, and for the "
            f"correct answer choice itself, use the English representation ({topic}) exactly as "
            "given - do not translate or transliterate it into Hebrew, even though the "
            "surrounding evidence and question text are primarily Hebrew. Do not substitute a "
            f"different English form (an abbreviation or alternate spelling) than the one given "
            f"here ({topic})."
        )
    return (
        "TARGET LANGUAGE = Hebrew\n\n"
        "No English representation is available for this target - the Hebrew representation "
        "already present in the supplied evidence is required for the correct answer. Do not "
        "invent or guess an English translation or transliteration that is not already present "
        "in the evidence."
    )


_NO_TARGET_EVIDENCE_ROLE_TEXT = (
    "No additional evidence-role note applies to this target - it is the subject of its own "
    "descriptive evidence, per the general instructions above."
)


def format_target_evidence_role(target: QuestionTarget) -> str:
    """WP-043 Part B: deterministically format an explicit note about the
    target's own role within its evidence, based only on
    ``target.is_source_role`` (see
    ``planning.target_role.detect_source_evidence_role()`` - a narrow,
    keyword-proximity check, never a general relationship extractor).

    WP-042's diagnostic investigation found that when a target's evidence
    positions it as the *source* of another, more salient described
    entity (e.g. ``Basillar artery``, labeled as the "source:" of
    ``Superior Cerebellar Artery`` in its own evidence), generation
    repeatedly constructed a question of the form "which artery supplies
    X" - a shape whose evidence-supported answer is the *other*, more
    salient entity, not the assigned target - and grounding correctly and
    repeatedly rejected it. This note makes the target's own evidence
    role explicit so generation can construct a question the target's
    evidence actually supports as an answer (e.g. "which artery is the
    source/origin of Y"), without requiring a new validator, a relaxed
    grounding check, or a general source/destination relationship
    extractor.

    Honestly renders ``_NO_TARGET_EVIDENCE_ROLE_TEXT`` (never silently
    omits the section) for the ordinary case (``is_source_role=False`` -
    true for the overwhelming majority of targets) - the same fail-
    honest-sentinel convention every other WP-040/041 formatting function
    already established.
    """
    if not target.is_source_role:
        return _NO_TARGET_EVIDENCE_ROLE_TEXT

    topic = target.topic
    downstream = target.source_relationship_entity
    if downstream is not None:
        # WP-044 Part B: the concrete downstream entity name, deterministically
        # identified by planning.target_role.extract_source_relationship_entity() -
        # a structural strengthening of this same note (named, not merely
        # described), per WP-044 section 6/13's "state the specific
        # relationship, not just a role label" architectural direction.
        return (
            f"TARGET EVIDENCE ROLE = SOURCE\n\n"
            f"The supplied evidence explicitly labels TARGET CONCEPT ({topic}) as the source/origin "
            f"of a separately-named entity: {downstream}. Do not construct a question whose "
            f"evidence-supported answer would be {downstream} rather than {topic} (for example, do "
            f"not ask which entity supplies or produces {downstream} if the evidence instead "
            f"supports {topic}, not {downstream}, as the upstream/originating entity for that "
            f"relationship). Construct the question so its evidence-supported answer is {topic} - "
            f"for example, which entity is the source or origin of {downstream}. The correct answer "
            f"choice must name {topic}, never {downstream}."
        )
    return (
        f"TARGET EVIDENCE ROLE = SOURCE\n\n"
        f"The supplied evidence describes TARGET CONCEPT ({topic}) as the source/origin of "
        "another, separately-named entity - not as the entity being supplied, fed, or acted upon. "
        f"Do not construct a question whose natural evidence-supported answer would be that other "
        f"entity rather than {topic} itself (for example, do not ask which entity supplies or "
        f"produces some downstream effect if the evidence instead supports {topic} as the "
        "upstream/originating entity for that effect). Construct the question around the "
        f"relationship the evidence actually supports {topic} as the correct answer to - for "
        f"example, which entity is the source, origin, or starting point of the described "
        "downstream entity."
    )


_NO_ENUMERATION_REQUIREMENT_TEXT = (
    "No additional enumeration-member note applies to this target - follow the general 'Testing "
    "enumeration or classification targets' guidance above only if the evidence itself happens to "
    "have that shape."
)


def format_target_enumeration_requirement(target: QuestionTarget) -> str:
    """WP-044 Part A: deterministically format an explicit, target-specific
    reinforcement of the existing general "testing enumeration or
    classification targets" prompt guidance, based only on
    ``target.is_enumeration_member`` (see
    ``planning.concept_anchor.detect_enumeration_member_shape()`` - a
    narrow, deterministic cue-phrase-proximity check, never a general
    enumeration classifier).

    WP-043's live pilot found the general, always-present prompt guidance
    alone insufficient for a target whose own anchored evidence happens to
    be exactly an enumeration-introduction sentence (the real corpus
    ``Corpos Striatum`` shape) - this makes the target's own situation
    explicit, the same "prompt instruction is no longer enough on its own,
    make the specific case explicit" direction WP-043 Part B already
    established for source-role targets (see
    ``format_target_evidence_role()``).

    Honestly renders ``_NO_ENUMERATION_REQUIREMENT_TEXT`` (never silently
    omits the section) for the ordinary, non-enumeration case - the same
    fail-honest-sentinel convention every WP-040/041/043 formatting
    function already established. Never produced for a target whose
    enumeration evidence provided no member-specific distinguishing
    content at all - such a target is never built in the first place (see
    ``planning.concept_anchor.is_enumeration_evidence_insufficient()``,
    used by the planner to skip it entirely rather than assign it).
    """
    if not target.is_enumeration_member:
        return _NO_ENUMERATION_REQUIREMENT_TEXT

    topic = target.topic
    return (
        f"ENUMERATION-MEMBER TARGET = {topic}\n\n"
        f"The supplied evidence introduces TARGET CONCEPT ({topic}) as one member of a list of "
        f"several similarly-described items. Do not ask a generic membership question whose "
        f"evidence-supported answer could equally be a different member of that same list (for "
        f"example, do not ask 'which of the following belongs to X' if the evidence does not "
        f"distinguish {topic} from its siblings for that exact question). Use only the evidence-"
        f"supported information specific to {topic} itself (a distinguishing property, function, "
        "location, or relationship) as required by the general 'Testing enumeration or "
        f"classification targets' guidance above - this note only confirms that guidance applies "
        f"to this specific target."
    )


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
