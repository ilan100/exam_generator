# Architecture Review — WP-043

**Review Date:** 2026-08-12  
**Status:** **ACCEPTED WITH REQUIRED FOLLOW-UP — DO NOT PROCEED TO EXPANSION**

## 1. Executive Summary

WP-043 is **architecturally sound as an investigation and implementation of two useful primitives**, but it did **not solve the live generation problem** it was intended to solve.

The live acceptance trend is:

```text
WP-040: 11/12 accepted
WP-041:  9/12 accepted
WP-043:  5/12 accepted
```

The report explicitly identifies this as a material regression. fileciteturn27file0L81-L85

At the same time, WP-043 discovered two important and more precise facts:

1. The `Corpos Striatum` span-recovery fix successfully retrieves genuine surrounding evidence, but that evidence is an **enumeration-introduction sentence** that can actively encourage an ambiguous question form.
2. The `Basillar artery` source-role detector works correctly, but the resulting **free-text generation instruction is not reliably obeyed** by the LLM.

Therefore:

> **Retain the deterministic evidence-sufficiency and target-role primitives, but do not consider the generation problem solved. The next work must operate at the generation-constraint boundary.**

---

## 2. WP-043 Implementation Quality

The implementation itself is strong and safe:

- `source_line_indices` preserves the true reconstruction span;
- deterministic evidence sufficiency was added;
- bounded broad evidence fallback was added;
- deterministic source-role detection was added;
- generation context was extended;
- planner integration was added;
- validators were not changed;
- coverage was not changed;
- retry budget was not changed;
- public contracts were not changed;
- **1350/1350 tests pass**. fileciteturn27file0L17-L29 fileciteturn27file0L57-L65

This should be **kept**.

---

## 3. Corpos Striatum — The New Root Cause

WP-043 corrected the previous evidence-anchor problem.

The system now recovers genuine source text around:

```text
Corpos Striatum
```

instead of only the bare concept. fileciteturn27file0L45-L49

However, the recovered text has the form:

```text
Basal nuclei contain several sub-structures
```

This is an **enumeration-introduction**.

Combined with the existing target-answer requirement:

```text
Answer must be:
Corpos Striatum
```

the generator is naturally tempted to produce:

```text
Which of the following is a sub-structure of the basal nuclei?
```

But multiple answers can satisfy that question.

Therefore grounding correctly rejects it.

This is more precise than the WP-042 diagnosis:

```text
WP-042:
not enough context

WP-043:
context exists, but its semantic shape is unsuitable
for the required single-target answer
```

This is an important architectural discovery.

---

## 4. More Evidence Is Not Always Better

WP-043 demonstrates that we must not adopt:

```text
if evidence is insufficient:
    retrieve more evidence
```

as a universal rule.

The correct model is:

```text
retrieve more evidence
        ↓
evaluate its shape/usefulness
        ↓
only use it if it supports a valid target-answer relationship
```

Otherwise:

```text
insufficient evidence
```

can become:

```text
misleading evidence
```

which is worse.

---

## 5. The Span Fix Is Correct

The report identified the original lookup bug precisely:

```text
"Corpos Str"
"ia"
"tum"
```

was reconstructed across multiple raw lines, so the reconstructed concept did not exist verbatim as a single raw line.

The old exact-line lookup therefore failed.

Preserving:

```text
source_line_indices
```

is the correct architectural fix because it preserves provenance rather than introducing fuzzy matching. fileciteturn27file0L15-L21

**Keep this change.**

---

## 6. Broad Fallback Is Safe but Not Yet Proven as a Live Solution

The broad mode correctly remains bounded by:

- raw-scan limits;
- collected-line limits;
- paragraph boundaries;
- sibling-concept boundaries.

An earlier version that crossed paragraph boundaries was correctly rejected after it reached unrelated document metadata. fileciteturn27file0L35-L39

This is good engineering.

However:

```text
fallback_occurred = False
```

throughout the WP-043 pilot.

Therefore:

> **The fallback is verified as safe, but its production effectiveness has not yet been demonstrated.**

Do not claim otherwise.

---

## 7. Basillar Artery — Detector Works, Generation Does Not Reliably Obey It

The source-role detector correctly identifies:

```text
Basillar artery:
is_source_role = True
```

and the sibling target as false. fileciteturn27file0L41-L43

But the generator still frequently constructs:

```text
Which artery supplies X?
```

instead of using the desired source/origin framing.

The architecture therefore currently looks like:

```text
Role detection
      ✓
      ↓
Role representation
      ✓
      ↓
Generation follows role
      ✗ unreliable
```

This is the main direction for WP-044.

---

## 8. Prompt Instruction Is No Longer Enough

WP-043 has shown that simply adding:

```text
Target evidence role:
SOURCE
```

as prose is not reliably controlling question construction.

The next step should investigate a **structural generation constraint**, preferably using the existing blueprint mechanism.

Conceptually:

```text
target:
    Basillar artery

role:
    SOURCE

tested relationship:
    source/origin of Superior Cerebellar Artery

required answer:
    Basillar artery
```

The exact representation must fit the existing architecture.

The important principle is:

> **The generation plan should encode what relationship the question is allowed to test.**

---

## 9. Corpos Striatum Requires a Different Fix

Do not treat both failures as one generic problem.

### Corpos Striatum

```text
evidence shape:
enumeration

target:
one member of the enumeration

problem:
multiple entities can satisfy a membership question
```

### Basillar artery

```text
evidence shape:
relationship

target:
upstream/source entity

problem:
generator asks about the downstream entity
```

They require different constraints.

---

## 10. Recommended Corpos Striatum Direction

WP-044 should investigate:

### Option A — Explicit generation constraint

When evidence is enumeration-shaped and the required answer is one entity, prohibit generic membership questions unless the evidence uniquely distinguishes that entity.

### Option B — Deterministic evidence-shape handling

Detect enumeration-introduction evidence and avoid giving it to generation when it naturally produces an ambiguous target question.

If no uniquely usable evidence exists, prefer:

```text
skip target
```

over:

```text
generate a known ambiguous question
```

The report itself proposes these directions. fileciteturn27file0L130-L138

I prefer the structural/deterministic solution if it fits the current architecture cleanly.

---

## 11. Do Not Weaken Validation

The validators are doing the correct thing.

The system should reject:

```text
Which of the following is a part of Corpos Striatum?
Answer: Corpos Striatum
```

when the evidence does not uniquely support it.

Likewise, it should reject an incompatible interpretation of the `Basillar artery` evidence.

Therefore:

> **Validation is protecting the architecture. Do not relax it to improve acceptance.**

---

## 12. Do Not Increase the Retry Budget

Keep:

```text
3 attempts
```

The issue is not insufficient retries.

The issue is that the generator repeatedly produces question forms that are incompatible with the evidence/target relationship.

More retries would mainly increase cost and hide the structural problem.

---

## 13. Target Alignment Is an Additional Known Weakness

WP-043 observed one accepted question with:

```text
Target:
Corticospinal Tract

Answer:
Precentral Gyrus
```

The report correctly identifies this as a live example where the WP-040 target-answer requirement is not a hard guarantee. fileciteturn27file0L89-L95

Do **not** broaden WP-044 to solve every target-alignment problem.

However, record this as a known architectural weakness:

```text
target identity is currently strongly instructed,
but not structurally guaranteed
```

This may become important when strengthening the generation blueprint.

---

## 14. English-First Remains Solved

WP-043 confirms:

```text
5/5 = 100%
```

English-first compliance among accepted questions. fileciteturn27file0L93-L95

Therefore:

> **Do not modify WP-041.**

The current regression is not a language-compliance regression.

---

## 15. Concept Rotation Interpretation

The repeated selection of `Corpos Striatum` is now a different problem from the earlier coverage issue.

Previously:

```text
question accepted
    ↓
coverage failed to recognize answer
    ↓
same concept selected
```

Now:

```text
question never accepted
    ↓
concept never becomes covered
    ↓
same concept selected again
```

Coverage is therefore not the current blocker.

---

## 16. Expansion Status

**Do not expand beyond the three pilot categories.**

Current acceptance:

```text
5/12 = 41.7%
```

Two of the three pilot categories are unreliable.

Expansion would make the diagnosis harder, not easier.

---

## 17. Final Decision on WP-043

### Status

**ACCEPTED WITH REQUIRED FOLLOW-UP**

### Keep

- `source_line_indices`;
- deterministic span-aware anchoring;
- deterministic evidence sufficiency;
- bounded broad fallback;
- `is_source_role`;
- source-role detection;
- existing tests;
- English-first;
- strict validation;
- three-attempt budget;
- coverage behavior.

### Not solved

- `Corpos Striatum` generation;
- `Basillar artery` generation;
- overall acceptance reliability.

The WP implementation is accepted, but its intended live-pilot outcome is not.

---

# 18. Recommended WP-044

## WP-044 — Structural Generation Constraints for Evidence Shape and Target Role

WP-044 should investigate two narrowly scoped mechanisms.

### Part A — Enumeration-shaped evidence

For cases like:

```text
Corpos Striatum
```

where the recovered evidence naturally forms:

```text
X contains several sub-structures:
A, B, C, ...
```

determine how to prevent generation from producing:

```text
Which of the following is a sub-structure of X?
```

when multiple answers are valid.

Prefer a structural generation constraint over increasingly elaborate prompt prose.

### Part B — Source-role relationship

For:

```text
Basillar artery
```

investigate replacing the free-text role note with a structural generation constraint.

Conceptually:

```text
target = Basillar artery

role = SOURCE

tested_relationship =
    source/origin of Superior Cerebellar Artery

required_answer =
    Basillar artery
```

The actual model must fit the existing blueprint architecture.

---

## 19. WP-044 Must Preserve

Do not change:

```text
English-first
validators
coverage
retry budget
public contracts
evidence provenance
```

unless a concrete architectural necessity is demonstrated.

---

## 20. WP-044 Evaluation

Use the same three categories:

```text
אספקת דם
גרעיני הבסיס
מסילות עצביות
```

Four sequential questions each.

Measure:

```text
acceptance
attempt count
target alignment
English compliance
concept rotation
failure reason
```

Specifically track:

```text
Corpos Striatum
Basillar artery
```

and verify that improved acceptance is not achieved by relaxing validation.

---

## 21. Final Architectural Position

The progression is now:

```text
WP-041
    ↓
English-first problem solved

WP-042
    ↓
English-first not responsible for regression

WP-043
    ↓
Evidence-anchor bug fixed
    ↓
Real surrounding evidence recovered
    ↓
Two deeper generation-shape problems exposed
```

We now know:

> **The system can retrieve genuine evidence and correctly identify target roles, but the generation layer does not yet have strong enough structural constraints to reliably transform that information into a question whose answer is the selected target.**

That is the next architectural problem.

---

## 22. Final Recommendation

**Proceed to WP-044.**

But WP-044 should be **narrow and structural**, not another broad prompt experiment.

It should determine whether the existing generation blueprint can encode:

```text
evidence shape
+
target semantic role
+
required answer identity
```

as actual generation constraints.

If it can, that should become the preferred architecture.

If it cannot, we should explicitly reconsider the target-generation design rather than continuing to add prompt hints.

**WP-043: ACCEPTED WITH REQUIRED FOLLOW-UP.**
