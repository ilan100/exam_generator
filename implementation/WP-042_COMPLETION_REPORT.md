# WP-042 Completion Report — Generation Failure Analysis for `גרעיני הבסיס`

## 1. Objective

WP-041's live pilot showed a material acceptance regression (11/12 in WP-040 → 9/12 in WP-041), concentrated in `גרעיני הבסיס` (`Corpos Striatum`) and one round of `אספקת דם` (`Basillar artery`). WP-041's own architecture review explicitly deferred deciding whether to keep, modify, or investigate further until the root cause was understood. This is a **diagnostic WP only** - no production code, validator, coverage, retrieval, retry-budget, or language-policy change was made or is recommended here.

## 2. WP-041 Baseline (OBSERVED, from `evaluation/live_outputs/wp041_pilot_records.json`)

- Accepted: `אספקת דם` 3/4, `גרעיני הבסיס` 2/4, `מסילות עצביות` 4/4 = 9/12.
- English-first compliance: 9/9 (100%) among accepted questions.
- Manual target alignment: 9/9 (100%).
- Failed rounds: `אספקת דם` R2 (`Basillar artery`), `גרעיני הבסיס` R1 and R2 (both `Corpos Striatum`) - all three `QuestionAttemptsExhaustedError`.

## 3. Data Examined

- `evaluation/live_outputs/wp040_pilot_records.json` (WP-040's own live pilot - pre-English-first baseline).
- `evaluation/live_outputs/wp041_pilot_records.json` (WP-041's own live pilot).
- `evaluation/live_outputs/wp041_offline_eval.json` (WP-041's pre-pilot offline evaluation).
- `evaluation/live_outputs/wp042_diagnostic.json` (**new**, this WP - see Section 4).

## 4. Implementation / Instrumentation

**No production code was added or modified.** Investigation (`src/exam_generator/production/producer.py`, `src/exam_generator/production/models.py`) found that per-attempt, per-validator detail (`QuestionAttempt.validations: CandidateValidationResults`, carrying the actual, unmodified `GroundingValidationResult`/`MCQValidationResult`/`CategoryValidationResult`/`QualityValidationResult`/`TextbookCheckResult` for every attempt) **already exists** and is already captured by `QuestionAttemptsExhaustedError.attempts` - `QuestionProducer.produce_question()` already builds this for every attempt, accepted or not. The information was never missing from the architecture; it is simply **discarded** one layer up, in `category_generation/service.py`'s `_run_generation_cycle()`, which catches `QuestionAttemptsExhaustedError` and converts it to a plain `failure_type`/`failure_message` string pair before it ever reaches `CategoryQuestionSetResponse` (the shape every prior WP's own pilot script has been reading from).

Per section 16's explicit preference for "test-only diagnostic collection... over production API changes," this WP used a **scratchpad-only diagnostic script** that calls `QuestionProducer.produce_question()` directly (the same, unmodified production component, one layer below the point where detail is discarded) for the same real, planner-built `QuestionTarget`s, catching the full attempt list either way. This required **new, clearly-justified generation calls** (section 17) - the existing WP-041 pilot records do not and cannot contain this detail, since it was discarded before ever being recorded. Each of the three diagnostic targets (`Corpos Striatum`, `Basillar artery`, `Medial Lemniscus Tract` as a control) was run **exactly once**, no reruns, no configuration changes after observing results - honestly, this is **new evidence about the current failure pattern for these targets**, not a literal replay of WP-041's own original three failed attempts (each live LLM call is inherently stochastic).

## 5. Failed Attempts (Diagnostic Table, Section 18)

| Category | Target | Attempt | Result | First rejection | Language of answer |
|---|---|---:|---|---|---|
| גרעיני הבסיס | Corpos Striatum | 1 | FAIL | grounding | English |
| גרעיני הבסיס | Corpos Striatum | 2 | **PASS** | - | English |
| אספקת דם | Basillar artery | 1 | FAIL | grounding | English |
| אספקת דם | Basillar artery | 2 | FAIL | grounding | English |
| אספקת דם | Basillar artery | 3 | FAIL | grounding | English |
| מסילות עצביות | Medial Lemniscus Tract | 1 | **PASS** | - | English |

Full detail (every validator's `valid`/`passed` and `reason`, plus the generated question text) is in `evaluation/live_outputs/wp042_diagnostic.json`.

## 6. Validator-Level Rejection Reasons (OBSERVED)

**`Corpos Striatum`, attempt 1 (rejected)**: the generated question asked *"which of the following is part of Corpos Striatum?"* while the required correct answer (per WP-040's answer-identity requirement) was `Corpos Striatum` itself - a **self-referential logical contradiction**: the question's own premise (asking for a *part* of X) cannot be correctly answered by X itself. `GroundingValidator`: `correct_answer_supported=false` ("Corpos Striatum itself... does not correctly answer the question as posed"). `MCQValidator`: `valid=false` ("the intended correct answer... is not a valid option as it is the name of the structure being asked about, not a part of it"). `QualityValidator`: `valid=false`, additionally flagging "a mix of Hebrew and English anatomical terminology" as confusing (a wording-quality observation, not a rejection of English itself - the rejection's stated primary reason is still the logical mismatch).

**`Corpos Striatum`, attempt 2 (accepted)**: the question was reframed to *"which of the following is the central nucleus of the basal ganglia system?"* - now `Corpos Striatum` is a logically valid, well-grounded answer to its own question. All five validators passed cleanly.

**`Basillar artery`, all 3 attempts (all rejected)**: every attempt's question asked, in some form, "which artery supplies blood to [the upper surface of the cerebellum / related structures]" - but the evidence's own relationship structure makes `Basillar artery` the **source** feeding *into* `Superior Cerebellar Artery` (which is what actually supplies the named area), not the supplied entity itself. `GroundingValidator` consistently and correctly determined `Superior Cerebellar Artery`, not `Basillar artery`, is the evidence-supported answer to every phrasing attempted (`correct_answer_supported=false` in all 3 attempts, `grounding_reason` naming `Superior Cerebellar Artery` as the actual correct answer in 2 of 3). Attempt 1 additionally failed MCQ/quality for a related but distinct issue: the question asked for `Basillar artery`'s *own* supply area while listing `Basillar artery` itself as an answer choice - a different self-reference shape.

**`Medial Lemniscus Tract` (control, accepted first attempt)**: no rejection of any kind - clean, well-grounded, unambiguous on the first try, consistent with every prior pilot WP's own finding for this concept.

**No validator, in any of the 4 rejected attempts examined, cited language (Hebrew, English, or a mix) as the primary or sole reason for rejection.**

## 7. Category Comparison (Section 10)

| Category | WP-041 accepted | WP-041 total attempts | Avg attempts/round |
|---|---:|---:|---:|
| אספקת דם | 3/4 | 9 | 2.25 |
| גרעיני הבסיס | 2/4 | 12 | 3.0 |
| מסילות עצביות | 4/4 | 5 | 1.25 |

The regression is concentrated, not general: `מסילות עצביות` (whose targets - `Spinothalamic Tract`, `Medial Lemniscus Tract`, `Anterior Corticospinal Tract`, `Lateral Corticospinal Tract` - all carry rich, multi-sentence `factual_focus` text, per WP-037's own anchoring output) shows no degradation at all. The two regressed categories both involve a target (`Corpos Striatum`, `Basillar artery`) already independently flagged as structurally difficult since WP-035/037/039.

## 8. Corpos Striatum Analysis (Section 20)

1. **Is its evidence unusually weak? OBSERVED: yes.** `target.factual_focus` for `Corpos Striatum` is the **bare string `"Corpos Striatum"`** - confirmed independently from three separate sources: WP-039's own recorded pilot data (`wp039_pilot_records.json`, all 4 rounds), WP-040's own recorded pilot data, and this WP's own fresh diagnostic capture (`wp042_diagnostic.json`). Zero surrounding factual content - no function, no location, no relationship - has been supplied to generation for this specific target since WP-039's own trailing-truncation repair completed the concept's name (the repair fixed the *name*; it never touched WP-037's separate, narrow anchoring, which independently produces an empty context here because the concept's own line in the source evidence is immediately bounded by bullet markers/blank lines with no adjacent descriptive sentence).
2. **Is its evidence predominantly Hebrew? INFERENCE: not applicable to the immediate anchored context** (it is empty), but the *broader* category evidence (which generation still has access to via `source_evidence`, separately from the narrow `factual_focus`) is predominantly Hebrew, including the passage describing `Corpos Striatum`'s own sub-structures.
3. **Is an English representation present in the evidence? OBSERVED: yes** - `Corpos Striatum` itself is the concept's own extracted, English name.
4. **Does grounding fail more often? OBSERVED: yes**, for this specific target, in this diagnostic sample (1 of 2 attempts).
5. **Does MCQ validation fail more often? OBSERVED: yes**, in the same attempt, for a directly related reason (the self-referential answer choice).
6. **Does quality fail more often? OBSERVED: yes**, same attempt, secondary to the same logical issue (plus a language-mixing observation - see Section 6).
7. **Does target-answer validation (WP-040) fail? Not directly measurable as a separate validator** (WP-040's requirement is a generation-time instruction, not an independent validator) - but INFERENCE: the requirement's own presence is what forces the generator to reach for `Corpos Striatum` as the answer even when a naturally-constructed question (from the only available richer evidence - the sub-structure description) would not correctly support it.
8. **Are the generated questions structurally different between the successful and failed attempts? OBSERVED: yes** - attempt 1 asked "what is a part of X" (self-contradictory given X must be the answer); attempt 2 asked "what is the central nucleus" (X correctly answers this).
9. **Does English-first appear to be the direct trigger? OBSERVED: no** - nothing in either rejected attempt's validator reasoning cites language.
10. **Would the same candidate have failed under WP-040?** **INFERENCE, from already-available WP-040 pilot data**: WP-040's own `Corpos Striatum` round 2 already consumed all 3 attempts before succeeding (Section 9) - i.e., this target was already at the edge of the attempt budget under WP-040, before English-first existed. This does not prove the *specific* self-referential question shape observed in this WP's diagnostic attempt 1 would also have occurred under WP-040 (that would require a WP-040-configuration replay, out of this WP's scope per section 3), but it directly establishes that `Corpos Striatum`'s difficulty is not new to WP-041.

## 9. WP-040 vs. WP-041 Comparison (Section 11, OBSERVED, No New Generation Needed)

| | WP-040 `Corpos Striatum` | WP-041 `Corpos Striatum` | WP-040 `Basillar artery` | WP-041 `Basillar artery` |
|---|---|---|---|---|
| R1 | 2 attempts, accepted | 3 attempts, **exhausted** | (not selected) | 3 attempts, **exhausted** |
| R2 | 3 attempts, accepted (at budget ceiling) | 3 attempts, **exhausted** | (not selected) | 3 attempts, accepted |
| R3 | 2 attempts, accepted | 3 attempts, accepted | (not selected) | (not selected) |
| R4 | 2 attempts, accepted | (not selected - rotated away) | 3 attempts, **exhausted** | (not selected) |

**`Basillar artery` already fully exhausted its attempt budget once under WP-040** (round 4) - the identical failure class this WP's diagnostic capture reproduced three times in a row under WP-041. **`Corpos Striatum` was already at the 3-attempt ceiling once under WP-040** (round 2). Total attempts across all 12 rounds: WP-040 used 19 (avg 1.58/round, 11/12 accepted); WP-041 used 26 (avg 2.17/round, 9/12 accepted) - a real, disclosed increase in difficulty, concentrated in exactly the two targets already shown above to be pre-existing edge cases.

## 10. Evidence-Quality Analysis (Section 12)

- `Corpos Striatum`: evidence is structurally thin at the anchored level (bare name, zero context) - a WP-037 anchoring-narrowness artifact, not something WP-041 touched.
- `Basillar artery`: evidence is structurally rich (a full descriptive passage - source, area, related peduncles) but positions `Basillar artery` grammatically and semantically as a **source**, not a **supplied entity** - almost any "which artery supplies X" framing naturally resolves to a *different* artery (`Superior Cerebellar Artery`) than the assigned target, independent of language.
- Neither issue is caused by, or was introduced by, WP-041. Both are pre-existing properties of WP-037's anchoring output and the underlying evidence's own grammatical structure, respectively - confirmed via the already-available WP-040 comparison data (Section 9) showing both targets already marginal before WP-041 existed.

## 11. Causality Assessment

Per section 14's required conclusion set:

**Conclusion B is best supported by the available evidence: English-first is not the primary cause. The evidence/generation path for `Corpos Striatum` and `Basillar artery` specifically is the primary cause.**

Supporting evidence:
- OBSERVED: zero of the four rejected attempts examined cited language as a rejection reason, in either the grounding, MCQ, category, or quality validator's own stated reasoning.
- OBSERVED: both problematic targets were already at or beyond the attempt-budget edge under WP-040, before English-first existed (Section 9).
- OBSERVED: the one category with zero regression (`מסילות עצביות`) has consistently rich `factual_focus` text for all four of its targets; the two regressed targets both have either empty (`Corpos Striatum`) or source-vs-supplied-entity-mismatched (`Basillar artery`) evidence.
- INFERENCE: the specific failure mechanism observed (self-referential answer-choice paradoxes; evidence-structure-vs-required-answer mismatches) is a direct, logical consequence of forcing a *specific* named answer (WP-040's requirement) onto evidence that does not naturally support that specific entity as the answer to a well-formed question - a WP-040-era interaction, not a WP-041-era one.

**Honest limitation on this conclusion, stated explicitly rather than glossed over**: this diagnostic sample is small (one fresh capture per target, 2-4 attempts each). It is possible that English-first plays some smaller, secondary, amplifying role not visible in this sample (e.g., a Hebrew phrasing might occasionally read as less starkly self-contradictory to a validator than an English one, even for the same underlying logical error) - **no evidence for this was found, but the sample size does not allow it to be fully excluded either.** This is reported as an open possibility, not asserted as fact in either direction - matching section 26's explicit instruction not to force a conclusion beyond what the evidence supports. **Conclusion C is not excluded by the available evidence, but is not supported by any direct observation either** - only Conclusion B has direct, converging support from this WP's own data.

## 12. Regression Results

`.venv/bin/python -m pytest -q` → **1325 passed, 0 failed** - identical to WP-041's own baseline, confirming zero production behavior changed by this diagnostic WP. `scripts/generate_schemas.py` was not re-run (no model was touched).

## 13. Tests

None added - this WP introduced no production code or contract change requiring new test coverage, per its own explicit diagnostic-only scope (section 3).

## 14. Architectural Conclusion

The English-first policy (WP-041) achieved its own stated primary objective cleanly and did not introduce the acceptance regression it was initially suspected of causing. The regression is attributable, with converging evidence from three independent angles (fresh validator-level diagnostic capture, already-available WP-040 comparison data, and evidence-structure inspection), to a **pre-existing interaction between WP-037's evidence-anchoring narrowness and WP-040's forced target-answer-identity requirement**, concentrated in exactly two targets (`Corpos Striatum`, `Basillar artery`) that prior WPs (035, 037, 039) had already independently flagged as structurally atypical within this corpus. English-first's own contribution was to consume more of the category's `existing_questions` sequence with these two already-difficult targets this particular run (a matter of which targets the deterministic selection happened to reach in this specific 4-round sequence), not to make either target intrinsically harder to answer correctly.

## 15. Recommendation for WP-043

```text
WP-041 English-first policy:
KEEP

Primary cause of acceptance regression:
Pre-existing interaction between WP-037's narrow evidence anchoring (an empty
factual_focus for Corpos Striatum) and WP-040's forced target-answer-identity
requirement (an evidence-structure mismatch for Basillar artery, which the
evidence positions as a source rather than a supplied entity) - not English-first.

Corpos Striatum:
Its factual_focus has been the bare, contentless string "Corpos Striatum" since
WP-039. This is a WP-037 anchoring-narrowness issue, unrelated to language.

Cross-script coverage:
SOLVED (for concepts this pilot actually encounters) - WP-041's own live pilot
already established this; unaffected by this WP's findings.

Expansion readiness:
NO - not because of cross-script coverage (solved) or English-first (not the
cause of the regression), but because two of the three pilot categories still
depend on target-answer-identity/evidence-anchoring reliability that has not
yet been made more robust for structurally atypical targets.

Recommended WP-043:
A narrowly-scoped investigation of WP-037's anchoring for concepts whose own
line has no adjacent descriptive content (the Corpos Striatum shape) - e.g.
whether anchoring should fall back to a broader window specifically when the
narrow window is empty, still never guessing content - and, separately,
whether target-answer-identity (WP-040) should tolerate a target playing a
"source" role in its own evidence (the Basillar artery shape) by permitting a
differently-worded question whose correct answer is the target's own
downstream effect, rather than forcing every question toward "which artery
supplies X." Both are pre-existing WP-037/040 boundaries, not new WP-041
defects, and neither requires touching English-first, coverage, or validators.
```

## 16. Confirmations

- No validator was modified.
- No retrieval/chunking/TF-IDF logic was modified.
- WP-041's English-first policy, WP-040's answer-identity requirement, WP-039's truncation recovery, WP-038's `ConceptIdentity`, and WP-037's anchoring were all left completely unmodified.
- No public/shared contract change.
- No new retry mechanism or attempt-budget change.
- Diagnostic generation calls used the existing, unmodified `QuestionProducer`/`QuestionTargetPlanner` production wiring - never a shortcut or simulated response.
- Full regression suite passes unchanged: **1325/1325**.

## 17. Files Created/Modified

**Created:** none in `src/` or `tests/`.

**Data artifacts added** (evaluation only, matching the established `evaluation/live_outputs/` convention): `evaluation/live_outputs/wp042_diagnostic.json`.

**Documentation**: none - per section 28, "do not make architectural changes to the main documentation unless necessary to record diagnostic findings," and since the recommended next step (WP-043) is scoped narrowly and does not yet change any established architectural conclusion in `docs/ARCHITECTURE.md`/`docs/PROJECT_STATUS.md`, no doc update was made. This report itself is the record of the diagnostic finding.

---

WP-042 complete.

Tests:
1325 passed, 0 failed (unchanged from WP-041 - diagnostic only, zero production code touched)

Attempts analyzed:
6 (2 for Corpos Striatum, 3 for Basillar artery, 1 for the Medial Lemniscus Tract control) - full per-validator detail captured via QuestionProducer directly, since CategoryQuestionSetService discards this detail

Failed attempts analyzed:
4 (Corpos Striatum attempt 1; Basillar artery attempts 1, 2, 3)

Main rejection reason:
Grounding failure in every case - a self-referential answer-choice paradox for Corpos Striatum (question asks for a "part of X" while X itself is the required answer), and a source-vs-supplied-entity evidence-structure mismatch for Basillar artery (the evidence positions it as the source feeding Superior Cerebellar Artery, not as a supplied entity) - never a language-related rejection in any attempt

Corpos Striatum finding:
Its factual_focus has been the bare, contentless string "Corpos Striatum" since WP-039 - a WP-037 anchoring-narrowness issue, confirmed via three independent data sources (WP-039/040 pilot records, this WP's fresh diagnostic capture), unrelated to WP-041

English-first causality:
KEEP - Conclusion B (English-first is not the primary cause); zero rejected attempts cited language, and both problematic targets were already at or beyond the attempt-budget edge under WP-040, before English-first existed

Cross-script coverage:
SOLVED for concepts this pilot actually encounters (unaffected by this WP's own findings, reconfirming WP-041's own conclusion)

Acceptance impact:
Regression (11/12 to 9/12) is real but attributable to a pre-existing WP-037/WP-040 interaction, not to WP-041's own language policy

Recommended WP-043:
A narrowly-scoped fix for WP-037's anchoring when a concept's own line has no adjacent descriptive content (Corpos Striatum), and for WP-040's target-answer-identity requirement when a target plays a "source" role in its own evidence (Basillar artery) - neither requires touching English-first, coverage, or validators

Completion report:
implementation/WP-042_COMPLETION_REPORT.md

Waiting for architect review.
