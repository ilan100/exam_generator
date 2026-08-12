# Architecture Review — WP-044

**Review Date:** 2026-08-12  
**Status:** **ACCEPTED WITH REQUIRED FOLLOW-UP — DO NOT EXPAND THE PILOT**

## Executive Summary

WP-044 is a **successful architectural step**, but it does not solve the entire generation-ambiguity problem.

The live acceptance trend is:

```text
WP-040: 11/12 accepted
WP-041:  9/12 accepted
WP-043:  5/12 accepted
WP-044:  8/12 accepted
```

This is a meaningful recovery from WP-043. The improvement occurred without weakening validators or increasing the three-attempt budget. fileciteturn28file0L70-L80

More importantly, WP-044 demonstrated that **structural generation constraints can change live LLM behavior**, rather than merely adding more prompt prose:

- `Corpos Striatum` was skipped before generation because its evidence was deterministically recognized as an unsafe enumeration shape.
- `Basillar artery` generated source/origin questions in both attempts and was accepted on attempt 2. fileciteturn28file0L84-L98

This validates the architectural direction.

However, the remaining failures show that the broader ambiguity problem is larger than these two initial cases:

```text
Globus Pallidus
Corticospinal Tract
```

Both repeatedly generated questions with multiple evidence-supported correct answers. fileciteturn28file0L114-L120

Therefore:

> **Accept WP-044 and continue the structural-constraint approach, but do not expand the pilot yet.**

## 1. Implementation Quality

The implementation reuses the existing architecture rather than introducing a large new generation abstraction.

It extends existing structures such as `QuestionTarget`, reuses the planner and existing generation path, and adds narrow deterministic checks. fileciteturn28file0L13-L21

The safety boundary is excellent:

- no validator modification;
- no coverage modification;
- no retry-budget increase;
- no public schema changes;
- no LLM semantic judge;
- no embeddings;
- no external terminology source. fileciteturn28file0L57-L60

**Keep these architectural boundaries.**

## 2. Corpos Striatum — Correct Decision

WP-044 chose:

```text
skip
```

rather than forcing generation.

The system detected:

```text
enumeration introduction
+
no target-specific distinguishing content
```

and prevented the target from reaching generation. fileciteturn28file0L25-L33

This follows the established principle:

> **Prefer missing over wrong.**

For medical question generation, this is the correct safety decision.

## 3. Important Insight — Evidence Must Support a Unique Target Answer

The architecture now distinguishes:

```text
target has evidence
```

from:

```text
target has evidence that can safely support a question whose answer is target
```

This is a major improvement.

The relevant architectural question is no longer simply:

> Does the evidence mention the target?

It is:

> **Does the evidence support a valid, uniquely answerable question whose correct answer is the selected target?**

This should remain central to future work.

## 4. Basillar Artery — Structural Role Constraint Works

This is the strongest live result of WP-044.

The target:

```text
Basillar artery
```

was recognized as the source/upstream entity and the concrete downstream entity:

```text
Superior cerebellar artery
```

was identified.

Both generated attempts used source/origin framing rather than the previously problematic downstream framing. Attempt 2 passed all five validators. fileciteturn28file0L92-L98

This demonstrates that:

```text
specific structural relationship
```

is more effective than:

```text
generic role instruction
```

## 5. Qualification — Source-Role Rejection Check Is Not Live-Proven

The deterministic consistency check was not triggered during the pilot.

Therefore distinguish:

```text
source-role detection        = live-proven
source-role generation       = live-proven for one target
consistency rejection check  = unit-tested, not live-exercised
```

Do not claim the rejection path is production-proven yet. fileciteturn28file0L98-L98

## 6. Remaining Problem Is Broader Than Enumeration

The most important remaining failures are:

```text
Globus Pallidus
Corticospinal Tract
```

Both repeatedly exhausted the three-attempt budget because generated questions had multiple evidence-supported correct answers. fileciteturn28file0L114-L116

This is structurally related to the `Corpos Striatum` problem, but the current enumeration detector does not recognize these cases.

The broader problem should now be described as:

> **Evidence-supported question ambiguity**

rather than simply:

> enumeration detection.

The pattern is:

```text
Evidence
    ↓
Question asks for a category/member/class
    ↓
Multiple entities in the evidence satisfy the question
    ↓
MCQ has multiple correct answers
    ↓
grounding rejects
```

## 7. Do Not Build a General Semantic Classifier

The next WP should NOT introduce:

- an LLM ambiguity detector;
- a general semantic classifier;
- a medical ontology;
- an LLM judge.

Instead:

1. inspect the two real failures;
2. identify their common structural pattern;
3. determine whether a deterministic signal can capture it;
4. implement only that signal;
5. test it against the real failures and regression cases.

This is the same evidence-first methodology that worked in WP-044.

## 8. Distinguish Three Potential Failure Shapes

The next investigation should explicitly distinguish:

### A. Enumeration ambiguity

```text
A, B, C are all members of X
```

### B. Classification ambiguity

```text
X is a member of a broader class
A, B, C also belong to that class
```

### C. Hierarchical ambiguity

```text
X
└── X.1
```

where both parent and child can appear to satisfy a generated question.

Do not combine these into one rule unless the evidence demonstrates that they share a safe deterministic representation.

## 9. Globus Pallidus Requires Separate Attention

The report identifies an additional case:

```text
Globus Pallidus
vs.
Globus Pallidus Internus
```

where parent/child hierarchy creates another ambiguity. fileciteturn28file0L120-L120

Do not automatically classify this as the same problem as ordinary membership/classification ambiguity.

## 10. Corticospinal Tract Is a Valuable Diagnostic Case

`Corticospinal Tract` is useful because its evidence appears to describe a broader classification such as motor tracts beginning from the cortex.

This makes it a good test of whether the actual problem is:

```text
enumeration
```

or more generally:

```text
classification evidence
```

The evidence should be analyzed before changing code.

## 11. Acceptance Is Better, But Not Yet Stable

WP-044 improved:

```text
5/12 → 8/12
```

which is meaningful.

But:

```text
8/12 = 66.7%
```

is not yet a sufficiently stable result for expansion.

Two of the three pilot categories still contain unresolved repeated failures. fileciteturn28file0L74-L80

## 12. Concept Rotation

Current results:

```text
אספקת דם       4/4 distinct
גרעיני הבסיס   3/4 distinct
מסילות עצביות  3/4 distinct
```

This is improving.

But repeated:

```text
Globus Pallidus
Corticospinal Tract
```

shows that failed generation still prevents coverage progression. fileciteturn28file0L110-L110

Coverage is therefore still not the root problem.

## 13. Target Alignment

WP-044 reports:

```text
8/8 = 100%
```

accepted questions aligned with their assigned target. fileciteturn28file0L100-L102

This is excellent.

However, general target identity is still not a universal structural invariant; the new source-role check strengthens it only for that narrow case. fileciteturn28file0L43-L45

Continue monitoring it, but do not broaden WP-045 unnecessarily.

## 14. English-First

WP-044 reports:

```text
8/8 = 100%
```

English-first compliance among accepted answers. fileciteturn28file0L104-L106

No reason to modify WP-041.

The language issue is no longer the current blocker.

## 15. Test and Regression Quality

The implementation quality is excellent:

```text
1379 passed
0 failed
```

Public schemas remained byte-identical.

Validators and configuration were untouched.

The three-attempt limit remains unchanged. fileciteturn28file0L49-L60

## 16. Technical Limitation — Source Relationship Extraction

WP-044 discovered that:

```text
extract_source_relationship_entity()
```

operates on raw chunk text rather than the repaired concept inventory.

One truncated source line therefore produced:

```text
nterior Inferior Cerebellar Artery (AICA)
```

instead of the complete name. fileciteturn28file0L122-L122

This is a real limitation and should be fixed when the source-role mechanism is next revisited.

It does not invalidate the WP-044 result because the exercised `Basillar artery` pairing was not affected.

## 17. Recommended WP-045

# WP-045 — Deterministic Detection of Evidence-Supported Question Ambiguity

Objective:

> Determine why `Globus Pallidus` and `Corticospinal Tract` repeatedly generate questions with multiple evidence-supported correct answers, and determine whether a narrow deterministic pre-generation constraint can prevent this class of question.

### Phase 1 — Diagnosis

Before changing code, inspect:

```text
Globus Pallidus
Corticospinal Tract
```

including:

- exact `factual_focus`;
- target position;
- sibling concepts;
- evidence boundaries;
- generated questions;
- all rejected answers;
- why multiple options are supported;
- whether the evidence is classification-shaped;
- whether it is enumeration-shaped without explicit cue phrases;
- whether it is parent/child structured;
- whether the question pattern itself is too broad.

Do not assume the common cause.

### Phase 2 — Narrow deterministic solution

Only after the common structural pattern is established should implementation begin.

The preferred direction is a pre-generation constraint that prevents questions for which the supplied evidence supports multiple equally-correct answers.

Do not use another LLM to determine uniqueness.

## 18. Preserve the Successful WP-044 Mechanisms

WP-045 must retain:

```text
Corpos Striatum enumeration skip
```

and:

```text
Basillar artery concrete source relationship
```

Do not regress either.

Their tests remain mandatory.

## 19. Expansion Decision

**Still NO expansion.**

The pilot is now:

```text
8/12
```

with unresolved repeated failures.

We need the three-category pilot to become substantially more stable before applying the architecture to the full exam.

## 20. Final Assessment

| Area | Assessment |
|---|---|
| Structural generation direction | **Validated** |
| Corpos Striatum handling | **Correct / safely skipped** |
| Basillar artery handling | **Strong live success** |
| Target alignment | **8/8 accepted** |
| English-first | **8/8 accepted** |
| Regression suite | **1379/1379** |
| Overall acceptance | **Improved to 8/12** |
| Remaining ambiguity problem | **Real and clearly identified** |
| Expansion readiness | **No** |

### Final Status

**WP-044 ACCEPTED WITH REQUIRED FOLLOW-UP**

## 21. Final Architectural Position

```text
Evidence
   ↓
Concept extraction / repair
   ↓
Concept identity
   ↓
Evidence anchoring
   ↓
Evidence sufficiency
   ↓
Evidence-shape constraints
   ↓
Target semantic role
   ↓
Structural generation constraints
   ↓
LLM question generation
   ↓
Strict validation
   ↓
Coverage
```

The remaining central question is:

> **Can the evidence support exactly one valid question whose answer is the selected target?**

That should be the central question for WP-045.

**Recommendation: proceed to WP-045, but keep it narrow and evidence-driven.**
