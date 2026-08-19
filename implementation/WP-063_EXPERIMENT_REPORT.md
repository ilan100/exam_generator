# WP-063 Experiment Report — First Single-Category Deterministic Target-Planning Pilot

## 1. Selected Category

`המערכת הלימבית` (the Limbic System). See `implementation/WP-063_CATEGORY_SELECTION.md` for the full selection process.

## 2. Selection Rationale

Selected over two other WP-060-spot-checked candidates (`עצבים קרניאליים`, `מערכת העצבים ההיקפית`) for having the cleanest, most directly source-verified inventory of the three (no numbering-fragment junk entries, no confirmed category leakage), at the disclosed cost of lower historical question volume (7 vs. 26/13). See the selection report for the full 9-criterion evaluation.

## 3. Inventory Construction

`refine_concept_inventory()` (the real, unmodified, category-agnostic function - zero code change) run against the real, freshly-retrieved student-summary evidence for `המערכת הלימבית` (8 chunks). Preserves genuine `chunk_id` provenance and first-occurrence order, exactly as for the three existing pilot categories.

## 4. Inventory Size

36 concepts (refined), reproducing WP-060's own snapshot exactly.

## 5. Inventory-Quality Findings

The pre-experiment inspection (`WP-063_CATEGORY_SELECTION.md` section 4) found this inventory the cleanest of the three candidates - true for the great majority of its 36 concepts. **The live experiment itself surfaced one concrete, previously-undetected defect that the offline inspection did not catch**: the very first concept in inventory order, `Limbic`, is not a real limbic-system sub-structure at all. Its anchored evidence is:

```text
האונה הלימביתThe Limbic Lobe
:
 המערכת הלימבית, או האונה הלימביתLobe
Limbic
., מקבלת שמה מהמילה לימבוס = גבול
היא כוללת
:עוד מבנים שאינם חלק ממוח ההרחה
```

This is a bidi-scrambled **chapter-heading line** ("האונה הלימבית / The Limbic Lobe" - "the Limbic Lobe") that PDF extraction split across several fragments; `extract_concept_inventory()`'s structural line-pattern filter matched the standalone-line fragment `Limbic` as a candidate concept because it satisfies the same ASCII/capitalized/short-line signal a genuine named entity would. `refine_concept_inventory()`'s existing WP-037 category-self-restatement exclusion did not catch it, because that exclusion is keyed to the category's own literal Hebrew text (`המערכת הלימבית`) and this fragment is an English near-synonym of a *different* Hebrew phrase (`האונה הלימבית`, "the limbic lobe") that never literally appears as the category name. `Limbic` is therefore, in substance, a second, undetected self-restatement case - the concept names the section/category itself, not a testable sub-structure - but in a textual form the existing exclusion logic was never designed to recognize. A quick look at the immediately-following inventory entries (`(DG)`, `The Rhinencephalon` vs. `Rhinencephalon` as a near-duplicate pair) suggests this specific chunk is unusually heading-dense; this is disclosed as an open question (see section 20), not fully characterized within this WP's scope.

## 6. Baseline Configuration

`QuestionTargetPlanner` constructed with `pilot_categories` explicitly fixed to the pre-WP-063 set (`{אספקת דם, מסילות עצביות, גרעיני הבסיס}`, excluding `המערכת הלימבית`) - the unmodified LLM-based free-text planning path, byte-identical to how this category behaved before this WP. Same `QuestionProducer.from_default_configuration()` (all five real validators), same `CategoryQuestionSetService`, same real OpenAI API, `GenerationMode.INDEPENDENT`.

## 7. Pilot Configuration

`QuestionTargetPlanner` constructed with no override - the real, now-updated production `PILOT_CATEGORIES` default (includes `המערכת הלימבית` after this WP's own production change) - the zero-LLM-call deterministic concept-inventory path. Otherwise identical to baseline: same producer configuration, same service, same API, same generation mode.

## 8. Sample Size

4 sequential questions per condition (8 total `CategoryQuestionSetService.generate_next()` calls), mirroring WP-036's own "four sequential questions per pilot category" evaluation shape (`implementation/WP-036_COMPLETION_REPORT.md`) - the only comparable sample-size precedent in this repository. Each condition's calls accumulate their own `existing_questions` across rounds, so category-coverage-based diversity behaves exactly as real production use would.

## 9. LLM-Call Count

Target-planning calls (directly instrumented via a counting wrapper around each condition's own `LLMProvider`): **baseline 4** (`LLMProfile.GENERATION`, one per round, no retry loop - confirms `QuestionTargetPlanner.plan_targets()`'s documented "exactly one LLM call" contract); **pilot 0** (confirms the deterministic path made zero LLM calls for target planning, as designed). Generation/validation LLM calls (inside `QuestionProducer`) were not separately instrumented; total production-cycle *attempts* (each attempt = one generation call + up to five validator calls) is used as the cost proxy instead - see section 16.

## 10. Retry Count

Total production attempts: baseline `1 + 2 + 3 + 3 = 9`; pilot `3 + 3 + 3 + 3 = 12` (every pilot round exhausted the full 3-attempt budget). Zero duplicate-replacement attempts occurred in either condition (all 8 rounds: `duplicate_replacement_attempts = 0`).

## 11. Validation Results

**Baseline**: round 1 accepted on attempt 1; round 2 accepted on attempt 2; rounds 3-4 exhausted 3/3 attempts each, every rejection driven by **grounding** ("all four answer choices are supported by the evidence" - a genuine classification-membership ambiguity, not a validator false positive) cascading into **MCQ**/**quality** rejections for the same underlying reason.

**Pilot**: all 4 rounds exhausted 3/3 attempts (12/12 attempts rejected). Rejections were overwhelmingly **grounding** + **MCQ** + **quality** failures citing the same root cause across every attempt: the assigned target `Limbic` is not a specific structure, so the model could not construct a single-best-answer question around it - real limbic structures (Hippocampus, Amygdala, Cingulate Gyrus) kept surfacing as equally-defensible correct answers. One attempt (round 3, attempt 2) was instead rejected deterministically pre-generation-acceptance by the existing WP-046 distractor-containment check (`InvalidGeneratedOutputError`: `'Limbic'` and `'Limbic System'` stand in a textual containment relationship) - direct evidence that the existing safety checks correctly recognized `Limbic` as a malformed, near-duplicate-prone target, even though they could not recover from it (no target-skip-and-retry mechanism exists within a single round).

## 12. Target-Alignment Results

**Baseline** (both accepted questions): round 1 (`היפוקמפוס ותפקודיו`, Hippocampus and its functions) produced a clean, property-based, strongly-aligned question ("Which limbic-system structure is associated with memory and learning?", correct = Hippocampus) - **strong alignment**. Round 2 (`מבנים במערכת הלימבית`, a generic "structures in the limbic system" target - itself a classification-shaped, not individually-named, target) produced a bare membership question ("Which of the following is considered part of the limbic system?") - **weak alignment**: valid in this one specific realization only because its distractors (brainstem, frontal lobe) happen to be genuine non-members, not because the target itself was well-formed; a different attempt against the same weak target could easily have failed the same way `Limbic` did in the pilot condition.

**Pilot** (target `Limbic`, all 4 rounds): **wrong target** in every attempt, per WP-063 section 19's own taxonomy - not "target name present but question asks about another concept," but the more fundamental case of a target that names the category/section itself rather than a testable member of it. Every one of the 12 attempts is target-incoherent by construction, independent of any single attempt's specific wording.

## 13. Target-Drift Cases

No classic mid-generation drift (a question silently answering a different, neighboring concept) was observed in either condition. The pilot condition's failure mode is a *pre-generation* target-quality defect (the assigned target itself is not a valid testable entity), categorically distinct from drift.

## 14. Grounding Results

Every rejection in both conditions that cited grounding did so correctly per the actual evidence (verified by direct reading of each `reason` string) - no grounding false positive or false negative was found. Grounding continues to behave as a reliable check throughout this experiment.

## 15. Language Observations

Recorded per WP-063 section 21, separately from validator pass/fail:

- **Pilot** (`Limbic`, `named_entity_target=True`): every attempt correctly rendered the target's own name in English ("Limbic") per the WP-041/058/062 deterministic mechanism - the language-compliance validator behaved exactly as designed for this one case; no attempt was rejected for a language reason.
- **Baseline** (`named_entity_target=False` for every LLM-planned target, since WP-062's own disclosed limitation means the deterministic language check never applies to non-pilot targets): round 1's accepted answers were `['היפוקמפוס', 'אמיגדלה', 'פורניקס', 'olfactory bulb']` - three Hebrew renderings of terms with established English forms (Hippocampus, Amygdala, Fornix) alongside one English term (olfactory bulb), an internally inconsistent application of `docs/LANGUAGE_POLICY.md` within a single accepted question. Round 2's accepted answers were `['פורניקס', 'קורטקס אולפקטורי', 'גזע המוח', 'האונה הפרונטלית']` - entirely Hebrew, despite every term having an established English form. **Both are real, live-observed confirmations of WP-062's own disclosed limitation** ("do not interpret absence of validator failure as proof of full language-policy compliance") - not a new defect, but the first concrete empirical instance of it actually occurring in this category.

## 16. Cost Observations

Pilot made **zero** target-planning LLM calls (vs. baseline's 4) but consumed **more** total production attempts (12 vs. 9) and achieved **zero** accepted questions (vs. baseline's 2) - i.e., the pilot condition's LLM-call savings on target planning were more than offset by wasted generation/validation attempts against a single unusable target, repeated identically every round because coverage-based exclusion only excludes concepts from *accepted* questions (WP-034's existing, correct design) and the deterministic mechanism has no fallback to a different concept within a failed round or across a failed round's boundary.

## 17. Failure Taxonomy

| Failure class | Baseline | Pilot |
|---|---:|---:|
| Accepted | 2 | 0 |
| Grounding-driven exhaustion (genuine classification ambiguity) | 2 | 4 |
| Deterministic pre-generation rejection (WP-046 containment check) | 0 | 1 attempt (within an otherwise-exhausted round) |
| Target itself invalid (not a testable entity) | 0 | 4/4 rounds |

## 18. Baseline Comparison

| Metric | Baseline (LLM planning) | Pilot (deterministic planning) |
|---|---:|---:|
| Rounds accepted | 2/4 (50%) | 0/4 (0%) |
| Target-planning LLM calls | 4 | 0 |
| Total production attempts | 9 | 12 |
| Strong-alignment accepted questions | 1/2 | 0/0 |
| Rounds blocked by a single defective target | 0 | 4/4 |

## 19. Interpretation

This is a clear, evidence-grounded **negative result for this category as currently configured**: deterministic target planning did not improve target alignment or generation acceptance for `המערכת הלימבית` - it performed materially worse than the pre-existing LLM-based baseline on the same evidence, same category, same validators, same sample size. The cause is precisely diagnosed, not merely observed: a single inventory-extraction defect (a bidi-scrambled chapter-title fragment, `Limbic`, misidentified as concept #1 in deterministic first-occurrence order) blocked all 4 pilot rounds identically, because the deterministic mechanism has no way to advance past a concept that fails every attempt within a round, and coverage-based exclusion (which works correctly for *accepted* targets, per WP-034's existing design) never gets the chance to exclude a concept that is never accepted. This is a genuine, disclosed limitation of applying the existing deterministic mechanism to a *new* category without first repeating the same per-category evidence-quality validation the three original pilot categories received over roughly a dozen WPs (WP-036 through WP-047) - exactly the risk WP-060's own section 11 already warned about in the abstract; this experiment now provides the first concrete instance of it for a specific new category.

## 20. Limitations

- This is a single-round, n=4-per-condition experiment (an engineering-scale sample, per this project's own established convention for such pilots, e.g. WP-053/WP-056) - not a statistically powered study. A different random ordering of LLM stochasticity in the baseline condition could plausibly have produced a different accept/reject split for its own 2 borderline rounds.
- The defective `Limbic` concept was diagnosed in depth because it dominated the pilot condition's entire result; the remaining 35 concepts in this category's inventory were not individually re-validated with the same scrutiny WP-036/037's own iterative process gave the three original pilot categories, so undiscovered, similar defects elsewhere in the inventory cannot be ruled out (the adjacent `(DG)` / `The Rhinencephalon` vs. `Rhinencephalon` entries are a disclosed, unconfirmed suspicion, not a confirmed second instance).
- Generation/validation LLM-call counts were not directly instrumented (only target-planning calls were); total production attempts are used as a cost proxy instead, per section 9.
- No manual repair or prompt modification was performed during or after the experiment, per WP-063 sections 23-24 - the pilot condition's 0/4 result is reported exactly as observed, not as it might look after a targeted fix.

## 21. Recommendation

**Do not keep `המערכת הלימבית` on deterministic target planning in production as currently configured.** The specific, diagnosed root cause (the `Limbic` title-fragment concept) is narrow and plausibly fixable (either by extending the WP-037 self-restatement exclusion to catch title-line artifacts more generally, or by excluding this one concept specifically), but WP-063's own scope explicitly prohibits fixing it mid-experiment or during this WP (`implementation/WP-063.md` sections 23-24, "no prompt optimization/manual repair during the experiment"). See `implementation/WP-063_COMPLETION_REPORT.md` section 16 for the full recommendation to the architect, including the option of either reverting this category from `PILOT_CATEGORIES` or authorizing a narrow, targeted fix-and-rerun as a follow-up WP.
