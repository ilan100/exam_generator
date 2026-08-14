# WP-055 Completion Report — Globus Pallidus Classification-Ambiguity Investigation

## 1. Objective

Determine why `Globus Pallidus` (category `גרעיני הבסיס`, strategy `DEFAULT` per WP-054) repeatedly produces classification/membership-style questions that fail grounding, identify the actual failure mechanism, and establish the smallest justified architectural direction for resolving it. **Diagnostic only - no production fix implemented in this WP.**

## 2. Scope

Primary target: `Globus Pallidus` in `גרעיני הבסיס`. Related evidence/generated questions inspected only as needed: `Putamen`, `Caudate Nucleus`, `Nucleus Accumbens`, `(GPe)`/`(GPi)` sub-structures, direct/indirect pathway relationships. No change to identity-first mappings, target selection, coverage, JSON schemas, retry count, source authority, or any validator. **`git status` confirms zero files under `src/` or `tests/` were touched by this WP** (the only diffs present are WP-054's own already-completed, unrelated changes from the prior session).

## 3. Inputs Examined (OBSERVED)

- `evaluation/live_outputs/wp054_verification_records.json` - the three real, fresh Globus Pallidus attempts from WP-054's own live end-to-end verification (the triggering evidence for this WP).
- `evaluation/live_outputs/wp045_pilot_records.json`, `wp046_pilot_records.json`, `wp049_pilot_records.json` - every historical `Globus Pallidus`/`(GPe)` round from prior live pilots (5 rounds total, spanning 3 separate WPs).
- The real historical Excel workbook (`data/questions_full_export.xlsx`, via `HistoricalQuestionRepository`) - all 34 `גרעיני הבסיס` historical questions, filtered to the 9 that reference `Globus Pallidus`/`GPe`/`GPi`.
- A fresh, deterministic, **zero-LLM-call** reconstruction (`implementation/wp055_diagnosis.py`, prototype-only, not imported by `src/`) of: the exact retrieval evidence (`retrieve_for_category`), the exact `QuestionTarget` (`refine_concept_inventory`/`anchor_concept_evidence`, mirroring `wp054_verification.py`'s own construction), `extract_relationship()`, `discover_competitors()`, and a direct call to the existing, unmodified `_validate_target_answer_identity()` (WP-047) against a synthetic response carrying the historical WP-045 accepted answer text - all pure, deterministic application logic already in `src/`, invoked read-only for diagnosis, never modified.
- `prompts/generation/question.txt` (current, unmodified) and `docs/ARCHITECTURE.md`'s WP-010/044/047/048/050 sections, read for existing validator/prompt-mechanism understanding.

No new LLM/API call was made anywhere in this WP - the one "fresh" activity was the deterministic reconstruction above, which touches only retrieval (local TF-IDF) and pure Python functions.

## 4. The Three Globus Pallidus Failures (OBSERVED, from WP-054's live verification)

| Attempt | Question (Hebrew) | Answers (correct marked *) | Grounding result |
|---|---|---|---|
| 1 | "איזה מבנה הוא חלק מגרעיני הבסיס ומסייע בוויסות תנועות מוטוריות?" (Which structure is part of the basal nuclei and helps regulate motor movement?) | *Globus Pallidus, Putamen, Caudate Nucleus, Substantia Nigra | REJECTED |
| 2 | "איזה מבנה מהווה חלק מגרעיני הבסיס?" (Which structure is part of the basal nuclei?) | *Globus Pallidus, Nucleus Accumbens, Caudate Nucleus, Putamen | REJECTED |
| 3 | "איזה מהבאים הוא גרעין הנמצא בתוך הגרעינים הבסיסיים?" (Which of the following is a nucleus found within the basal nuclei?) | *Globus Pallidus, Nucleus Accumbens, Putamen, Caudate Nucleus | REJECTED |

MCQ/category/quality validators all returned `valid: true` for all three attempts (structurally well-formed MCQs); textbook status `CONSISTENT` for all three. **Grounding was the sole rejecting validator in every case.**

## 5. Generated Propositions (OBSERVED)

All three questions assert, in substance: *"Globus Pallidus has property P"*, where P is one of: "is part of the basal nuclei" (2, 3) or "is part of the basal nuclei and helps regulate motor movement" (1).

## 6. Retrieved Evidence (OBSERVED, deterministically reconstructed, 8 chunks)

The full retrieval result for `גרעיני הבסיס` (unchanged from WP-054's own run - retrieval is deterministic TF-IDF over an unmodified corpus) is recorded verbatim in the diagnostic script's stdout. Key facts, directly quoted from the authoritative student-summary evidence:

- `"התפקוד המרכזי של גרעיני הבסיס הוא בהוצאה לפועל של תנועה מוטורית"` ("the central function of the basal nuclei is executing motor movement") - stated as a **group-level** fact about the basal nuclei as a whole, not specific to Globus Pallidus.
- `"...Globus Pallidus Internus (GPi) – אחד ממדכאי התלמוס"` ("Globus Pallidus Internus (GPi) - one of the thalamus suppressors") - a genuine distinguishing fact, but attributed specifically to **GPi**, a sub-structure of Globus Pallidus, not to "Globus Pallidus" as an undifferentiated whole.
- A separate passage: `"מסלול עקיף... הקורטקס מפעיל את הפוטמן, אשר מדכא את ה-GPe, אשר מפסיק לדכא את הגרעין הסאב-תלמי"` ("indirect pathway... the cortex activates the putamen, which suppresses GPe, which stops suppressing the subthalamic nucleus") - a **different, functionally distinct** role attributed specifically to **GPe**.

**Both of WP-050's and WP-053's previously-reported distinguishing facts for Globus Pallidus remain reachable in the evidence generation actually receives today** - confirmed by direct substring search (script output): `תלמוס` (thalamus), `מדכא` (suppresses), and `ממוקם` (located) are all present in the full retrieved evidence text. This is not an evidence-availability problem at the corpus/retrieval level.

## 7. Evidence-Proposition Comparison (OBSERVED)

| Generated proposition | Authoritative evidence | Relationship | Reason for validator decision |
|---|---|---|---|
| "GP is part of basal nuclei + helps regulate motor movement" (Attempt 1) | Motor regulation is stated as a function of the basal nuclei **as a group**; every listed distractor (Putamen, Caudate Nucleus, Substantia Nigra) is equally a basal-nuclei/motor-circuit member per the evidence | PARTIAL (true but non-unique) | Correctly rejected - the evidence supports the claim for all four options equally, not GP specifically |
| "GP is part of basal nuclei" (Attempts 2, 3) | Every listed distractor is equally, explicitly a basal-nuclei member per the same evidence bullet list | SAME (true for all four, not just GP) | Correctly rejected - identical reasoning |

**None of the three generated propositions used the target-specific facts actually available** (GPi = thalamus suppressor via the direct pathway; GPe = suppressed-by-putamen / suppresses-STN via the indirect pathway) - all three reverted to the group-level classification/membership shape the production prompt's own "Testing enumeration or classification targets" section (unmodified since WP-044) already explicitly names as the weak framing to avoid, using an almost identical basal-nuclei worked example.

## 8. Grounding-Validator Analysis (OBSERVED + INFERENCE)

`GroundingValidator` (WP-010) independently retrieves its own evidence (never trusting generation's claims) and asks the LLM to assess whether the correct answer is supported and whether the other answers are **not equally correct**. All three recorded rejection reasons explicitly state that the other three answer choices are *also* supported by the evidence for the exact proposition asked - i.e. the validator correctly identified a genuine non-uniqueness problem, not a false rejection of a well-supported, unique claim. **This matches WP-048's own, independently-reached conclusion for this exact failure family** ("the existing validators already correctly reject every genuine instance"). No validator false-positive was found or is plausible here - the propositions themselves, as worded, are genuinely non-unique relative to the evidence.

## 9. Competitor Analysis (OBSERVED)

`discover_competitors()`, deterministically recomputed for the exact reconstructed target/evidence, returns an **empty** competitor list - because `extract_relationship()` classifies the target's (near-empty, see below) `factual_focus` as `UNSPECIFIED`, and competitor discovery requires a classified relationship type to search for. **Competitor selection did not, and structurally could not, contribute to this failure** - there was no competitor list to mislead generation with. This rules out root cause C entirely for this target/round.

## 10. Historical Comparison (OBSERVED, WP-045/046/049 live pilots)

| Source | Round | Accepted question shape | Correct answer text | Outcome |
|---|---|---|---|---|
| WP-045 round 3 | property/function | "מהו תפקידו של ה-Globus Pallidus..." (what is GP's role) | "מדכא את התלמוס ומפחית תנועה" (Hebrew functional description, does **not** contain "Globus Pallidus") | ACCEPTED (attempt 2 of 2) |
| WP-045 round 4 | identity, qualified | "...הגרעין הפנימי של גרעיני הבסיס הנקרא Globus Pallidus?" | "Globus Pallidus" | ACCEPTED (attempt 3 of 3) |
| WP-046 round 3 | identity, reverse-framed | "איזה מהגרעינים הבסיסיים הוא Globus Pallidus?" ("which of the basal nuclei **IS** GP") | "Globus Pallidus" | ACCEPTED (attempt 2 of 2) |
| WP-046 round 4 | identity, reverse-framed | same shape, target `(GPe)` | "(GPe)" | ACCEPTED (attempt 2 of 2) |
| WP-049 round 4 | identity, reverse-framed | "איזה מבין הגרעינים הבאים הוא Globus Pallidus?" | "Globus Pallidus" | ACCEPTED (attempt **1** of 1) |
| **WP-054 (this investigation's trigger)** | bare membership (3/3) | see section 4 | "Globus Pallidus" (never reached, all rejected) | **REJECTED (3 of 3)** |

**Pattern**: every historical Globus Pallidus success used either (a) a genuine property/function fact (1 round, now structurally closed - see section 11) or (b) an identity-establishing, reverse-framed question ("which of the following **IS** X" - 3 rounds, one succeeding on attempt 1). **Not one historical success used the bare "which structure is part of/belongs to X" framing that all three of WP-054's fresh attempts used exclusively.** This is consistent with, not contradicted by, WP-052's own retrospective classification for this target (property attempts 1/4 = 25% success, identity attempts 3/4 = 75% success) - WP-054's fresh run simply landed, by chance, entirely in the less-reliable branch of that known distribution across all 3 of its attempts.

## 11. A New, Previously-Undocumented Finding: WP-047 Retroactively Closed the Property-Answer Pathway (OBSERVED, deterministic proof)

A direct call to the current, unmodified `_validate_target_answer_identity()` (WP-047) against a synthetic `GeneratedQuestionResponse` carrying the exact WP-045-round-3 accepted answer text (`"מדכא את התלמוס ומפחית תנועה"`) **raises `InvalidGeneratedOutputError`** - confirmed by direct execution, not inferred:

```text
Generated response's correct answer 'מדכא את התלמוס ומפחית תנועה' does not
identify the assigned target 'Globus Pallidus' - target-to-answer identity
requirement violated (WP-047)
```

WP-047 was implemented *after* WP-045 and applies unconditionally to every `named_entity_target=True` target (Globus Pallidus included). **This means the one confirmed historical property-based success shape for Globus Pallidus (a bare functional description not literally containing the target's name) is now structurally impossible under the current architecture** - not merely unlikely, but a deterministic rejection every time it would occur. Any future property-based success for Globus Pallidus must now explicitly include the target's own name in the answer text (e.g. "Globus Pallidus suppresses the thalamus" rather than bare "suppresses the thalamus"), a real, undocumented-until-now interaction between two independently-justified WPs (WP-045's own accepted precedent and WP-047's own safety check). Neither of the three WP-054 failures is *caused* by this interaction (all three attempted bare membership, not property, so WP-047's check never even fired), but it materially narrows which repair strategies remain viable going forward.

## 12. A Second New Finding: Target/Evidence Granularity Mismatch (INFERENCE)

The deterministically-reconstructed target's own anchored `factual_focus` is near-empty enumeration-bullet noise (`'utamen\nP\no\nGlobus Pallidus\n'`) - **confirming WP-050's already-disclosed finding still holds unchanged today**. Separately, `refine_concept_inventory()` over the same evidence produces `"Globus Pallidus"` as one flat concept **and**, independently, `"(GPe)"`, `"Globus Pallidus Externus"`, `"(GPi)"` as distinct concepts - and the evidence itself consistently attributes the two genuinely distinguishing facts (thalamus-suppression via the direct pathway; putamen-suppressed/STN-suppressing via the indirect pathway) to **GPi and GPe specifically**, never uniformly to "Globus Pallidus" as a whole (the two sub-structures play functionally different, even opposite-pathway roles). **INFERENCE, not proven**: this granularity mismatch may make it harder for generation to state a single, cleanly-supported distinguishing property for the flat "Globus Pallidus" target specifically (as opposed to GPi or GPe individually), nudging it toward the safer-seeming but ultimately non-unique group-membership framing instead. This is offered as a documented observation for a possible future planning-layer investigation - **not** a claim proven by this WP's 3-attempt sample, and explicitly out of this WP's implementation scope.

## 13. Prompt Analysis (OBSERVED)

`prompts/generation/question.txt`'s existing "Testing enumeration or classification targets" section (unmodified since WP-044) already contains a worked example naming almost exactly this failure shape:

> "Weak framing (avoid): 'Which of the following is part of the basal nuclei?'... every sibling nucleus that genuinely belongs to the same grouping is equally correct..."

All three WP-054 Globus Pallidus attempts used precisely this already-discouraged framing. **This is not a missing-guidance problem** - the guidance is present, specific, and uses this exact target family as its own example - **it is a reliability problem**: generation does not reliably follow existing, explicit, correctly-targeted guidance for this specific target, three times in a row in one fresh run. This is the same characterization WP-048 independently reached for the broader classification-ambiguity family.

## 14. Retrieval Analysis (OBSERVED)

Retrieval returns the same 8 chunks used by every other target in this category (not narrowed per-target) - 5 of the 8 chunks contain direct or indirect textual reference to Globus Pallidus/GPi/GPe. Retrieval is not target-specific by design (WP-006's category-level retrieval baseline, unchanged) - the target-specific distinguishing facts exist within the broader supplied evidence, not within the target's own narrow anchor (section 6/12 above). No quantitative "relevant vs. category-level chunk" metric beyond substring/manual inspection is currently producible by the existing infrastructure without inventing a new measurement mechanism, which this WP was instructed not to do.

## 15. Failure Taxonomy

| Attempt | Failure class | Evidence |
|---|---|---|
| 1 | CLASSIFICATION_MEMBERSHIP (primary) + CATEGORY_LEVEL_FACT (secondary) | Motor-regulation property stated group-wide in evidence; all four answers equally satisfy it |
| 2 | CLASSIFICATION_MEMBERSHIP | Bare basal-nuclei membership; all four answers equally satisfy it |
| 3 | CLASSIFICATION_MEMBERSHIP | Bare basal-nuclei membership (near-identical to attempt 2); all four answers equally satisfy it |

## 16. Required Failure Taxonomy Summary

| Failure class | Count | Evidence |
|---|---:|---|
| CLASSIFICATION_MEMBERSHIP | 3 | All three attempts assert group membership the evidence supports equally for every distractor |
| RELATIONSHIP_TO_MEMBERSHIP | 0 | Not observed in this sample |
| CATEGORY_LEVEL_FACT | 1 (attempt 1, secondary) | Motor-regulation property is a basal-nuclei-wide fact, not GP-specific |
| TARGET_IDENTITY | 0 | Not observed in this sample |
| EVIDENCE_GAP | 0 | Distinguishing facts confirmed present in the retrieved evidence (section 6) |
| COMPETITOR_PROBLEM | 0 | Competitor list confirmed empty (section 9) |
| PROMPT_PROBLEM | 0 (existing guidance already correctly targets this shape - section 13) | - |
| VALIDATOR_PROBLEM | 0 | No false positive found or plausible (section 8) |
| OTHER | 0 | - |

## 17. Root Cause

**F - Multiple interacting causes**, specifically:

1. **Primary (B-adjacent, reliability not content)**: generation did not reliably apply its own existing, correctly-targeted "avoid bare classification/membership" guidance for this target across all 3 attempts of this specific run - a known, previously-classified reliability limitation (WP-048), not a new defect, and not a missing/wrong prompt instruction.
2. **Contributing (E)**: the flat "Globus Pallidus" target/evidence representation does not surface either of its two genuinely distinguishing facts (both attributed to GPi/GPe sub-structures specifically) within its own anchored `factual_focus`; those facts remain reachable only via the broader supplied evidence, which generation did not draw on in any of these 3 attempts.
3. **A newly-confirmed structural constraint (not a cause of these 3 failures, but relevant to any fix)**: WP-047's target-answer-identity check has retroactively closed off the one historically-confirmed property-only success shape for this target (section 11) - any future property-based fix must produce an answer literally containing "Globus Pallidus".

Explicitly excluded by direct evidence: **A** (evidence retrieval/context insufficiency - facts are present, section 6), **C** (competitor selection - list was empty, section 9), **D** (validator incorrectness - no false positive found, section 8).

## 18. Confidence

**MEDIUM.**

All three of WP-054's fresh failures share the identical, cleanly-identified proposition-mismatch mechanism, and this is independently corroborated by a much larger prior dataset (5 historical live-pilot rounds across 3 separate WPs, plus 9 real historical exam questions, all pointing the same direction: bare membership fails, identity/property-with-name succeeds). This is not a 3-data-point guess. However, this WP did not run a controlled experiment (that is explicitly WP-056's job, if approved) and cannot claim to have proven *why* generation chose bare-membership framing 3/3 times in this specific run rather than the historically-more-common mixed pattern - that remains a property of the underlying LLM's stochastic behavior, not something this diagnostic can fully explain. HIGH confidence would require either a controlled multi-round experiment or direct inspection of the model's own reasoning process, neither of which this WP performed (per its own instruction to avoid unnecessary LLM calls).

## 19. Production Changes

**NONE.** `git status` confirms no file under `src/exam_generator/` or `tests/` was modified by this WP. The only new file is `implementation/wp055_diagnosis.py` - a prototype-only, read-only diagnostic script, imported by nothing in `src/`, making zero LLM/API calls, that reconstructs already-deterministic application state (retrieval, target construction, relationship/competitor computation) and exercises one existing, unmodified function (`_validate_target_answer_identity()`) for verification purposes only.

## 20. Regression Result

```text
REGRESSION: NOT APPLICABLE
```
(Production code unchanged; `pytest -q` re-run anyway for due diligence: `1426 passed, 0 failed` - identical to the state at the end of WP-054, confirming nothing was disturbed.)

## 21. Architectural Conclusion

The Globus Pallidus classification-ambiguity problem is **not** a defect in any single component - retrieval supplies the needed facts, competitor selection contributes nothing, the grounding validator correctly rejects every genuinely non-unique proposition, and the prompt already names this exact failure shape as one to avoid. It is a **generation-reliability problem localized to one target**, compounded by a **representation-granularity mismatch** (flat target vs. sub-structure-specific evidence) and a **newly-identified, previously-undocumented cross-WP interaction** (WP-047 closing off the one confirmed historical property-only success shape). This is consistent with, and extends, WP-048's own prior finding for the broader classification-ambiguity family: "not a safety/detection gap... a reliability problem with no safe deterministic fix." **The WP-054 identity-first mapping was NOT changed** - `Globus Pallidus` remains `DEFAULT`, exactly as approved.

## 22. Recommended Next WP

Per WP-055 section 37's own explicit instruction ("if the investigation concludes that Globus Pallidus should become identity-first, that is only a HYPOTHESIS and must lead to a separate controlled experiment before implementation"):

**HYPOTHESIS (not a decision): identity-first, reverse-framed generation ("which of the following IS X") appears to be Globus Pallidus's most reliable historical success pattern** (3 of 5 historical successes, including the only attempt-1 success; the property-based pathway is now additionally constrained by WP-047, section 11).

**Recommended: WP-056 - Globus Pallidus Identity-First Controlled Experiment**, mirroring WP-053's own methodology exactly (a fresh, in-memory-only experimental instruction, never touching the production prompt file; Globus Pallidus as the sole experimental target this time; a genuine current-control comparison round; explicit small-sample caveats). This is the smallest next step consistent with this project's established evidence → experiment → implementation discipline, and does not bypass it merely because three fresh failures were observed.

A secondary, unconfirmed, lower-priority direction (documented in section 12, not recommended for immediate action): whether the concept-inventory/target-planning layer's flat "Globus Pallidus" representation should be reconsidered relative to its own GPi/GPe sub-concepts - this would require its own dedicated investigation into target/concept granularity, likely affecting more than just this one target, and is explicitly out of this WP's scope.

---

# Required Final Architecture Table

| Area | Current state | WP-055 finding | Change authorized now |
|---|---|---|---|
| Caudate Nucleus | IDENTITY_FIRST | unchanged | NONE |
| Nucleus Accumbens | IDENTITY_FIRST | unchanged | NONE |
| Globus Pallidus | DEFAULT | diagnostic finding: reliability + representation-granularity + WP-047 interaction (section 17) | NONE unless explicitly approved |
| Other targets | DEFAULT | out of scope | NONE |
| Validators | unchanged | analyzed (grounding confirmed correct, no false positive found) | NONE |
| Retrieval | unchanged | analyzed (evidence confirmed sufficient; not target-specific by design) | NONE unless root cause demands follow-up |
| Retry budget | 3 | unchanged | NONE |
| Schemas | unchanged | unchanged | NONE |

# Required Decision Table

| Question | Result |
|---|---|
| Why did the three Globus Pallidus attempts fail? | All three asserted bare basal-nuclei group membership/classification, a proposition the evidence supports equally for every distractor - correctly rejected by grounding (section 4/7/15) |
| Is the generated proposition supported by the authoritative evidence? | Partially - true but non-unique (group-level, not GP-specific) (section 7) |
| Did retrieval provide sufficient target-specific evidence? | Evidence containing GP-specific distinguishing facts (via GPi/GPe) was present in the full 8-chunk retrieval; the target's own narrow anchor did not surface it (section 6/12) |
| Did competitor selection contribute? | No - competitor list was empty (section 9) |
| Did the prompt contribute? | No missing guidance - the existing prompt already names this exact failure shape; generation did not reliably follow it (section 13) |
| Is the grounding validator correct? | Yes, in all three cases - confirmed by direct comparison against the evidence, no false positive found (section 8) |
| Is the problem target representation? | Contributing factor (INFERENCE): flat "Globus Pallidus" vs. GPi/GPe-specific evidence facts (section 12) |
| Is identity-first now justified for Globus Pallidus? | HYPOTHESIS only, supported by historical pattern (3/5 successes reverse-framed identity); requires a controlled experiment before implementation (section 22) |
| Was production code changed? | No (section 19) |
| Was WP-054 modified? | No |
| Recommended next WP | WP-056 - Globus Pallidus Identity-First Controlled Experiment |

---

# Terminal Summary

```text
WP-055 complete.

Objective:
Determine why Globus Pallidus repeatedly produces classification/
membership questions that fail grounding, and establish the smallest
justified next direction - diagnostic only, no production fix.

Target:
Globus Pallidus

Category:
גרעיני הבסיס

Attempts analyzed:
3 fresh (WP-054 live verification) + 5 historical (WP-045/046/049 live
pilots) + 9 real historical exam questions (Excel, style reference only)

Primary failure pattern:
Bare classification/membership ("which structure is part of X"),
3 of 3 fresh attempts - a proposition the evidence supports equally
for every distractor, never using the target-specific facts (GPi/GPe)
actually present in the broader retrieved evidence.

Generated proposition analysis:
All three propositions are TRUE but NON-UNIQUE relative to the evidence -
group-level facts, not Globus-Pallidus-specific facts.

Evidence analysis:
Distinguishing facts (thalamus-suppression via GPi; putamen-suppressed/
STN-suppressing via GPe) confirmed still present in the retrieved
evidence today - not an evidence-availability problem. Attributed to
GPi/GPe specifically, not uniformly to the flat "Globus Pallidus" target.

Retrieval analysis:
Sufficient - not target-narrowed by design (unchanged WP-006 baseline);
the target's own anchored factual_focus is near-empty noise (confirms
WP-050's already-disclosed finding, unchanged).

Competitor analysis:
Empty list (relationship_type UNSPECIFIED) - ruled out as a contributing
cause.

Prompt analysis:
Existing "Testing enumeration or classification targets" guidance
already names this exact failure shape - a reliability gap in following
existing guidance, not a missing-instruction gap.

Grounding validator analysis:
Correct in all three cases - no false positive found or demonstrable.

Root cause:
F (multiple interacting causes: generation reliability + target/evidence
granularity mismatch + a newly-confirmed WP-047 interaction closing off
the historical property-only success shape)

Confidence:
MEDIUM

Production changes:
NONE

WP-054 identity-first mapping:
UNCHANGED

Regression:
NOT APPLICABLE (production code unchanged; pytest re-run anyway: 1426
passed, 0 failed)

Architectural conclusion:
Reliability + representation problem, not a validator/retrieval/
competitor defect. Consistent with and extends WP-048's prior finding
for the broader classification-ambiguity family.

Recommended next WP:
WP-056 - Globus Pallidus Identity-First Controlled Experiment
(HYPOTHESIS only - requires a controlled experiment before any
implementation, mirroring WP-053's own methodology)

Completion report:
implementation/WP-055_COMPLETION_REPORT.md

Waiting for architect review.
```
