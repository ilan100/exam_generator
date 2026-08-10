# Architecture Review — WP-039

**Review Date:** 2026-08-10  
**WP Reviewed:** WP-039 — Deterministic Trailing-Truncation Recovery  
**Status:** **ACCEPTED — TARGETED PROBLEM SOLVED, BUT A NEW GENERATION-LEVEL BOTTLENECK IS NOW CLEARLY VISIBLE**

## 1. Executive Summary

WP-039 is accepted.

It successfully solved the specific problem it was designed to solve: trailing-truncated concept identities are now repaired or safely excluded at the extraction layer instead of contaminating planning and coverage.

The implementation is correctly located in `planning/concept_anchor.py`, preserves public contracts, does not modify generation or validation, and passes the complete regression suite: **1304/1304**. The report confirms that QuestionGenerator, QuestionProducer, OpenAIProvider, validators, WP-037 anchoring, and WP-038 ConceptIdentity/coverage remain unchanged. fileciteturn23file0L5-L6 fileciteturn23file0L99-L103

The live pilot achieved **11/12 accepted questions**, exactly matching the WP-036 baseline and improving over WP-037's 8/12 and WP-038's 10/12. fileciteturn23file0L120-L130

Most importantly, WP-038's truncation failure was independently reproduced after the fix: `Anterior Corticospinal Tract` and `Corpos Striatum` are now complete concepts and coverage correctly excludes them after they have been tested. fileciteturn23file0L134-L144

However, WP-039 also makes the next major bottleneck clear:

> **The current binding problem is now generation alignment/framing, not extraction.**

The live pilot achieved only **5/11 (~45%) manual target alignment**. The report carefully attributes this to pre-existing generation drift and functional-answer drift rather than to WP-039 itself. fileciteturn23file0L146-L170

---

## 2. Overall Assessment

| Area | Assessment |
|---|---|
| Scope discipline | Excellent |
| Architectural ownership | Excellent |
| Deterministic extraction | Strong |
| Safety / fail-closed behavior | Strong |
| Regression discipline | Excellent |
| Primary WP objective | Achieved |
| Target alignment | Still inadequate |
| Coverage | Improved for extracted concepts, known cross-script gap remains |
| Architectural learning | Excellent |

**Overall assessment: 9.5 / 10**

---

## 3. WP-039 Objective Was Achieved

The WP correctly moved the repair to:

```text
Evidence
    ↓
Concept Extraction
    ↓
Concept Quality / Completeness
    ↓
Concept Identity
    ↓
Coverage
```

rather than making coverage understand malformed concepts.

That ownership decision is correct.

The implementation added the trailing-recovery pass as an additive final stage and deliberately left generation, validators, WP-037 anchoring, and WP-038 identity/coverage unchanged. fileciteturn23file0L5-L6

---

## 4. Root Cause Was Properly Established

The report inspected the actual raw evidence and found that the missing pieces were physically separated in extracted PDF text, for example:

```text
Corpos Str
    +
ia
    +
tum
```

and:

```text
Anterior Corticospinal T
    +
ract
```

The root cause was identified as the existing PDF bidi extraction behavior in mixed Hebrew/English text, rather than chunking, heading parsing, or punctuation. fileciteturn23file0L9-L21

This gives strong confidence that the fix addresses the actual source of the problem.

---

## 5. Detection and Reconstruction Are Appropriately Conservative

The detection rule uses pure ASCII, lowercase-starting neighboring lines, existing extraction characteristics, and bounded searches. The investigation covered all 139 raw concepts in the three pilot categories. fileciteturn23file0L23-L31

The reconstruction policy is also correct:

```text
no evidence
    → keep unchanged

one valid direction
    → repair

one direction but invalid result
    → exclude

both directions
    → exclude
```

This correctly preserves the rule:

> Never guess.

The bounded scan and fragment limits are appropriate. fileciteturn23file0L35-L54

---

## 6. The Cross-Concept Consumption Fix Is Important

A real development bug was found where fragment lines could be reused by another concept after a failed reconstruction.

The resulting bad concept was:

```text
NSp.)rs Reticulata (a
```

The fix marks discovered fragment lines as consumed even when reconstruction fails.

This is excellent defensive design and should remain a regression invariant. fileciteturn23file0L56-L59

---

## 7. Real-Data Impact

Across 139 raw concepts:

- 115 required no repair;
- 3 were already handled by leading truncation;
- 12 trailing repairs were found;
- 11 remained after deduplication;
- 2 were excluded as ambiguous/malformed. fileciteturn23file0L105-L118

This demonstrates that WP-039 handles a genuine class of extraction artifacts rather than only the two motivating examples.

---

## 8. Important Caveat: One False Repair Exists

The implementation produced:

```text
Deep Brain Stimulati
    ↓
Deep Brain Stimulatino D(SB.)
```

which is semantically wrong.

The report is transparent about this. fileciteturn23file0L185-L190

This does not invalidate WP-039, but it prevents us from calling the extraction mechanism universally safe.

The correct architectural boundary remains:

> deterministic structural recovery of missing fragments is allowed; semantic correction of corrupted fragments is not.

We should not turn this component into a general OCR/error-correction engine merely to eliminate this one residual case.

---

## 9. Primary Success Criterion Was Verified

The live run did not happen to produce the exact fifth-round situation needed to observe the coverage loop directly.

Instead, WP-038's exact failure case was reproduced offline after WP-039:

```text
Anterior Corticospinal Tract
```

is now correctly recognized by coverage as already tested.

The same was verified for:

```text
Corpos Striatum
```

This directly demonstrates that the truncation-induced coverage loop has been removed. fileciteturn23file0L134-L144

---

## 10. Reliability Recovered

The live pilot achieved:

```text
11/12 accepted = 91.7%
```

matching WP-036.

The one failure was identified as ordinary existing WP-013 attempt exhaustion rather than a truncation failure. fileciteturn23file0L179-L181

This is a strong result.

---

## 11. Diversity Is Still Not Solved

The live selections show:

### אספקת דם

```text
Superior cerebellar artery
        ↓
Basillar artery
        ↓
Basillar artery
        ↓
Basillar artery
```

### גרעיני הבסיס

```text
Corpos Striatum
        ↓
Corpos Striatum
        ↓
Corpos Striatum
        ↓
Corpos Striatum
```

### מסילות עצביות

```text
Spinothalamic Tract
        ↓
Medial Lemniscus Tract
        ↓
Medial Lemniscus Tract
        ↓
Anterior Corticospinal Tract
```

The third category demonstrates that the architecture can rotate concepts successfully. The first two expose remaining generation/coverage-loop problems. fileciteturn23file0L173-L177

---

## 12. Target Alignment Is Now the Binding Problem

The manual alignment result was:

```text
5/11 ≈ 45%
```

This is materially worse than WP-037's 87.5%.

However, the report gives strong causal evidence that this was not caused by WP-039:

1. `אספקת דם` had zero WP-039 repairs, so its generation drift cannot be attributed to the extraction change.
2. `גרעיני הבסיס` repeats the same functional-description drift already observed for the same concept in WP-037. fileciteturn23file0L164-L170

I agree with that causal analysis.

But from the system's perspective, the important conclusion is:

> **The generated answer is not reliably expressing the assigned target.**

That is now the next architectural problem.

---

## 13. Named Concepts vs. Functional Answers

The most revealing examples are:

```text
Selected:
Corpos Striatum

Answer:
"involved in executing planned motor movements"
```

and:

```text
Selected:
Medial Lemniscus Tract

Answer:
"advanced sensations"
```

These answers may be related to the selected concept, but they do not demonstrate that the generated question is testing the selected named concept.

The generator is sometimes choosing a **property/function of the concept** instead of the concept itself.

That undermines deterministic concept rotation.

---

## 14. Recommended Next WP

The next WP should be:

# WP-040 — Target-Answer Framing for Named Concepts

Objective:

> When the deterministic planner selects a named anatomical structure, tract, artery, nucleus, or similar named entity, generation should produce a question whose correct answer identifies that target rather than merely describing one of its properties or functions.

This is now a **generation-contract/prompt problem**, not an extraction problem.

---

## 15. Why This Is the Correct Next Layer

The project has progressively isolated the problem:

```text
WP-025
Generation diversity problem
        ↓
WP-036
Deterministic concept selection
        ↓
works
WP-037
Concept-anchored evidence
        ↓
alignment improves
WP-038
Concept identity
        ↓
same-language identity robust
WP-039
Trailing truncation
        ↓
concept inventory cleaned
```

What remains:

```text
Selected concept
        ↓
Question generation
        ↓
Answer actually identifies selected concept?
        ↓
NOT RELIABLE ENOUGH
```

That is now the correct place to work.

---

## 16. WP-040 Should NOT Be a Validator

Do not solve this primarily as:

```text
generate
    ↓
target mismatch validator
    ↓
retry
```

That would recreate the architecture we have deliberately avoided.

It would consume the bounded generation budget and could cause many questions to fail before producing useful partial results.

Instead:

> **Change how the question is generated in the first place.**

The generation contract should explicitly distinguish a named target from a target whose intended answer is a function, relationship, or other property.

---

## 17. Do Not Overconstrain All Questions

We should not globally require every question to answer with a named entity.

Educational questions can legitimately target:

- function;
- relationship;
- clinical significance;
- pathway;
- mechanism.

The stricter target-answer rule should apply when the deterministic planner selected a **named entity concept**.

This preserves educational diversity while protecting target alignment.

---

## 18. WP-040 Investigation Requirements

Before changing prompts, Claude should inspect:

1. How the selected target is currently passed to the LLM.
2. Whether target type is already available.
3. Whether the target can be deterministically classified as:
   - named entity;
   - function;
   - relationship;
   - other.
4. Whether the current generation prompt contains contradictory or permissive wording.
5. Why the LLM can legally return a functional description when a named concept was selected.

Only then should the prompt/generation contract be changed.

---

## 19. Validation Must Not Be Impacted

This is critical.

The change should make questions **more likely to be valid before validation**, not cause validation rejection to increase.

Measure together:

```text
target alignment
+
acceptance rate
+
generation attempts
```

Success is not merely higher alignment if it comes at the cost of significantly more validation failures.

---

## 20. Proposed WP-040 Success Criteria

### Primary

Substantially increase manual target alignment for named concepts.

### Secondary

No material degradation in:

- acceptance;
- generation attempts;
- MCQ validity;
- grounding;
- textbook validation.

### Diversity

Sequential questions should actually move to different selected concepts.

### Safety

No semantic/fuzzy matching.

---

## 21. Cross-Script Coverage Remains Open

WP-038's cross-script coverage limitation remains.

WP-039 did not solve it, and it was not supposed to.

However, it should not be addressed before target-answer framing.

The correct order is:

```text
1. Make generation answer the selected target.
2. Measure remaining coverage failures.
3. Decide whether cross-script handling is still materially blocking rotation.
```

If generation itself is not reliably aligned, improving coverage cannot solve the more fundamental problem.

---

## 22. Expansion Decision

Do **not** expand beyond the three pilot categories yet.

The complete loop is not sufficiently reliable:

```text
Select concept
    ↓
Generate aligned question
    ↓
Recognize coverage
    ↓
Select next concept
```

WP-039 fixed one part of that loop, but target alignment is still only about 45% in the latest live run.

The pilot needs another iteration before expansion.

---

## 23. Final Decision

**STATUS: ACCEPTED**

WP-039 achieved its stated objective.

The trailing-truncation mechanism is:

- correctly owned by extraction;
- deterministic;
- bounded;
- provenance-preserving;
- regression-tested;
- effective on the observed truncation class.

The one disclosed false repair is a legitimate limitation but does not invalidate the WP because it results from intra-fragment corruption outside the deterministic structural-recovery scope.

The project should now move to the next layer.

### Recommended next WP

**WP-040 — Target-Answer Framing for Named Concepts**

Focus on the generation contract/prompt so that when the planner selects a named concept, the generated answer actually identifies that concept rather than merely describing its function or a related property.

Do this at generation time, **not as another rejection/retry validator**.

Keep the three-category pilot.

Do not expand yet.

---

## 24. Required WP-040 Architectural Goal

The desired pipeline is becoming:

```text
Evidence
   ↓
Clean Concept Inventory
   ↓
Concept Identity
   ↓
Coverage
   ↓
Deterministic Concept Selection
   ↓
Concept-Anchored Evidence
   ↓
Target-Aware Generation
   ↓
Aligned Question
   ↓
Validation
   ↓
Coverage Update
```

The next WP should make **Target-Aware Generation** reliable.
