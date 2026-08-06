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

WP-018 through WP-022's full acceptance runs each aborted before writing any output (the CLI only writes files after the full plan completes, or — since WP-023 — safely reaches the end with a mix of accepted/failed questions), so no output pairs exist for those.

The `wp025_*_targets.json`/`wp026_*_targets.json` files are an addition specific to WP-025/WP-026: `QuestionTargetPlanner.plan_history`, captured by running the same production `ExamOrchestrator.from_default_configuration()` wiring the CLI itself uses (not a shortcut) via a small script, since the real CLI does not expose planned-target data - needed to review planned-target-vs-generated-question diversity honestly rather than guessing from question text alone.

See `evaluation/wp023_completion_report.md`, `implementation/WP-024_COMPLETION_REPORT.md`, `implementation/WP-025_COMPLETION_REPORT.md`, and `implementation/WP-026_COMPLETION_REPORT.md` for the full analysis of these runs.
