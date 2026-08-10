# Architecture Review — WP-037

**Review Date:** 2026-08-10  
**Reviewer:** ChatGPT (Architecture Review)  
**WP Reviewed:** WP-037 — Concept-Anchored Evidence for Deterministic Targets  
**Status:** **ACCEPTED — POSITIVE RESULT, WITH A REQUIRED FOLLOW-UP BEFORE EXPANSION**

---

## 1. Executive Summary

WP-037 is a successful and important work package.

The central hypothesis was:

> If the application selects a deterministic concept and supplies narrow evidence specifically anchored to that concept, the generated question should be much more likely to actually test that concept.

The live experiment supports this hypothesis.

Manual target-alignment improved from approximately **45% in WP-036 to 87.5% in WP-037** (7/8 accepted questions). The report documents the methodology and manually reviewed all accepted questions after discovering that the initial deterministic substring check was not language-tolerant. fileciteturn21file0L69-L88

This is a genuine architectural improvement.

However, WP-037 also exposed a new interaction: narrower evidence causes the LLM to answer more naturally in Hebrew, while coverage recognition still relies on exact textual matching against the assigned concept. As a result, target selection became stuck for two categories and acceptance fell from **11/12 in WP-036 to 8/12 in WP-037**. The report traces this regression to coverage recognition, not to deterioration in question-generation quality. fileciteturn21file0L90-L109

Therefore:

**WP-037 should be accepted, but the concept-anchored pilot should not yet be expanded beyond the three pilot categories.**

---

## 2. Overall Assessment

| Area | Assessment |
|---|---|
| Architectural direction | Excellent |
| Implementation discipline | Excellent |
| Experimental methodology | Excellent |
| Target-to-question alignment | Strong improvement |
| Reliability | Regression caused by identifiable interaction |
| Provenance safety | Excellent |
| Scope control | Excellent |
| Architectural learning | Outstanding |

**Overall assessment: 9.5 / 10**

---

## 3. What WP-037 Successfully Proved

WP-036 established that deterministic concept selection was possible but insufficient.

WP-037 now establishes the next missing link:

```text
Deterministic Concept Selection
        ↓
Concept-Anchored Evidence
        ↓
Question Generation
```

This substantially improves the probability that the generated question actually addresses the selected concept.

The measured improvement was:

```text
WP-036: ~45% target alignment
WP-037: 87.5% target alignment
```

This is strong directional evidence, while the report correctly notes that the sample remains small. fileciteturn21file0L84-L88

---

## 4. The Most Important Architectural Result

We have now solved another major part of the original diversity problem.

The system increasingly owns the process:

```text
Evidence
   ↓
Concept Inventory
   ↓
Coverage
   ↓
Concept Selection
   ↓
Concept-Anchored Evidence
   ↓
Question Generation
```

The LLM is no longer responsible for deciding what part of the evidence should be tested.

It is increasingly responsible for expressing a preselected factual target as a good educational question.

This is the correct architectural direction.

---

## 5. The New Failure Is Precisely Localized

WP-037 identified a concrete interaction.

The narrower context causes the model to produce Hebrew answers such as:

```text
Superior cerebellar artery
        ↓
עורק סופריור צרבלרי
```

The existing coverage mechanism performs exact textual matching.

Therefore:

```text
Selected concept:
Superior cerebellar artery

Generated answer:
עורק סופריור צרבלרי

Exact match:
NO

Coverage:
concept appears unused
```

The planner then selects the same concept again.

This produces:

```text
Concept selected
    ↓
Question generated correctly
    ↓
Answer language differs
    ↓
Coverage fails to recognize concept
    ↓
Same concept selected again
    ↓
Duplicate question pressure
    ↓
Bounded rejection/exhaustion
```

This is a very useful diagnosis. fileciteturn21file0L90-L99

---

## 6. This Is Not a Reason to Reject Concept Anchoring

The data should not be interpreted as simply:

> WP-037 made the system worse.

The more accurate conclusion is:

> WP-037 improved target alignment but exposed a previously hidden weakness in coverage recognition.

The accepted questions themselves required fewer attempts:

```text
WP-036: ~1.27 attempts
WP-037: 1.125 attempts
```

So generation did not become intrinsically less reliable. The problem is that correctly generated questions are not always recognized as covering the selected concept. fileciteturn21file0L106-L109

---

## 7. Other WP-037 Findings

### 7.1 Trailing Truncation

WP-037 encountered:

```text
Corpos Str
```

for what appears to be:

```text
Corpus Striatum
```

The existing conservative repair handles leading truncation but not this trailing/multi-fragment form.

I agree with the decision not to introduce general OCR/PDF repair.

The principle should remain:

> Never guess.

A smaller trustworthy inventory is better than a larger corrupted one. fileciteturn21file0L128-L132

This is worth addressing later, but it is not the immediate blocker.

### 7.2 Referential Completeness

The report identifies a legitimate concern with narrow anchoring: a very small context can omit the information needed to understand a relationship.

The correct goal is therefore not:

> make the context as small as possible.

It is:

> **make the context concept-specific while retaining the minimum context required to preserve the factual meaning.**

---

## 8. What We Should NOT Do Next

We should explicitly avoid:

- returning to LLM-based concept selection;
- adding more prompt instructions saying "use the selected concept";
- increasing generation attempts;
- adding a diversity validator;
- returning to the old wide evidence window;
- introducing general fuzzy or semantic coverage matching.

In particular, another validator would treat the symptom after generation.

The current issue is in **coverage recognition**, not primarily generation quality.

---

## 9. Recommended Next WP

The immediate next WP should address one problem:

> **Coverage recognition must be robust to deterministic language/script variation without becoming semantic matching.**

The cleanest direction is a small internal **Concept Identity / Coverage Matching** mechanism.

Instead of relying only on:

```text
assigned concept text
        ==
generated answer text
```

the application should maintain a stable internal identity for the selected concept.

Concept identity could contain:

```text
canonical concept
    |
    +-- normalized form(s)
    +-- explicitly derivable language/script form(s)
```

The important constraint is:

**deterministic only.**

Do not ask an LLM whether two expressions mean the same thing.

---

## 10. Identity vs. Semantic Similarity

The next WP must distinguish:

### Identity equivalence

```text
Superior cerebellar artery
עורק סופריור צרבלרי
```

when the relationship can be established deterministically and safely.

from:

### Semantic similarity

```text
Superior cerebellar artery
arterial supply of the cerebellum
```

These must not be treated as equivalent.

The first can potentially represent the same concept in another language/script.

The second is a broader functional description.

Collapsing them would damage diversity.

---

## 11. Recommended Next Experiment

Use exactly the same:

- three pilot categories;
- four sequential questions per category;
- live production retrieval;
- real generation;
- no reruns.

Compare:

1. current exact matching;
2. deterministic normalization;
3. narrowly defined cross-script handling where safe.

Measure together:

- target alignment;
- actual tested-content diversity;
- accepted count;
- average attempts;
- concept-selection rotation.

Do not optimize for one metric at the expense of the others.

---

## 12. Expansion Decision

Do **not** expand concept-anchored planning beyond the current three categories yet.

The next experiment should first demonstrate that the coverage loop works:

```text
Select concept
      ↓
Anchor evidence
      ↓
Generate aligned question
      ↓
Recognize concept as covered
      ↓
Select next concept
```

Once this loop is reliable, expansion to additional categories becomes justified.

---

## 13. Final Decision

**Status: ACCEPTED — DO NOT EXPAND YET**

WP-037 is accepted.

The central hypothesis was supported:

> Narrow, concept-anchored evidence substantially improves the probability that generated questions actually test the selected concept.

The regression in accepted questions is explained by a specific downstream interaction:

> **Exact-text coverage matching is not robust to the language/script variation introduced by the narrower evidence context.**

This is a localized and actionable problem.

Therefore the correct next step is **not** to abandon concept anchoring, add more retries, or add a diversity validator.

The correct next step is to make **concept coverage identity robust to safe, deterministic language/script variation**, while preserving the project's strict rule against semantic guessing.

Only after that is demonstrated should concept-anchored planning be expanded beyond the three pilot categories.
