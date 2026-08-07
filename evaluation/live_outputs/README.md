# Live run outputs

Actual `exam.json`/`exam_audit.json` pairs written by real `exam-generator generate` invocations against the live OpenAI API during WP acceptance testing, copied here from the session scratchpad so they persist.

| File pair | WP | Scope | Result |
|---|---|---|---|
| `wp023_smoke_*` | WP-023 | 1 category × 2 questions | COMPLETE |
| `wp023_acceptance_*` | WP-023 | 20 categories × 2 questions (40 planned) | PARTIAL — 39/40 accepted, 1 failed (position 2, generation attempts exhausted) |
| `wp024_smoke_*` | WP-024 | 1 category × 2 questions | COMPLETE |
| `wp024_acceptance_*` | WP-024 | 20 categories × 2 questions (40 planned) | COMPLETE — 40/40 accepted |
| `wp025_smoke_*` (+ `_targets.json`) | WP-025 | 3 categories × 2 questions, targeting WP-024's worst-diversity pairs | COMPLETE — 6/6 accepted, all 3 category pairs DISTINCT |
| `wp025_acceptance_*` (+ `_targets.json`) | WP-025 | 20 categories × 2 questions (40 planned) | PARTIAL — 36/40 accepted, 4 failed (normal MCQ/quality rejections, zero generation-contract failures) |
| `wp026_control_run_results.json` | WP-026 | Focused 4-target control run, reusing the exact WP-025A diagnostic targets | 4/4 accepted (WP-025A baseline: 3/4) |
| `wp026_pos27_supplementary_probe.json` | WP-026 | Informal second production call on the single hardest control-run target (position 27, PNS divisions), for completion-report detail only | Exhausted (3/3 rejected) — recorded honestly as a residual-fragility data point, not part of the sanctioned control run |
| `wp026_acceptance_*` (+ `_targets.json`) | WP-026 | 20 categories × 2 questions (40 planned) | PARTIAL — 35/40 accepted, 5 failed (none matching the enumeration/list-recall pattern WP-026 targeted; see completion report) |
| `wp027_reeval_persisted_results.json` | WP-027 | Re-evaluation of 5 persisted WP-026 suspicious candidates (#8/#14/#23/#32/#30, not regenerated) through the strengthened GroundingValidator | #8/#23/#32 now correctly rejected; #14/#30 still correctly pass |
| `wp027_focused_live_test_results.json` | WP-027 | Focused 3-target live test (full pipeline), reusing the exact WP-026 targets for the #8/#23/#32 shapes | 3/3 accepted with genuinely single-answer framings |
| `wp027_acceptance_*` (+ `_targets.json`) | WP-027 | 20 categories × 2 questions (40 planned) | PARTIAL — 34/40 accepted, 6 failed; all 12 grounding rejections were "another answer also supported"; false-acceptance review: 0 confirmed, 1 possible (see completion report) |
| `wp028_focused_eval_results.json` | WP-028 | Focused live evaluation, 6 candidates across מערכת העצבים ההיקפית/אספקת דם/תאי מערכת העצבים | 5/6 accepted; 1 exhaustion for a non-false-acceptance reason (factual distractor errors, category-scope drift) |
| `wp028_acceptance_*` (+ `_targets.json`) | WP-028 | 20 categories × 2 questions (40 planned) - **second attempt**, the first crashed on an unrelated WP-020 structured-output truncation before completing (see completion report) | PARTIAL — 31/40 accepted, 9 failed; grounding "another answer also supported" rose to 14 (vs. WP-027's 12) - the WP's own primary metric did not improve; false-acceptance review: 0 confirmed, 2 possible (see completion report) |

WP-018 through WP-022's full acceptance runs each aborted before writing any output (the CLI only writes files after the full plan completes, or — since WP-023 — safely reaches the end with a mix of accepted/failed questions), so no output pairs exist for those.

The `wp025_*_targets.json`/`wp026_*_targets.json`/`wp027_*_targets.json`/`wp028_*_targets.json` files are an addition specific to WP-025 through WP-028: `QuestionTargetPlanner.plan_history`, captured by running the same production `ExamOrchestrator.from_default_configuration()` wiring the CLI itself uses (not a shortcut) via a small script, since the real CLI does not expose planned-target data - needed to review planned-target-vs-generated-question diversity honestly rather than guessing from question text alone.

See `evaluation/wp023_completion_report.md`, `implementation/WP-024_COMPLETION_REPORT.md`, `implementation/WP-025_COMPLETION_REPORT.md`, `implementation/WP-026_COMPLETION_REPORT.md`, `evaluation/wp026_false_acceptance_diagnostic.md`, `implementation/WP-027_COMPLETION_REPORT.md`, and `implementation/WP-028_COMPLETION_REPORT.md` for the full analysis of these runs.
