# WP-047 Completion Report — Target-to-Answer Contract and Identity Enforcement Study

## 1. Objective

WP-046 introduced a narrow post-generation distractor-containment check, and separately exposed that `Corticospinal Tract` produced an accepted question whose correct answer was `Precentral Gyrus` - factually grounded, all five validators passed, but not the requested target. WP-047's objective: determine what constitutes a valid relationship between the requested target, the tested relationship, and the accepted answer - and only then decide whether deterministic enforcement is justified. The explicit instruction not to assume `correct_answer == target` is universally required, and to search first for legitimate related-entity answers, is treated as a real constraint on this investigation, not a formality.

## 2. WP-046 Findings Relevant to Target Identity (Recap, OBSERVED)

`Corticospinal Tract` → `Precentral Gyrus` (WP-046's own pilot round 4) is a live, independent recurrence of the identical substitution WP-043's own pilot already produced once (round 3, `מסילות עצביות`) - the same target, the same wrong answer, two WPs and months of work apart. WP-046's own architecture review named this "Problem C: target identity substitution... unresolved and repeatedly demonstrated" and explicitly recommended this WP investigate the contract before implementing anything.

## 3. Current Target/Relationship Architecture (Section 7 Investigation)

Inspected `models/target.py`, `models/relationship.py`, `generation/relationship.py`, `planning/concept_identity.py`, `generation/generator.py`, `prompts/formatting.py` before proposing anything:

- **`QuestionTarget`** (`models/target.py`) represents WHAT to test: `topic` (the target's own name/description), `factual_focus` (anchored evidence), plus the WP-040/043/044 boolean/optional signals (`named_entity_target`, `is_source_role`, `source_relationship_entity`, `is_enumeration_member`).
- **`QuestionRelationship`** (`models/relationship.py`) + `extract_relationship()` represents the tested relationship as a coarse, deterministic, keyword-classified `relationship_type` - derived from `target.factual_focus` (the evidence), **not** from anything the LLM actually produces. It is a pre-generation *hint*, never a post-hoc record of what the final candidate actually tests.
- **`ConceptIdentity`** (`planning/concept_identity.py`, WP-038) represents deterministic normalization (whitespace/case/Unicode) plus a narrow, evidence-derived alternate-language form - but WP-038's own investigation found **zero** explicit bilingual pairings exist anywhere in the real pilot-category corpus, so this mechanism has never actually recognized a cross-script form for any of these targets. It is not a general aliasing solution.
- **Existing (informal) target-alignment checking**: **there is no deterministic target-alignment check in production code before this WP.** WP-040's own `format_target_answer_requirement()` states the requirement as prompt prose only ("the correct answer choice itself names TARGET CONCEPT... not a description of it"); every "alignment" measurement in every prior WP's own pilot script (`deterministic_alignment_preclassification`) is a **read-only, diagnostic-only** annotation computed for observability, never a gate on acceptance. WP-044 Part B's `_validate_target_role_consistency()` is the one existing *structural* check, but it is scoped only to `is_source_role` targets, checking only that the answer does not name the *specific known downstream entity* - not a general target-identity check.
- **Coverage** (`planning/coverage.py`, WP-034/038) tracks accepted answer *text*, not target identity - an unrecognized-answer directly causes target reselection (already documented as the WP-045 `Globus Pallidus` coverage-recognition consequence).

**Conclusion (section 7's own explicit instruction: "do not invent a new abstraction if the existing architecture already contains the required concept")**: the required concept - "does this candidate's answer already identify the target" - has no existing deterministic check to extend beyond WP-044 Part B's own narrow pattern. That pattern (a plain, normalized substring-containment check, raising the same `InvalidGeneratedOutputError` category, before any of the five validators) is the correct architectural precedent to generalize, not a new subsystem.

## 4. Relationship Inventory (Section 8, Required Table)

All ten classified relationship types from `generation/relationship.py`'s own keyword table, checked against every real, historically-accepted pilot-category case found (section 7 below):

| Relationship | Target's role (real observed cases) | Expected answer role | May answer differ from target? | Why |
|---|---|---|---|---|
| `SUPPLIES` | Source/supplier (`Basillar artery`) or supplied entity (`Superior cerebellar artery`) | The target itself | **No, in every real case observed** - WP-043/044 Part B already exists specifically to keep the answer as the source-role target itself, never the downstream entity | WP-040's answer-identity requirement is unconditional; WP-044 Part B enforces it structurally for this one role |
| `CONTAINS` | Category/member (`Globus Pallidus`, basal-nuclei siblings) | The target itself | No real case found where it legitimately differs | Same |
| `LOCATED_IN`, `CONNECTS`, `INNERVATES`, `PROJECTS_TO`, `DEVELOPS_INTO`, `RECEIVES_INPUT_FROM`, `DRAINS_INTO`, `SURROUNDS` | Not exercised by any real accepted pilot-category question found with a non-`UNSPECIFIED` classification of these specific types | The target itself, by the same unconditional WP-040 requirement | No real case found | WP-040's requirement is stated independently of relationship type |
| `UNSPECIFIED` | Most real pilot-category targets (the keyword table rarely matches this corpus's own anchored evidence text) | The target itself | No real case found | Same |

**This table is a real limitation, not a gap glossed over**: most real pilot-category targets classify as `UNSPECIFIED` (the keyword table is derived from `factual_focus`, which for many targets is a bare or near-bare anchored snippet with no relationship keyword) - `relationship_type` was **not** found to be a reliable predictor of anything about the actual generated question or answer in this dataset, confirming section 8's own request not to assume the relationship list, or its predictive value, is complete or useful without evidence. The single exception where a target's *role* (not `relationship_type`) provably matters is `is_source_role`, already handled by WP-044 Part B.

## 5. Known Failure Reconstruction (Section 9)

**OBSERVED, directly from WP-046's own real pilot data** (`evaluation/live_outputs/wp046_pilot_records.json`, `מסילות עצביות` round 4):

```
Target identity:        Corticospinal Tract (named_entity_target=True, is_source_role=False)
Question:                "מהו המקום בו מתחילה המסילה המוטורית Corticospinal Tract במוח?"
                          ("where does the Corticospinal Tract motor pathway begin in the brain?")
Question relationship:   an origin/location question - never explicitly classified by
                          extract_relationship() as anything but whatever its factual_focus happened
                          to match (this specific candidate's own tested relationship is never recorded
                          anywhere deterministic - only the LLM's own free-text, untrusted blueprint
                          reasoning, which is discarded)
Correct answer:          Precentral Gyrus
Evidence:                genuinely supports "the Corticospinal Tract begins at the Precentral Gyrus" -
                          the grounding validator's own reason confirms this literally
Validator results:       grounding passed, mcq passed, category passed, quality passed, textbook CONSISTENT
Target-alignment result: the pilot's own deterministic preclassification correctly flagged NOT_ALIGNED
                          (informational only at the time - not yet a gate)
Coverage result:         Corticospinal Tract was NOT recognized as tested (coverage tracks answer text,
                          and "Precentral Gyrus" bears no textual relationship to "Corticospinal Tract")
```

**Why the existing architecture accepted it**: every one of the five validators independently checks its own narrow concern (factual grounding, MCQ structure, category fit, quality/clarity, textbook consistency) - **none of them is responsible for, or capable of, checking whether the correct answer identifies the assigned target**, since none of them receives `target` as an input at all (confirmed by inspecting each validator's own call signature in `validation/`). WP-040's own answer-identity requirement is prompt-only prose, and nothing before this WP structurally verified it for the general case.

## 6. Additional Real Cases (Section 10/11, Not Built Around One Example)

Mined every real, historically-accepted `(target, correct_answer_text)` pair recorded across every pilot WP's own live-run JSON artifact (`evaluation/live_outputs/wp036_pilot_records.json` through `wp046_pilot_records.json` - genuine production data, never manufactured):

### A. Direct target answers (the overwhelming majority)

Every `אספקת דם`/`גרעיני הבסיס`/`מסילות עצביות` accepted answer from WP-041 onward (English-first policy active) that is not listed below - 41 of 44 real post-WP-041 accepted candidates.

### B. Valid related-entity answers

**None found.** Despite specifically searching for this category across the full real dataset (WP-036 through WP-046, ~54 real accepted pilot-category questions total), **no real, historically-accepted case exists anywhere in this project's own data where a named-entity target's correct answer legitimately, intentionally identified a different entity.** This is a genuine, disclosed negative finding, not an oversight - see section 12 for the direct consequence.

### C. Invalid target substitutions (real, classified `INVALID_TARGET_SUBSTITUTION` only after inspecting each one's own relationship/evidence, never assumed from the answer text alone)

| # | WP | Target | Accepted answer | Why classified invalid |
|---|---|---|---|---|
| 1 | WP-036 (pre-WP-043) | `Basillar artery` | `Superior Cerebellar Artery` | The exact downstream-entity substitution WP-042 later diagnosed and WP-043/044 Part B fixed structurally for this one role |
| 2 | WP-036 | `The Basal Gang` | `חלק ממערכת העצבים המרכזית` ("part of the CNS") | A functional/categorical description, not an entity name at all |
| 3 | WP-037 | `Corpos Str` | `להגביר תנועה על ידי הפעלת מסלולי תנועה` (functional description) | Same shape |
| 4 | WP-038 (pre-WP-040) | `Corpos Str` | `Caudate Nucleus` | A different, unrelated named sibling entity |
| 5 | WP-043 | `Corticospinal Tract` | `Precentral Gyrus` | Section 5 above |
| 6 | WP-045 | `Globus Pallidus` | `מדכא את התלמוס ומפחית תנועה` (functional description) | Already documented in WP-045's own report |
| 7 | WP-046 | `Corticospinal Tract` | `Precentral Gyrus` | The direct repeat that triggered this WP |

### D. Uncertain cases

**None found** - every real misalignment instance in the dataset was independently diagnosed, at the time it occurred, by that WP's own manual review or architecture review as a genuine defect, never left ambiguous.

## 7. Successful Controls (Mandatory)

44 real post-WP-041 accepted candidates were checked directly against the proposed containment rule (normalized `target.topic` contained in normalized `correct_answer_text`): **41/44 pass cleanly** (correctly identify their own target), and the 3 that fail are exactly the 3 post-WP-041 instances already listed in section 6.C (rows 5-7) - not one additional, previously-unknown case was incorrectly flagged.

## 8. Target-to-Answer Matrix (Section 13, Required Deliverable)

| Target | Relationship | Answer | Answer = Target? | Related entity? | Valid alignment? | Evidence |
|---|---|---|---|---|---|---|
| `Corticospinal Tract` | origin/location (untracked `relationship_type`) | `Precentral Gyrus` | No | Yes | **No** | Evidence genuinely supports the *fact*, but not as the target's own identity |
| `Basillar artery` | `SUPPLIES` (source role) | `Basillar artery` | Yes | - | Yes | WP-044 Part B already enforces this |
| `Globus Pallidus` | `CONTAINS`-adjacent (member of basal nuclei) | `Globus Pallidus` (WP-044/046) or a functional description (WP-045) | Yes / No | - / No | Yes / **No** | Same target, different runs - confirms the *answer*, not the relationship, determines alignment |
| `Corpos Striatum` | `UNSPECIFIED` | `Corpos Striatum` (post-WP-040) or `Caudate Nucleus` (pre-WP-040) | Yes / No | - / Yes | Yes / **No** | Same |
| `Inferior Cerebellar Artery (PICA)` | `UNSPECIFIED` | `Inferior Cerebellar Artery (PICA)` | Yes | - | Yes | Consistently aligned across three separate pilots |

**Reading the matrix**: `relationship_type` never predicts misalignment in this dataset - the same target under the same nominal relationship classification is sometimes aligned and sometimes not, purely as a function of what the LLM happened to answer with on a given attempt. This directly supports section 12's own required question: **the answer's own identity is what determines alignment, not the relationship type or evidence shape.**

## 9. Target-Alignment Definition (Section 14)

Given section 6.B's empirical finding (zero real legitimate related-entity answers exist for named-entity pilot-category targets), the evidence supports the **simpler**, not the more permissive, hypothesis stated in section 14 of the WP spec:

```
TARGET_ALIGNED :=
    target.named_entity_target is True
    AND normalize(target.topic) is contained within normalize(correct_answer_text)
```

with the honest, disclosed caveat that this is validated only for the scope actually observed (pilot-category, named-entity, post-WP-041 English-first targets) - not proposed as a claim about relationship semantics in general, since no relationship type in the real data was found to require a different definition.

## 10. Identity/Alias/Normalization Analysis (Section 15/16)

- **Do not define identity as bare string equality** - correctly avoided: the check uses containment (target's name may appear within a longer answer), not equality, matching the existing `_validate_target_role_consistency()`/`_validate_distractor_containment()` precedent.
- **`ConceptIdentity` was investigated and found insufficient for this purpose** (section 3) - it has never recognized a cross-script form for any real pilot-category target (WP-038's own already-disclosed Outcome C), so it provides no aliasing capability beyond what plain normalization already gives.
- **Abbreviations/parenthetical forms**: real targets like `Anterior Inferior Cerebellar Artery (AICA)` are always answered with their **full, verbatim topic text** in every real accepted case examined - never the bare abbreviation alone. WP-041's own instruction explicitly forbids substituting "a different English form (an abbreviation or alternate spelling)," so no additional alias-handling was found necessary or evidence-justified.
- **Why cross-script matching is safe to skip now, when it was not safe in WP-038**: every historical Hebrew-transliteration answer in the dataset (section 6, e.g. `עורק סופריור צרבלרי` for `Superior cerebellar artery`) **predates WP-041's English-first policy**. Since WP-041, every named-entity pilot-category target's own `topic` is required, by explicit instruction, to be answered in English/ASCII verbatim - eliminating the legitimate-cross-script-answer scenario going forward. This check would **not** have been safe to add before WP-041 existed; it is safe now specifically because WP-041 already solved the language half of this problem, leaving only the identity half for this WP.

## 11. Enforcement-Location Analysis (Section 19)

Considered `planning` (target selection - too early, nothing to check yet), `generation constraints` (prompt-only - already tried, WP-040's own existing prose, proven insufficient by the repeated real failures this WP investigates), `validation` (would require adding `target` as an input to one of the five validators or adding a sixth - explicitly forbidden by every prior WP's hard constraints, and WP-047's own), and **post-generation deterministic check** (the WP-044/046 precedent). The last is the only option consistent with every hard constraint in this project's history; selected, matching WP-044 Part B's and WP-046's own exact architectural pattern.

## 12. Deterministic Feasibility (Section 20)

**YES**, for the scope actually observed (named-entity pilot-category targets, current post-WP-041 architecture) - not `PARTIALLY` or `NO`. This is a stronger conclusion than WP-047's own spec anticipated (section 31 lists all three outcomes as acceptable), reached only because the empirical search for outcome B/C's own required counter-examples (legitimate related-entity answers) came back genuinely empty across the full real dataset, not because the question was assumed easy.

## 13. Safety Analysis (Section 21, All Eleven Criteria Checked)

| Criterion | Met? | Evidence |
|---|---|---|
| Explains multiple real cases or one clear structural class | ✓ | 7 real historical instances (section 6.C), one clear class: named-entity target, answer fails to contain target's own name |
| Has successful controls | ✓ | 41/44 real accepted candidates correctly unflagged (section 7) |
| Supports legitimate related-entity answers | N/A→✓ | None exist in the real data to support; nothing to break |
| Does not depend on target-specific names | ✓ | Generic mechanism |
| Does not depend on one exact phrase | ✓ | Substring containment, not phrase matching |
| Does not use fuzzy semantic matching | ✓ | Exact normalized substring only |
| Does not require an LLM judge | ✓ | |
| Preserves existing validators | ✓ | Zero validator files touched |
| Preserves the three-attempt budget | ✓ | Unchanged, confirmed live (pilot attempts still capped at 3) |
| Does not break WP-046 | ✓ | `_validate_distractor_containment()` fired independently and correctly 5 times in this WP's own live pilot; dedicated coexistence test added |
| Deterministic and testable | ✓ | |

**All eleven criteria met. Decision: implement**, per section 31 Outcome 1 (a safe general deterministic contract) for the scope this WP actually investigated.

## 14. Implementation

**`_validate_target_answer_identity()`** (new, `generation/generator.py`), called immediately after `_validate_distractor_containment()` inside `QuestionGenerator.generate_candidate_question()`. For `named_entity_target` targets, rejects a candidate whose correct-answer text does not contain the target's own `topic` text (normalized) - **one-directional only** (answer must contain target, never the reverse, to avoid accepting a bare partial-word fragment of the target's own name as if it were a complete answer). Raises the identical `InvalidGeneratedOutputError` category and attempt-consumption behavior as every other pre-validator check in this module. No validator, coverage, retry-budget, schema, English-first, or WP-044/046 mechanism was touched (confirmed via `git diff --stat`).

## 15. Tests

10 new tests, `tests/unit/test_generation.py`: direct target-identity answer accepted; whitespace/case variation still accepted (normalization, not a new alias mechanism); target name plus surrounding text still accepted (one-directional containment); the real `Corticospinal Tract`/`Precentral Gyrus` regression (mandatory, section 27E) rejected; the real `Globus Pallidus` functional-description shape rejected; the real pre-WP-040 `Corpos Striatum`/`Caudate Nucleus` sibling-substitution shape rejected; non-named-entity targets never trigger the check; the check never consumes a second LLM call; the check's own source is deterministic; **WP-046's own distractor-containment check still fires independently and correctly alongside this new check** (mandatory coexistence test, section 26/27F).

## 16. Regression

`.venv/bin/python -m pytest -q` → **1396 passed, 0 failed** (up from 1386, WP-046's own baseline). `scripts/generate_schemas.py` re-run: all three public schema files byte-identical. `git diff --stat` confirms `src/exam_generator/validation/`, `config/app.yaml`, and every WP-037 through WP-046 mechanism outside `generation/generator.py` are untouched - only one new function plus its call site were added, and `tests/unit/test_generation.py` gained the 10 new tests.

## 17. Pilot Methodology

One fresh live run (required since production code changed): same three pilot categories × four sequential questions each, via the real, unmodified `CategoryQuestionSetService`. No manual repair, no configuration change after seeing results, no selective reruns. Launched with `python3 -u` and direct file redirection from the start; completed cleanly.

## 18. Pilot Results

**7/12 accepted (58.3%)**, down from WP-046's own 11/12 - a real, disclosed number, investigated in full below before any interpretation is offered.

| Category | Accepted | Distinct targets | Notable |
|---|---|---|---|
| `אספקת דם` | 2/4 | 2/4 | `Basillar artery` exhausted rounds 2-3, accepted round 4 |
| `גרעיני הבסיס` | 2/4 | 2/4 | `Nucleus Accumbens` exhausted rounds 2-3, accepted round 4 |
| `מסילות עצביות` | 3/4 | 3/4 | `Corticospinal Tract` exhausted round 3, accepted round 4 |

**Critical, directly-verified finding: the new WP-047 check fired zero times in this entire pilot (confirmed by inspecting every one of the 29 real attempts' own `generation_failure_message` text for a "WP-047" citation - none found).** Every one of the 5 rejected/exhausted rounds' attempts was rejected for a different, already-existing reason:

- `מסילות עצביות` round 3 (`Corticospinal Tract`, all 3 attempts) and round 4 attempts 1-2: **WP-046's own distractor-containment check fired** (5 times total this pilot, up from WP-046's own pilot's 3 times) - `Anterior`/`Lateral Corticospinal Tract` chosen as a distractor again, the same already-understood mechanism, not a new problem.
- `אספקת דם` round 2-3 (`Basillar artery`, 6 attempts) and `גרעיני הבסיס` round 2-3 (`Nucleus Accumbens`, 6 attempts): **ordinary grounding/MCQ/textbook validator rejections**, unrelated to target identity - e.g. `"Both the Basilar artery and the Anterior Inferior Cerebellar Artery (AICA) are..."` (grounding, multiple-supported-answers, the same generic classification-ambiguity family WP-046 already found unresolved for `גרעיני הבסיס`, now also observed for `אספקת דם`), `"multiple plausible answer[s]... Both the Nucleus Accumbens and the Globus Pallidus..."` (MCQ), one `textbook: POTENTIAL_CONFLICT`. **Both targets have a 100% first-attempt-acceptance track record across every one of WP-044/045/046's own prior pilots** - this run's difficulty is ordinary run-to-run generation stochasticity (the same phenomenon WP-045 already extensively documented for `Corticospinal Tract` itself), not a regression this WP introduced.

**Target alignment among accepted questions: 7/7 (100%)** - every single accepted answer this run correctly identified its own target, with zero exceptions. English-first: 7/7 (100%).

## 19. Acceptance

7/12 (58.3%). **Explicitly not attributed to the new WP-047 mechanism** - directly verified via per-attempt inspection (section 18) that it never fired. The shortfall traces entirely to WP-046's own mechanism (firing more this run than its own pilot) and ordinary validator-level stochastic variance for two previously-100%-reliable targets. This is disclosed in full rather than left ambiguous, per this project's own established practice of not letting a lower headline number go unexplained.

## 20. Target Alignment

**7/7 (100%)** among accepted questions - the first pilot in this project's history where every single accepted question is confirmed target-identity-aligned, with a structural guarantee behind it rather than only a favorable sample.

## 21. English-First

**7/7 (100%)** among accepted questions - unaffected by this WP, WP-041's own mechanism untouched.

## 22. Concept Rotation

`אספקת דם`: 2/4 distinct (`Superior cerebellar artery`, `Basillar artery` - the latter repeated rounds 2-4 since rounds 2-3 were never accepted). `גרעיני הבסיס`: 2/4 distinct (`Caudate Nucleus`, `Nucleus Accumbens` - same repetition pattern). `מסילות עצביות`: 3/4 distinct (`Spinothalamic Tract`, `Corticobulbar/Corticonuclear Tract`, `Corticospinal Tract` repeated rounds 3-4). Lower than WP-046's own best-to-date result, directly following from the lower acceptance count (a target that is never accepted is never recognized as covered, so it is reselected - the same, already-established WP-043/044 mechanism, not a new one).

## 23. Globus Pallidus / Caudate Nucleus (Section 25's Explicit Instruction)

Not made the primary implementation target of this WP, per its own explicit instruction. **Newly and directly relevant this pilot**: `Nucleus Accumbens`'s own rejected attempts this run showed the identical generic classification-ambiguity shape (`"Both the Nucleus Accumbens and the Globus Pallidus..."`), further confirming WP-046's own finding that this risk family is not limited to `Globus Pallidus`/`Caudate Nucleus` - it now has a third real instance (`Nucleus Accumbens`). This is recorded as WP-046's own instruction requires ("may record whether target identity interacts with classification ambiguity") without attempting to solve it here.

## 24. Unresolved Issues

1. **The generic classification-ambiguity family (WP-046's "Problem B") remains unresolved and now has a third confirmed instance** (`Nucleus Accumbens`, this WP's own pilot) - still no safe deterministic candidate-level or evidence-level signal identified for it.
2. **`Basillar artery`'s own new rejections this pilot (rounds 2-3) show the same generic-classification-adjacent ambiguity shape** (`"Both the Basilar artery and the Anterior Inferior Cerebellar Artery (AICA) are..."`) applied to `אספקת דם` for the first time in this project's own recorded history - worth the next WP's awareness even though not investigated further here (out of this WP's own scope).
3. **`relationship_type` (WP-030) was found, empirically, not to be a reliable signal for anything relevant to this investigation** (section 4) - a disclosed, if secondary, architectural observation: the coarse keyword classifier rarely matches this corpus's actual anchored evidence for pilot-category targets, and never predicted alignment either way.

## 25. Architectural Conclusion

WP-047 reached Outcome 1 (section 31: "a safe general deterministic target-to-answer contract exists") for the scope actually investigated - named-entity pilot-category targets under the current, post-WP-041 architecture - after an exhaustive search across this project's entire real historical dataset (54 real accepted pilot-category questions spanning WP-036 through WP-046) found **zero legitimate related-entity answer cases**, only confirmed defects wherever `answer != target` occurred. This is a stronger, more general result than WP-046's own review anticipated ("a narrower deterministic contract for specific relationship types" was the review's own expectation) - reached only because the evidence itself supported the stronger conclusion, not assumed in advance.

The new check's own live pilot behavior is the clearest possible confirmation of correct scoping: it never fired once in a fresh 29-attempt run, yet every single accepted answer was already, independently confirmed aligned - the check adds a structural guarantee exactly where the architecture was previously relying on an honored-in-the-breach prompt instruction, without disturbing a single currently-correct generation. The pilot's lower raw acceptance number (7/12) is real and disclosed in full, but directly, verifiably attributable to pre-existing mechanisms (WP-046's own check, ordinary validator stochasticity) - not to this WP's own change.

## 26. Recommendation for WP-048

1. **Investigate the generic classification-ambiguity family directly, now with a third real instance (`Nucleus Accumbens`) and a fourth candidate signal (`Basillar artery`'s new rejections)** - WP-046 correctly declined to force a fix without a safe signal; this WP's own pilot adds real, fresh evidence that may (or may not) change that conclusion. Approach with the same evidence-first discipline as WP-044/045/046, not by assumption.
2. **Consider whether `relationship_type`'s own weak predictive value (section 4/24) warrants revisiting** - not urgent, but a real, disclosed architectural observation from this WP's own investigation that a future WP touching `generation/relationship.py` should be aware of.
3. **Do not expand beyond the three pilot categories** - target alignment is now structurally guaranteed for named-entity targets, but overall acceptance reliability (7/12 this run) has not stabilized, and the classification-ambiguity family remains open.
4. **Preserve everything WP-044/046/047 built** - the new target-answer-identity check is empirically validated against the entire real historical dataset and should not be weakened while pursuing the remaining open problems.

---

## Terminal Summary

```
WP-047 complete.

Objective: determine the target-to-answer contract before implementing enforcement - not assume correct_answer == target

Existing target/relationship architecture: QuestionTarget/QuestionRelationship/ConceptIdentity inventoried; no existing deterministic target-alignment check found beyond WP-044 Part B's narrow is_source_role case; relationship_type found not to reliably predict anything in this dataset

Known target-substitution failure: Corticospinal Tract -> Precentral Gyrus fully reconstructed - factually grounded, passed all five validators, no existing mechanism checked target identity for the general case

Additional cases analyzed: 54 real accepted pilot-category questions across WP-036 through WP-046, 7 confirmed real historical target-substitution instances, 0 legitimate related-entity answer cases found

Valid related-answer cases: none found anywhere in the real dataset - a genuine, disclosed negative finding

Invalid related-answer cases: 7 real historical instances, all independently pre-diagnosed as defects at the time

Target-to-answer contract: TARGET_ALIGNED = named_entity_target AND normalize(target.topic) contained in normalize(correct_answer_text) - Outcome 1, a safe general deterministic contract for named-entity pilot-category targets under the current post-WP-041 architecture

Target alignment definition: one-directional containment (answer must contain target's own name), never bare equality, never the reverse direction

Identity / alias / normalization findings: ConceptIdentity insufficient (never recognizes cross-script forms in this corpus); safe now specifically because WP-041's English-first policy already eliminates the legitimate-cross-script-answer scenario this check would otherwise have unsafely flagged

Deterministic enforcement feasibility: YES, for named-entity pilot-category targets

Implementation: yes - _validate_target_answer_identity(), generation/generator.py, one new function, one call site

Tests: 1396 passed, 0 failed (up from 1386, +10 new)

Regression: 1396/1396 passed, schemas byte-identical, validators/coverage/retry-budget/English-first/WP-044/WP-046 all unchanged

Pilot: one fresh live run, 7/12 accepted - the new check fired zero times (directly verified); the shortfall is fully attributable to WP-046's own check (5 fires) and ordinary validator stochasticity for two previously-reliable targets, not to this WP

Acceptance: 7/12 (58.3%) - not attributable to this WP's own change

Target alignment: 7/7 (100%) among accepted questions - every accepted answer this run correctly identified its target

English-first: 7/7 (100%)

Concept rotation: אספקת דם 2/4, גרעיני הבסיס 2/4, מסילות עצביות 3/4 - lower than WP-046, directly following from lower acceptance, not a new mechanism

Globus Pallidus: not the primary target of this WP; its classification-ambiguity family now has a third real instance (Nucleus Accumbens) and a new fourth candidate (Basillar artery)

Corticospinal Tract: the mandatory regression case (Precentral Gyrus substitution) is now structurally rejected; WP-046's own containment check continues firing independently and correctly for the same target

Architectural conclusion: a safe, general, evidence-validated target-to-answer identity contract was found and implemented for named-entity pilot-category targets; it never fired in the live pilot yet every accepted answer was already aligned, confirming correct scope; the lower raw acceptance number is real but verifiably unattributable to this WP's own change

Recommended WP-048: investigate the generic classification-ambiguity family directly, now with a third real instance (Nucleus Accumbens) and a new candidate (Basillar artery); do not expand beyond the three pilot categories; preserve everything built so far

Completion report:
implementation/WP-047_COMPLETION_REPORT.md

Waiting for architect review.
```
