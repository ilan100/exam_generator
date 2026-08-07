# WP-029 Completion Report — Distractor Synthesis Architecture

## 1. Investigation Performed

WP-029 was a design-only work package: no code, prompt, validator, configuration, or test file was modified. The investigation consisted of:

- Reading `docs/MASTER_PROJECT_BRIEF.md`, `docs/ARCHITECTURE.md`, `docs/PROJECT_STATUS.md`, `implementation/WP-025.md` through `WP-028.md`, `implementation/WP-028_COMPLETION_REPORT.md`, and `implementation/WP-028_ARCHITECTURE_REVIEW.md` in full.
- Direct source inspection (read-only) of `src/exam_generator/generation/generator.py`, `src/exam_generator/models/target.py`, `src/exam_generator/planning/planner.py`, `src/exam_generator/orchestration/orchestrator.py` (specifically `_produce_unique_question()` and the per-category target-planning loop in `generate_exam()`), and `src/exam_generator/prompts/context.py` (`GenerationPromptContext`) - to establish precisely what information is and is not currently available to generation, and where sibling-target/diversity information already exists but is currently discarded before reaching generation.
- Failure analysis sourced entirely from existing evidence: `evaluation/wp025_failed_target_diagnostic.md`, `evaluation/wp026_false_acceptance_diagnostic.md`, WP-027's and WP-028's own acceptance-run audit data (`evaluation/live_outputs/wp027_acceptance_audit.json`, `wp028_acceptance_audit.json`) and their respective completion reports' validator-rejection breakdowns, and WP-028's focused-live-evaluation results (`evaluation/live_outputs/wp028_focused_eval_results.json`). No new question generation was performed for this analysis, per the WP's explicit instruction.

## 2. Documents Produced

- `implementation/WP-029_ARCHITECTURE_PROPOSAL.md` - the required deliverable, containing: current architecture (background investigation), identified weaknesses, a failure taxonomy grounded in the actual observed data from WP-025A/026/027/028 (with approximate observed scale, not invented estimates), a distractor taxonomy for neuroanatomy (extending WP-028's own archetype list with two new archetypes directly named after the two `POSSIBLE_SECOND_CORRECT_ANSWER` cases observed in WP-028's own live run), application-knowledge recommendations, a `QuestionTarget` evolution recommendation (extend, not redesign), a strategy-selection recommendation (Hybrid, weighted toward application-chosen), an evidence-constrained-generation feasibility analysis (with an explicit, honest limitation for the real-world-overlap failure subtype), a validation-compatibility analysis, a cost analysis (zero net new LLM calls across the full proposal), three complete alternative architectures with a comparison and ranking, one recommended architecture (Evidence-Constrained, Application-Guided Distractor Synthesis), a 3-phase independently-implementable migration plan, expected benefits, and four explicit open questions for the architect/reviewer.
- `implementation/WP-029_COMPLETION_REPORT.md` (this file).

## 3. Recommendations (Summary)

**Recommended architecture:** Evidence-Constrained, Application-Guided Distractor Synthesis - distractors are constructed via named, evidence-anchored transformations (reusing the project's proven `evidence_refs` local-reference pattern from WP-022/024/027) rather than free invention, and archetype *selection* moves from the model (WP-028's failed approach) to deterministic application logic, while archetype *execution* against the specific evidence remains the model's job. This explicitly does **not** ask the model to self-certify correctness - WP-027's independent, deterministic per-option `GroundingValidator` check remains the unchanged, sole authority on acceptance.

**Recommended migration:** 3 phases, each independently implementable and measurable via the project's existing live-evaluation methodology, none touching `validation/`, `production/`, `orchestration/`, or `retrieval/`:
1. Sibling-topic and relationship-shape awareness (planning-side, reuses the existing planning call).
2. Evidence-anchored distractor construction (generation-side, reuses the existing generation call, replaces rather than extends WP-028's now-frozen blueprint fields).
3. Application-guided archetype selection (a new, small, independently unit-testable deterministic selection function).

**Rejected alternative:** an independent distractor pre-verification call (a new LLM call before the full five-validator pipeline) - not recommended as a default, since it would duplicate `GroundingValidator`'s already-established, already-free responsibility and break the project's zero-new-calls discipline maintained since WP-020.

Full reasoning, comparison matrix, and citations to the specific evidence behind every claim are in `implementation/WP-029_ARCHITECTURE_PROPOSAL.md`.

## 4. Confirmation: No Code Modified

No file under `src/exam_generator/`, `prompts/`, `tests/`, or any configuration/schema file was modified. `docs/ARCHITECTURE.md` and `docs/PROJECT_STATUS.md` were **not** updated for this WP, since WP-029 produced no architectural change to document there (an architecture *proposal* is not an architecture *decision* - per this project's own established pattern, `docs/ARCHITECTURE.md` documents what has been *built*, not what has been proposed). The full regression suite was re-run after producing both documents and remains unchanged at **1070/1070 passing**, identical to the count entering this WP - confirming no accidental modification occurred.

## 5. Confirmation: No Production Behavior Changed

`git status --short` confirms the only files touched in this WP are the two new documents in `implementation/` (`WP-029_ARCHITECTURE_PROPOSAL.md`, `WP-029_COMPLETION_REPORT.md`) plus the externally-supplied `WP-029.md` and `WP-028_ARCHITECTURE_REVIEW.md` spec files themselves. Every pre-existing uncommitted change in the working tree predates this WP (WP-027/WP-028's own work) and was left untouched. No validator, prompt, model, or pipeline behavior differs from WP-028's final state in any way.

---

WP-029 complete.

Production code modified:
NO

Architecture proposal:
implementation/WP-029_ARCHITECTURE_PROPOSAL.md

Completion report:
implementation/WP-029_COMPLETION_REPORT.md

Waiting for architect review.
