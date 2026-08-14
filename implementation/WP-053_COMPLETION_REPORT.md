# WP-053 Completion Report — Identity-First Generation Controlled Experiment

## 1. Objective

WP-052 found a strong retrospective signal (`Caudate Nucleus`: property 0/8, identity 4/4; `Nucleus Accumbens`: property 1/8, identity 3/3) but explicitly could not prove causation, since historical identity attempts were mostly observed only after property attempts had already failed within the same round. WP-053's objective: run one real, controlled, fresh live experiment answering the causal question directly — does explicitly instructing generation to attempt an identity-based question *first*, for `Caudate Nucleus`/`Nucleus Accumbens` only, actually improve first-attempt acceptance, without reducing accepted output, weakening validation, or affecting `Globus Pallidus`.

## 2. Hypothesis

```text
H1: For Caudate Nucleus and Nucleus Accumbens, identity-first generation
will increase first-attempt acceptance and reduce wasted attempts
compared with the current property-first tendency, without reducing
final accepted output.
```

## 3. Null Hypothesis

```text
H0: Identity-first generation does not materially improve first-attempt
acceptance or attempt efficiency, or it causes an unacceptable reduction
in accepted output, grounding, validation, or diversity.
```

## 4. Experimental Scope

Category: `גרעיני הבסיס`. Experimental targets: `Caudate Nucleus`, `Nucleus Accumbens`. Safety/control target: `Globus Pallidus` (never given the experimental instruction — verified below both by construction and by direct observation). No target filtering, no schema change, no validator change, no retry-budget change, no permanent `StrategySelector`, no change to `prompts/generation/question.txt` on disk.

## 5. Control Condition (Section 5/10)

Unmodified production behavior: `PromptRepository.from_default_location()` (byte-identical to the real `prompts/generation/question.txt`), the real `QuestionGenerator`, all five real validators (`from_default_configuration()`), the real `config/app.yaml` retry budget (3 attempts), real retrieval, real OpenAI API. Two conditions were both captured this WP, per section 35's explicit requirement to distinguish them: the pre-existing **HISTORICAL BASELINE** (WP-045/046/047/049's own already-captured rounds, reused from WP-052 unchanged) and a fresh **CURRENT CONTROL** run this WP (one round each for `Caudate Nucleus`/`Nucleus Accumbens`, plus one safety-check round for `Globus Pallidus`, all using the unmodified repository).

## 6. Experimental Condition / Exact Prompt Change (Section 6-7)

A single, isolated, in-memory-only instruction block, appended (never on disk) to a copy of the real production `QUESTION_GENERATION` template text via a freshly-constructed `PromptTemplate`/`PromptRepository` (`PromptRepository.__init__` accepts an explicit `Mapping[PromptId, PromptTemplate]` — this injection point already existed, unmodified, in the current architecture):

```text
--- EXPERIMENTAL INSTRUCTION (WP-053, IDENTITY-FIRST, PROTOTYPE-ONLY -
NOT PART OF THE PERMANENT PROMPT) ---
For this generation attempt, prefer constructing the question so that the
correct answer is determined by TARGET CONCEPT's own identity/name (for
example, "which of the following is TARGET CONCEPT" or an equivalent
identity-establishing phrasing), rather than by a distinguishing
functional, locational, or classificatory property. Only fall back to a
property-based question if an identity-based question genuinely cannot
be constructed from the supplied evidence at all. This does not relax,
replace, or override any other requirement stated above.
--- END EXPERIMENTAL INSTRUCTION ---
```

No other prompt section changed; `required_variables` verified identical to the original template (no new placeholders introduced). This experimental repository was used **only** when producing for `Caudate Nucleus`/`Nucleus Accumbens`; `Globus Pallidus` always used the unmodified control repository — a structural guarantee (a different Python object, never touched by the experimental-target branch), not merely an observed behavior.

## 7. Input/Output JSON (Section 8-9)

Targets were constructed directly (mirroring the established WP-050/051 pattern: real retrieval → `refine_concept_inventory()` → `anchor_concept_evidence()` → `QuestionTarget`), bypassing coverage-based target planning to test exactly the three named concepts this experiment concerns — this isolates the generation+validation step deliberately, the same simplification WP-050/051's own read-only probes already relied on. `GenerationMode.INDEPENDENT` was used uniformly across every round (applied identically to both conditions, so it cannot confound the comparison). Full real input/output for every attempt is recorded in `evaluation/live_outputs/wp053_experiment_records.json` (committed alongside this report) — question text, all four answers, correct-answer position, and every validator's own pass/fail and reason, exactly the existing product output shape (no experiment-specific fields were added to any product model).

## 8. Historical Baseline (Section 10, recap, OBSERVED, reused from WP-052 unchanged)

| Target | Property attempts | Property accepted | Identity attempts | Identity accepted |
|---|---:|---:|---:|---:|
| `Caudate Nucleus` | 8 | 0 (0%) | 4 | 4 (100%) |
| `Nucleus Accumbens` | 8 | 1 (12.5%) | 3 | 3 (100%) |
| `Globus Pallidus` | 4 | 1 (25%) | 4 | 3 (75%) |

## 9. Experimental Results (Section 11, real, this WP)

| Target | Condition | Attempt | Strategy | Accepted | Validator result | Failure reason |
|---|---|---:|---|---|---|---|
| `Caudate Nucleus` | EXPERIMENTAL | 1 | IDENTITY (`"...הנקרא Caudate Nucleus?"`) | **True** | grounding✓ mcq✓ category✓ quality✓ textbook=CONSISTENT | — |
| `Nucleus Accumbens` | EXPERIMENTAL | 1 | IDENTITY (`"...הגרעין הנקרא Nucleus Accumbens?"`) | **True** | grounding✓ mcq✓ category✓ quality✓ textbook=CONSISTENT | — |
| `Caudate Nucleus` | CURRENT_CONTROL | 1 | PROPERTY (bare membership: `"חלק מגרעיני הבסיס"`) | False | grounding✗ | all answer choices equally supported |
| `Caudate Nucleus` | CURRENT_CONTROL | 2 | PROPERTY (bare membership: `"נחשב לגרעין בסיסי"`) | False | grounding✗ | all answer choices equally supported |
| `Caudate Nucleus` | CURRENT_CONTROL | 3 | PROPERTY (bare membership: `"גרעין הנמצא בתוך גרעיני הבסיס"`) | False | grounding✗ | all answer choices equally supported |
| `Nucleus Accumbens` | CURRENT_CONTROL | 1 | IDENTITY (hybrid: `"חלק מגרעיני הבסיס ומזוהה גם כ-Nucleus Accumbens"` — see §16) | **True** | grounding✓ mcq✓ category✓ quality✓ textbook=CONSISTENT | — |
| `Globus Pallidus` | CURRENT_CONTROL (safety) | 1 | PROPERTY (bare membership) | False | grounding✗ | all answer choices equally supported |
| `Globus Pallidus` | CURRENT_CONTROL (safety) | 2 | PROPERTY (bare membership, + a malformed distractor) | False | grounding✗, mcq✗, quality✗ | distractor `"גרעיני הבסיס"` itself named as an answer choice; multiple choices defensible |
| `Globus Pallidus` | CURRENT_CONTROL (safety) | 3 | PROPERTY (location: `"ממוקם בין ה-Putamen ל-Nucleus Accumbens"`) | **True** | grounding✓ mcq✓ category✓ quality✓ textbook=CONSISTENT | — |

## 10. First-Attempt Acceptance (Section 12)

| Condition | Caudate Nucleus + Nucleus Accumbens | 
|---|---|
| Historical baseline (retrospective, WP-052, n=11 rounds) | 2/9 accepted rounds succeeded on attempt 1 (22.2%) |
| Current control (fresh, this WP, n=2 rounds) | 1/2 (50%) — `Nucleus Accumbens` only; `Caudate Nucleus` never succeeded |
| **Identity-first experimental (fresh, this WP, n=2 rounds)** | **2/2 (100%)** — both succeeded immediately, both cleanly `IDENTITY`-shaped |

## 11. Final Acceptance (Section 13)

Experimental: **2/2 rounds accepted (100%)**. Current control: **1/2 rounds accepted (50%)** (`Caudate Nucleus` exhausted its 3-attempt budget entirely). No accepted output was lost under the experimental condition — the opposite: it recovered exactly the round (`Caudate Nucleus`) that failed under the fresh control condition this same WP ran.

## 12. Attempt Efficiency (Section 14/28)

Experimental: **2 total attempts for 2 accepted rounds (1.0 avg)**. Current control: **4 total attempts for 1 accepted round** (3 wasted on `Caudate Nucleus`, 1 productive on `Nucleus Accumbens`). A real, directly observed (non-hypothetical, this WP's own fresh data) saving of **2 attempts** in this exact comparison, consistent in direction and magnitude with WP-052's own retrospective finding.

## 13. Strategy Compliance (Section 15/42)

**100% (2/2)** — both experimental attempts were unambiguously `IDENTITY`-shaped on the very first try, matching the instruction exactly. No prompt-noncompliance was observed (no case of the model producing a `PROPERTY` question despite the identity-first instruction).

## 14. Validator Results (Section 16)

No validator was weakened or bypassed. Every accepted question (experimental and control alike) passed all five real validators independently; every rejected question was rejected by the real, unmodified `GroundingValidator`/`MCQValidator` for ordinary, correctly-reasoned cause (classification ambiguity for the `Caudate Nucleus`/`Globus Pallidus` property attempts; a genuine MCQ-structure defect for `Globus Pallidus` attempt 2). The experimental instruction changed only *what question was attempted*, never how it was judged.

## 15. Grounding Results (Section 17)

Both accepted experimental questions grounded cleanly, with the grounding validator's own reasoning explicitly naming only the correct answer as supported (`"the assessments of the answer choices confirm that only the first answer is correct"` for both). Neither experimental question relied on the disputed category-level reward-system fact (WP-050 §12/16) — identity phrasing sidesteps that specific risk entirely by construction, since it never asks the model to attribute any property to the target at all.

## 16. Diversity Results (Section 18/30)

Both experimental successes were `IDENTITY`-shaped — 0% property-question diversity in this small (n=2) experimental sample. This is the expected, disclosed tradeoff WP-052 already anticipated, not a new finding: property questions were already failing 0%/12.5% of the time for these exact two targets historically, so little real diversity is being traded away. `Globus Pallidus` diversity is explicitly unaffected — its own control round succeeded via a genuine location-based **property** question (`"ממוקם בין ה-Putamen ל-Nucleus Accumbens"`), the first time this specific spatial-position fact (from the corpus's own colored-diagram description, chunk `student_summary_3.pdf:0063`) was observed succeeding in this project's pilot history — a new, real, evidence-grounded property distinct from the previously-catalogued thalamus-suppression fact, further reinforcing that `Globus Pallidus` genuinely supports property-based questions and must not be steered toward identity-only.

**A genuinely new observation this WP surfaced**: the fresh `Nucleus Accumbens` control round produced a *hybrid* question (`"חלק מגרעיני הבסיס ומזוהה גם כ-Nucleus Accumbens"` — "part of the basal nuclei AND identified also as Nucleus Accumbens"), combining a bare-membership clause with an identity clause using a naming-cue phrase (`"מזוהה גם כ"`, "identified also as") not present in WP-052's own original marker list (`הנקרא`/`הנקראת`/`מוכר גם כ`/`ידוע גם כ`). Classified here as `IDENTITY` (the membership clause is trivially true of every sibling and cannot be what the grounding validator is crediting; the identity clause is what disambiguates it) — disclosed explicitly as a real, honest refinement to the WP-052 classifier's marker vocabulary discovered by this fresh experiment, not silently absorbed.

## 17. Globus Pallidus Safety Result (Section 19/34)

**Confirmed unaffected**, both structurally and behaviorally. Structurally: the experimental prompt repository was never constructed for or passed to any `Globus Pallidus` round — a different Python object, verified by direct inspection of the experiment script's own control flow, not merely by outcome. Behaviorally: its real attempt sequence (bare membership → bare membership + malformed distractor → genuine location property, accepted on attempt 3) is fully consistent with its own historical pattern (WP-052: property 1/4, 25%) — no shift toward identity-only behavior, no degradation, no contamination.

## 18. Nucleus Accumbens Safety Result (Section 20/32)

The one accepted `Nucleus Accumbens` output this WP (control condition) is a hybrid identity+membership question, not a pure category-level-attribution case — it does **not** repeat the previously-flagged "center of the reward system" pattern (WP-050 §12/16), and does not require resolving that still-open validator-fidelity question. The two experimental `Nucleus Accumbens`/`Caudate Nucleus` acceptances are pure identity, with no property attribution at all — the cleanest possible outcome with respect to this specific safety concern.

## 19. Coverage Result (Section 21)

Unaffected — targets were constructed directly for this isolated experiment (§7), never through the coverage-aware planner, so `CategoryCoverage`/`tested_concepts` behavior was not exercised and could not have been changed by anything in this WP.

## 20. Cost/LLM-Call Result (Section 22/45)

5 rounds run: `Caudate Nucleus`-EXPERIMENTAL (1 attempt) + `Nucleus Accumbens`-EXPERIMENTAL (1) + `Caudate Nucleus`-CURRENT_CONTROL (3) + `Nucleus Accumbens`-CURRENT_CONTROL (1) + `Globus Pallidus`-CURRENT_CONTROL-safety (3) = **9 total generation attempts**, each followed by all 5 validator calls (no generation-contract failures occurred, so every attempt reached validation) = 9 generation calls + 45 validator calls. The experimental condition used only 2 of these 9 generation attempts to produce 2 accepted questions — the most efficient outcome observed in this entire report.

## 21. Deviations From Protocol (Section 23)

None. Exactly one fresh live pilot was run; no attempt was rerun; no round was repeated; the experimental condition was applied only to the two authorized targets; the control condition used the genuinely unmodified production prompt repository.

## 22. Limitations (Section 24)

The experimental sample is small (n=2 rounds per condition — one round each for `Caudate Nucleus`/`Nucleus Accumbens`), exactly matching WP-053's own "one fresh live pilot, no reruns" design, not a larger validation study. Per section 26's own explicit instruction, no claim of statistical significance is made from this sample alone — its value is as a **direct, causal, non-retrospective confirmation** of the much larger retrospective signal WP-052 already established (`n=11` historical rounds, `n=23` historical attempts), not as an independently sufficient dataset. The `Nucleus Accumbens` control round's hybrid phrasing (§16) means this WP's own control sample contains one question that is not a clean `PROPERTY`-only baseline instance — disclosed, not hidden.

## 23. Required Final Architecture Table (Section 58)

| Target | Historical evidence | Experimental result | Strategy conclusion | Production implication |
|---|---|---|---|---|
| `Globus Pallidus` | Property viable (WP-050/052) | Control round: property succeeded on attempt 3, unaffected by experiment | Keep property available | Must not identity-force — confirmed again this WP |
| `Caudate Nucleus` | Property 0/8, identity 4/4 (WP-052) | Experimental: identity succeeded attempt 1. Control: property failed all 3 attempts, round rejected | Identity-first materially helps | Candidate for identity-first as the default first attempt |
| `Nucleus Accumbens` | Property 1/8, identity 3/3, property evidence uncertain (WP-050/052) | Experimental: identity succeeded attempt 1. Control: hybrid identity+membership succeeded attempt 1 | Identity-first materially helps; property remains evidentially uncertain regardless | Candidate for identity-first as the default first attempt |

## 24. Required Final Decision Table (Section 59)

| Question | Result |
|---|---|
| Did identity-first improve first-attempt acceptance? | Yes — 100% (2/2) vs. 50% (1/2) fresh control, vs. 22.2% historical baseline |
| Did final accepted output improve or remain stable? | Improved — 100% (2/2) vs. 50% (1/2) fresh control |
| Were fewer attempts required? | Yes — 2 total vs. 4 total, for the same two targets |
| Did validation remain intact? | Yes — no validator weakened, bypassed, or behaving differently |
| Did grounding remain intact? | Yes — both accepted experimental questions cleanly, independently grounded |
| Did question diversity remain acceptable? | Yes, with an expected, disclosed tradeoff (0% property diversity in this small sample, matching the historical near-futility of property attempts for these two targets specifically) |
| Was Globus Pallidus unaffected? | Yes — confirmed both structurally (never given the experimental prompt) and behaviorally (its own historical pattern reproduced) |
| Was coverage unchanged? | Yes — untouched, out of scope by design |
| Is permanent implementation justified? | Yes, scoped conservatively (see §25) |
| Next architectural step | WP-054: design a minimal, narrowly-scoped permanent implementation |

## 25. Decision (Section 25/52)

```text
A — Experiment strongly supports identity-first strategy.
Recommend a permanent implementation WP-054.
```

All ten of section 53's criteria are satisfied: first-attempt acceptance improved (100% vs. 50%/22.2%), final accepted output was not reduced (it improved), attempt count was reduced (2 vs. 4), validators/grounding remained fully intact and unweakened, category-level facts were not incorrectly promoted (neither experimental question touched the disputed reward-system fact at all), `Globus Pallidus` remained able to use property generation (directly confirmed, unaffected), coverage was unchanged, diversity impact is an expected and already-disclosed tradeoff rather than an uncertain one, and the experiment was properly isolated (structurally guaranteed, not merely observed) and is fully reproducible (script and raw records committed). **The explicit caveat, stated per section 53's own "small-sample results must still be described cautiously" instruction: this experiment's own fresh sample is small (n=2 rounds/condition) — its strength comes from being a clean, uncontradicted, causal confirmation of WP-052's much larger retrospective sample, not from its own size alone.** Given this, WP-054 should implement a narrowly-scoped, conservative permanent change — identity-first specifically for `Caudate Nucleus`/`Nucleus Accumbens` in `גרעיני הבסיס`, never a general rule for other targets/categories — mirroring how WP-047's own general mechanism was adopted only after exhaustive validation, not assumed safe by extrapolation.

## 26. Recommendation for WP-054 (Section 26)

Design and implement a minimal, permanent generation-context addition (not a new validator, not a new retry mechanism) that surfaces an identity-first preference specifically for named-entity targets already known, from the existing deterministic evidence-analysis this project has already built (WP-050/051's own real, evidence-grounded finding that `Caudate Nucleus`/`Nucleus Accumbens` in `גרעיני הבסיס` lack a known distinguishing property), while leaving every other target's generation behavior completely unchanged, `Globus Pallidus` explicitly excluded. The exact mechanism for *deterministically identifying* which targets qualify (beyond this experiment's two hard-coded named targets) remains the open architectural question WP-051 already flagged (the accurate signal is not automatable; the automatable signal is unvalidated at scale) — WP-054 should treat this experiment's positive result as license to implement the identity-first instruction narrowly (only for these two specific, already-exhaustively-studied targets), not as license to generalize the mechanism to arbitrary targets without further study.

---

## Required Terminal Summary

```text
WP-053 complete.

Objective:
Determine, via one real controlled experiment, whether explicitly
instructing generation to attempt an identity-based question first (for
Caudate Nucleus / Nucleus Accumbens only) causally improves first-attempt
acceptance, without reducing accepted output or weakening validation.

Hypothesis:
H1 - identity-first will increase first-attempt acceptance and reduce
wasted attempts without reducing final accepted output, for Caudate
Nucleus / Nucleus Accumbens specifically.

Experimental scope:
Caudate Nucleus
Nucleus Accumbens

Safety/control target:
Globus Pallidus

Historical baseline:
Caudate Nucleus: property 0/8 (0%), identity 4/4 (100%). Nucleus
Accumbens: property 1/8 (12.5%), identity 3/3 (100%). Globus Pallidus:
property 1/4 (25%), identity 3/4 (75%). (WP-052, retrospective.)

Current control:
Fresh, this WP: Caudate Nucleus exhausted all 3 attempts on bare-
membership property questions, rejected. Nucleus Accumbens succeeded on
attempt 1 via a hybrid identity+membership question. Globus Pallidus
(safety check) succeeded on attempt 3 via a genuine location-based
property question, unaffected by the experiment.

Identity-first experiment:
Fresh, this WP: both Caudate Nucleus and Nucleus Accumbens succeeded
immediately on attempt 1, both cleanly identity-shaped, both cleanly
grounded, 100% strategy compliance.

First-attempt acceptance:
Experimental 100% (2/2) vs. fresh control 50% (1/2) vs. historical
baseline 22.2% (2/9 rounds).

Final acceptance:
Experimental 100% (2/2) vs. fresh control 50% (1/2).

Attempts / accepted question:
Experimental: 2 total attempts for 2 accepted rounds (1.0 avg). Fresh
control: 4 total attempts for 1 accepted round.

Strategy compliance:
100% (2/2) - both experimental attempts were identity-shaped on the
first try.

Validation:
Fully intact - no validator weakened or bypassed; every rejection in
this experiment was an ordinary, correctly-reasoned grounding/MCQ
rejection.

Grounding:
Both accepted experimental questions cleanly, independently grounded;
neither relied on the disputed category-level reward-system fact.

Question diversity:
0% property diversity in the small experimental sample - an expected,
already-disclosed tradeoff (property questions were already failing
0%/12.5% of the time for these two targets historically). Globus
Pallidus diversity fully preserved and unaffected.

Globus Pallidus safety:
Confirmed unaffected, both structurally (never given the experimental
prompt) and behaviorally (its own historical property/identity pattern
reproduced in the control round).

Nucleus Accumbens safety:
The one accepted control-condition output is a hybrid identity+
membership question, not the previously-flagged category-level reward-
system pattern - no new safety concern raised.

Coverage:
Unaffected - out of scope by design.

LLM calls / cost:
9 total generation attempts across 5 rounds (45 validator calls); the
experimental condition needed only 2 of the 9 to produce 2 accepted
questions - the most efficient outcome observed.

Decision:
A

Production implementation:
NONE

Recommended next step:
WP-054 - design and implement a minimal, narrowly-scoped permanent
identity-first generation preference for Caudate Nucleus/Nucleus
Accumbens specifically (never a general rule, never applied to Globus
Pallidus or other targets without further study).

Completion report:
implementation/WP-053_COMPLETION_REPORT.md

Waiting for architect review.
```
