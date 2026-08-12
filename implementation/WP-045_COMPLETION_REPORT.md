# WP-045 Completion Report — Deterministic Detection of Evidence-Supported Question Ambiguity

## 1. Objective

WP-044 validated the structural-generation-constraint approach (8/12 accepted, up from WP-043's 5/12) but left two targets, `Globus Pallidus` and `Corticospinal Tract`, repeatedly failing because generated questions had multiple evidence-supported correct answers. WP-045's objective: determine why, and whether a narrow, deterministic, structural constraint can prevent this class of question **before** invalid generation reaches validation - without assuming the two targets share a common cause (the WP's own explicit "Critical Principle," section 2).

## 2. WP-044 Findings (Recap, OBSERVED from WP-044's own completion report and architecture review)

Both targets exhausted all 3 attempts in WP-044's live pilot. Every rejection cited grounding's `other_answers_not_equally_correct=false` - a generic question (e.g. "which of the following is part of the basal nuclei," "which motor tract is responsible for innervating skeletal muscles") to which multiple real, evidence-supported entities are equally correct answers. WP-044's own enumeration-shape detector (`is_enumeration_evidence_insufficient()`) does not fire for either target - neither target's own narrow anchored evidence contains an enumeration-introduction cue phrase within the bounded detection window.

## 3. Globus Pallidus Diagnosis

**OBSERVED** (from WP-044's own pilot data, `evaluation/live_outputs/wp044_pilot_records.json`, and this WP's own fresh pilot, `evaluation/live_outputs/wp045_pilot_records.json`):

- `Globus Pallidus`'s own narrow anchored `factual_focus` is `"utamen\nP\no\nGlobus Pallidus\n"` (or `"...\n"` depending on trailing-bullet variance) - a fragment of the *preceding* sibling's own truncated name (`"utamen\nP"`, itself a leading-truncation of `"Putamen"`) plus bullet-marker noise (`"o"`, `""`). Zero content specific to `Globus Pallidus` itself.
- Of 8 total rejected attempts observed across both WPs' pilots for this target, 6 asked a generic classification/membership question ("which structure is part of the basal ganglia/basal nuclei" - every basal-nuclei member is equally correct), and exactly 1 (WP-045's own round 4 attempt 2 equivalent, and WP-044's own round-4-attempt-2) asked specifically about the `Globus Pallidus`/`Globus Pallidus Internus` parent/child pair.
- The real corpus evidence for `גרעיני הבסיס` extracts `Globus Pallidus`, `Globus Pallidus Externus`, and (separately, via a leading-truncation-losing-its-"Globus"-prefix artifact) `Pallidus Internus` as three separate inventory concepts - `Globus Pallidus` is textually a proper substring of `Globus Pallidus Externus`.

**INFERENCE**: `Globus Pallidus`'s dominant failure mode (6/8 rejections) is a **broad classification/enumeration ambiguity** - structurally the same family as `Corpos Striatum`'s WP-043/044-diagnosed problem (a list member with no target-specific distinguishing content, so generation falls back to generic membership framing) - but WP-044's own cue-phrase detector cannot reach it, because the actual enumeration-introduction sentence ("the basal nuclei contain several sub-structures") sits far enough back in the source text that multiple sibling candidate-concept lines separate it from `Globus Pallidus`'s own anchor window, which `anchor_concept_evidence()` correctly (by WP-037's own design) refuses to cross.

**A critical, direct counter-example was found empirically, not assumed**: `Caudate Nucleus` and `Nucleus Accumbens` - both selected and successfully accepted in both pilots - have **structurally identical** narrow anchored evidence to `Globus Pallidus` (also bare bullet-marker fragments, e.g. `"o\nCaudate Nucleus\no"`, with zero real local content). There is no local, structural, textual property of `Globus Pallidus`'s own anchored evidence that distinguishes it from these two successful siblings. This is a genuine, verified negative finding, not an oversight: **no safe deterministic signal was found that explains why generation tends toward generic-membership framing for `Globus Pallidus` specifically but not for its evidence-identical-looking siblings.**

## 4. Corticospinal Tract Diagnosis

**OBSERVED**: `Corticospinal Tract`'s own narrow anchored evidence, from its actually-selected chunk (`STUDENT_SUMMARY:student_summary_3.pdf:0148:0001`, chosen by first-occurrence/retrieval-rank order over a cleaner alternative chunk, `0104`, that also contains the concept), is garbled OCR text (`"...למסילות האלו יש כל מיני \n.תחנות..."` - "these tracts have various stations," a statement equally true of the sibling `Corticobulbar/Corticonuclear Tract` listed just above it in that same passage). The concept inventory separately extracts `Anterior Corticospinal Tract` and `Lateral Corticospinal Tract` from a *different* chunk (`0106`) - both already filtered out by WP-043's own pre-existing `is_factual_focus_sufficient()` check (their own anchored evidence is bare), so neither is independently selectable as a target, but both remain visible to the LLM in the full supplied evidence set (`format_student_summary_evidence()` always includes every retrieved chunk, not only the target's own anchor).

Every one of the 4 rejected attempts observed across WP-044's and WP-045's own pilots explicitly named the parent **and** one or both children as jointly evidence-supported, verbatim from the real rejection reasons: *"...the Corticospinal and Anterior Corticospinal Tracts... Both these tracts are supported as correct answers..."*; *"...the Corticospinal Tract and its subdivisions originate in the precentral gyrus..."*; *"...Both the Corticospinal Tract and the Lateral Corticospinal Tract are supported as correct answers..."*.

**OBSERVED, from this WP's own fresh pilot (round 4, accepted on attempt 1)**: a **structurally identical** question ("which tract is responsible for innervating skeletal muscles and limbs") was asked again and this time **accepted**, because the four generated answer choices this attempt were `Corticospinal Tract`/`Corticobulbar Tract`/`Medial Lemniscus Tract`/`Spinothalamic Tract` - the generator's own distractor choice this time did not include `Lateral`/`Anterior Corticospinal Tract` at all, so grounding's own per-answer-choice ambiguity check (scoped only to the four presented choices) never had reason to flag it, even though the same underlying evidence ambiguity (the children still exist, still evidence-supported, still visible to the LLM) is equally present in both the accepted and rejected attempts.

**INFERENCE**: `Corticospinal Tract`'s failure is a genuine **parent/child hierarchy ambiguity** - every general property the evidence states about `Corticospinal Tract` as a category is also true of its own named children, so a question testing that general property is satisfied by more than one entity *whenever the generator happens to include a child as one of its four answer choices*. This is directly, repeatedly confirmed by the rejection reasons' own explicit language, not inferred from evidence shape alone.

**A second, more precise inference, confirmed by the round-4 accepted counter-example**: whether this ambiguity is actually *caught* by grounding is not purely a function of the target's evidence shape - it also depends on the generator's own stochastic **distractor selection** for that specific attempt. The same target, same evidence, same production code produced both a rejected and an accepted outcome for structurally the same question, differing only in which four entities happened to be offered as answer choices.

## 5. Evidence Analysis (Section 6/7 Investigation Findings, Summarized)

Both targets were investigated per section 6/7's own checklist (enumeration, classification, parent/child, shared predicate, neighboring-concept contamination, question wording) against their actual real corpus text, never assumed. Neither investigation stopped at the first plausible explanation - `Globus Pallidus` in particular was checked against its structurally-identical-looking successful siblings specifically to test (and, per section 3 above, falsify) the hypothesis that local evidence shape alone explains its failures.

## 6. Common-Pattern Analysis (Section 8's Required Comparison)

| Question | Answer |
|---|---|
| Do they share the same evidence shape? | **No.** `Globus Pallidus`'s local evidence is bare/noise-only; `Corticospinal Tract`'s local evidence is non-empty but generic/shared-with-sibling. |
| Do they share the same relationship type? | Not classified identically - `Corticospinal Tract`'s ambiguity is specifically parent/child inheritance; `Globus Pallidus`'s dominant mode is flat sibling-membership, unrelated to hierarchy. |
| Do they share the same local sibling structure? | Partially - both sit among several candidate-concept siblings in a bulleted list, but so do their *successful* siblings (`Caudate Nucleus`, `Nucleus Accumbens`, `Spinothalamic Tract`, `Corticobulbar/Corticonuclear Tract`), so this alone does not explain the divergence. |
| Do they share the same question pattern? | Partially - both attracted "generic classification membership" framings at some point, but `Corticospinal Tract`'s failures are more precisely and consistently parent/child-specific (100% of its own rejections named a child explicitly), while `Globus Pallidus`'s are predominantly (6/8) the broader, less specific classification shape. |
| Do they fail for the same grounding reason? | Same *validator field* (`other_answers_not_equally_correct=false`) but different underlying evidence relationships (sibling-of-many vs. parent-of-named-child). |
| Can one deterministic rule safely cover both? | **No - see section 9 for the specific, empirically-demonstrated reason.** |

**Conclusion: Do not force a common abstraction (per section 8's own explicit instruction). The two targets fail for meaningfully different reasons, one of which (`Corticospinal Tract`) has a confirmed, specific structural explanation, and one of which (`Globus Pallidus`, dominant mode) does not have a safely-identifiable deterministic explanation at all.**

## 7. Evidence Ambiguity vs. Question Ambiguity (Section 9)

- `Corticospinal Tract`: an **evidence problem** for the general/category-level property actually tested ("innervates skeletal muscles/limbs," "originates at Precentral Gyrus") - the evidence genuinely, structurally supports more than one entity for that exact property (the parent and its named children). Whether this evidence problem becomes a *visible* rejection is additionally gated by a **question/generation-time factor** (whether the generator's own distractor choice happens to include a competing child) - see section 4's round-4 counter-example.
- `Globus Pallidus`: predominantly an **evidence problem** too (no target-specific distinguishing content exists in the target's own local anchor for the majority failure mode), but **INFERENCE, not fully confirmed**: since structurally-identical-evidence siblings succeed reliably, the actual determining factor for whether generation reaches for a generic classification question vs. a specific one appears to be substantially a **generation-time (LLM stochastic) choice**, not a deterministically-predictable property of the evidence alone.

## 8. Enumeration / Classification / Hierarchy Assessment (Section 8 of WP-045)

- **A. Enumeration ambiguity**: does not apply to either target as WP-044's own narrow detector defines it (no cue phrase reachable in either target's own anchor).
- **B. Classification ambiguity** (broader category membership, no explicit intro cue): the dominant, better-fitting description of `Globus Pallidus`'s majority failure mode.
- **C. Parent/child hierarchy ambiguity**: the precise, confirmed description of `Corticospinal Tract`'s failure mode, and of exactly one of `Globus Pallidus`'s eight observed failures.

## 9. Architectural Decision

**A candidate deterministic signal was designed, implemented as a diagnostic-only function, tested directly against real corpus data across all three pilot categories, and found unsafe to deploy as a production skip mechanism - a confirmed, not merely suspected, false positive was found.**

The signal (`has_named_child`, kept out of `src/` - see below): true when another concept in the same category's own concept inventory contains the target's own (normalized) text as a whole-word substring - e.g. `"Globus Pallidus"` is contained within `"Globus Pallidus Externus"`; `"Corticospinal Tract"` is contained within `"Anterior Corticospinal Tract"`. This directly, cleanly flags exactly `Globus Pallidus` and `Corticospinal Tract` among every concept actually selected in either pilot.

**However, applied against the full real `אספקת דם` inventory, the same signal also flags `Inferior Cerebellar Artery (PICA)`** - a target that was **selected and cleanly accepted on the first attempt in both WP-044's and this WP's own pilot**. Direct investigation confirmed why: `"Posterior inferior cerebellar artery (PICA)"` (a separate inventory entry, extracted from a different chunk) contains `"Inferior Cerebellar Artery (PICA)"` as a substring - but these are **the same real-world artery**, extracted twice because one occurrence's raw source line is simply missing the leading word `"Posterior"` (an ordinary extraction-completeness gap, not a genuine parent/child relationship). A purely textual containment check cannot safely distinguish "genuine anatomical subtype" (`Corticospinal Tract` → `Anterior`/`Lateral Corticospinal Tract`, real, distinct subdivisions) from "the same entity missing a word" (`Inferior Cerebellar Artery (PICA)` / `Posterior inferior cerebellar artery (PICA)`) - both shapes use an ordinary directional-adjective modifier, and several refinements were attempted (restricting to same-chunk co-occurrence; restricting to a closed vocabulary of Latin anatomical qualifiers; requiring multiple matching children) - each either failed to preserve the genuine positive case, failed to exclude the confirmed false positive, or both (documented in full below).

**A second, independent, and arguably stronger reason not to deploy any such signal emerged from this WP's own live pilot** (section 4 above): the *same* target (`Corticospinal Tract`), with the *same* evidence, under the *unmodified* production code, both failed (round 3) and succeeded (round 4) in the same pilot run - because whether the ambiguity is actually exposed depends on the generator's own stochastic distractor selection, not on the target's evidence shape alone. A deterministic pre-generation skip keyed only to evidence shape would have permanently blocked `Corticospinal Tract` from ever reaching generation - including the cases (like round 4) where generation would have succeeded cleanly on its own. This directly demonstrates that "has a named child in the inventory" is not even a reliable *predictor* of failure for the one target it was built to explain, beyond being an unsafe general rule.

**Decision: Outcome C (WP-045 section 15) - no safe deterministic signal was found for a general or even a narrowly-scoped version of this specific ambiguity-detection idea. No production code was changed.** This is not a failure to try; three refinements were investigated and each is documented in section 20 below with the specific reason it was rejected, per this project's established practice of showing the negative-result work, not merely asserting a conclusion.

## 10. Implementation Changes

**None.** `src/exam_generator/` is byte-for-byte unchanged from WP-044 (confirmed via `git diff --stat src/` showing no output). WP-044's enumeration-shape skip, source-role naming, and deterministic consistency check remain completely intact and unmodified. The `has_named_child()` function described in section 9 was written and tested only as a throwaway diagnostic script (`wp045_pilot_run.py`, scratchpad-only, never added to the repository), computing a read-only annotation for pilot observability that never influences any production decision.

## 11. Tests

**No new tests were added**, since no production code was modified (WP-045 section 22: "If production code is modified, add deterministic tests for every new rule" - the converse holds: no rule was added, so no new rule-specific tests are required). All existing WP-044 tests continue to pass unmodified, including the ones specifically preserving `Corpos Striatum`'s enumeration skip and `Basillar artery`'s source-relationship extraction (WP-045 section 24's explicit requirement).

## 12. Regression Results

`.venv/bin/python -m pytest -q` → **1379 passed, 0 failed** - unchanged from WP-044's own baseline (expected, since no code was touched). `scripts/generate_schemas.py` re-run: all three public schema files byte-identical. `git diff --stat src/exam_generator/validation/ config/app.yaml prompts/generation/question.txt src/exam_generator/planning/ src/exam_generator/generation/ src/exam_generator/prompts/` all show no changes for this WP. English-first (WP-041), evidence sufficiency/enumeration handling/source-role handling (WP-043/044), coverage (WP-034/038), and the 3-attempt retry budget are all unchanged, confirmed both by the empty diff and by this WP's own fresh pilot continuing to exercise them identically to WP-044's own run.

## 13. Pilot Methodology

One fresh live run: the same three pilot categories × four sequential questions each, via the real, unmodified `CategoryQuestionSetService.from_default_configuration()` - identical methodology to WP-036 through WP-044. No manual repair, no configuration change after seeing results, no selective reruns. Learning from WP-044's own disclosed infrastructure incident, the run was launched with `python3 -u` and direct file redirection (not piped through `tail`) from the start, and completed cleanly on the first attempt with no infrastructure issues.

Because no production mechanism changed, this pilot serves a different purpose than WP-044's own: a **fresh, independent stability/reproducibility check** of WP-044's existing mechanisms, and a second, independent data point specifically on `Globus Pallidus`/`Corticospinal Tract`'s own behavior - which, as sections 3/4/9 describe, turned out to be genuinely informative (both targets succeeded at least once this run, where they had failed every time in WP-044's own pilot).

Per-attempt data captured for every round: category, round, target, `target_role`, `evidence_shape`, all four answer choices (not just the correct one - an addition over WP-044's own pilot script, per WP-045 section 27's explicit requirement), attempt number, full per-validator results, accept/reject, explicit rejection reasons, plus a read-only, diagnostic-only `has_named_child` annotation (section 9) and an explicit `skip_reason` field (always `null` this WP, since no skip mechanism was added - WP-045 section 27: "A skip is an intentional architectural outcome, not an unexplained failure," recorded honestly as not applicable here).

## 14. Pilot Results

**11/12 accepted (91.7%)**, up from WP-044's 8/12 (66.7%) - **but this improvement must not be read as evidence WP-045 fixed anything, since no code was changed; it is evidence of the genuine run-to-run stochastic variance documented in sections 3/4/9.**

| Category | Accepted | Distinct targets | Notable |
|---|---|---|---|
| `אספקת דם` | 4/4 | 4/4 | Unchanged from WP-044's own clean result; `Inferior Cerebellar Artery (PICA)` (has_named_child=True per the diagnostic-only signal) accepted first attempt, confirming section 9's counter-example live |
| `גרעיני הבסיס` | 4/4 | 3/4 | `Globus Pallidus` selected rounds 3-4, accepted both times - see section 15 for a material caveat on round 3 |
| `מסילות עצביות` | 3/4 | 3/4 | `Corticospinal Tract` selected rounds 3-4: round 3 exhausted (identical failure shape to WP-044); round 4 accepted attempt 1 - the direct counter-example discussed in section 4/9 |

Total attempts across all 12 rounds: 19 (avg 1.58/round); avg attempts per accepted question: 1.45.

## 15. Ambiguity Measurements (Section 28)

- `Globus Pallidus`: selected 2/2 possible rounds this pilot; both accepted; but **round 3's acceptance came at a real cost, disclosed in full**: attempt 1 was the familiar generic-classification rejection (`"...all four answer choices are supported as they are all recognized components of the Basal Ganglia..."`); attempt 2 pivoted to a *functional-description* question (`"מהו תפקידו של ה-Globus Pallidus"` - "what is the role of Globus Pallidus") whose accepted correct answer is `"מדכא את התלמוס ומפחית תנועה"` ("suppresses the thalamus and reduces movement") - **a functional description, not the target's own name, in Hebrew, not English** - a live, direct instance of the exact, already-disclosed WP-040/043 known weakness ("target identity is currently strongly instructed, but not structurally guaranteed" - WP-043 architecture review section 13/18). Round 3's own deterministic alignment preclassification correctly flagged this: `NOT_ALIGNED`, `ascii_english=False`. **This is not a WP-045 regression** (no code changed) - it is a naturally-occurring instance of a pre-existing, already-known limitation, surfaced by this WP's own pilot and disclosed here rather than silently absorbed into a higher accepted-count.
- **A direct downstream consequence, also disclosed**: because round 3's accepted *answer text* was a functional description rather than `"Globus Pallidus"` itself, WP-038's coverage-identity matching (which tracks accepted answer text, not the target's own topic) did not recognize `Globus Pallidus` as tested - so round 4 selected `Globus Pallidus` again. Round 4 this time produced a genuinely target-identity-compliant accepted answer (`"Globus Pallidus"` itself, `ALIGNED`, ASCII-English) via a differently-phrased question. This one incident cleanly, concretely reproduces the general "an identity-violating accepted answer defeats coverage recognition and causes reselection" failure shape this project's docs have described abstractly since WP-037/038, now traced to one specific, real live instance.
- `Corticospinal Tract`: selected 2/2 possible rounds; round 3 exhausted (3/3 attempts rejected, every rejection explicitly naming a shared child as also-supported - see section 4); round 4 accepted on attempt 1 (the distractor-avoidance counter-example, section 4/9).
- Number of ambiguous candidates observed this pilot (rejected specifically for `other_answers_not_equally_correct=false` or the equivalent MCQ-multiple-plausible-answers reason): 4 (3 for `Corticospinal Tract` round 3, 1 for `Globus Pallidus` round 3 attempt 1, 1 for `Globus Pallidus` round 4 attempts 1-2 - 6 total across both targets this pilot).

## 16. Skip Measurements

**Zero targets were skipped by any new mechanism this WP (none was implemented).** WP-044's own pre-existing skip mechanisms (enumeration-shape insufficiency) remained active and correctly did not fire for either `Globus Pallidus` or `Corticospinal Tract` (confirmed: `evidence_shape=ORDINARY` for both in every round this pilot) - consistent with section 3/4's finding that neither target's own narrow anchor contains an enumeration-introduction cue phrase.

## 17. Target Alignment

**10/11 (90.9%)** among accepted questions - a real, disclosed shortfall from WP-044's own 8/8 (100%), entirely attributable to the single `Globus Pallidus` round-3 instance described in section 15. No other accepted question in this pilot showed a target-identity mismatch.

## 18. English-First Compliance

**10/11 (90.9%)** among accepted questions - the same single `Globus Pallidus` round-3 instance (a Hebrew functional-description answer) accounts for the one non-compliant case. WP-041's own mechanism (`format_target_language_requirement()`) was not modified and is not implicated - the accepted answer violated the *identity* requirement (WP-040), not the *language* requirement in isolation (a Hebrew description would also have been non-compliant had the answer correctly named the target in Hebrew, but that is not what happened here; the deeper issue is the description itself, not its language).

## 19. Concept Rotation

`אספקת דם`: 4/4 distinct - unchanged, best result to date. `גרעיני הבסיס`: 3/4 distinct (`Caudate Nucleus`, `Nucleus Accumbens`, `Globus Pallidus` - the last selected twice, rounds 3-4, for the coverage-recognition reason described in section 15, not target exhaustion). `מסילות עצביות`: 3/4 distinct (`Spinothalamic Tract`, `Corticobulbar/Corticonuclear Tract`, `Corticospinal Tract` - the last selected twice, rounds 3-4, since round 3 was never accepted so never entered coverage at all - the same "coverage is not the blocker; the concept just never gets accepted, so it keeps getting reselected" mechanism WP-043/044 already identified).

## 20. Failures and Limitations

**The central limitation of this WP is disclosed in full, not summarized away: no safe, general, deterministic ambiguity-prevention mechanism was found, despite a genuine, multi-angle investigation.** Three specific refinement attempts and their specific rejection reasons:

1. **Plain substring containment across the whole category inventory** (`has_named_child` as designed): correctly identifies both `Globus Pallidus` and `Corticospinal Tract`, but produces a confirmed false positive on `Inferior Cerebellar Artery (PICA)` (section 9) - **rejected**.
2. **Restricting the child search to the target's own originating chunk only**: would have avoided the `PICA` false positive (different chunks) but would have *also* missed `Corticospinal Tract`'s own genuine children, which come from a different chunk than `Corticospinal Tract`'s own selected occurrence (section 4) - **rejected, under-inclusive for the confirmed positive case**.
3. **Restricting matching to a closed vocabulary of Latin anatomical-subdivision qualifiers** (`Externus`/`Internus`/`Compacta`/`Reticulata`, excluding ordinary directional adjectives like `Anterior`/`Posterior`/`Lateral`): `Corticospinal Tract`'s own confirmed children use exactly the excluded directional-adjective category (`Anterior`/`Lateral Corticospinal Tract`), and the confirmed false positive (`Posterior inferior cerebellar artery`) uses the identical lexical category - **rejected, cannot distinguish the true and false positive with this vocabulary split, since both use the same word class**.

**Additionally disclosed**: `Globus Pallidus`'s dominant failure mode (broad classification ambiguity, 6/8 observed rejections) has **no candidate deterministic signal at all** that was found to distinguish it from its structurally-identical, reliably-successful siblings (`Caudate Nucleus`, `Nucleus Accumbens`) - this is a more fundamental gap than the `has_named_child` investigation above, and is the single most important open problem for the next WP to consider, more so than the parent/child shape (which at least has a confirmed, if currently unsafely-generalizable, structural explanation).

**Also disclosed (WP-045 section 32, source-role follow-up)**: the WP-044-discovered limitation of `extract_source_relationship_entity()` (operates on raw, unrepaired chunk text, can return a truncated downstream-entity name) was not investigated further this WP - it was not required by this WP's own ambiguity investigation (neither `Globus Pallidus` nor `Corticospinal Tract` involves `is_source_role`), and per section 32's own explicit instruction ("do not broaden WP-045 into a general source-role refactor unless the current ambiguity investigation requires it"), it remains a separate, still-open follow-up item for whichever future WP next touches `target_role.py`.

## 21. Source-Role Limitation (Section 21/32)

Not relevant to this WP's own findings beyond the acknowledgment in section 20 above - neither diagnosed target is a source-role target, and the limitation itself was not touched or investigated further.

## 22. Architectural Conclusion

WP-045's diagnosis phase (the WP's own explicitly primary deliverable, section 35: "the first deliverable... must be a fact-based diagnosis") produced three genuinely new, precise findings beyond what WP-044's architecture review anticipated:

1. `Globus Pallidus` and `Corticospinal Tract` do **not** share a common root cause - `Corticospinal Tract`'s failure is a confirmed parent/child hierarchy ambiguity; `Globus Pallidus`'s dominant failure mode is a broad classification ambiguity with no local structural differentiator from its successful siblings.
2. A textually well-justified, narrowly-targeted candidate signal for the parent/child shape (`has_named_child`) was designed, and rejected only after being tested directly against real corpus data and found to produce a confirmed false positive - the same "test broadly before finalizing" discipline this project's prior WPs (WP-039, WP-043) have already established as a hard requirement, applied here to an *investigation* rather than a shipped mechanism.
3. **A materially important, independently-confirming finding**: this WP's own fresh live pilot showed both previously-100%-failing targets succeed at least once, with the exact same, unmodified production code - direct, empirical evidence that whether the underlying evidence ambiguity is exposed as a live rejection depends substantially on the generator's own stochastic distractor choice for that specific attempt, not solely on a fixed property of the target's evidence. This materially weakens the case for *any* purely evidence-shape-keyed pre-generation skip for this problem family, beyond the specific false-positive already found - even a signal with zero false positives elsewhere would still incorrectly and permanently block genuinely-successful generation attempts like this pilot's own `Corticospinal Tract` round 4.

**No claim is made that the ambiguity problem is solved.** Acceptance improved this run (11/12 vs. WP-044's 8/12), but per this WP's own explicit primary success criterion (section 29: "A higher acceptance percentage alone is NOT sufficient"), this is **not** claimed as a WP-045 success - it is disclosed as unattributable to any change this WP made, alongside a real, concrete instance of a known, disclosed, unresolved target-identity weakness (section 15) that the higher acceptance number would otherwise obscure.

## 23. Recommendation for WP-046

1. **Do not pursue a pre-generation, evidence-shape-only skip mechanism for this ambiguity family** - this WP's own investigation found it either unsafe (false positives) or actively harmful (blocking genuinely-successful stochastic outcomes like `Corticospinal Tract` round 4). This is a settled negative finding for this specific approach, not merely an unexplored option.
2. **The more promising direction, suggested directly by section 4's own counter-example, is at the *distractor-selection* layer, not the pre-generation target-selection layer**: since `Corticospinal Tract`'s failures are consistently caused by a genuine child entity being offered as one of the four answer choices, investigate whether the *existing* competitor-discovery mechanism (`generation/competitors.py`, WP-031) or a new, narrow, deterministic post-generation check could flag "a candidate distractor's own text is contained within, or contains, the correct answer's own text" as a *specific*, structurally-justified signal - much narrower in scope than a general ambiguity classifier, and directly targeted at the confirmed mechanism (not the unconfirmed evidence-shape hypothesis).
3. **`Globus Pallidus`'s dominant classification-ambiguity failure mode remains genuinely unexplained at the deterministic-signal level** - a future WP should not assume this is the same problem as `Corticospinal Tract`'s (this WP explicitly found it is not) and should not attempt a fix for it without first finding a real, evidence-grounded structural differentiator from its successful siblings, which this WP's own thorough search did not find.
4. **Do not expand beyond the three pilot categories** - per WP-045 section 31's own explicit instruction, unaffected by this WP's acceptance number, since the underlying reliability question (is the 11/12 this run representative, or was 8/12 the more typical case, or is variance itself the finding) remains genuinely open.
5. **Preserve everything WP-044 built** - nothing was touched, nothing should be reverted; this WP is a pure diagnostic addition to the existing, unmodified architecture.

---

## Terminal Summary

```
WP-045 complete.

Diagnosis — Globus Pallidus: dominant failure mode (6/8 observed rejections) is broad classification/enumeration ambiguity with no evidence-shape differentiator found from its structurally-identical, reliably-successful siblings (Caudate Nucleus, Nucleus Accumbens); a minority failure (1/8) is a confirmed parent/child ambiguity with Globus Pallidus Externus/Internus

Diagnosis — Corticospinal Tract: confirmed parent/child hierarchy ambiguity - every rejection explicitly named a named child (Anterior/Lateral Corticospinal Tract) as also evidence-supported; whether this surfaces as a rejection depends on the generator's own stochastic distractor choice, confirmed by a live round-4 counter-example where the same target succeeded

Common structural pattern: NONE CONFIRMED - the two targets fail for different reasons; do not treat as one problem

Evidence ambiguity vs question ambiguity: both - genuine evidence-level ambiguity exists for Corticospinal Tract's general properties, but whether it is exposed as a rejection is additionally gated by generation-time distractor selection

Enumeration / classification / hierarchy: Globus Pallidus = classification (dominant) + hierarchy (minor); Corticospinal Tract = hierarchy (confirmed, primary)

Architectural decision: Outcome C - no safe deterministic signal found; a candidate signal (has_named_child) was designed, tested against real corpus data, and rejected after finding a confirmed false positive (Inferior Cerebellar Artery (PICA))

Implementation: none - no production code changed

Tests: 1379 passed, 0 failed (unchanged from WP-044, no new tests needed)

Acceptance: 11/12 (91.7%), up from WP-044's 8/12 - NOT attributed to any WP-045 change; evidence of genuine run-to-run stochastic variance, not a fix

Ambiguous candidates: 6 rejected attempts across both targets this pilot (3 Corticospinal Tract round 3, 1 Globus Pallidus round 3, 2 Globus Pallidus round 4)

Skipped targets: 0 (no new skip mechanism implemented)

Target alignment: 10/11 (90.9%) - one disclosed identity-violation instance (Globus Pallidus round 3), a live example of the already-known WP-040/043 target-identity weakness, not a WP-045 regression

English-first compliance: 10/11 (90.9%) - same single instance as target alignment

Concept rotation: אספקת דם 4/4, גרעיני הבסיס 3/4, מסילות עצביות 3/4 distinct targets

Regression status: 1379/1379 passed, schemas byte-identical, no source code touched

Architectural conclusion: diagnosis is complete and precise; the two targets do not share a root cause; a well-justified candidate fix was found unsafe upon direct empirical testing and correctly not deployed; higher acceptance this run is disclosed as unattributable stochastic variance, not claimed as a fix

Recommended WP-046: investigate a post-generation, distractor-text-containment check (narrower than evidence-shape prediction, targeted at the confirmed Corticospinal Tract mechanism) rather than any pre-generation evidence-shape skip; leave Globus Pallidus's dominant failure mode as an open, unexplained problem rather than force a speculative fix; do not expand beyond the three pilot categories

Completion report:
implementation/WP-045_COMPLETION_REPORT.md

Waiting for architect review.
```
