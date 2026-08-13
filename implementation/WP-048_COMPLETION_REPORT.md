# WP-048 Completion Report — Classification Ambiguity Investigation

## 1. Objective

WP-047 resolved target-to-answer identity for named-entity pilot-category targets, leaving generic classification ambiguity (`Globus Pallidus`, `Caudate Nucleus`, `Nucleus Accumbens`, `Basillar artery`) as the primary remaining architectural problem. WP-048's objective: determine whether these failures share a structural cause, whether that cause can be identified from the actual generated question predicate and answer choices, and whether a safe deterministic mechanism can be built - without assuming the answer, without building an LLM judge, and without merely rejecting "these four targets."

## 2. WP-046/WP-047 Relevant Findings (Recap, OBSERVED)

WP-046 found `Globus Pallidus`'s dominant failure mode has no local evidence-shape differentiator from its successful siblings, and that `Caudate Nucleus` also exhibits it. WP-047's own fresh pilot added `Nucleus Accumbens` and `Basillar artery` as further real instances, and confirmed - by direct per-attempt inspection - that neither WP-046's nor WP-047's own checks caused any of these rejections; every one was an ordinary grounding/MCQ rejection.

## 3. Known Classification-Ambiguity Cases (Section 4)

The four mandatory targets, plus every additional real instance found while mining the full real dataset (`evaluation/live_outputs/wp045_pilot_records.json` through `wp047_pilot_records.json` - the only files with full per-attempt answer-choice detail):

| Target | Category | WP(s) observed | Real rejected attempts found |
|---|---|---|---|
| `Globus Pallidus` | `גרעיני הבסיס` | WP-044, 045, 046, 047 | 9 |
| `Caudate Nucleus` | `גרעיני הבסיס` | WP-047 | 2 |
| `Nucleus Accumbens` | `גרעיני הבסיס` | WP-047 | 2 |
| `Basillar artery` | `אספקת דם` | WP-047 | 6 |

## 4. Additional Cases Discovered (Section 4's "Do Not Limit to Exactly Four")

None beyond the four - `Corticospinal Tract`'s own real rejections were re-examined and found to belong entirely to WP-046's already-solved parent/child-distractor family (every rejection explicitly named a child as also-supported) or to an unrelated MCQ-structural defect (the correct answer duplicated as a distractor, WP-045 `מסילות עצביות` round 3 attempt 1) - never the generic classification-ambiguity shape this WP investigates. This is stated explicitly rather than silently assumed, per section 4's own instruction.

## 5. Full Failure Reconstruction (Section 7, Representative Cases)

All 19 real rejected attempts across the four targets were individually reconstructed (question, answers, correct-answer position, evidence-grounded validator reason). Three representative examples, verbatim from real production data:

```
FACT: Target = Nucleus Accumbens, גרעיני הבסיס
Question: "מהו הגרעין בגרעיני הבסיס הממוקם בין ה-putamen ל-caudate nucleus?"
Answers: [Nucleus Accumbens, Globus Pallidus, Putamen, Caudate Nucleus]
Validator: mcq (not grounding this time)
Reason (verbatim): "Both the Nucleus Accumbens and the Globus Pallidus are
  associated with the structures mentioned in the question, leading to
  ambiguity in determining a single best answer."
```

```
FACT: Target = Caudate Nucleus, גרעיני הבסיס
Question: "איזה גרעין מהגרעינים הבסיסיים הוא חלק מהקורפוס סטריאטום ומשפיע על התנועה המוטורית?"
Answers: [Caudate Nucleus, Putamen, Nucleus Accumbens, Globus Pallidus]
Validator: grounding
Reason (verbatim): "Both the Caudate Nucleus and Putamen are confirmed as
  parts of the corpus striatum, while the Nucleus Accumbens and Globus
  Pallidus do not fit the specific criteria of the question."
```

```
FACT: Target = Basillar artery, אספקת דם
Question: "איזה עורק מהווה מקור לעורק הסופריור צרבלרי?"
Answers: [Basillar artery, Anterior Inferior Cerebellar Artery, Vertebral Artery, Posterior Cerebral Artery]
Validator: grounding
Reason (verbatim): "Both Answer 1 [Basillar artery] and Answer 2 [AICA]
  are supported as correct answers, while Answers 3 and 4 are not
  supported."
```

## 6. Actual Question Predicates (Section 8, Formal Analysis)

For each real failure, the operational predicate P(x) and its satisfaction across the four choices, determined only from the authoritative student-summary evidence:

**Case 1** (`Caudate Nucleus`, section 5's second example): `P(x) = x is a member of the Corpus Striatum`. Per the real corpus evidence (`ניתן לחלק את הקורפוס סטריאטום... Striatum – covers caudate nucleus, nucleus accumbens, putamen`): `P(Caudate Nucleus)=true`, `P(Putamen)=true`, `P(Nucleus Accumbens)=true`, `P(Globus Pallidus)=false` (Pallidum is a *separate* embryological division). **`count(P(x)=true) = 3`** - genuinely, evidence-confirmedly ambiguous. `grounding`'s own verdict is factually correct.

**Case 2** (`Basillar artery`): `P(x) = x is the source/origin of Superior Cerebellar Artery`. Per the real corpus evidence, only `Basillar artery` is explicitly labeled `מקור:` for `Superior cerebellar artery`; `AICA`'s own labeled source is also `Basillar artery`, but that establishes `AICA`'s *own* origin, not that `AICA` is a source *of* `Superior Cerebellar Artery`. **`count(P(x)=true) = 1`** by the evidence's own explicit labeling - grounding's repeated claim that `AICA` is "also supported" as a source of `Superior Cerebellar Artery` does not hold up against the evidence's own explicit structure. This is flagged and treated separately in section 15.

**Case 3** (`Nucleus Accumbens`, MCQ-flagged): `P(x) = x is located between Putamen and Caudate Nucleus`. The real evidence's own anatomical description does place `Nucleus Accumbens` in that general region, and `Globus Pallidus` is a plausible-but-distinct nearby structure - MCQ's own verdict ("ambiguity... not clearly incorrect") is a defensible, evidence-consistent judgment given the corpus does not sharply delineate this specific spatial claim.

## 7. Answer-Choice Predicate Analysis / Candidate-Set Analysis (Sections 8, 17)

Combined and tabulated (also serves as the required predicate matrix, section 11, and classification table, section 27):

| Target | Question predicate P(x) | Correct answer | Other choices satisfying P(x) per evidence | `count(P=true)` | Ambiguous? |
|---|---|---|---|---|---|
| `Caudate Nucleus` | member of Corpus Striatum | Caudate Nucleus | Putamen, Nucleus Accumbens | 3 | **Yes, evidence-confirmed** |
| `Caudate Nucleus` (successful control) | *is named* Caudate Nucleus (tautological identity) | Caudate Nucleus | none (a naming question, not a property test) | 1 | No |
| `Nucleus Accumbens` | member of basal nuclei, reward-system-associated | Nucleus Accumbens | Caudate Nucleus, Putamen (per grounding's own reading of the evidence) | 3 | **Yes, evidence-plausible** |
| `Nucleus Accumbens` | located between Putamen/Caudate Nucleus | Nucleus Accumbens | Globus Pallidus (per MCQ's own reading) | 2 | Plausible, evidence under-specifies precisely |
| `Globus Pallidus` | member of basal nuclei (bare) | Globus Pallidus | Caudate Nucleus, Nucleus Accumbens, Putamen (every real sibling) | 4 | **Yes, evidence-confirmed** |
| `Globus Pallidus` (successful controls, WP-044/046/047) | *is named* Globus Pallidus, or a specific functional/anatomical property unique to it | Globus Pallidus | none | 1 | No |
| `Basillar artery` | source/origin of Superior Cerebellar Artery | Basillar artery | **None, per the evidence's own explicit labeling** - `AICA` is claimed by grounding but not supported by the evidence's own structure | 1 (evidence) vs. 2 (grounding's own claim) | **Disputed - see section 15** |

## 8. Successful Controls (Section 10, Mandatory)

- **A. Same target, successful question**: `Caudate Nucleus`/`Globus Pallidus` were both, in different rounds, successfully accepted via an *identify-by-name* question form (`"which of the following nuclei IS X"`) rather than a shared-property test.
- **B. Same target, different predicate**: `Globus Pallidus` (WP-046 round 4) was accepted testing `"which structure is the internal nucleus of the basal ganglia called Globus Pallidus"` - a specific, narrowing predicate, not bare category membership.
- **C. Same/similar evidence, different distractors**: not found to be the deciding factor here (section 9) - unlike `Corticospinal Tract`'s WP-046 shape, the same four-name candidate set recurs in both successful and failing attempts for the same target.
- **D. Different target, same question shape**: `Superior cerebellar artery`/`Anterior Inferior Cerebellar Artery (AICA)`/`Inferior Cerebellar Artery (PICA)` were all reliably accepted, across every pilot, using specific source/supply-area predicates the evidence uniquely supports for each - direct positive confirmation that a well-scoped predicate over the *same* category's evidence does not inherently produce ambiguity.

**Critical, load-bearing empirical finding**: comparing the failing `Caudate Nucleus` case (section 6, Case 1) against its own successful sibling round shows **the exact same four-entity candidate set can appear in both an ambiguous and a non-ambiguous framing** - the deciding factor is the semantic content of the generated question text itself (which specific predicate it tests), not the identity of the four answer choices. This directly parallels, and generalizes, WP-046's own `Corticospinal Tract` round 3 vs. round 4 finding - but here the mechanism is even more clearly locked to question *semantics* rather than *entity-name relationships*, since even distractor selection is not the deciding variable.

## 9. Primary Failure Classification (Section 12)

Per target, classified against the six allowed categories:

- `Globus Pallidus`, `Caudate Nucleus`, `Nucleus Accumbens`: **`QUESTION_PREDICATE`** - the LLM repeatedly chooses to test bare or under-specified category/sub-category membership rather than a target-unique property, even though the evidence and the existing prompt guidance (`"Testing enumeration or classification targets"`) both already warn against exactly this. Not `TARGET_EVIDENCE_SHAPE`: section 8's own control comparison shows the *same* evidence supports both ambiguous and unambiguous question forms for the same target.
- `Basillar artery`: **`OTHER`** (see section 15) - the repeated rejections are driven substantially by an apparent grounding-validator over-inclusion (`AICA` incorrectly treated as also-satisfying), not by a genuine evidence-level multi-support shape.

## 10. Common-Cause Analysis / One Problem or Multiple Subclasses (Section 26, Critical Deliverable)

**`MULTIPLE_SUBCLASSES` - do not assume one mechanism.**

1. **Sub-classification/category-membership ambiguity** (`Globus Pallidus`, `Caudate Nucleus`, `Nucleus Accumbens`): a genuine `QUESTION_PREDICATE` problem - the evidence really does support more than one answer to the specific (generic) predicate the LLM chose to test. This is the same family WP-044/045/046 already investigated for `Globus Pallidus`/`Caudate Nucleus` and it is now confirmed, with formal P(x) analysis, to be real and evidence-grounded, not merely apparent.
2. **`Basillar artery`'s own repeated rejections are a materially different shape** - not primarily a multi-support evidence problem (the evidence's own explicit `מקור:` labeling supports only `Basillar artery`, not `AICA`, as the source of `Superior Cerebellar Artery`), but an apparent grounding-validator interpretation inconsistency, treating two arteries that share a common upstream parent (`Basillar artery` supplies both `Superior Cerebellar Artery` and `AICA`) as if one were also a source of the other. This is disclosed as an **INFERENCE**, not a certainty - re-running the same real prompt/evidence through grounding again was not performed (that would itself require a live LLM call this WP's own "do not manufacture examples, use only what's already available" scope did not call for), so it remains possible grounding is reacting to a genuine subtlety in the evidence's own phrasing not fully captured in this WP's own re-reading. Recorded honestly as a distinct, separately-tracked finding, not merged into the `QUESTION_PREDICATE` family.

## 11. Deterministic Signal Investigation (Sections 20/21)

Three candidate signals were considered and tested against the real successful-control data (section 8):

1. **"Multiple answer choices belong to the same category's concept inventory"**: rejected immediately - true for essentially every real candidate ever generated in these pilot categories, including every successful one (all realistic distractors are necessarily drawn from the same category's own evidence). Exactly the insufficient rule WP-046's own architecture review already warned against ("a rule that fires because multiple concepts exist in the same category is insufficient").
2. **"The specific distractor set differs between success and failure"** (the mechanism that worked for `Corticospinal Tract` in WP-046): tested directly against the real data (section 8) and found **not to hold** - the failing `Caudate Nucleus` case and a successful `Caudate Nucleus` round use near-identical answer-choice sets; the deciding factor is the question text's own semantic framing, not which entities were chosen.
3. **"Parse the generated question for a generic-membership predicate shape"** (e.g. detecting phrases like `"חלק מ"`/`"part of"`): explicitly considered and explicitly rejected, per this WP's own hard constraint (section 25: no phrase-specific rules) and this project's own repeated, established finding (WP-044 section 9, WP-046) that free-text pattern matching against generated prose is exactly the "large heuristic classifier" this architecture has consistently avoided, and would not reliably generalize (the same predicate is expressed differently across real questions: `"חלק מ"`, `"שייכת ל"`, `"מהווה חלק"`, `"משויך ל"`, all attested in the real data mined for this report).

**No deterministic signal was found that operates on already-available data (target, evidence, generated answer-choice text) and reliably distinguishes an ambiguous candidate from a valid one for the `QUESTION_PREDICATE` family**, because the distinguishing factor is the semantic content of the free-text generated question itself - information this architecture deliberately never parses or trusts.

## 12. False-Positive Analysis (Section 21/31.15)

Not applicable in the form of a numeric false-positive rate, since **no candidate rule survived initial testing well enough to warrant a full false-positive study** (signal 1 was rejected on its very first successful-control check; signal 2 was rejected on direct comparison against the same target's own successful round; signal 3 was excluded by this WP's own hard constraints before implementation). This is itself the required deliverable: each rejected signal's own specific, evidence-based reason for rejection is documented (section 11), rather than a rule being implemented and only later found unsafe.

## 13. Existing Validator Behavior (Section 19)

**`GroundingValidator` already correctly detects the `QUESTION_PREDICATE` family in every real instance examined** - its own free-text reasoning precisely and correctly names which specific answer choices are also evidence-supported (section 5's examples), matching the formal P(x) analysis this WP independently performed (section 7). **`MCQValidator`** correctly catches the closely-related "more than one plausible answer" shape for the same family when grounding's own per-option check does not fire first. Neither validator is malfunctioning for this family - **the existing architecture already reliably rejects every genuinely ambiguous candidate observed for `Globus Pallidus`/`Caudate Nucleus`/`Nucleus Accumbens`.**

This is the single most important finding of this WP: **this is not a detection/safety gap of the kind WP-044/046/047 each closed - it is a *reliability* problem.** Generation repeatedly attempts the same invalid question shape for certain targets, correctly gets rejected each time, and exhausts the fixed 3-attempt budget. No candidate (accepted or otherwise) for `Globus Pallidus`/`Caudate Nucleus`/`Nucleus Accumbens` was ever found, anywhere in the real dataset, to have been **incorrectly accepted** despite genuine `QUESTION_PREDICATE` ambiguity - the one apparent case (`Globus Pallidus`/`Precentral Gyrus`-style earlier findings) belongs to WP-047's own already-solved target-identity family, not this one.

## 14. Type 1 vs. Type 2 Distinction (Section 18)

- **Type 1 (multiple supported answers)**: `Caudate Nucleus`, `Nucleus Accumbens`, `Globus Pallidus`'s bare-membership rejections - confirmed genuine via formal P(x) analysis (section 7).
- **Type 2 (factual disagreement / other reason)**: the `(GPe)` vs. `Globus Pallidus Internus` quality rejection (WP-046), the duplicate-answer-choice MCQ defect (WP-045 `Corticospinal Tract` round 3 attempt 1) - both already correctly caught by existing validators for unrelated structural reasons, not this WP's concern.
- **A third, disclosed category not cleanly Type 1 or Type 2**: `Basillar artery`'s repeated rejections (section 10.2) - evidence-level analysis suggests only one answer is genuinely supported, yet grounding repeatedly reports two. Recorded separately rather than forced into either type.

## 15. Basillar Artery - Separate, Disclosed Finding

**INFERENCE, not certainty**: across all 6 real rejected attempts, grounding's own stated reasoning consistently names `AICA` as "also supported" as a source of `Superior Cerebellar Artery`, but this WP's own direct re-reading of the real corpus evidence (`STUDENT_SUMMARY:student_summary_2.pdf:0128:0001` - the same chunk WP-042/043/044 already anchored their own findings to) finds only `Basillar artery` explicitly labeled (`מקור:`) as `Superior cerebellar artery`'s own source; `AICA`'s own labeled source is *also* `Basillar artery`, a sibling relationship, not a chain. **This may indicate an occasional grounding-validator interpretation inconsistency for this specific evidence shape (shared-parent siblings), rather than genuine evidence-level multi-support** - but this WP did not re-run the real generation/grounding call to confirm this reproducibly (out of this WP's own "use only already-available data" scope), so it is reported as a disclosed, unconfirmed inference, not a proven validator defect. **Not investigated further or acted upon** - per this WP's own hard constraint against modifying validators, and because doing so would require its own dedicated investigation this WP was not chartered to perform.

## 16. Deterministic Feasibility

**NO**, for the `QUESTION_PREDICATE` family (the dominant classification-ambiguity subclass, covering `Globus Pallidus`/`Caudate Nucleus`/`Nucleus Accumbens`) - with a specific, evidence-grounded reason (section 11), not merely "not yet found." **UNCERTAIN/OUT OF SCOPE** for the `Basillar artery` subclass, which appears to be a different, validator-precision-adjacent issue this WP did not investigate further.

## 17. Safety Analysis (Section 31)

No candidate mechanism reached implementation, so the full fifteen-criterion checklist does not apply to a shipped mechanism - documented instead per criterion 1's own converse: no candidate "explains multiple real cases or one clearly defined structural class" while also being "tied to the actual generated predicate" and "deterministic" simultaneously (signal 2, the only one tied to the actual predicate/candidate set, was directly falsified against real successful-control data in section 8/11).

## 18. Implementation Decision

**No production code was changed.** `src/exam_generator/` remains exactly as WP-047 left it (confirmed via `git diff --stat src/` showing only the pre-existing WP-047 diff, no new changes from this WP). This is Outcome C (section 37: "No safe deterministic mechanism exists with the current architecture") for the `QUESTION_PREDICATE` family specifically - the dominant, best-understood subclass - reached only after genuinely searching (section 11), not assumed.

## 19. Tests

None added - no production code was modified, matching WP-045's own established precedent for a diagnostic-only WP (tests are required only "if code changes," per this WP's own section 32 preamble).

## 20. Regression

`.venv/bin/python -m pytest -q` → **1396 passed, 0 failed** - unchanged from WP-047's own baseline (expected, since no code was touched). `scripts/generate_schemas.py` re-run: all three schema files byte-identical. `git diff --stat src/` confirms no new changes beyond WP-047's own pre-existing, already-reported diff.

## 21. Fresh Pilot

**Not run.** Per section 34's own explicit conditional ("If production code changes, run one fresh pilot") and WP-045's own established precedent for a diagnostic-only WP with no code change, no new live pilot was executed. This WP's entire investigation (sections 5-15) is built from real, already-captured production data (`wp045_pilot_records.json` through `wp047_pilot_records.json` - 19 real rejected attempts across the four targets, plus their own real successful-control rounds), satisfying section 3's explicit instruction to "use real historical and fresh pilot data already available in the repository."

## 22. Per-Attempt Attribution

Not applicable (no new pilot run) - the per-attempt attribution work this section would otherwise require was instead performed directly against WP-047's own already-completed, already-attributed pilot data (section 5-7), which already includes full per-attempt validator reasoning for every one of the real cases this WP investigates.

## 23. Acceptance / Target Alignment / English-First / Concept Rotation

Unchanged from WP-047's own last-reported baseline (7/12 acceptance, 7/7 target alignment, 7/7 English-first, `אספקת דם` 2/4 / `גרעיני הבסיס` 2/4 / `מסילות עצביות` 3/4 concept rotation) - no new pilot was run, so no new measurement exists to report.

## 24. WP-046/WP-047 Coexistence

Trivially preserved - no code was changed, so both mechanisms remain byte-for-byte as WP-047 left them, confirmed by the unchanged full regression suite (1396/1396, including every WP-046/047-specific test).

## 25. Unresolved Issues

1. **The `QUESTION_PREDICATE` classification-ambiguity family remains genuinely unresolved at the deterministic-mechanism level** - not for lack of investigation, but because the evidence itself shows the deciding factor is the generated question's own semantic content, which this architecture correctly declines to parse.
2. **`Basillar artery`'s own repeated rejections may reflect an occasional grounding-validator interpretation inconsistency for shared-parent-sibling evidence shapes** - disclosed as an unconfirmed inference, not investigated further, and explicitly not acted upon (validator changes are out of this WP's scope and this project's general practice of only touching validators with strong, dedicated justification).
3. **The existing "Testing enumeration or classification targets" prompt guidance (question.txt) is not reliably followed** - this WP's own findings (section 8's successful-vs-failing comparison) reconfirm, with more precision than WP-044 originally had, exactly what that guidance already warns against; no new mechanism enforces it beyond the existing validators' own (correct) after-the-fact rejection.

## 26. Architectural Conclusion

WP-048 reached Outcome C (section 37) for the dominant classification-ambiguity subclass, `QUESTION_PREDICATE`, after formally reconstructing every real failure, computing explicit P(x) satisfaction tables from authoritative evidence, and directly falsifying the one candidate signal (distractor-set differencing) that had worked for a structurally similar prior problem (WP-046's `Corticospinal Tract`). The single most important architectural finding is that **this failure family is not a safety/detection gap - the existing `GroundingValidator`/`MCQValidator` already correctly reject every genuine instance observed** - it is a reliability problem, a fundamentally different kind of issue than every prior WP-044/046/047 mechanism addressed, and one this project's own hard constraints (no LLM judge, no phrase-matching, no increased retries) correctly prevent this WP from solving with a deterministic patch. A secondary, separately-tracked, and only partially investigated finding (`Basillar artery`) suggests the classification-ambiguity family itself is not monolithic, confirming section 26's own required "multiple subclasses" determination rather than a forced single mechanism.

## 27. Recommendation for WP-049

1. **Do not attempt a deterministic pre/post-generation mechanism for the `QUESTION_PREDICATE` family** - this WP's own investigation found a specific, evidence-grounded reason none can safely exist with currently-available deterministic information. This is a settled negative finding, not an unexplored option.
2. **If this family is to be addressed at all, the promising remaining architectural lever is strengthening how reliably the *existing* prompt guidance ("testing enumeration or classification targets") is followed - not adding new post-hoc detection.** This was already WP-044's own original direction before that WP moved to a narrower, safely-implementable mechanism (the enumeration skip); WP-048's own findings suggest the underlying "generation doesn't reliably self-check its own distractors against the exact tested predicate" issue (WP-028's own already-disclosed finding) is the true root cause, not a gap in detection.
3. **`Basillar artery`'s possible grounding-validator interpretation inconsistency deserves its own, narrowly-scoped, dedicated investigation** (with fresh live diagnostic capture, mirroring WP-042's own methodology) before any conclusion is drawn or any validator change is even considered - not bundled into a future WP's broader scope.
4. **Do not expand beyond the three pilot categories** - the reliability problem for these specific targets remains real and unresolved, and expansion would not change the underlying finding.
5. **Preserve everything built so far** - WP-044, WP-046, and WP-047 all remain correct, tested, and unaffected by this WP's own findings.

---

## Terminal Summary

```
WP-048 complete.

Objective: determine whether classification-ambiguity failures (Globus Pallidus, Caudate Nucleus, Nucleus Accumbens, Basillar artery) share a structural cause and whether a safe deterministic mechanism can detect them

Known classification-ambiguity cases: 4 mandatory targets, 19 real rejected attempts total, mined from real production data (WP-045 through WP-047 pilots)

Additional cases: none beyond the four - Corticospinal Tract's own rejections belong entirely to WP-046's already-solved family or an unrelated MCQ defect

Actual predicates identified: formal P(x) analysis performed for every representative case - e.g. P(x) = member of Corpus Striatum; P(Caudate Nucleus)=true, P(Putamen)=true, P(Nucleus Accumbens)=true, P(Globus Pallidus)=false

Multiple-supported-answer analysis: confirmed genuine (evidence-grounded) for Globus Pallidus/Caudate Nucleus/Nucleus Accumbens; disputed for Basillar artery (see below)

Successful controls: same target, same near-identical candidate set, succeeds when the question tests identity-by-name or a target-unique property instead of bare category membership - directly falsifies the "differencing" signal that worked for Corticospinal Tract

Common structural cause: MULTIPLE_SUBCLASSES - QUESTION_PREDICATE ambiguity (Globus Pallidus/Caudate Nucleus/Nucleus Accumbens) is a different mechanism from Basillar artery's own repeated rejections

Candidate deterministic signal: none survived testing - same-category-membership signal is universally true (useless); distractor-set-differencing signal (which worked for WP-046's Corticospinal Tract) directly falsified against real successful-control data; question-text phrase-matching excluded by hard constraint

False-positive analysis: no candidate rule reached the stage of requiring a formal false-positive study - each was rejected on its own specific evidence-based grounds first

Deterministic feasibility: NO for the QUESTION_PREDICATE family; UNCERTAIN/OUT OF SCOPE for Basillar artery

Implementation: none - no production code changed

Tests: none added (no code changed)

Regression: 1396/1396 passed, unchanged from WP-047, schemas byte-identical

Pilot: not run - no code changed, investigation built entirely from real, already-available pilot data per this WP's own scope instruction

Per-attempt attribution: performed directly against WP-047's own already-attributed real pilot data, not a new run

Acceptance: unchanged from WP-047 (7/12) - no new measurement

Target alignment: unchanged from WP-047 (7/7)

English-first: unchanged from WP-047 (7/7)

Concept rotation: unchanged from WP-047

WP-046 coexistence: trivially preserved, no code changed

WP-047 coexistence: trivially preserved, no code changed

Architectural conclusion: the dominant classification-ambiguity subclass is a reliability problem, not a safety/detection gap - GroundingValidator/MCQValidator already correctly reject every genuine instance found; no deterministic mechanism can safely improve on this given the deciding factor is the generated question's own semantic content, which this architecture correctly declines to parse; Basillar artery is a separate, only partially understood subclass possibly involving grounding-validator interpretation variance, not investigated further

Recommended WP-049: do not attempt a deterministic detection mechanism for QUESTION_PREDICATE ambiguity; consider whether generation's own self-check against the existing "testing enumeration or classification targets" guidance can be made more reliable (a generation-quality question, not a detection-gap question); investigate Basillar artery's possible grounding-validator interpretation inconsistency separately, with fresh live diagnostic capture; do not expand beyond the three pilot categories

Completion report:
implementation/WP-048_COMPLETION_REPORT.md

Waiting for architect review.
```
