# WP-029 Architecture Proposal — Distractor Synthesis Architecture

**Status: design document only. No code, prompt, validator, or configuration file was modified to produce this proposal.**

## 0. Summary

WP-028's live evidence, and the architecture review that followed it, converge on one conclusion: the dominant remaining bottleneck is not planning (WP-025), not MCQ framing (WP-026), not grounding rigor (WP-027 - which is working correctly), and not internal blueprint reasoning (WP-028 - which does not reliably control output quality). It is **distractor synthesis**: generation still routinely produces at least one distractor that is either (a) also a genuinely correct answer to the exact question, or (b) constructed poorly enough (factually wrong in a confusing way, structurally weak, or ambiguous) to fail MCQ/quality/category validation.

This document recommends **Evidence-Constrained, Application-Guided Distractor Synthesis**: replace free-form distractor invention with a small set of *named, evidence-anchored transformations*, applied to the *specific evidence passage that grounds the correct answer* rather than to the evidence corpus in the abstract, with the *application* (not the model) increasingly responsible for choosing which transformation strategy to use per distractor. Crucially, this proposal does **not** ask the model to self-certify correctness (WP-028's failed mechanism) - it relies on WP-027's already-proven, already-free (zero additional LLM call) independent grounding check as the correctness backstop, unchanged. The improvement lever is making the *candidate* better before it reaches that check, not trusting the model's own claim that it already checked.

A 3-phase migration is proposed, each phase independently implementable and individually measurable via the project's existing live-evaluation methodology.

---

## 1. Current Architecture (Background Investigation)

### 1.1 How distractors are currently requested

Entirely through prose in `prompts/generation/question.txt`, inside the single `LLMProfile.GENERATION` call (`QuestionGenerator.generate_candidate_question()`, `src/exam_generator/generation/generator.py`). The model receives:
- the assigned `QuestionTarget` (`topic`, `factual_focus`, `supporting_evidence_chunk_ids`);
- the full retrieved student-summary evidence for the category (`top_k=8` chunks, `config/app.yaml`'s `retrieval.top_k`);
- (STYLE_SIMILAR only) one historical style reference;
- since WP-026/027: prose rules about narrowing enumeration/classification targets, making hierarchy level explicit, and checking each distractor individually against the evidence for whether it would also answer the exact question;
- since WP-028: a required internal `blueprint` field (`QuestionBlueprint`) capturing an `archetype`, `plausibility_reason`, `incorrectness_reason`, and self-reported `evidence_checked` boolean for each of the three distractors.

There is **no deterministic constraint** anywhere in this path on what a distractor's *content* must be derived from, or on which *strategy* produces it. The model chooses freely; WP-028 added a requirement to *describe* that choice, not to *constrain* it - this is exactly the review's finding (`WP-028_ARCHITECTURE_REVIEW.md` section 5: "documents reasoning... does not constrain reasoning").

### 1.2 How QuestionTarget influences generation

`QuestionTarget` (`src/exam_generator/models/target.py`) is planned once per category, before any generation for that category begins (`QuestionTargetPlanner.plan_targets()`), and held fixed across every retry of every attempt for its assigned position (`_produce_unique_question()`/`QuestionProducer.produce_question()`, both WP-025). It carries exactly four fields: `target_id`, `category`, `topic`, `factual_focus`, `supporting_evidence_chunk_ids`. It describes **what** to test; it says nothing about **how** to construct distractors, what hierarchy level is involved, or what other targets exist for the same category.

### 1.3 Where distractor decisions are currently made

Entirely inside the single generation LLM call, entirely by the model, entirely self-reported (WP-028's blueprint). No Python code makes or influences any distractor decision today.

### 1.4 Where diversity information is available

`QuestionTargetPlanner.plan_targets(category, count)` (`src/exam_generator/planning/planner.py`) plans **all** targets for a category in one call, before any of that category's questions are generated (confirmed directly in `orchestrator.py`: `targets = self._target_planner.plan_targets(category=category, count=count)`, called once, then looped over positionally). This means **the full sibling-target set for a category already exists in memory in the orchestrator at generation time** - but it is not currently threaded into any individual `generate_candidate_question()` call, which only ever receives its own single assigned target (`targets[index]`). This is a significant, currently-unused source of information: the application already knows, for free, what the *other* targets for the same category look like, and could in principle tell generation "do not construct a distractor that is actually target 2's own factual focus."

`seen_normalized_questions` (a set of every already-*accepted* question's normalized text, across the whole exam, WP-014/WP-023) is threaded into `_produce_unique_question()` for exact-text duplicate detection **after** a candidate is generated - it is never passed into the generation prompt itself. Previously-accepted question *content* (as opposed to exact-text duplication) is not available to generation at all today.

### 1.5 Where evidence is available

`source_evidence: tuple[SourceEvidenceChunk, ...]` - the full `top_k` retrieval result for the category - is passed to generation (`GenerationPromptContext`). The target's own `supporting_evidence_chunk_ids` identify *which* of those chunks the planner believed supported the target, but generation is not currently instructed to anchor each distractor to a *specific* chunk or sentence within that evidence - it may draw on the evidence holistically, or (per WP-018/WP-025A findings) occasionally introduce plausible-sounding but evidence-unsupported claims.

### 1.6 What the application already knows before generation, in full

Category (canonical, resolved) · the assigned `QuestionTarget` · the full retrieved evidence for the category · (STYLE_SIMILAR) one historical reference · the sibling targets for the same category (available in the orchestrator, not yet threaded to generation) · nothing about difficulty (WP-028's blueprint invents this per-call, not from a request-level signal) · nothing about question type/format beyond "one best of four" · nothing about previously-generated question content within the same run.

---

## 2. Identified Weaknesses

1. **Distractor content has no deterministic relationship to evidence.** A distractor is validated only *after* the fact (by `GroundingValidator`); nothing upstream increases the odds it will pass.
2. **Strategy selection is entirely the model's free choice**, self-reported (WP-028), never independently confirmed or application-directed. There is no mechanism to ensure archetype diversity within a question or across a category's two questions.
3. **Sibling-target information is computed but discarded.** The planner already knows, per category, what the *other* target looks like - this is thrown away before generation runs.
4. **No mechanism anchors a distractor to a specific evidence sentence.** "Evidence-supported" is currently a holistic, not per-distractor, property of the generation call.
5. **Self-verification (WP-028) does not reliably improve outcomes** - documented, measured, and now formally rejected as a direction (`WP-028_ARCHITECTURE_REVIEW.md`).

---

## 3. Failure Analysis

Sourced entirely from existing reports and live-run audit data - no new generation was performed for this analysis.

| Failure class | Primary source(s) | Approximate observed scale | Status |
|---|---|---|---|
| **Another answer also correct** (a distractor genuinely satisfies the exact question, per evidence) | `evaluation/wp026_false_acceptance_diagnostic.md`; WP-027 acceptance run (12 grounding rejections, 100% this shape); WP-028 acceptance run (14 grounding rejections, 87.5% this shape) | Dominant: 12-14 rejections per 40-question run, the single largest grounding-rejection cause in both of the two most recent full runs | **Confirmed dominant** - this is the failure class this proposal directly targets |
| **Hierarchy ambiguity** (adjacent hierarchy-level classification used as distractor) | `evaluation/wp025_failed_target_diagnostic.md`; WP-026's own diagnosed root cause (question #23's PNS-divisions case, and its recurrence through WP-027/WP-028's own live runs on the same target) | A structural subtype of "another answer also correct" - the single most reliably-reproducing hard case across five consecutive WPs' live evidence | Largely a special case of the row above, not independently eliminated by WP-026/027's prose guidance |
| **Multiple valid enumeration members** (a target names 2+ members, 2+ appear as answer choices, only one marked correct) | `evaluation/wp025_failed_target_diagnostic.md` (WP-025A's original diagnosis) | Original trigger for WP-026; now subsumed into the same underlying mechanism as the two rows above | Same root mechanism |
| **Real-world domain/functional overlap** (a distractor is a genuine fact about a *related* relationship that a domain expert could defend as also satisfying a broadly-worded question) | WP-027's own #7 (Diffusion Imaging is technically an MRI modality); WP-028's #11 (SCA also arguably supplies "posterior" regions) and #12 (venous sinuses drain via both jugular vein and emissary veins) | 1-2 `POSSIBLE_SECOND_CORRECT_ANSWER` cases per 30-35 accepted questions in the two most recent runs | A narrower, harder variant of "another also correct" - even a subject-matter-correct human reviewer might disagree; not fully solvable by evidence-anchoring alone (see section 8) |
| **Weak/implausible distractor, or structural MCQ defect** | WP-027 MCQ rejections: 8/40 planned; WP-028 MCQ rejections: **18/40 planned - more than doubled** | Newly dominant in WP-028's own run | Suggests blueprint-driven generation's added complexity may have made *structural* MCQ quality *worse*, not just failed to improve factual correctness - see section 4 below |
| **Factual fabrication inside distractor content** (a distractor states something outright false, e.g. WP-028's focused-eval PNS case: "the autonomic nervous system controls voluntary skeletal-muscle movement," which is simply wrong) | WP-028 focused live evaluation (`evaluation/live_outputs/wp028_focused_eval_results.json`) | Observed directly in the one focused-eval exhaustion; not separately counted in aggregate validator statistics (folds into MCQ/quality/category rejections) | A distinct failure shape from "another also correct" - the distractor isn't *also true*, it's *fabricated*, and fabricated-but-inconsistent distractors can still trigger "not a single best answer" MCQ rejections when the fabrication itself creates confusion about which answer is "most" correct |
| **Wording/quality ambiguity** (unclear phrasing, not a factual defect) | WP-027 quality rejections: 10/40; WP-028: 15/40 | Present, roughly proportional to overall attempt volume, not clearly a distinct root cause from the above | Likely a downstream symptom of weak distractor construction rather than an independent problem |

**Estimate: "another answer also correct" and its structural variants (hierarchy ambiguity, enumeration-membership ambiguity, real-world overlap) together account for the large majority of grounding-caused rejections in every live run measured since WP-026's diagnostic. This is the correct primary target for WP-029/WP-030.** The doubling of MCQ rejections under WP-028 is a secondary, important finding: added self-reported reasoning complexity did not just fail to help correctness, it plausibly hurt structural quality too - this proposal's Phase 2 (section 13) is designed to *replace*, not *add to*, that complexity.

---

## 4. Distractor Taxonomy

For neuroanatomy MCQ generation specifically, grounded in the archetypes WP-028 already introduced (which were reasonable *as a taxonomy*, even though self-reported selection of them did not help) plus additions justified by the failure analysis above.

| Strategy | Definition | Educational purpose | Expected difficulty | Advantages | Risks | Example |
|---|---|---|---|---|---|---|
| **Sibling substitution** | Replace the correct answer with another member of the same explicit classification named in the evidence | Tests precise recall within a known set | Medium-high (the classic "another also correct" trap) | Natural, evidence-grounded, tests real discrimination | **Highest risk of producing a second correct answer** - requires the question to add a specific, narrowing qualifier the correct answer alone satisfies (WP-026/027's "narrow to one distinguishing property" guidance, already proven to work when actually followed - e.g. WP-027's accepted #24/#26/#27/#28, WP-028's #13/#16/#23) | "Association fibers" (correct, connects same-hemisphere cortex) vs. "commissural fibers" (real sibling, connects hemispheres - wrong for *this* relationship) |
| **Parent-category substitution** | Replace with the immediate parent classification | Tests level-of-abstraction precision | Medium | Naturally, obviously wrong once hierarchy level is explicit | Ambiguous if the question's hierarchy level is not made explicit (WP-026's core original finding) | "Peripheral nervous system" as a distractor for "which division of the PNS..." |
| **Child-category substitution** | Replace with a more specific sub-classification one level down | Tests over-specification awareness | Medium | Same as above, inverted | Same as above | "Sympathetic division" as a distractor for "what are the two main PNS divisions" |
| **Neighboring-anatomy substitution** | Replace with a structurally/spatially adjacent but functionally distinct structure | Tests spatial/structural precision | Medium | Rarely produces a second-correct-answer (different structure entirely) | Can be too easy if evidence doesn't genuinely support confusing the two | Postcentral gyrus (correct, S1) vs. precentral gyrus (real neighbor, M1 - wrong for the sensory question) |
| **Functional confusion** | Replace with a structure/process that performs a *different*, real function often confused with the tested one | Tests function-vs-structure precision | Medium-high | Educationally valuable (tests real misconceptions) | Can create real-world overlap risk if the "different" function is not cleanly different (this proposal's section 8 addresses this) | Direct pathway (correct, increases movement) vs. indirect pathway (real, opposite function) |
| **Location confusion** | Replace with a structure at a different, real, plausible-sounding location | Tests localization precision | Medium | Rarely ambiguous | Low risk generally | Superior cerebellar artery (correct, upper cerebellum) vs. PICA (real, different territory) |
| **Developmental-stage confusion** | Replace with a fact true at a different developmental stage/timepoint | Tests temporal/developmental precision | Medium-high (requires evidence with explicit staging) | Rare failure mode observed so far (WP-028's #27, correctly handled) | Requires evidence to actually state distinct stages, or the distractor may be unfalsifiable from supplied evidence | "Third developmental stage" vs. other stages for lateral-ventricle C-shaping |
| **Terminology/synonym confusion** | Replace with a distractor using a real alternate name or closely related term for a *different* structure | Tests terminology precision, not just concept recall | Low-medium | Easy to construct correctly since names are unambiguous facts | Risk of accidentally using a genuine synonym for the *same* structure, which would be a grounding failure, not a valid distractor | "Emboliform nucleus" (a genuine alternate name for a *different* cerebellar nucleus) as a distractor |
| **Blood-supply confusion** *(new, justified by failure analysis)* | Replace with a different vessel that supplies a *related but distinct* territory | Directly targets the observed WP-027 #14/WP-028 #11 recurring failure shape (arterial-territory overlap) | High - this specific shape has now failed twice | Names the exact recurring problem explicitly, making it a first-class design concern rather than an instance of "sibling structure" | The territories genuinely can overlap in reality (e.g. borderzone/watershed regions) - may need the question to specify a precise, non-borderzone location | PCA (correct, "posterior CNS") vs. SCA (real, also technically posterior/cerebellar) - **this exact pair has already twice produced a `POSSIBLE_SECOND_CORRECT_ANSWER` case** |
| **Drainage/pathway-route confusion** *(new, justified by WP-028's #12)* | Replace with a different real route/pathway for the *same* general process, when more than one real route exists | Names WP-028's venous-sinus-drainage overlap explicitly | High for the same reason as above | Same as above | Venous sinuses genuinely drain via *both* jugular vein and emissary veins in reality - a distractor naming the second real route is not simply false | Jugular vein (correct, primary route) vs. emissary veins (real, secondary route) |
| **Anatomical-orientation confusion** | Replace with the same structure/relationship stated with an inverted anatomical direction (superior/inferior, anterior/posterior, medial/lateral) | Tests directional precision specifically | Low-medium | Clean, rarely ambiguous, easy to construct | Requires evidence to state direction explicitly | "Superior" vs. "inferior" sagittal sinus |

The **blood-supply confusion** and **drainage/pathway-route confusion** additions are not hypothetical - they name the exact two `POSSIBLE_SECOND_CORRECT_ANSWER` cases observed in WP-028's own live run. Treating them as named, tracked archetypes (rather than instances of the generic "sibling structure" category) is itself a small, concrete improvement: it makes explicit that these specific relationship types carry elevated risk and may need additional narrowing guidance beyond what generic sibling-substitution guidance provides.

---

## 5. Application Knowledge

Currently available to generation (section 1.6, restated for this section's specific ask): category, target, full retrieved evidence, historical reference (STYLE_SIMILAR only).

**Should be expanded to include:**
- **Sibling targets for the category** (already computed by `QuestionTargetPlanner.plan_targets()`, currently discarded before reaching generation) - zero retrieval/LLM cost to add, since the data already exists in memory in the orchestrator when it calls `_produce_unique_question()`.
- **The specific evidence chunk(s) that ground the correct answer** (already known - `QuestionTarget.supporting_evidence_chunk_ids`) - currently supplied as part of the full evidence bundle but not singled out as "this is the passage your correct answer must come from, and each distractor's evidence-anchor should be identified separately."
- **A recommended (not mandatory) distractor-archetype assignment per question** (new - see section 6/7) - zero additional LLM call if computed deterministically or piggybacked onto the existing planning call.

**Should NOT be expanded to include** (per the WP's own scope discipline and this proposal's cost philosophy): previously-generated question text (would require passing growing state into every generation call, a meaningful architectural change for uncertain benefit - diversity is already handled by construction per WP-025, and duplicate-text detection already exists post-hoc); a general "requested difficulty" parameter (no evidence any live failure was difficulty-related; WP-028's own self-reported `intended_difficulty` field showed no measurable effect and per the review should not be extended).

---

## 6. QuestionTarget Evolution

**Recommendation: extend, not redesign.**

`QuestionTarget` should remain the stable, minimal "what to test" contract it has been since WP-025 (four fields, no persistence into the audit, held fixed across every retry). A redesign is not justified: nothing in the failure analysis points to a defect in what `QuestionTarget` itself describes - the problem is entirely downstream, in how distractors are constructed from it.

**Proposed additions** (optional, backward-compatible - default values preserve exact current behavior):
- `preferred_distractor_archetypes: tuple[DistractorArchetype, ...] = ()` - an application-assigned (not model-chosen) hint, empty by default. When populated (Phase 3, section 13), generation is *instructed* rather than *free* to use one of the named strategies. An empty tuple means "no change from today's behavior" - this is additive, not breaking.
- `sibling_topics: tuple[str, ...] = ()` - the *topics* (not full targets - keeps the field small) of the category's other planned targets, so generation can be told "do not construct a distractor whose content actually belongs to one of these other topics" (directly targets the enumeration/sibling-substitution failure class).

**Explicitly not recommended:** `forbidden_concepts`/`forbidden_previous_targets` as free-text fields - too unstructured to act on reliably, and the `sibling_topics` addition above already covers the concrete, evidence-based version of this need (the *actual* other targets for the category, not a vague forbidden-list). `concept_granularity`/`preferred_reasoning_style`/`relationship_type` as separate fields would duplicate what `tested_relationship`-style narrowing (already partially achieved via prompt guidance since WP-026) should express as prose, not as a new structured field - adding more structured fields without a corresponding *independent verification* mechanism repeats WP-028's exact mistake.

---

## 7. Strategy Selection

Comparing the three options the WP names:

| | A. LLM chooses | B. Application chooses | C. Hybrid |
|---|---|---|---|
| Determinism | None - proven unreliable (WP-028) | Full - Python decides, testable, reproducible | Partial - bounded choice |
| Diversity | Uncontrolled, no measured improvement | Fully controllable (e.g. round-robin/weighted across archetypes) | Controllable within an application-set menu |
| Implementation complexity | Lowest (current state) | Higher - needs a selection policy (even a simple deterministic rotation) | Medium |
| Validation compatibility | Unchanged either way - grounding is independent of how a distractor was chosen | Unchanged | Unchanged |
| Educational quality | Unproven | Can deliberately ensure coverage across archetypes over an exam, avoiding one dominant weak strategy | Best of both - application avoids known-risky archetypes for known-risky relationship types (e.g. never assign blood-supply confusion without an explicit narrowing instruction), while the LLM still exercises judgment on *how* to execute the chosen strategy for this specific evidence |

**Recommendation: C, Hybrid**, weighted toward B. The application should choose *which archetype(s)* to require per distractor (a small, deterministic decision - e.g. simple round-robin across the taxonomy in section 4, or informed by keyword/structure signals already computable from the target's `factual_focus` text, such as detecting enumeration language). The LLM retains judgment over *how* to execute that archetype against the specific evidence for this specific question - this is not full application control (which would require the application to already know anatomical facts it cannot verify), but it removes the *selection* freedom that WP-028 showed does not reliably produce good outcomes on its own, while keeping the *execution* freedom that generation is well-suited for.

This directly answers WP-029 section 7 with a concrete default: **archetype selection moves from the model (WP-028) to the application; execution against evidence remains the model's job.**

---

## 8. Evidence-Constrained Generation

**Feasible, and recommended as the core mechanism - with an explicit, honest limitation.**

Proposed transformation-based construction: for each distractor, generation is instructed to (1) identify the specific evidence sentence/phrase that grounds the *correct* answer, (2) apply its assigned archetype (section 7) to that specific passage or an explicitly different passage in the same evidence bundle, and (3) report which evidence reference(s) it drew the distractor's content from - reusing the exact WP-022/024/027 call-local `evidence_refs` pattern already proven throughout this project, rather than inventing a new provenance mechanism.

**This is still generation-time, self-reported provenance** - identical in kind to WP-024's `evidence_refs` on `GeneratedQuestionResponse` today, which the project has never treated as authoritative on its own; it is bounds-checked deterministically (an invalid reference is rejected, exactly like every other evidence-reference field in this codebase) but its *semantic correctness* (does this reference actually support this distractor's specific claim) is still ultimately confirmed by the **independent** `GroundingValidator` per-option check (WP-027), unchanged. This is the crucial architectural difference from WP-028: **evidence-anchoring is a construction discipline that improves the odds of producing a good candidate; it is explicitly not proposed as a substitute for WP-027's independent verification**, which remains the sole authority on whether a distractor is actually valid.

**Honest limitation (section 4's "real-world overlap" row):** evidence-anchoring cannot fully eliminate the blood-supply-confusion/drainage-route-confusion failure shape, because the risk there is not that the distractor is *unsupported* by evidence - it's that the evidence *itself*, read broadly, could support more than one answer to a broadly-worded question. This is fundamentally a **question-wording precision** problem, not a distractor-sourcing problem, and evidence-anchoring alone will not fully resolve it. The mitigation is procedural, not architectural: the generation prompt must continue to require (as it already does, since WP-027 section 11) that a distractor's specific relationship be checked against the specific question wording, not just against evidence in the abstract - and for the archetypes in section 4 flagged as elevated-risk, the recommended architecture (section 12) requires an additional narrowing instruction specifically for those two archetypes.

---

## 9. Validation Compatibility

For the recommended architecture (section 12):

- **Will it reduce grounding failures?** Likely yes for the "another answer also correct" class specifically, since distractors are now explicitly anchored to *different* evidence content than the correct answer, and sibling-topic awareness (section 6) directly targets the enumeration/hierarchy sub-variant. Not claimed to fully eliminate the real-world-overlap subtype (section 8's honest limitation).
- **Will it reduce MCQ failures?** Likely yes, since MCQ rejections roughly doubled specifically when WP-028 introduced *unconstrained* archetype self-selection with no evidence anchor - removing that unconstrained freedom while keeping (not removing) evidence-grounding discipline should at minimum undo that regression.
- **Will it reduce quality failures?** Plausibly, as a secondary effect of clearer, evidence-anchored distractor construction, but not a primary target of this proposal.
- **Will it preserve validator independence?** Yes - `GroundingValidator`/`MCQValidator`/`CategoryValidator`/`QualityValidator`/`TextbookValidator` are untouched in every phase of the migration plan (section 13). No validator gains new inputs, no validator's responsibility changes.
- **Will it preserve deterministic acceptance?** Yes - `CandidateValidationResults.accepted` is untouched; acceptance remains purely a function of the five existing validators' verdicts.
- **Will it preserve current retry behavior?** Yes - `max_generation_attempts`, WP-020's structured-output retry, and WP-021's provenance retry are all untouched in every phase.

---

## 10. Cost Analysis

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Additional LLM calls | 0 (reuses the existing planning call) | 0 (reuses the existing generation call) | 0 (deterministic application logic, or piggybacked on the existing planning call) |
| Prompt complexity | Small increase (planner reports one additional classification field) | Moderate increase (generation must report per-distractor evidence anchors - comparable in size to WP-028's blueprint, but replacing rather than adding to it) | Small increase (generation prompt receives an explicit, application-chosen archetype list to follow, replacing free choice - not necessarily larger) |
| Latency | Negligible | Comparable to WP-028's current latency (similar response size) | Negligible |
| Token usage | Small increase (target gains 1-2 short fields) | Comparable to WP-028's current usage | Small increase (target gains a short archetype-preference field) |
| Maintainability | Low risk - purely additive fields with safe defaults | Medium - replaces WP-028's blueprint schema, a real but bounded migration (see section 13) | Low risk - a small, testable, deterministic selection function |
| Extensibility | High - classification field can inform later phases without further redesign | High - the archetype+evidence-anchor pattern generalizes cleanly to new archetypes (section 4's table is designed to be extended) | High - selection policy is isolated and independently swappable (e.g. round-robin today, informed-by-heuristics later) |

**Overall: this proposal is cost-neutral relative to WP-028 in LLM call count (zero net new calls across all three phases) and is expected to *reduce* net cost in practice by reducing wasted regeneration attempts** (fewer grounding/MCQ rejections means fewer of WP-013's bounded retry attempts consumed per accepted question) - though, consistent with this project's evidence-based discipline, that reduction is a hypothesis to be measured via live evaluation after implementation, not asserted as guaranteed.

---

## 11. Alternative Architectures

### Alternative A — Evidence-Constrained Distractor Synthesis (transformation-based, LLM-chosen archetype)

Generation is required to construct each distractor via a named transformation of a specific evidence passage (section 8), but archetype *choice* remains the model's own judgment (as in WP-028, but now anchored to evidence rather than free invention).

- **Advantages:** Simplest change from current state; directly addresses the evidence-anchoring weakness; reuses the proven `evidence_refs` pattern.
- **Disadvantages:** Retains WP-028's core weakness (archetype *selection* is still unconstrained/self-reported) - only partially addresses the failure analysis.
- **Implementation effort:** Low-medium (one prompt rewrite, reuse of existing infrastructure).
- **Architectural cleanliness:** High - purely a prompt/schema change to the existing generation call.
- **Compatibility with existing WPs:** Full - no validator, retrieval, planning, or orchestration change.

### Alternative B — Application-Guided Strategy Selection with Structured Slot-Filling

The application deterministically assigns one archetype per distractor slot (via a simple policy - round-robin, or informed by lightweight text-pattern detection over the target's `factual_focus`), and the generation prompt explicitly instructs "distractor 1 must use archetype X, distractor 2 must use archetype Y, distractor 3 must use archetype Z" - without necessarily requiring the evidence-anchoring of Alternative A.

- **Advantages:** Directly improves determinism and cross-exam archetype diversity; simple to implement and test in isolation (the selection policy is pure Python, unit-testable without any LLM call).
- **Disadvantages:** Does not by itself address evidence-anchoring - a model could still construct a "sibling structure" distractor that happens to also be correct, just as before, merely with a label attached.
- **Implementation effort:** Low (a small selection function plus a prompt-wording change).
- **Architectural cleanliness:** High.
- **Compatibility with existing WPs:** Full.

### Alternative C — Independent Distractor Pre-Verification (a new lightweight check before the full five-validator pipeline)

After generation proposes a candidate (via either A or B's mechanism, or unconstrained as today), route the three distractors through a new, narrowly-scoped verification call - conceptually similar to WP-027's per-option grounding, but performed *before* the full five-validator pass, so a bad candidate can be cheaply rejected and regenerated without spending a full grounding/MCQ/category/quality/textbook cycle on it.

- **Advantages:** Could reduce wasted validator calls on candidates that would fail anyway; a genuinely independent check (not self-reported), consistent with the project's proven pattern.
- **Disadvantages:** **Adds a new LLM call** - a real, measurable cost increase this project has consistently avoided since WP-020's establishment of the "no additional calls" discipline; also meaningfully duplicates `GroundingValidator`'s own responsibility (the diagnostic and WP-027 already established that grounding is the correct architectural home for exactly this check - see `evaluation/wp026_false_acceptance_diagnostic.md` sections 11-13), risking two independent sources of truth for the same question.
- **Implementation effort:** Medium-high (new component, new prompt, new tests, new wiring into `QuestionProducer` or `QuestionGenerator`).
- **Architectural cleanliness:** Medium - introduces a new call-count precedent the project has not needed since WP-020.
- **Compatibility with existing WPs:** Full, but represents a philosophy change (accepting a new LLM call) that should be an explicit, deliberate decision if ever adopted - not a default.

### Ranking

1. **Combination of A + B** (this proposal's recommendation, section 12) - addresses both weaknesses (evidence-anchoring and strategy determinism) identified in the failure analysis, at zero additional call cost.
2. **Alternative A alone** - a safe, smaller first step if the combined proposal is judged too large for one WP; still directly addresses the dominant failure class.
3. **Alternative B alone** - improves determinism but does not address the root evidence-anchoring gap; weaker in isolation.
4. **Alternative C** - not recommended as a default; the cost (new LLM call) is not justified when grounding already performs this exact check for free, per the project's own established architecture.

---

## 12. Recommended Architecture

**Evidence-Constrained, Application-Guided Distractor Synthesis** = Alternative A + Alternative B, combined, phased (section 13).

- **Scalability:** The archetype taxonomy (section 4) is designed to grow without redesign - new archetypes are additive enum values with their own comparison-matrix row, exactly like `DistractorArchetype` already does since WP-028 (kept, not discarded - the taxonomy itself was sound; only self-reported *selection* was the problem).
- **Maintainability:** Zero new components; extends existing models (`QuestionTarget`, the generation response contract) and existing prompts (`prompts/generation/question.txt`, `prompts/generation/question_target_planning.txt`) in the same pattern every successful prior WP has used.
- **Correctness:** Does not touch `GroundingValidator` or any other validator - WP-027's independent, deterministic per-option check remains the sole authority on acceptance. This proposal only tries to make what reaches that check better, never asks it to trust anything new.
- **Educational quality:** The taxonomy (section 4) explicitly documents pedagogical purpose per archetype, and application-guided selection (section 7) can ensure a category's two questions do not lean on the same weak archetype twice - a concrete, testable diversity improvement beyond WP-025's target-level diversity.
- **Interaction with validation:** None - by design, per section 9.

---

## 13. Migration Plan

Each phase is independently implementable, independently measurable via the project's existing live-evaluation methodology (focused live test + one full 20×2 acceptance run + false-acceptance human review + diversity review, the same pattern used since WP-025), and does not require the later phases to already exist.

### Phase 1 — Sibling-topic and relationship-shape awareness (planning-side, zero new calls)

- Extend `QuestionTargetPlanningResponse`/`PlannedQuestionTargetResponse` (`models/target.py`) so the existing single planning call additionally classifies each planned target's relationship shape (e.g. `single_fact` / `enumeration_member` / `hierarchical_level` / `comparison`) - reusing the exact call that already runs once per category.
- Thread the category's other planned targets' `topic` values into each `QuestionTarget` as `sibling_topics` (section 6) - pure application wiring, no LLM change needed for this part (the orchestrator already holds all targets in memory when constructing each one).
- **Measurable outcome:** no behavior change yet if generation doesn't read the new fields - this phase is safe to land and verify (full regression + one live smoke test) before Phase 2 begins.

### Phase 2 — Evidence-anchored distractor construction (generation-side, zero new calls)

- Replace WP-028's free-form `DistractorDesign.archetype`/`plausibility_reason`/`incorrectness_reason`/`evidence_checked` fields with evidence-anchored equivalents: each distractor reports which specific `evidence_refs` (WP-022/024/027 pattern) it was constructed from, and which archetype (section 4's taxonomy, extended with the two new archetypes) it used.
- Update `prompts/generation/question.txt` to require this anchoring explicitly, replacing (not layering onto) WP-028's blueprint section.
- **Measurable outcome:** focused live evaluation on the categories WP-028 struggled with (`מערכת העצבים ההיקפית`, `אספקת דם`, `תאי מערכת העצבים`), directly comparable to WP-028's own focused-eval methodology, before committing to a full acceptance run.

### Phase 3 — Application-guided archetype selection (planning+generation-side, zero new calls)

- Add a small, deterministic selection function (pure Python, independently unit-testable) that assigns `preferred_distractor_archetypes` (section 6) per target, using Phase 1's relationship-shape classification (e.g. `enumeration_member` targets get a mandatory sibling-substitution *avoidance* instruction plus a required narrowing property, directly targeting the dominant failure class; `blood-supply`/`drainage-route`-flagged evidence gets the elevated-risk-archetype narrowing instruction from section 8).
- Update the generation prompt to follow the assigned archetypes when present, falling back to free choice when `preferred_distractor_archetypes` is empty (safe default, fully backward compatible).
- **Measurable outcome:** the full comparison methodology (40-question acceptance run, false-acceptance human review, diversity review, direct comparison against WP-027's and WP-028's own numbers) - this is the phase whose success or failure should be judged against WP-028's own explicitly-stated primary metric (grounding rejections caused by another supported answer).

Each phase avoids large refactoring: Phase 1 touches only `models/target.py` and the planning prompt; Phase 2 touches only `models/question.py` and the generation prompt (replacing, not extending, WP-028's now-frozen blueprint fields); Phase 3 touches a new small selection module plus both of the above prompts' consumption of it. No phase touches `validation/`, `production/`, `orchestration/`, or `retrieval/`.

---

## 14. Expected Benefits

- A measurable reduction in "another answer also correct" grounding rejections (the explicit metric WP-028 was measured against and did not move), by construction rather than by hoping a self-reported check catches it.
- A measurable reduction in MCQ rejections back toward (or below) WP-027's baseline, by removing WP-028's unconstrained-selection complexity while keeping its useful taxonomy.
- Improved, more predictable distractor archetype diversity within and across a category's questions, addressed for the first time as an explicit design property rather than an emergent one.
- Zero net new LLM calls across the full migration, preserving the project's cost discipline.
- A clean rollback path at every phase boundary - if Phase 2's live evaluation does not show improvement, Phase 3 need not be attempted, and the recommendation can be revisited with fresh evidence, exactly as this project's own standing practice requires.

## 15. Open Questions

1. **Should the "real-world overlap" archetypes (blood-supply confusion, drainage-route confusion) be actively avoided by the application, rather than merely flagged as elevated-risk?** This proposal recommends flagging-plus-narrowing (section 8) rather than avoidance, on the theory that avoiding real anatomical relationships entirely would reduce the exam's educational range; but this is a judgment call the architect/reviewer may weigh differently.
2. **Should Phase 1's relationship-shape classification be a free-text field (simpler, less structured) or a closed enum (more structured, more testable, but requires the taxonomy to be complete up front)?** This proposal assumes a closed enum for consistency with the rest of the codebase's typed-model discipline, but the exact enum membership is an implementation-time decision for WP-030, not fixed here.
3. **How should Phase 3's deterministic selection policy be seeded/validated initially** - a simple fixed round-robin, or informed by lightweight heuristics over `factual_focus` text (e.g. detecting enumeration language)? This proposal recommends starting with the simplest reliable policy (round-robin) and only adding heuristic sophistication if live evidence after Phase 3's initial rollout shows a specific archetype is being systematically over/under-used in a way a heuristic could fix - consistent with the project's "don't add complexity without evidence" discipline, the same discipline whose absence is exactly what WP-028's review found lacking.
4. **Should WP-028's blueprint fields be formally removed, or merely superseded** when Phase 2 lands? This proposal recommends replacement (not layering) at the schema level for cleanliness, but the completion report for whichever WP implements Phase 2 should explicitly document this as a deliberate contract change, per this project's standing practice around breaking an LLM-facing (never public) contract.
