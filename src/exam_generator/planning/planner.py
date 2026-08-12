"""Evidence-grounded question-target planning (WP-025).

Diversity between multiple questions requested from the same category is
achieved primarily BY CONSTRUCTION: before any question is generated, this
module identifies up to the requested number of distinct, evidence-
supported factual targets for a category, so each later
``QuestionGenerator`` call can be pointed at a specific, already-distinct
focus rather than generating arbitrary questions and relying on rejection
to enforce diversity after the fact.

Connects existing infrastructure only - no competing retrieval, prompt, or
LLM abstraction is introduced here:

    canonical category
           v
    student-summary retrieval          (exam_generator.retrieval, WP-006)
           v
    prompt construction                (exam_generator.prompts, WP-008)
           v
    structured LLM call                (exam_generator.llm, WP-007)
           v
    local evidence_refs -> canonical chunk ids   (WP-022/WP-024 pattern)
           v
    QuestionTarget(s)                  (exam_generator.models, WP-025)

This is planning only: it never generates a final question, validates a
candidate, decides acceptance, or performs orchestration/output - that
remains ``QuestionGenerator``/``QuestionProducer``/``ExamOrchestrator``.
"""

from __future__ import annotations

from exam_generator.config import load_llm_config
from exam_generator.generation import InvalidGeneratedOutputError, MissingEvidenceError
from exam_generator.llm import LLMProfile, LLMProvider, build_llm_provider
from exam_generator.models import (
    CategoryCoverage,
    PlannedQuestionTargetResponse,
    QuestionTarget,
    QuestionTargetPlanningResponse,
    SourceEvidenceChunk,
)
from exam_generator.planning.concept_anchor import (
    anchor_concept_evidence,
    detect_enumeration_member_shape,
    is_enumeration_evidence_insufficient,
    is_factual_focus_sufficient,
    refine_concept_inventory,
)
from exam_generator.planning.concept_identity import concept_identities_for_inventory, concept_identity_matches_text
from exam_generator.planning.concept_inventory import PILOT_CATEGORIES, InventoryConcept
from exam_generator.planning.target_role import detect_source_evidence_role, extract_source_relationship_entity
from exam_generator.prompts import PromptId, PromptRepository, QuestionTargetPlanningPromptContext, build_prompt_messages
from exam_generator.retrieval import (
    CategoryResolver,
    FactualRetrievalIndex,
    build_category_resolver,
    build_student_summary_retrieval_index,
    retrieve_for_category,
)


def _select_remaining_concepts(
    inventory: tuple[InventoryConcept, ...],
    *,
    coverage: CategoryCoverage,
    count: int,
    chunk_text_by_id: dict[str, str],
) -> list[InventoryConcept]:
    """Deterministically exclude every inventory concept already tested,
    then return up to ``count`` of whatever remains, in the inventory's
    own (first-occurrence, retrieval-rank) order. Never reorders, never
    re-ranks, never guesses at a substitute when fewer than ``count``
    remain.

    Since WP-038, "already tested" is decided by each concept's
    ``ConceptIdentity`` (``planning/concept_identity.py``) - its own text
    plus deterministic normalizations plus any genuinely evidence-derived
    alternate-language form - rather than WP-034/036's plain exact-text
    comparison. This still performs exact matching only (WP-036 section 6:
    "use exact matching only... do not implement synonym handling") -
    WP-038 does not introduce fuzzy/semantic matching, it only widens the
    set of forms a concept's own identity legitimately includes, and only
    when that widening is itself derived from real, adjacent evidence
    rather than guessed.
    """
    identities = concept_identities_for_inventory(inventory, chunk_text_by_id=chunk_text_by_id)
    remaining = [
        concept
        for concept in inventory
        if not any(
            concept_identity_matches_text(identities[concept.concept], tested_concept)
            for tested_concept in coverage.tested_concepts
        )
    ]
    return remaining[:count]


def _resolve_planned_targets(
    raw_targets: list[PlannedQuestionTargetResponse],
    *,
    category: str,
    source_evidence: tuple[SourceEvidenceChunk, ...],
) -> list[QuestionTarget]:
    """Strictly validate every raw target's call-local ``evidence_refs``
    (WP-025, mirroring WP-022/WP-024's proven local-reference pattern)
    against the evidence actually supplied to this planning call, then
    deterministically resolve them to genuine canonical
    ``SourceEvidenceChunk.chunk_id`` values.

    Fails closed on the *whole* response - a single invalid reference on
    any one target discards every target from this attempt, never
    partially repaired, exactly as WP-022/WP-024 never repair a
    partially-invalid response.
    """
    resolved: list[QuestionTarget] = []
    for target_id, raw in enumerate(raw_targets, start=1):
        invalid_refs = [ref for ref in raw.evidence_refs if not (1 <= ref <= len(source_evidence))]
        if invalid_refs:
            raise InvalidGeneratedOutputError(
                f"Planning response's target {target_id} claims evidence reference(s) outside "
                f"the supplied range 1..{len(source_evidence)}: {invalid_refs}"
            )
        deduplicated_refs = list(dict.fromkeys(raw.evidence_refs))
        chunk_ids = tuple(source_evidence[ref - 1].chunk_id for ref in deduplicated_refs)
        resolved.append(
            QuestionTarget(
                target_id=target_id,
                category=category,
                topic=raw.topic,
                factual_focus=raw.factual_focus,
                supporting_evidence_chunk_ids=chunk_ids,
            )
        )
    return resolved


class QuestionTargetPlanner:
    """Application-facing entry point for one category's target-planning
    call.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks. Use
    ``QuestionTargetPlanner.from_default_configuration()`` for the normal
    application wiring against real project configuration/data.
    """

    def __init__(
        self,
        *,
        category_resolver: CategoryResolver,
        student_summary_index: FactualRetrievalIndex,
        prompt_repository: PromptRepository,
        llm_provider: LLMProvider,
        pilot_categories: frozenset[str] = PILOT_CATEGORIES,
    ) -> None:
        self._category_resolver = category_resolver
        self._student_summary_index = student_summary_index
        self._prompt_repository = prompt_repository
        self._llm_provider = llm_provider
        self._pilot_categories = pilot_categories
        self._plan_history: list[tuple[str, tuple[QuestionTarget, ...]]] = []

    @classmethod
    def from_default_configuration(cls) -> "QuestionTargetPlanner":
        """Construct the normal application wiring: the real category
        resolver, the real student-summary retrieval index, the real
        production prompt repository, the configured OpenAI provider, and
        WP-036's real ``PILOT_CATEGORIES`` set.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``build_llm_provider`` at this point, not earlier) - note this is
        still required even though pilot categories never call the LLM
        for planning, since non-pilot categories (the large majority)
        still do.
        """
        return cls(
            category_resolver=build_category_resolver(),
            student_summary_index=build_student_summary_retrieval_index(),
            prompt_repository=PromptRepository.from_default_location(),
            llm_provider=build_llm_provider(load_llm_config()),
        )

    @property
    def plan_history(self) -> tuple[tuple[str, tuple[QuestionTarget, ...]], ...]:
        """Observability only (WP-025): every ``plan_targets()`` call's
        canonical category and resulting targets, in call order. Never
        used to make any application decision - mirrors WP-020/WP-021's
        existing retry-event observability pattern."""
        return tuple(self._plan_history)

    def plan_targets(
        self, *, category: str, count: int, coverage: CategoryCoverage | None = None
    ) -> list[QuestionTarget]:
        """Identify up to ``count`` distinct, evidence-supported question
        targets for ``category``.

        Makes exactly one LLM call (``LLMProfile.GENERATION``) - no retry
        loop of any kind (WP-025 section 10: diversity planning must not
        become a hidden retry loop, and must not consume WP-013's
        candidate-production attempt budget). May return fewer than
        ``count`` targets - never more - if the supplied evidence does not
        genuinely support that many distinct targets, or if the response
        claimed a local evidence reference never actually supplied (a
        stochastic per-call reliability issue that degrades to "zero
        usable targets from this attempt" rather than aborting the whole
        exam or being silently repaired). Never fabricates a target.

        Since WP-034, ``coverage`` (a deterministic summary of what the
        category's already-generated questions have already tested - see
        ``exam_generator.planning.coverage.extract_category_coverage()``)
        is threaded into the planning prompt as information, never a
        rejection mechanism: it may influence which target the LLM
        chooses, but a target overlapping with already-tested knowledge is
        never itself rejected or retried here - that would reintroduce the
        hidden retry loop WP-025 section 10 already forbids. Defaults to
        an empty ``CategoryCoverage()`` ("nothing tested yet") when omitted,
        so every pre-WP-034 caller continues to behave identically.

        Since WP-036, for the three categories in ``self._pilot_categories``
        only, this method takes an entirely different, LLM-free path: see
        ``_plan_targets_from_concept_inventory()``. ``coverage`` is reused
        there too, but to *filter a deterministic candidate list* rather
        than to inform an LLM prompt - the mechanism WP-034/035 concluded
        is necessary for coverage-awareness to actually constrain
        selection rather than merely describe it. Every category outside
        the pilot set is completely unaffected - the exact same LLM-based
        path documented above, byte-for-byte.

        Raises ``MissingEvidenceError`` (reused from
        ``exam_generator.generation`` - the identical condition, at the
        identical retrieval step, generation itself already treats as
        system-level) if no student-summary evidence can be retrieved for
        ``category`` at all - a genuine data-completeness problem,
        distinct from "evidence exists but doesn't support N distinct
        targets".
        """
        canonical_category = self._category_resolver.resolve(category)

        retrieval_results = retrieve_for_category(
            canonical_category, self._category_resolver, self._student_summary_index
        )
        source_evidence = tuple(result.chunk for result in retrieval_results)
        if not source_evidence:
            raise MissingEvidenceError(
                f"No student-summary evidence retrieved for category {canonical_category!r}"
            )

        resolved_coverage = coverage if coverage is not None else CategoryCoverage()

        if canonical_category in self._pilot_categories:
            targets = self._plan_targets_from_concept_inventory(
                canonical_category=canonical_category,
                count=count,
                source_evidence=source_evidence,
                coverage=resolved_coverage,
            )
            self._plan_history.append((canonical_category, tuple(targets)))
            return targets

        context = QuestionTargetPlanningPromptContext(
            category=canonical_category,
            count=count,
            source_evidence=source_evidence,
            coverage=resolved_coverage,
        )
        messages = build_prompt_messages(
            system_template=self._prompt_repository.get(PromptId.SYSTEM),
            task_template=self._prompt_repository.get(PromptId.QUESTION_TARGET_PLANNING),
            variables=context.render_variables(),
        )

        response = self._llm_provider.generate_structured(
            messages=messages,
            response_model=QuestionTargetPlanningResponse,
            profile=LLMProfile.GENERATION,
        )

        try:
            targets = _resolve_planned_targets(
                response.targets, category=canonical_category, source_evidence=source_evidence
            )
        except InvalidGeneratedOutputError:
            targets = []

        targets = targets[:count]
        self._plan_history.append((canonical_category, tuple(targets)))
        return targets

    def _plan_targets_from_concept_inventory(
        self,
        *,
        canonical_category: str,
        count: int,
        source_evidence: tuple[SourceEvidenceChunk, ...],
        coverage: CategoryCoverage,
    ) -> list[QuestionTarget]:
        """WP-036/037 pilot: deterministically construct up to ``count``
        targets directly from a concept inventory - **zero LLM calls**.

        1. Extract and refine a concept inventory from ``source_evidence``
           (``refine_concept_inventory()``, ``planning/concept_anchor.py``
           - WP-036's structure-first, marker-based, honest-fallback
           extraction, plus WP-037's additive extraction-artifact and
           category-self-restatement policies: never guesses a repair,
           excludes what it cannot safely repair or distinguish from the
           category's own name).
        2. Exclude every concept whose ``ConceptIdentity`` matches any of
           ``coverage.tested_concepts`` (WP-034/038, exact text match
           only, against a concept's own text plus its deterministic
           normalizations plus any genuinely evidence-derived alternate-
           language form - see ``planning/concept_identity.py``; WP-036
           section 6 still forbids synonym/semantic matching, and WP-038
           does not relax that - it only widens what a concept's own
           identity legitimately includes).
        3. Take up to ``count`` of whatever concepts remain, in the
           inventory's own deterministic (first-occurrence) order - never
           re-ranked, never chosen by any judgment call.
        4. Build one ``QuestionTarget`` per selected concept directly:
           ``topic`` from the concept's own deterministic extraction
           (never LLM-authored); ``factual_focus`` from WP-037's
           ``anchor_concept_evidence()`` - a narrow, line-bounded context
           around the concept's own occurrence, replacing WP-036's wide
           fixed-character window specifically to avoid pulling in a more
           salient neighboring fact (WP-036's live pilot showed this is
           what caused generation to repeatedly drift away from the
           assigned concept); ``supporting_evidence_chunk_ids`` the
           concept's own genuine source chunk id (stronger, more direct
           provenance than the LLM-planning path's self-reported
           ``evidence_refs``, since it is never a claim to verify - it is
           the exact chunk the concept was mechanically found in);
           ``named_entity_target=True`` (WP-040) - every concept reaching
           this path is, by construction, a named entity (this is exactly
           what ``extract_concept_inventory()``'s own structural filter
           extracts - WP-035/036's own "named entity" signal), so this is
           never a new judgment call, only surfacing a fact already
           established by extraction. The LLM-based planning path below
           never sets this (defaults to ``False``), since its own
           self-authored ``topic`` text is not reliably a named entity.

        Returns fewer than ``count`` targets - possibly zero - if the
        inventory (after refinement and coverage exclusion) does not
        contain enough remaining concepts (WP-036 section 11: "if the
        inventory becomes exhausted, report it honestly; do not invent
        concepts"), **or** (WP-043) if a remaining concept's evidence
        turns out to be insufficient even after the broader deterministic
        fallback (see below) - such a concept is skipped entirely, never
        used to build a target that could only produce an unsupported
        question. The caller (``_run_generation_cycle()``,
        ``category_generation/service.py``) already treats an empty
        target list as ``InsufficientDistinctTargetsError`` - the same
        honest, question-local failure category-inventory exhaustion
        belongs to; WP-036/037 deliberately reuse this existing failure
        type rather than inventing a new one for what is, from every
        caller's perspective, the same observable outcome ("no further
        distinct target available").

        WP-043 evidence-sufficiency and target-role handling: for each
        remaining concept, in order, until ``count`` targets are built or
        the remaining list is exhausted:

        1. Build the narrow ``factual_focus`` via ``anchor_concept_evidence()``,
           passing the concept's own ``source_line_indices`` when present
           (WP-039 trailing-reconstructed concepts - see that function's
           own docstring for the root-cause this fixes).
        2. If ``is_factual_focus_sufficient()`` finds only the concept's
           bare name (no surrounding context at all), retry with
           ``anchor_concept_evidence(..., broad=True)`` - a wider, but
           still same-source-evidence and still paragraph-bounded,
           deterministic fallback (WP-043 Part A).
        3. If still insufficient after the broader fallback, this concept
           is skipped entirely for this round - never used to build a
           target that could only produce an unsupported question (WP-043
           section 10: "do not invent context... conclude insufficient
           evidence"). The next remaining concept is tried instead.
        4. ``is_source_role`` (WP-043 Part B) is set via
           ``detect_source_evidence_role()`` - a narrow, deterministic
           keyword-proximity check (never a general relationship
           extractor) for whether the concept's own evidence positions it
           as the source of a different, more salient described entity
           (the real corpus ``Basillar artery`` shape WP-042's diagnostic
           investigation found). When set, ``source_relationship_entity``
           (WP-044 Part B) is also populated via
           ``extract_source_relationship_entity()`` - the deterministically
           -identified name of that other, downstream entity, when one can
           be found.
        5. ``is_enumeration_member`` (WP-044 Part A) is set via
           ``detect_enumeration_member_shape()`` once the final
           ``factual_focus`` has already passed
           ``is_enumeration_evidence_insufficient()`` below (i.e. this
           concept's evidence has enumeration shape but genuinely does
           carry member-specific distinguishing content, not merely the
           shared list intro).

        WP-044 additionally skips a concept entirely (like the WP-043
        insufficiency check above) when its final ``factual_focus`` has
        enumeration shape but provides no member-specific distinguishing
        content beyond the shared enumeration-introduction sentence (see
        ``is_enumeration_evidence_insufficient()`` - the real corpus
        ``Corpos Striatum`` shape WP-043's live pilot surfaced: evidence
        that is only ever "the basal nuclei contain several sub-
        structures," identical for every sibling in the same list, never
        genuinely distinguishing this one member). WP-044 section 11:
        "prefer missing over wrong" - such a concept could only produce a
        known-ambiguous generic membership question, so it is skipped
        rather than built into a target at all.
        """
        inventory = refine_concept_inventory(source_evidence)
        chunk_text_by_id = {chunk.chunk_id: chunk.text for chunk in source_evidence}
        remaining = _select_remaining_concepts(
            inventory, coverage=coverage, count=len(inventory), chunk_text_by_id=chunk_text_by_id
        )

        targets: list[QuestionTarget] = []
        for concept in remaining:
            if len(targets) >= count:
                break

            chunk_text = chunk_text_by_id[concept.evidence_chunk_id]
            factual_focus = anchor_concept_evidence(
                chunk_text=chunk_text, concept=concept.concept, source_line_indices=concept.source_line_indices
            )
            if not is_factual_focus_sufficient(factual_focus=factual_focus, concept=concept.concept):
                factual_focus = anchor_concept_evidence(
                    chunk_text=chunk_text,
                    concept=concept.concept,
                    source_line_indices=concept.source_line_indices,
                    broad=True,
                )
                if not is_factual_focus_sufficient(factual_focus=factual_focus, concept=concept.concept):
                    continue  # insufficient evidence even after fallback - skip, never force

            if is_enumeration_evidence_insufficient(factual_focus=factual_focus, concept=concept.concept):
                continue  # WP-044 Part A: shared enumeration intro only - skip, never force

            is_source_role = detect_source_evidence_role(chunk_text, concept.concept)
            source_relationship_entity = (
                extract_source_relationship_entity(chunk_text, concept.concept) if is_source_role else None
            )

            targets.append(
                QuestionTarget(
                    target_id=len(targets) + 1,
                    category=canonical_category,
                    topic=concept.concept,
                    factual_focus=factual_focus,
                    supporting_evidence_chunk_ids=(concept.evidence_chunk_id,),
                    named_entity_target=True,
                    is_source_role=is_source_role,
                    source_relationship_entity=source_relationship_entity,
                    is_enumeration_member=detect_enumeration_member_shape(
                        factual_focus=factual_focus, concept=concept.concept
                    ),
                )
            )
        return targets
