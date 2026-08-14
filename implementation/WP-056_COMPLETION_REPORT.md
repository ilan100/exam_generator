# WP-056 Completion Report — Globus Pallidus Identity-First Controlled Experiment

## 1. Objective

Determine, via a controlled experiment against the real production pipeline, whether explicitly encouraging **reverse-framed identity generation** ("Which of the following IS Globus Pallidus?") improves Globus Pallidus generation quality/acceptance relative to the current `DEFAULT` behavior - the specific hypothesis WP-055 raised but explicitly left untested. **Experiment only - no production change authorized or made.**

## 2. Hypothesis

```text
H1: Explicit reverse-framed identity guidance will increase the
probability of generating a valid Globus Pallidus identity question
compared with current DEFAULT behavior.

H0: Reverse-framed identity guidance does not produce a meaningful
improvement over DEFAULT under the current architecture.
```

## 3. Control Definition

Unmodified production behavior: `PromptRepository.from_default_location()` (byte-identical to `prompts/generation/question.txt` on disk, verified by direct equality assertion before any API call), the real `QuestionGenerator`, all five real validators (`from_default_configuration()`), the real `config/app.yaml` retry budget (3 attempts), real retrieval, real OpenAI API. Strategy: `DEFAULT` (Globus Pallidus's current, unchanged WP-054 mapping).

## 4. Experimental Definition

A single, isolated, in-memory-only instruction block appended (never on disk) to a copy of the real production `QUESTION_GENERATION` template text, via a freshly-constructed `PromptTemplate`/`PromptRepository` (the same, already-established `PromptRepository.__init__(explicit templates mapping)` injection point WP-053 used unmodified):

```text
--- EXPERIMENTAL INSTRUCTION (WP-056, REVERSE-FRAMED IDENTITY,
PROTOTYPE-ONLY - NOT PART OF THE PERMANENT PROMPT) ---
For this generation attempt, prefer a reverse-framed identity question
that asks which answer choice IS TARGET CONCEPT itself - for example,
"Which of the following IS TARGET CONCEPT?" or an equivalent
identity-establishing phrasing that names TARGET CONCEPT within the
question text and as the correct answer.
Do NOT use a broader category-membership question such as "Which
structure is part of the basal nuclei?" or "Which of the following is
part of X?" - this framing has repeatedly failed grounding for this
exact target, because the same membership property is equally true of
every sibling structure.
This identity framing is a preference, not an unconditional validity
override: it does not relax, replace, or override any other requirement
stated above (grounding, uniqueness, target-answer identity, category,
quality, or any other existing constraint).
--- END EXPERIMENTAL INSTRUCTION ---
```

No other prompt section changed; `required_variables` verified identical to the original template.

## 5. Experimental Isolation (OBSERVED, verified before and after execution)

A self-check function (`_self_check_experimental_isolation()`, run unconditionally before any API call) asserted: the control template carries no `"REVERSE-FRAMED IDENTITY"` text; the experimental template does; the control template is byte-identical to `PromptRepository.from_default_location()`'s own live template; target/category are pinned to exactly `Globus Pallidus`/`גרעיני הבסיס`. All four assertions **PASSED** (script output: `experimental isolation self-check: PASSED`).

`git status`/`git diff` on `src/`, `tests/`, `prompts/` before and after this WP's execution show **no new or modified file under any of those three directories from this WP** - the only diffs present are the already-accepted, unrelated WP-054 changes from a prior session (7 modified + 3 new files, all pre-dating WP-056). This WP added exactly two new files: `implementation/wp056_experiment.py` (prototype, imported by nothing in `src/`) and `evaluation/live_outputs/wp056_experiment_records.json` (results).

## 6. Sample Size

3 independent CONTROL rounds + 3 independent EXPERIMENT rounds (the exact "recommended engineering sample" WP-056 section 18 names), each using the existing, unmodified 3-attempt production budget. No round was rerun; no condition was run until success. All 6 rounds executed in one uninterrupted session (fresh generation for every round, never reusing a previous round's output as input to the next, per section 19).

## 7. Model/Provider

The real, configured OpenAI provider (`build_llm_provider(load_llm_config())`) - the same provider/model configuration the rest of the production system uses; not overridden for this experiment.

## 8. Actual Generated Questions (OBSERVED, full record in `evaluation/live_outputs/wp056_experiment_records.json`)

| Condition | Round | Attempt | Question | Correct answer text |
|---|---:|---:|---|---|
| CONTROL | 1 | 1 | "האם הGlobus Pallidus הוא חלק מהגרעינים הבסיסיים?" | Globus Pallidus |
| CONTROL | 1 | 2 | "איזה מהמבנים הבאים הוא Globus Pallidus?" | "1. Globus Pallidus" |
| CONTROL | 1 | 3 | "איזה מבנה מהגרעינים הבסיסיים הוא Globus Pallidus?" | "1. Globus Pallidus" |
| CONTROL | 2 | 1 | "איזה מבנה נמצא בין ה-putamen לגרעין הסובטלמי?" | Globus Pallidus |
| CONTROL | 3 | 1 | "איזה מהבאים הוא גרעין בגרעיני הבסיס ומעורב במערכת המוטורית?" | Globus Pallidus |
| CONTROL | 3 | 2 | "איזה מבנה מהמבנים הבאים הוא Globus Pallidus?" | Globus Pallidus |
| CONTROL | 3 | 3 | "איזה מהמבנים הבאים הוא חלק מגרעיני הבסיס?" | Globus Pallidus |
| EXPERIMENT | 1 | 1 | "איזה מהגרעינים הבאים הוא Globus Pallidus?" | Globus Pallidus |
| EXPERIMENT | 2 | 1 | *(generation-contract failure - see section 9)* | "Globbus Pallidus" (typo, rejected) |
| EXPERIMENT | 2 | 2 | "איזה מהמבנים הבאים הוא ה-Globus Pallidus?" | Globus Pallidus |
| EXPERIMENT | 3 | 1 | "איזה מהמבנים הבאים הוא ה-Globus Pallidus?" | Globus Pallidus |

## 9. Question-Shape Classification (OBSERVED, deterministic keyword classifier)

A small, explicit, keyword-based classifier (`classify_question_shape()`, `implementation/wp056_experiment.py`) distinguishes `VALID_IDENTITY_SHAPE` (target named *inside* the question text, with a copula/naming cue, no membership marker) from `MEMBERSHIP_CLASSIFICATION` (a membership marker present, target *not* named in the question text itself) from `PROPERTY`/`OTHER`. **Self-checked against all six already-known real examples before the live run** (the three WP-054 fresh failures, correctly classified `MEMBERSHIP_CLASSIFICATION`; three real historical successes, two correctly classified `VALID_IDENTITY_SHAPE`, one `PROPERTY`) - script output: `classifier self-check: PASSED (6/6 known cases)`.

| Condition | Round | Attempt | Shape |
|---|---:|---:|---|
| CONTROL | 1 | 1 | MEMBERSHIP_CLASSIFICATION |
| CONTROL | 1 | 2 | VALID_IDENTITY_SHAPE |
| CONTROL | 1 | 3 | VALID_IDENTITY_SHAPE |
| CONTROL | 2 | 1 | OTHER (property/location) |
| CONTROL | 3 | 1 | OTHER (property/motor-function) |
| CONTROL | 3 | 2 | VALID_IDENTITY_SHAPE |
| CONTROL | 3 | 3 | MEMBERSHIP_CLASSIFICATION |
| EXPERIMENT | 1 | 1 | VALID_IDENTITY_SHAPE |
| EXPERIMENT | 2 | 1 | *(unclassified - generation-contract failure, no candidate produced)* |
| EXPERIMENT | 2 | 2 | VALID_IDENTITY_SHAPE |
| EXPERIMENT | 3 | 1 | VALID_IDENTITY_SHAPE |

**CONTROL produced a mix of shapes (2 membership, 3 identity, 2 property/other) - EXPERIMENT produced identity-shaped questions in every classifiable attempt (3 of 3).**

## 10. Validator Results (OBSERVED, full reasons in the JSON record)

**CONTROL:**
- Round 1 attempt 1 (membership): grounding **FAILED** ("all four answer choices are supported as they are all components of the Basal Ganglia").
- Round 1 attempts 2-3 (identity): grounding **PASSED** both times, but **quality FAILED** both times for an unrelated reason - the LLM's own answer choices redundantly repeated leading enumeration numbering (e.g. `"1. Globus Pallidus"`), duplicating the exam format's own numbering. Not a classification-ambiguity failure.
- Round 2 attempt 1 (property/location - "positioned between the putamen and the subthalamic nucleus"): all five validators **PASSED**. Accepted.
- Round 3 attempt 1 (property/motor-involvement): grounding **FAILED** (non-unique - shared by Putamen/Caudate Nucleus too).
- Round 3 attempt 2 (identity): grounding **PASSED**, but **MCQ FAILED** - a distractor ("Basal Ganglia") judged too broad/plausible.
- Round 3 attempt 3 (membership): grounding **FAILED** (identical non-uniqueness reasoning to round 1 attempt 1).

**EXPERIMENT:**
- Round 1 attempt 1 (identity): all five validators **PASSED**. Accepted on the first attempt.
- Round 2 attempt 1: **generation-contract failure** - the LLM's own correct-answer text was `"Globbus Pallidus"` (a genuine spelling typo, extra "b"), which WP-047's existing, unmodified `_validate_target_answer_identity()` correctly rejected (the normalized target text is not a substring of the misspelled answer) - never reached the five validators at all.
- Round 2 attempt 2 (identity): all five validators **PASSED**. Accepted.
- Round 3 attempt 1 (identity): all five validators **PASSED**. Accepted on the first attempt.

**Grounding never once rejected a `VALID_IDENTITY_SHAPE` attempt in this sample (0/6 across both conditions)** - every grounding rejection in this experiment (3 of 3) was against a `MEMBERSHIP_CLASSIFICATION` or non-unique `OTHER` attempt. This is a clean, direct confirmation of WP-055's own core diagnostic finding: identity-shaped propositions are inherently unique (tautologically - "which one IS X" has exactly one true answer by construction), while membership/group propositions are not.

## 11. Aggregate Metrics

| Metric | CONTROL | EXPERIMENT |
|---|---:|---:|
| Rounds | 3 | 3 |
| Total attempts | 7 | 4 |
| Identity-shaped attempts | 3 | 3 (+1 unclassified contract failure) |
| Valid identity questions (primary success metric, section 21) | **0** | **3** |
| Membership-shaped attempts | 2 | 0 |
| Grounding failures | 3 | 0 |
| Target-identity (WP-047) failures | 0 | 1 (spelling typo, not a framing/shape issue) |
| Other validation failures (quality/MCQ, on structurally identity-shaped attempts) | 3 | 0 |
| Accepted questions (any shape) | 1 / 3 rounds | 3 / 3 rounds |
| First-attempt accepted | 1 / 3 rounds | 2 / 3 rounds |
| Eventually accepted (within 3) | 1 / 3 rounds | 3 / 3 rounds |

## 12. Comparison

**EXPERIMENT strongly outperformed CONTROL on every metric that matters to the hypothesis**: 3/3 rounds accepted vs. 1/3; 3/4 attempts reaching the full primary-success bar (identity-shaped + grounded + unique + all validators pass + target-answer-identity satisfied) vs. 0/7; zero grounding failures vs. 3/7; zero membership-shaped attempts vs. 2/7. The one experimental failure (a spelling typo) is categorically different from the membership-classification failure family WP-055 diagnosed - it is a token-level generation-fidelity issue, not a strategic/framing choice, and the existing WP-047 check correctly caught it exactly as designed.

A secondary, honestly-disclosed nuance: CONTROL's low acceptance is **not entirely** attributable to the membership-classification family - 3 of CONTROL's 7 attempts were already identity-shaped by chance (without any experimental instruction) yet were still rejected, by *quality* (redundant answer-numbering artifact) and *MCQ* (an overly-plausible distractor) respectively, both unrelated to grounding/uniqueness. This means the experimental instruction's practical benefit in this sample comes from two combined effects: (a) shifting question-shape distribution toward identity more consistently (3/3 rounds vs. 3/7 attempts spread unevenly across CONTROL rounds), and (b) EXPERIMENT's identity-shaped attempts also happened to avoid the quality/MCQ artifacts CONTROL's own identity attempts hit - the latter is not something this small sample can attribute to the experimental instruction itself (which says nothing about answer-numbering format) versus ordinary stochastic variance.

## 13. Observed Findings

- **OBSERVED**: 3/3 EXPERIMENT rounds produced a `VALID_IDENTITY_SHAPE` question; 0/3 CONTROL rounds achieved a fully-accepted identity-shaped question (2 identity-shaped CONTROL attempts were rejected by quality/MCQ, not grounding).
- **OBSERVED**: 0/6 identity-shaped attempts (across both conditions) failed grounding; 3/3 grounding failures were against non-identity (membership or non-unique property) attempts.
- **OBSERVED**: the experimental instruction introduced exactly one new failure type not seen in CONTROL - a spelling-typo-driven target-answer-identity rejection - which resolved itself on the very next attempt within the same round's existing retry budget.
- **OBSERVED**: EXPERIMENT achieved first-attempt acceptance in 2/3 rounds (67%) vs. CONTROL's 1/3 (33%), and eventual acceptance (within budget) in 3/3 (100%) vs. CONTROL's 1/3 (33%).

## 14. Inference

- **INFERENCE**: the experimental instruction reliably shifts generation's question-shape choice toward reverse-framed identity for this specific target, and identity-shaped propositions are structurally safer against the grounding-uniqueness failure this project has repeatedly observed for Globus Pallidus.
- **NOT PROVEN**: that the experimental instruction improves reliability against *every* failure mode observed for this target - the quality/MCQ artifacts CONTROL's own identity attempts hit were not tested against the experimental condition at meaningful volume (EXPERIMENT never produced a non-identity attempt to compare against), so whether the experimental instruction itself would have avoided those specific artifacts, versus simply not having encountered them yet, cannot be concluded from n=3.
- **NOT PROVEN**: mathematical/statistical significance - this is a small, engineering-scale sample (3 rounds per condition, exactly as WP-056 itself recommends), not a large controlled trial.

## 15. Confidence

**MEDIUM-HIGH** for the narrow claim ("reverse-framed identity generation measurably outperformed DEFAULT for Globus Pallidus in this fresh, controlled, real-API sample") - the result is clean (0/7 vs 3/4 on the primary metric), internally consistent (grounding never rejected an identity-shaped attempt in either condition), and directly corroborates WP-055's own independent historical finding (3 of 5 prior live-pilot successes were reverse-framed identity) and WP-052's broader retrospective pattern for this target family. **MEDIUM**, not higher, because n=3 per condition is still a small engineering sample, one condition (EXPERIMENT) never got the chance to demonstrate resistance to the quality/MCQ artifacts CONTROL happened to hit, and this WP does not claim to have proven the mechanism will generalize beyond this exact target/category pair.

## 16. Production Changes

**NONE.** `git status`/`git diff` confirm no file under `src/exam_generator/`, `tests/`, or `prompts/` was modified by this WP. The two new files (`implementation/wp056_experiment.py`, `evaluation/live_outputs/wp056_experiment_records.json`) are prototype/evaluation artifacts only, imported by nothing in `src/`. The WP-054 strategy mapping (`generation/strategy.py`'s `_IDENTITY_FIRST_TARGETS_BY_CATEGORY`) was **not** touched - `Globus Pallidus` remains `DEFAULT`.

## 17. Regression Result

```text
REGRESSION: NOT APPLICABLE
```
(Production code unchanged; `pytest -q` re-run anyway for due diligence: `1426 passed, 0 failed` - identical to the state at the end of WP-055.)

## 18. Architectural Conclusion

**SUPPORTED.**

Per WP-056 section 45's own definition ("for a small engineering sample, SUPPORTED should mean the experiment provides sufficient practical evidence to justify an architectural review for permanent implementation - it does not mean mathematical proof"): this experiment's result (0/7 vs. 3/4 primary-success attempts; 0/3 vs. 3/3 rounds; zero grounding failures on any identity-shaped attempt in either condition; the result directly corroborating two independent prior WPs' own findings) clears that bar. It does **not** clear a "PROVEN" bar, and this report does not claim one.

## 19. Recommendation

Recommend an architect review of whether `גרעיני הבסיס` + `Globus Pallidus` should be added to the permanent `IDENTITY_FIRST` mapping (Outcome A, WP-056 section 29) - mirroring the exact WP-053 → WP-054 precedent (experimental support → architect review → narrow permanent implementation, if approved). **This WP does not make that change itself** - per its own explicit constraint (section 31: "Even if the experimental condition succeeds: DO NOT change Globus Pallidus → IDENTITY_FIRST during WP-056"). If approved, the permanent instruction should specifically preserve the *reverse-framed* semantic tested here ("which of the following IS X"), not a generic identity-first instruction, since that is the specific pattern this experiment - and WP-055's historical data - actually support. The one new failure mode observed (a spelling typo) should be noted as an accepted, existing-mechanism-handled cost (WP-047's check + the existing retry budget already absorbed it in this sample) rather than a reason for concern.

## 20. WP-054 Mapping Status

**UNCHANGED.** `גרעיני הבסיס` + `Caudate Nucleus` → `IDENTITY_FIRST`; `גרעיני הבסیס` + `Nucleus Accumbens` → `IDENTITY_FIRST`; `גרעיני הבסיס` + `Globus Pallidus` → `DEFAULT` (unchanged by this WP). No other target/category combination was touched.

---

# Required Experimental Results Table

| Condition | Round | Attempt | Question | Correct answer | Shape | Grounding | Target identity | Overall |
|---|---:|---:|---|---|---|---|---|---|
| CONTROL | 1 | 1 | "האם הGlobus Pallidus הוא חלק מהגרעינים הבסיסיים?" | Globus Pallidus | MEMBERSHIP_CLASSIFICATION | FAIL | PASS | REJECTED |
| CONTROL | 1 | 2 | "איזה מהמבנים הבאים הוא Globus Pallidus?" | "1. Globus Pallidus" | VALID_IDENTITY_SHAPE | PASS | PASS | REJECTED (quality) |
| CONTROL | 1 | 3 | "איזה מבנה מהגרעינים הבסיסיים הוא Globus Pallidus?" | "1. Globus Pallidus" | VALID_IDENTITY_SHAPE | PASS | PASS | REJECTED (quality) |
| CONTROL | 2 | 1 | "איזה מבנה נמצא בין ה-putamen לגרעין הסובטלמי?" | Globus Pallidus | OTHER (property) | PASS | PASS | **ACCEPTED** |
| CONTROL | 3 | 1 | "איזה מהבאים הוא גרעין בגרעיני הבסיס ומעורב במערכת המוטורית?" | Globus Pallidus | OTHER (property, non-unique) | FAIL | PASS | REJECTED |
| CONTROL | 3 | 2 | "איזה מבנה מהמבנים הבאים הוא Globus Pallidus?" | Globus Pallidus | VALID_IDENTITY_SHAPE | PASS | PASS | REJECTED (mcq) |
| CONTROL | 3 | 3 | "איזה מהמבנים הבאים הוא חלק מגרעיני הבסיס?" | Globus Pallidus | MEMBERSHIP_CLASSIFICATION | FAIL | PASS | REJECTED |
| EXPERIMENT | 1 | 1 | "איזה מהגרעינים הבאים הוא Globus Pallidus?" | Globus Pallidus | VALID_IDENTITY_SHAPE | PASS | PASS | **ACCEPTED** |
| EXPERIMENT | 2 | 1 | *(no candidate - typo)* | "Globbus Pallidus" | n/a | n/a | FAIL | REJECTED (contract) |
| EXPERIMENT | 2 | 2 | "איזה מהמבנים הבאים הוא ה-Globus Pallidus?" | Globus Pallidus | VALID_IDENTITY_SHAPE | PASS | PASS | **ACCEPTED** |
| EXPERIMENT | 3 | 1 | "איזה מהמבנים הבאים הוא ה-Globus Pallidus?" | Globus Pallidus | VALID_IDENTITY_SHAPE | PASS | PASS | **ACCEPTED** |

# Required Decision Table

| Question | Result |
|---|---|
| Did the experimental instruction change question shape? | Yes - 3/3 classifiable EXPERIMENT attempts were identity-shaped vs. 3/7 CONTROL attempts |
| Did it increase reverse-framed identity questions? | Yes |
| Did valid identity acceptance improve? | Yes - 0/7 CONTROL attempts vs. 3/4 EXPERIMENT attempts reached full primary-success |
| Did grounding failures decrease? | Yes - 3/7 CONTROL vs. 0/4 EXPERIMENT |
| Did target-answer identity failures occur? | Yes, once in EXPERIMENT (a spelling typo, not a framing/shape issue) |
| Did any other validator regress? | No - EXPERIMENT introduced no new quality/MCQ/category/textbook failure |
| Is the result stronger than the historical evidence alone? | It corroborates and strengthens it - a fresh, controlled sample now agrees with the retrospective WP-055 pattern |
| Is the result sufficient for production implementation? | NO — architect decision required |
| Was WP-054 modified? | NO |
| Recommended next step | Architect review of adding `Globus Pallidus` → `IDENTITY_FIRST` (reverse-framed semantic specifically), mirroring the WP-053→WP-054 precedent |

---

# Terminal Summary

```text
WP-056 complete.

Objective:
Determine whether reverse-framed identity generation improves
Globus Pallidus generation relative to DEFAULT.

Target:
Globus Pallidus

Category:
גרעיני הבסיס

Control:
DEFAULT

Experiment:
REVERSE_FRAMED_IDENTITY

Sample:
3 CONTROL rounds (7 attempts) + 3 EXPERIMENT rounds (4 attempts)

Identity-shaped results:
CONTROL 3/7 attempts, EXPERIMENT 3/3 classifiable attempts (3/4 total)

Valid identity results (primary success metric):
CONTROL 0/7, EXPERIMENT 3/4

Membership-shaped results:
CONTROL 2/7, EXPERIMENT 0/4

Grounding results:
CONTROL 3/7 failed, EXPERIMENT 0/4 failed
(zero grounding failures on any identity-shaped attempt in either condition)

Target-answer identity results:
CONTROL 0 failures, EXPERIMENT 1 failure (spelling typo, resolved on retry)

Overall acceptance:
CONTROL 1/3 rounds, EXPERIMENT 3/3 rounds

Comparison:
EXPERIMENT strongly outperformed CONTROL on every hypothesis-relevant
metric; the one experimental failure was a token-level spelling issue,
categorically different from the membership-classification family this
experiment targeted.

Conclusion:
SUPPORTED

Production changes:
NONE

WP-054 mapping:
UNCHANGED

Regression:
NOT APPLICABLE (production code unchanged; pytest re-run anyway: 1426
passed, 0 failed)

Recommended next step:
Architect review of adding Globus Pallidus -> IDENTITY_FIRST (the
specific reverse-framed semantic tested here), mirroring the
WP-053 -> WP-054 precedent. No implementation in this WP.

Completion report:
implementation/WP-056_COMPLETION_REPORT.md

Waiting for architect review.
```
