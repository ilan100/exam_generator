"""The first real question-generation path.

Connects existing infrastructure only - no competing retrieval, prompt, or
LLM abstraction is introduced here:

    canonical category
           v
    student-summary retrieval          (exam_generator.retrieval, WP-006)
           v
    historical style reference         (exam_generator.historical, WP-003; STYLE_SIMILAR only)
           v
    prompt construction                (exam_generator.prompts, WP-008)
           v
    structured LLM call                (exam_generator.llm, WP-007)
           v
    CandidateQuestion                  (exam_generator.models, WP-002)

This is generation only: the returned ``CandidateQuestion`` has not been
independently grounding/MCQ/category/quality/textbook validated - that is
WP-010 and later.
"""

from __future__ import annotations

from exam_generator.config import load_llm_config
from exam_generator.generation.errors import (
    GenerationContextError,
    InvalidGeneratedOutputError,
    MissingEvidenceError,
    MissingHistoricalReferenceError,
)
from exam_generator.generation.competitors import discover_competitors
from exam_generator.generation.relationship import extract_relationship
from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.llm import LLMProfile, LLMProvider, build_llm_provider
from exam_generator.models import (
    CandidateQuestion,
    GeneratedQuestionResponse,
    GenerationMode,
    HistoricalStyleReference,
    QuestionTarget,
    SourceEvidenceChunk,
)
from exam_generator.prompts import GenerationPromptContext, PromptId, PromptRepository, build_prompt_messages
from exam_generator.retrieval import (
    CategoryResolver,
    FactualRetrievalIndex,
    build_category_resolver,
    build_student_summary_retrieval_index,
    retrieve_for_category,
)


def _select_historical_reference(
    historical_repository: HistoricalQuestionRepository, canonical_category: str
) -> HistoricalStyleReference:
    """Deterministic ``STYLE_SIMILAR`` historical-reference selection policy
    for WP-009: the first historical question for the canonical category,
    in workbook order (``HistoricalQuestionRepository.questions_for_category()``
    already preserves that order). No randomness, no diversity/retry
    awareness - see WP-013 for that.
    """
    candidates = historical_repository.questions_for_category(canonical_category)
    if not candidates:
        raise MissingHistoricalReferenceError(
            f"No historical style reference available for category {canonical_category!r}"
        )
    return candidates[0]


def _resolve_generated_evidence_refs(
    evidence_refs: list[int], *, source_evidence: tuple[SourceEvidenceChunk, ...]
) -> list[str]:
    """Strictly validate the LLM's call-local ``evidence_refs`` (WP-024)
    against the evidence actually supplied to this generation call, then
    deterministically resolve them to genuine canonical
    ``SourceEvidenceChunk.chunk_id`` values - never trusting a
    caller-supplied string, mirroring WP-022's grounding/textbook pattern.

    Fails closed (raises, rather than drops/repairs/clamps/fuzzy-matches)
    on any reference outside ``1..len(source_evidence)`` - including zero,
    negative, and out-of-range values, all treated identically. A repeated
    reference (e.g. ``[1, 1, 3]``) resolves to its canonical id only once,
    preserving first-occurrence order - it is not evidence of anything
    beyond what a single citation already establishes.
    """
    invalid_refs = [ref for ref in evidence_refs if not (1 <= ref <= len(source_evidence))]
    if invalid_refs:
        raise InvalidGeneratedOutputError(
            f"Generated response claims evidence reference(s) outside the supplied range "
            f"1..{len(source_evidence)}: {invalid_refs}"
        )
    deduplicated_refs = list(dict.fromkeys(evidence_refs))
    return [source_evidence[ref - 1].chunk_id for ref in deduplicated_refs]


def _normalize_answer_text(text: str) -> str:
    """Deterministic normalization for the WP-044 target-role consistency
    check below - collapse whitespace, case-fold. A small, local
    implementation, not imported from
    ``exam_generator.planning.concept_inventory.normalize_concept_text``
    (which is byte-identical in behavior): ``exam_generator.planning``
    already imports from ``exam_generator.generation`` (this module's own
    ``InvalidGeneratedOutputError``/``MissingEvidenceError`` -
    ``planning.planner``'s established WP-025 dependency direction), so
    importing the reverse direction here would create a circular import -
    the same reasoning ``prompts.formatting._is_english_representable()``'s
    own docstring already documents for an analogous case."""
    return " ".join(text.split()).casefold()


def _validate_target_role_consistency(response: GeneratedQuestionResponse, *, target: QuestionTarget) -> None:
    """WP-044 Part B: deterministic blueprint/target-role consistency
    check - a structural extension of the existing blueprint mechanism
    (WP-044 section 16: "extend blueprint validation... deterministic
    validation where possible... do not add an LLM validator"), not a new
    entry in the five-validator pipeline (``exam_generator.validation``,
    untouched by this WP).

    When ``target.is_source_role`` and a downstream entity was
    deterministically identified (``target.source_relationship_entity`` -
    see ``planning.target_role.extract_source_relationship_entity()``),
    rejects a candidate whose own correct-answer text names that
    downstream entity rather than the assigned target itself - the exact,
    structurally-detectable shape of the failure WP-042/WP-043 diagnosed
    (generation constructs a question whose evidence-supported answer is
    the downstream entity, not the source-role target, even though the
    target-answer-identity requirement asks for the target's own name).

    Deterministic text comparison only (the same normalization shape
    already used for concept-identity matching elsewhere in this
    codebase) - never an LLM judgment, never inspecting the model's own
    free-text blueprint reasoning (too unconstrained to match safely).
    Raises the same ``InvalidGeneratedOutputError`` category
    ``_validate_generated_provenance`` already raises for a fabricated
    evidence claim, consuming this attempt exactly as that check already
    does - no new retry loop, no relaxed or additional validator.

    A no-op when ``target`` is not a source-role target, or when no
    downstream entity could be identified (nothing to check against) -
    the ordinary case for the overwhelming majority of targets.
    """
    if not target.is_source_role or target.source_relationship_entity is None:
        return

    correct_answer_text = response.answers[response.correct_answer - 1]
    downstream_normalized = _normalize_answer_text(target.source_relationship_entity)
    if downstream_normalized in _normalize_answer_text(correct_answer_text):
        raise InvalidGeneratedOutputError(
            f"Generated response's correct answer {correct_answer_text!r} names the downstream "
            f"entity {target.source_relationship_entity!r} rather than the assigned source-role "
            f"target {target.topic!r} - target/tested-relationship/required-answer inconsistency "
            "(WP-044 Part B)"
        )


def _validate_distractor_containment(response: GeneratedQuestionResponse, *, target: QuestionTarget) -> None:
    """WP-046: deterministic post-generation candidate-distractor
    consistency check, for named-entity targets only.

    WP-045's diagnosis found that a *pre-generation*, evidence-shape-only
    signal for this ambiguity family (a target textually contained in, or
    containing, another concept anywhere in the category's inventory) is
    unsafe - it produces a confirmed false positive (`"Inferior Cerebellar
    Artery (PICA)"` vs. `"Posterior inferior cerebellar artery (PICA)"`,
    the same real entity extracted twice, not a genuine hierarchy) and
    would also have blocked genuinely-successful generation attempts for
    `Corticospinal Tract` (WP-045 section 4's own live counter-example: the
    identical target, identical evidence, unmodified code, both failed and
    succeeded across two rounds of the same pilot, depending only on which
    distractors that specific attempt happened to choose).

    WP-046's own generalization study found the *narrower*, *post*-
    generation form of this same idea to be safe: checking only the
    *actual, final* correct-answer text against the *actual, final*
    distractor texts a candidate already contains - never the broader
    category inventory - explains every real, confirmed ambiguity
    rejection observed for `Corticospinal Tract` (both of WP-045's own
    live rejections citing a shared child as also-supported involved a
    distractor whose text contains the correct answer's own text, e.g.
    `"Lateral Corticospinal Tract"` contains `"Corticospinal Tract"`), and
    produces zero false positives against every other real accepted
    candidate examined (including the exact `Inferior Cerebellar Artery
    (PICA)` case the pre-generation signal incorrectly flagged - its own
    actual generated distractors never included the confusable duplicate
    entity, so this check correctly never fires for it).

    Deterministic text comparison only (the same normalization and plain-
    substring-containment shape `_validate_target_role_consistency()`
    above already uses) - never an LLM judgment, never a semantic/fuzzy
    match, never inspecting the model's own free-text blueprint reasoning.
    Rejects a candidate when the correct answer's own text and any one
    distractor's own text stand in a containment relationship in either
    direction - the exact, evidence-confirmed shape of a real, structural
    ambiguity risk (a more general or more specific form of the same named
    entity chosen as both the answer and a distractor), not a general
    "detect ambiguity" classifier. Raises the same
    ``InvalidGeneratedOutputError`` category the existing provenance/
    target-role checks already raise, consuming this attempt exactly as
    those checks already do - no new retry loop, no validator change.

    Scoped to ``target.named_entity_target`` only (the same precedent
    every WP-040/043/044 mechanism already established): for a free-text,
    non-named-entity answer, incidental substring overlap is far more
    likely to be coincidental prose rather than a genuine shared-entity
    risk, so this check would not be safely evidence-grounded there and
    is not attempted.
    """
    if not target.named_entity_target:
        return

    correct_answer_text = response.answers[response.correct_answer - 1]
    normalized_correct = _normalize_answer_text(correct_answer_text)
    for position, answer_text in enumerate(response.answers, start=1):
        if position == response.correct_answer:
            continue
        normalized_distractor = _normalize_answer_text(answer_text)
        if normalized_distractor in normalized_correct or normalized_correct in normalized_distractor:
            raise InvalidGeneratedOutputError(
                f"Generated response's correct answer {correct_answer_text!r} and distractor "
                f"{answer_text!r} stand in a textual containment relationship - a structural "
                "ambiguity risk (one may be a more general or more specific form of the same "
                "named entity), not a genuinely independent wrong answer (WP-046)"
            )


def _validate_generated_provenance(
    response: GeneratedQuestionResponse,
    *,
    source_evidence: tuple[SourceEvidenceChunk, ...],
    generation_mode: GenerationMode,
    historical_reference: HistoricalStyleReference | None,
) -> None:
    """Reject any provenance claim the LLM makes that does not correspond to
    what was actually supplied - a generated response is never trusted
    merely because it parsed as structured output. ``evidence_refs``
    resolution (WP-024) already fails closed on any reference the model
    was not actually shown; nothing further is required of it here beyond
    triggering that resolution - ``CandidateQuestion`` itself carries no
    evidence field to populate (unchanged since WP-009/WP-015)."""
    _resolve_generated_evidence_refs(response.evidence_refs, source_evidence=source_evidence)

    if generation_mode == GenerationMode.INDEPENDENT:
        if response.historical_reference_id is not None:
            raise InvalidGeneratedOutputError(
                "INDEPENDENT generation must not claim a historical_reference_id, "
                f"got {response.historical_reference_id!r}"
            )
        return

    # STYLE_SIMILAR: a claimed historical_reference_id must match the one
    # actually supplied. Reporting none is tolerated (the claim is optional -
    # see GeneratedQuestionResponse); reporting a different id is not.
    if response.historical_reference_id is not None:
        supplied_id = historical_reference.historical_question_id if historical_reference else None
        if response.historical_reference_id != supplied_id:
            raise InvalidGeneratedOutputError(
                f"Generated response claims historical_reference_id "
                f"{response.historical_reference_id!r}, but the historical reference "
                f"actually supplied was {supplied_id!r}"
            )


class QuestionGenerator:
    """Application-facing entry point for one candidate-generation call.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks. Use
    ``QuestionGenerator.from_default_configuration()`` for the normal
    application wiring against real project configuration/data.
    """

    def __init__(
        self,
        *,
        category_resolver: CategoryResolver,
        student_summary_index: FactualRetrievalIndex,
        historical_repository: HistoricalQuestionRepository,
        prompt_repository: PromptRepository,
        llm_provider: LLMProvider,
    ) -> None:
        self._category_resolver = category_resolver
        self._student_summary_index = student_summary_index
        self._historical_repository = historical_repository
        self._prompt_repository = prompt_repository
        self._llm_provider = llm_provider

    @classmethod
    def from_default_configuration(cls) -> "QuestionGenerator":
        """Construct the normal application wiring: the real category
        resolver, the real student-summary retrieval index (configured
        ``top_k``), the real historical repository, the real production
        prompt repository, and the configured OpenAI provider.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``build_llm_provider`` at this point, not earlier).
        """
        return cls(
            category_resolver=build_category_resolver(),
            student_summary_index=build_student_summary_retrieval_index(),
            historical_repository=HistoricalQuestionRepository.from_default_location(),
            prompt_repository=PromptRepository.from_default_location(),
            llm_provider=build_llm_provider(load_llm_config()),
        )

    def generate_candidate_question(
        self, *, category: str, generation_mode: GenerationMode, target: QuestionTarget
    ) -> CandidateQuestion:
        """Generate exactly one candidate question for ``category`` using
        ``generation_mode``, testing the assigned ``target`` (WP-025 -
        planned before generation begins, so multiple questions requested
        from the same category are diverse by construction rather than by
        after-the-fact rejection).

        Makes exactly one LLM call (``LLMProfile.GENERATION``) - no semantic
        retry loop. Performs no grounding/MCQ/category/quality/textbook
        validation; the returned candidate is not yet exam-ready.

        Since WP-044, also runs a deterministic target-role consistency
        check (``_validate_target_role_consistency()``); since WP-046, also
        runs a deterministic distractor-containment check
        (``_validate_distractor_containment()``) - all alongside the
        existing provenance check, all raising
        ``InvalidGeneratedOutputError`` for a structurally-invalid
        response, never a new validator.
        """
        if not isinstance(generation_mode, GenerationMode):
            raise GenerationContextError(f"Unsupported generation mode: {generation_mode!r}")

        canonical_category = self._category_resolver.resolve(category)

        retrieval_results = retrieve_for_category(
            canonical_category, self._category_resolver, self._student_summary_index
        )
        source_evidence = tuple(result.chunk for result in retrieval_results)
        if not source_evidence:
            raise MissingEvidenceError(
                f"No student-summary evidence retrieved for category {canonical_category!r}"
            )

        historical_reference: HistoricalStyleReference | None = None
        if generation_mode == GenerationMode.STYLE_SIMILAR:
            historical_reference = _select_historical_reference(
                self._historical_repository, canonical_category
            )

        relationship = extract_relationship(target)
        context = GenerationPromptContext(
            category=canonical_category,
            generation_mode=generation_mode,
            source_evidence=source_evidence,
            target=target,
            relationship=relationship,
            competitors=discover_competitors(target=target, relationship=relationship, source_evidence=source_evidence),
            historical_reference=historical_reference,
        )

        messages = build_prompt_messages(
            system_template=self._prompt_repository.get(PromptId.SYSTEM),
            task_template=self._prompt_repository.get(PromptId.QUESTION_GENERATION),
            variables=context.render_variables(),
        )

        response = self._llm_provider.generate_structured(
            messages=messages,
            response_model=GeneratedQuestionResponse,
            profile=LLMProfile.GENERATION,
        )

        _validate_generated_provenance(
            response,
            source_evidence=source_evidence,
            generation_mode=generation_mode,
            historical_reference=historical_reference,
        )
        _validate_target_role_consistency(response, target=target)
        _validate_distractor_containment(response, target=target)

        return CandidateQuestion(
            question=response.question,
            answers=response.answers,
            correct_answer=response.correct_answer,
            category=canonical_category,
            generation_mode=generation_mode,
        )
