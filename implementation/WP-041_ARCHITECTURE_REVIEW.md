# Architecture Review — WP-041

**Review Date:** 2026-08-11  
**WP Reviewed:** WP-041 — Deterministic English-First Language Policy  
**Status:** **ACCEPTED WITH REQUIRED FOLLOW-UP INVESTIGATION**

## 1. Executive Summary

WP-041 is accepted as an architectural implementation, but it is **not a full success against all of its own success criteria**.

The primary hypothesis was confirmed:

> When English is available, deterministically selecting English before generation removes the practical cross-script coverage problem without modifying coverage matching.

Evidence:

- Offline evaluation: **4/4 English correct answers**.
- Live English-first compliance: **9/9 accepted questions = 100%**.
- Target alignment: **9/9 = 100%**.
- Concept rotation improved in both previously cross-script-stuck categories.
- Coverage code was not changed.
- Full regression: **1325/1325**. fileciteturn25file0L70-L85 fileciteturn25file0L103-L119 fileciteturn25file0L176-L182

However, there is a material problem:

**Live acceptance dropped from 11/12 in WP-040 to 9/12 in WP-041.**

Therefore we should **not declare WP-041 completely successful and move on**.

The key question is whether the English-first policy itself is responsible for the increased generation difficulty, or whether it exposes/compounds an already weak evidence situation in `גרעיני הבסיס`, particularly around `Corpos Striatum`. The report itself correctly identifies this uncertainty. fileciteturn25file0L121-L133 fileciteturn25file0L164-L172

---

## 2. Overall Assessment

| Area | Assessment |
|---|---|
| English-first requirement | **Achieved** |
| Target alignment | **Excellent** |
| Cross-script rotation | **Improved / practically solved for encountered concepts** |
| Architectural placement | **Excellent** |
| Regression safety | **Excellent** |
| Scope discipline | **Excellent** |
| Acceptance | **Material regression** |
| Root cause of regression | **Not yet established** |
| Expansion readiness | **No** |

**Overall assessment: 9.0 / 10**

---

## 3. The Most Important Result

The original reason for WP-041 was valid.

WP-040 could generate:

```text
Target:
Corpos Striatum

Answer:
קורפוס סטריאטום
```

The answer was correct, but coverage could not recognize it against the English stored concept.

WP-041 now produces:

```text
Target:
Corpos Striatum

Answer:
Corpos Striatum
```

and the existing coverage mechanism recognizes the concept.

The live pilot demonstrates the intended effect:

```text
אספקת דם
WP-040: 2/4 distinct
WP-041: 3/4 distinct

גרעיני הבסיס
WP-040: 1/4 distinct
WP-041: 2/4 distinct

מסילות עצביות
WP-040: 4/4 distinct
WP-041: 4/4 distinct
```

The report confirms that the improved rotation followed the intended causal chain:

```text
English answer
    ↓
existing deterministic coverage
    ↓
concept recognized as covered
    ↓
next concept selected
```

with no coverage-layer modification. fileciteturn25file0L135-L143

---

## 4. English-First Compliance Is Excellent

The primary criterion was:

> If English exists, do not use Hebrew.

WP-041 achieved:

**9/9 = 100%**

among accepted live questions.

All recorded accepted answers used the English target representation and exactly matched their assigned target. fileciteturn25file0L103-L119

This confirms that the application-owned language decision is working.

---

## 5. The Implementation Is Architecturally Clean

WP-041:

- adds no public contract;
- adds no model field;
- does not modify validators;
- does not modify coverage;
- does not modify retrieval;
- does not modify extraction;
- does not modify ConceptIdentity;
- does not modify WP-040's answer-identity mechanism;
- introduces no fuzzy matching;
- introduces no embeddings;
- introduces no LLM judge;
- introduces no bilingual dictionary;
- introduces no new retry loop. fileciteturn25file0L176-L182

This is exactly the minimal-blast-radius approach we want.

---

## 6. The Existing Prompt Conflict Was Correctly Identified

The base generation prompt had a general Hebrew-language rule.

WP-041 correctly added a precise carve-out allowing English when the application explicitly specifies English for the target.

The validators were not changed because they already tolerated standard English/Latin terminology.

Therefore the conflict was instructional rather than a real validation incompatibility. fileciteturn25file0L9-L13

---

## 7. Representation Discovery Is Correctly Conservative

WP-041 does not attempt to discover bilingual equivalence.

It relies on the existing invariant that pilot-category concept targets are pure-ASCII English-representable text.

Therefore the decision:

```text
Does this selected target have an English representation?
```

reduces to the existing deterministic representation.

No search across unrelated evidence, no bilingual mapping, and no semantic matching was introduced. fileciteturn25file0L19-L29

I approve this boundary.

---

## 8. The Acceptance Regression Is Real

This is the issue we cannot ignore.

WP-040:

```text
11/12 = 91.7%
```

WP-041:

```text
9/12 = 75%
```

Three questions exhausted the three-attempt budget:

```text
אספקת דם — round 2
גרעיני הבסיס — round 1
גרעיני הבסיס — round 2
```

All were `QuestionAttemptsExhaustedError`. fileciteturn25file0L121-L133

This violates WP-041's own secondary acceptance criterion.

Therefore I would **not** mark WP-041 as fully successful.

The implementation is correct, but the system-level effect requires investigation.

---

## 9. The Regression Is Suspiciously Localized

The latest pilot shows:

```text
מסילות עצביות
4/4
```

while:

```text
אספקת דם
3/4
גרעיני הבסיס
2/4
```

The `גרעיני הבסיס` problem is particularly concentrated around:

```text
Corpos Striatum
```

The report notes that this same concept/evidence area has already been flagged in previous WPs as structurally problematic. fileciteturn25file0L127-L133 fileciteturn25file0L164-L172

This makes the following hypothesis plausible:

> English-first may not be the fundamental cause of the regression. It may be exposing an already difficult evidence/generation case because the generator now has one additional constraint.

But this remains a hypothesis.

---

## 10. We Need Attempt-Level Rejection Analysis

This is the most important next step.

For the failed questions, determine:

```text
Attempt 1
    ↓
Why rejected?

Attempt 2
    ↓
Why rejected?

Attempt 3
    ↓
Why rejected?
```

Specifically determine whether the failures are:

- grounding;
- MCQ;
- quality;
- category;
- target-answer;
- textbook;
- malformed structured output;
- or another existing rejection.

Without this information, we cannot determine whether English-first is actually causing the failures.

---

## 11. Do Not Immediately Change WP-041

I do **not** recommend weakening the English-first rule now.

The primary objective is working.

Changing it prematurely could lose the benefit:

```text
English answer
    ↓
deterministic coverage
    ↓
correct rotation
```

Instead, first isolate the acceptance regression.

---

## 12. Do Not Relax Validation or Increase Retries

Do not respond to the 9/12 result by:

- weakening validators;
- increasing the three-attempt budget;
- adding another retry mechanism.

That would hide the underlying problem.

The existing bounded-retry mechanism is functioning as designed. We need to determine why the valid-candidate rate dropped.

---

## 13. Recommended Next WP

I recommend a small diagnostic WP:

# WP-042 — Corpos Striatum / Generation Failure Analysis

Objective:

> Determine exactly why generation attempts are being rejected for `גרעיני הבסיס`, especially `Corpos Striatum`, after WP-041.

Initially this should **not change production behavior**.

It should expose enough existing attempt-level information to answer:

```text
What rejected each attempt?
```

---

## 14. What WP-042 Should Compare

Compare:

```text
WP-040
vs.
WP-041
```

with particular attention to:

```text
גרעיני הבסיס
Corpos Striatum
```

For every attempt record:

```text
target
attempt number
generated question
correct answer
grounding result
MCQ result
quality result
category result
textbook result
structured-output result
final rejection reason
```

Do not change generation rules while collecting this evidence.

---

## 15. Key Diagnostic Question

We need to distinguish:

### Hypothesis A — English-first causes the problem

```text
Corpos Striatum
    ↓
English target required
    ↓
evidence is predominantly Hebrew / structurally weak
    ↓
grounding or quality fails
```

### Hypothesis B — Existing evidence is the real problem

```text
Corpos Striatum
    ↓
already difficult evidence
    ↓
generation failures occur regardless of language
```

### Hypothesis C — Multiple constraints interact

```text
weak evidence
+
English-first
+
target identity
+
grounding
+
MCQ
+
quality
```

together push this target over the three-attempt threshold.

The evidence must determine which explanation is correct.

---

## 16. Evidence Quality Deserves Special Attention

The report notes that the `Corpos Striatum` evidence passage has already been flagged as less structurally clean.

WP-041 did not change retrieval or evidence extraction.

Therefore, if this target continues failing while other categories remain healthy, evidence quality becomes a strong suspect.

Inspect the actual evidence and attempt-level rejection reasons before modifying language policy.

---

## 17. Expansion Decision

**Do not expand beyond the three pilot categories yet.**

The reason is no longer cross-script coverage.

That problem is practically solved for the encountered concepts.

The current blocker is:

```text
acceptance = 75%
```

in the latest run.

We need to understand this regression first.

---

## 18. Current Architecture Status

```text
Concept extraction             ✓
Trailing truncation            ✓
Concept identity               ✓
Concept selection              ✓
Evidence anchoring             ✓
Target-aware generation        ✓
English-first policy           ✓
Target alignment               ✓
Cross-script rotation          ✓ practical improvement
Validation                     ✓
Overall acceptance             ⚠ regression to investigate
```

The project is closer than before.

We eliminated one major architectural blocker and uncovered a more localized generation/evidence reliability problem.

---

## 19. Final Decision

**WP-041: ACCEPTED WITH FOLLOW-UP**

### Accepted

The English-first architecture is correct.

The implementation is clean.

The primary behavior works:

```text
English available
    ↓
English selected
    ↓
English answer
    ↓
existing coverage recognizes concept
    ↓
concept rotation improves
```

This was confirmed in the live pilot. fileciteturn25file0L135-L155

### Not yet solved

The system-level reliability regression:

```text
WP-040: 11/12
WP-041: 9/12
```

remains unresolved.

---

## 20. Recommended Next Action

Before changing the English-first policy, perform a focused diagnostic investigation of:

```text
גרעיני הבסיס
Corpos Striatum
```

and the failed attempts.

Determine the exact rejection reasons for all three attempts in each failed round.

The key question is:

> **Is English-first itself causing the new failures, or is it exposing an existing weakness in the `Corpos Striatum` evidence/generation path?**

Do not change:

- validators;
- retry budget;
- coverage;
- language policy;
- retrieval;

until that question is answered.

---

## 21. Final Architectural Position

The system is now effectively:

```text
Evidence
   ↓
Clean Concept
   ↓
Target
   ↓
English-first language selection
   ↓
Target-aware generation
   ↓
English aligned answer
   ↓
Deterministic coverage
   ↓
Concept rotation
```

This chain is working.

The remaining uncertainty is:

```text
Evidence quality
       +
generation constraints
       ↓
three-attempt acceptance
```

That is where the next investigation should focus.
