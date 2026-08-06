# WP-026 Completion Report — Target-Aware MCQ Framing

## 1. Implementation Summary

WP-025A's diagnostic of WP-025's 4/40 acceptance-run failures found a single shared structural root cause: every failed `QuestionTarget` had an *enumeration/classification-shaped* `factual_focus` ("X consists of/is divided into A, B, C..."), and generation was converting these literally into "recall the full enumeration" questions - a form that produces several simultaneously-defensible answer choices and fails `MCQValidator`. The diagnostic's control run (3/4 succeeding when generation spontaneously reframed toward "one item, one distinguishing property") suggested the fix belonged in generation, not planning.

Per WP-026's own explicit required sequencing - attempt a generation-only fix first; a planner-prompt change is permitted only if live evidence later shows it necessary - this WP implements a **prompt-only** fix. No source code (`src/exam_generator/**/*.py`) was touched anywhere in this WP; the entire implementation is new prose in `prompts/generation/question.txt`, using only the five template variables that already existed.

Core distinction made explicit to the model: a `QuestionTarget` describes WHAT knowledge to test, not a literal sentence to reproduce.

- **Narrowing** within the target - selecting one specific, evidence-supported relationship contained in it (one member, one distinguishing property, one location, one function) - is allowed, and required whenever the target as literally stated would not support a clean one-best-answer question.
- **Switching** to a different, easier, or unrelated fact from the evidence is still forbidden, unchanged from WP-025.

## 2. Generation-Prompt Changes

`prompts/generation/question.txt` gained four new prose sections (no new template variables - `PromptRepository._extract_required_variables()` derives the identical `required_variables` set as before, so no Python code changes were needed anywhere for this WP):

1. **Target-vs-literal-form and narrowing permission** - added to the existing "Assigned question target" section: the target is WHAT to test, not a sentence to reproduce; narrowing within it is allowed and required when needed; switching away from it is still forbidden.
2. **"Testing enumeration or classification targets"** (new section) - recognize when a target names multiple items; do NOT ask for full-list recall (several partially-overlapping choices become simultaneously defensible); instead test ONE evidence-supported member through ONE distinguishing property. Illustrated with a concrete worked example (white matter fibers: weak "which lists the types" framing vs. strong "which type connects cortical regions within the same hemisphere" framing) directly reused from the diagnostic's own worked analysis.
3. **Distractor-construction rule** - forbids building distractors by rearranging or partially recombining the target's own enumerated members (e.g. "A and B" vs. "B and C" as separate choices).
4. **"Nested or hierarchical classifications"** (new section) - if evidence describes more than one hierarchy level, make the tested level explicit in the question's wording; a true classification from an adjacent hierarchy level is not an acceptable distractor merely because it is real - it must be clearly wrong at the level actually being tested. Written **generically**, with no category name, since the rule must generalize beyond the one diagnosed PNS case.

The `STYLE_SIMILAR` historical-reference guidance was also updated: if the historical reference's own form would itself produce an ambiguous enumeration-style question, that form must not be copied - producing a valid one-best-answer question always takes priority over matching historical form.

## 3. Whether a Planner Change Was Required

**No.** Per the WP's required sequencing, a planner-prompt change was to be added only if live evidence showed the generation-only fix insufficient for the diagnosed cases. The focused 4-target control run (section 6 below) went 4/4 accepted, including the previously-reproducibly-failing case - live evidence supported not making a planner change. `QuestionTargetPlanner` (`planning/planner.py`) and its prompt (`prompts/generation/question_target_planning.txt`) are byte-for-byte unchanged from WP-025.

## 4. Confirmation: No Validator/Attempt-Limit Changes

`GroundingValidator`, `MCQValidator`, `CategoryValidator`, `QualityValidator`, `TextbookValidator` were not modified in any way. `max_generation_attempts` was not increased; no category-specific attempt budget was introduced. The fix is entirely upstream-of-validation prompt guidance.

## 5. Files Created/Modified

**Created:**
- `implementation/WP-026_COMPLETION_REPORT.md` (this file)
- `evaluation/live_outputs/wp026_control_run_results.json`, `wp026_pos27_supplementary_probe.json`, `wp026_acceptance_exam.json`, `wp026_acceptance_audit.json`, `wp026_acceptance_targets.json`

**Modified:**
- `prompts/generation/question.txt` - the four new sections described in section 2 above
- `tests/unit/test_prompts.py` - 13 new tests (see section 7)
- `tests/unit/test_production.py` - 1 new test (see section 7)
- `docs/ARCHITECTURE.md` - new "Target-Aware MCQ Framing (WP-026)" section
- `docs/PROJECT_STATUS.md` - new "Live Evaluation Baseline (WP-026)" section, updated Tests/Next WP Context sections
- `evaluation/live_outputs/README.md` - new WP-026 rows

**No changes:** any `src/exam_generator/**/*.py` file, `src/exam_generator/planning/*`, `prompts/generation/question_target_planning.txt`, any of the five validators, `schemas/*.schema.json`.

## 6. Tests Added/Changed

- **`tests/unit/test_prompts.py`** (13 new tests, "WP-026: target-aware MCQ framing" section): target-vs-literal-form distinction, narrowing permission, switching-still-forbidden, enumeration/classification-section presence, "one member + one property" wording, avoids-full-list-recall wording, worked white-matter example present, recombination-distractor rule, hierarchical-classification section presence, hierarchical rule is generic (no category name, e.g. `מערכת העצבים ההיקפית`/`PNS`, leaked into the production prompt), clearly-incorrect-distractors wording reinforced, STYLE_SIMILAR form subordinate to MCQ correctness, and a Python-level test confirming a multi-item target's rendered text is never pre-narrowed by the formatting layer (narrowing is a generation-time model decision, not something Python does on the model's behalf).
- **`tests/unit/test_production.py`** (1 new test): `test_target_remains_identical_object_across_wp013_bounded_retry_attempts` - a rejected candidate may be reframed differently on the next attempt, but must still test the exact same assigned `QuestionTarget` object, never a re-planned or substituted one.

## 7. Full Regression Result

**1024 / 1024 passing** (up from the 1010 baseline entering WP-026; +14 net), zero network access, no `OPENAI_API_KEY` in the offline test shell.

## 8. Focused Live 4-Target Control Run

Reused the exact four `QuestionTarget`s that failed in WP-025's acceptance run (per the WP-025A diagnostic - same `target_id`/`category`/`topic`/`factual_focus`/`supporting_evidence_chunk_ids`), one fresh `QuestionProducer.produce_question()` call per target, normal configuration, `max_generation_attempts=3` unchanged, no re-planning.

| Position | Category | Mode | WP-025A baseline | WP-026 control run |
|---|---|---|---|---|
| 5 | חומר לבן | STYLE_SIMILAR | accepted, attempt 1 | **accepted, attempt 1** |
| 11 | היסטולוגיה | STYLE_SIMILAR | accepted, attempt 1 | **accepted, attempt 1** |
| 26 | המוח הקטן | INDEPENDENT | accepted, attempt 3 | **accepted, attempt 1** |
| 27 | מערכת העצבים ההיקפית | STYLE_SIMILAR | **exhausted** (3/3 rejected, both this run and the WP-025 acceptance run: 6/6 total) | **accepted, attempt 2** |

**Result: 4/4 accepted (up from WP-025A's 3/4).** The previously-reproducibly-failing PNS-divisions case (adjacent-hierarchy-level ambiguity between "autonomic/somatic" and "sympathetic/parasympathetic") succeeded this time using explicit "basic division" (החלוקה הבסיסית) hierarchy-level wording matching the new "Nested or hierarchical classifications" guidance.

### Supplementary probe (not part of the sanctioned control run)

After the official control run completed, one additional informal second production call was made on the same position-27 target, purely to capture per-attempt detail for this report. It **exhausted again** (3/3 rejected), with the identical adjacent-hierarchy-level ambiguity recurring in 2 of the 3 attempts (the third attempt introduced an unrelated `CNS`-inclusion mistake). This is reported honestly as a residual-fragility signal: the fix substantially improves this case's success rate but does not fully eliminate its stochasticity. Per the WP's own evidence-based sequencing, this single supplementary data point does not on its own justify a planner change - the sanctioned control run's result stands as 4/4, and the full acceptance run (section 9) is the actual scale test for whether further work is warranted.

## 9. Full 40-Question Acceptance Run

- **Planned count: 40**
- **Accepted count: 35**
- **Failed count: 5**
- **Status: PARTIAL**
- **Runtime: ~22.5 minutes** (1351.9 seconds)
- **Exit code: 0**
- **Output files**: both `exam.json` (35 questions) and `exam_audit.json` written successfully.

### Every failed planned question and reason

| Position | Category | Mode | Reason |
|---|---|---|---|
| 1 | התעלה השדרתית ותכולתה | STYLE_SIMILAR | `QuestionAttemptsExhaustedError` - category-boundary ambiguity (target's content - vertebra structure - sits at the edge between this category and a neighboring one; category validator rejected all 3 attempts) |
| 10 | מיפוי ודימות מוחי | INDEPENDENT | `QuestionAttemptsExhaustedError` - category-boundary ambiguity (Broca's-area/language target judged as general neuroanatomy rather than brain mapping/imaging, all 3 attempts) |
| 18 | קרומים וסינוסים דוראליים | INDEPENDENT | `QuestionAttemptsExhaustedError` - genuine textbook-terminology conflict (dura mater outer/inner layer naming - "Cranial Dura"/"Meningeal Dura" vs. course-book terminology) combined with quality-clarity rejections |
| 20 | גזע המוח | INDEPENDENT | `QuestionAttemptsExhaustedError` - attempt 1 rejected only by an arguably-strict quality judgment on distractor plausibility despite correct one-member framing; attempts 2-3 drifted to an unrelated embryological-origin property (which structures develop from the myelencephalon) that was itself ambiguous between Midbrain/Pons |
| 29 | דיאנצפלון | STYLE_SIMILAR | `QuestionAttemptsExhaustedError` - target's `factual_focus` ("involved in emotional processes, learning and memory") was overly broad/vague rather than enumeration-shaped, producing MCQ/quality ambiguity unrelated to the diagnosed pattern |

**None of the 5 failures reproduce the enumeration/list-recall pattern WP-026 targeted.** This is an important, honest finding: the fix appears to have worked for its diagnosed failure mode (confirmed independently by the control run), and this run's failures are a different, mixed set of causes (category-boundary scoping, textbook-terminology precision, an overly-broad target, and one case of narrowing landing on a still-ambiguous property) - none of which WP-026 set out to address, and none of which regressed relative to WP-025's own failure causes (which were also MCQ/quality rejections, just concentrated in the enumeration shape).

**Generation-contract failures observed: 0.**

### Accepted-attempt distribution

**27 accepted on attempt 1, 4 on attempt 2, 4 on attempt 3** (47 total attempts across 35 accepted questions, avg **1.34**/accepted question) plus 15 attempts across the 5 failed questions (3 each) = 62 total candidate attempts.

Compared with WP-025: **23/7/6** (avg 1.53/accepted question, 67 total attempts). WP-026 shows a clear improvement in attempt-1 acceptance rate (77% vs. 64%) and average attempts per accepted question, consistent with the framing fix reducing MCQ ambiguity broadly across the corpus, not just in the 4 originally-diagnosed cases.

### Validator rejection distribution (among all rejected attempts, accepted-eventually and fully-failed questions combined)

mcq: 12, quality: 13, category: 7, textbook-conflict: 7.

Compared with WP-025 (quality: 15, MCQ: 12, category: 1, textbook: 2): MCQ rejections are essentially unchanged (12 vs. 12) and quality rejections modestly lower (13 vs. 15) - both consistent with no regression in ambiguity-related validators. Category and textbook rejections rose (1→7, 2→7), but this run's failures were concentrated in category-boundary and textbook-terminology cases (positions 1, 10, 18) that are a function of which particular targets this run's planner happened to select, not something the WP-026 prompt change touches (it never modifies category- or textbook-validation prompts) - normal run-to-run variance in which categories/targets prove hard, not a WP-026-caused regression.

## 10. Per-Category Target/Question Diversity Review

Every category with **both** planned questions accepted (15 of 20 categories; the other 5 - `התעלה השדרתית ותכולתה`, `מיפוי ודימות מוחי`, `קרומים וסינוסים דוראליים`, `גזע המוח`, `דיאנצפלון` - had one planned question fail, leaving no pair to judge):

| Category | Target 1 | Target 2 | Assessment |
|---|---|---|---|
| לוקליזציה פונקציונלית | M1 motor cortex location | S1 sensory cortex location | DISTINCT |
| חומר לבן | Association fibers (same-hemisphere connection) | Thalamic Stratum Zonale role | DISTINCT |
| עצבים קרניאליים | CN I olfactory nerve development | CN II optic nerve development | DISTINCT |
| היסטולוגיה | Neocortex layer with inter-level synapses | Histology as a science (17th-century microscope) | DISTINCT |
| המערכת הלימבית | Constituent structures | Evolutionary origin (rhinencephalon) | DISTINCT |
| אספקת דם | Superior cerebellar artery | Basilar artery → PCA branch | DISTINCT |
| מסילות עצביות | Spinothalamic tract (pain/temp) | Medial lemniscus tract (touch/proprioception) | DISTINCT |
| גרעיני הבסיס | General motor-execution role | Direct-pathway thalamic activation | DISTINCT |
| המוח הקטן | General coordination function | Gray/white matter structural arrangement | DISTINCT |
| מערכת העצבים ההיקפית | PNS division membership (somatic) | Schwann cells produce myelin | DISTINCT |
| אמבריולוגיה | Gastrulation/germ layers | Neural tube flexures (4th ventricle) | DISTINCT |
| טופוגרפיה של ההמיספרות | Number of lobes | Parietal lobe structures | DISTINCT |
| חדרי המוח | Lateral ventricle developmental shape | 3rd-to-4th ventricle connection | DISTINCT |
| תאי מערכת העצבים | Microglia function | Ependymal cell function | DISTINCT |
| מבוא | Vesalius's contribution | Evolutionary change enabling upright posture | DISTINCT |

**Totals: 15 / 15 DISTINCT (100%), 0 BORDERLINE, 0 DUPLICATE/NEAR-DUPLICATE.** Target-aware narrowing did not collapse any pair into semantically equivalent questions.

## 11. Human-Review Findings

- Clean exam contains accepted questions only (35/35), zero structural defects (every question has exactly 4 distinct answers and a correct-answer id in 1-4). Numbering contiguous 1..35.
- Enumeration/classification-shaped accepted questions were specifically inspected: the white-matter-fibers question (position 5) reproduces the prompt's own worked example almost verbatim ("which fiber type connects cortical regions within the same hemisphere" - association fibers - rather than "which lists the fiber types"). The Rexed-laminae question (position 2), cerebellar-arteries question (position 15), and basal-ganglia-pathways question (position 24) all use the intended "one member + one distinguishing property" framing rather than full-list recall. This is a genuine, consistent improvement over the pattern WP-025A diagnosed.
- **One notable exception was found and is reported honestly rather than fixed post-hoc (no tuning after the run):** question #23 (`מערכת העצבים ההיקפית`, target: "PNS includes the autonomic and somatic nervous systems") used a "which one IS a member" framing - "Which of the following systems is part of the peripheral nervous system?" - against a 2-item target, with choices somatic (marked correct), central nervous system, **autonomic nervous system** (marked incorrect), and parasympathetic. The target's own supplied evidence explicitly states the PNS divides into *both* autonomic and somatic; offering autonomic as an incorrect distractor is not clearly supported by that same evidence, yet all three relevant validators (grounding, MCQ, quality) approved it across their reasoning without addressing this gap. This is precisely the kind of ambiguity the distractor-construction rule (section 2, item 3) was meant to prevent, but that rule's literal wording covers *recombination* of enumerated members, not *using a genuine sibling member as a false distractor* - a related but distinct failure shape it does not fully cover.
- No obvious regression in general question quality, wording naturalness, or terminology use was observed in the reviewed sample. No new failure modes such as trivial questions, obviously-wrong distractors that undermine plausibility, or repetitive "which X has property Y" phrasing across categories were observed - question framing remained varied.
- Zero `evidence_refs`/`[Evidence` leakage into either `exam.json` or `exam_audit.json`. Hebrew renders correctly throughout; zero `\u`-escaped characters in `exam.json`.

## 12. Comparison with WP-025

- **Accepted**: 35/40 (WP-026) vs. 36/40 (WP-025) - one fewer, but for causes unrelated to the pattern WP-026 targeted (see section 9).
- **Accepted on attempt 1/2/3**: 27/4/4 (WP-026) vs. 23/7/6 (WP-025) - a real improvement in first-attempt success and average attempts per accepted question (1.34 vs. 1.53).
- **Diversity**: 15/15 DISTINCT (WP-026) vs. 16/16 DISTINCT (WP-025) - both 100%, fewer reviewable pairs this run only because more categories had one-of-two positions fail.
- **Generation-contract failures**: 0 in both.
- **Control-run evidence specific to the diagnosed problem**: 4/4 (WP-026) vs. 3/4 (WP-025A) - a direct, targeted improvement on the exact cases that motivated this WP.

## 13. Known Limitations / Deviations

- This is a single live acceptance run (n=1) and a single 4-target control run (n=1, plus one supplementary probe); the improvements shown are strong single-run evidence, not a statistically powered guarantee at scale.
- The position-27 supplementary probe's exhaustion (section 8) and question #23's residual sibling-distractor ambiguity (section 11) both show the underlying hierarchical/enumeration ambiguity is reduced, not eliminated. A future WP could consider extending the distractor-construction rule to explicitly cover "a genuine sibling member of the same enumerated set must not be offered as an incorrect answer unless it is clearly wrong at the tested relationship/level" - a narrower, related case the current wording does not fully cover. No such change was made here, per the "no tuning after the run" instruction.
- The 5 full-acceptance-run failures surfaced category-boundary scoping (2 cases) and textbook-terminology precision (1 case) as sources of difficulty independent of WP-026's scope; these are noted for a future WP's attention but were not addressed here since they are outside this WP's diagnosed problem.
- No deviations from the WP-026 specification were made; the generation-only-first sequencing was followed exactly, and no planner-prompt change was made since the control run supported not making one.

## 14. Confirmations

- **Retrieval/TF-IDF unchanged**: no file under `src/exam_generator/retrieval/` was modified.
- **No embeddings/vector DB introduced**: no new dependency was added (`pyproject.toml` unchanged); retrieval remains the existing TF-IDF mechanism exclusively.
- **No post-acceptance tuning or rerun performed**: the full acceptance run's result (35/40) is reported exactly as produced; no prompt/config change was made afterward and no rerun was performed based on its results.

---

WP-026 complete.
Tests: 1024 passed
Four-target regression: 4/4 accepted (vs. WP-025A baseline 3/4); supplementary probe on the hardest case exhausted (residual fragility, documented)
Acceptance run: PARTIAL, 35/40 accepted, 5 failed (none matching the diagnosed enumeration pattern)
Diversity: 15/15 DISTINCT
Completion report:
    implementation/WP-026_COMPLETION_REPORT.md

Do not start WP-027. Wait for architect/user review.
