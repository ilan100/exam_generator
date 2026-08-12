# Architecture Review — WP-042

**Date:** 2026-08-11  
**Status:** **ACCEPTED — DIAGNOSIS CONFIRMED; PROCEED TO WP-043**

## 1. Executive Summary

WP-042 successfully answered the central question left open by WP-041:

> **The English-first policy is not the primary cause of the acceptance regression.**

The evidence is strong:

- WP-041 acceptance regression: **11/12 → 9/12** is real.
- Four rejected diagnostic attempts were examined at validator level.
- **None identified language as the primary rejection reason.**
- `Corpos Striatum` has a structurally empty `factual_focus`.
- `Basillar artery` has evidence whose semantic relationship makes it a source feeding another artery rather than the supplied entity naturally expected by the generated question.
- Both problematic targets were already difficult under WP-040.
- `Medial Lemniscus Tract`, used as a control, passed on the first attempt.
- Full regression remains **1325 passed, 0 failed**. fileciteturn26file0L94-L108

**Overall assessment: 9.5 / 10**

---

## 2. Decision on WP-041

### KEEP WP-041

The English-first policy should remain unchanged.

WP-042 found no evidence supporting:

```text
English-first
    ↓
acceptance regression
```

Instead:

```text
pre-existing evidence/generation weakness
    ↓
difficult target generation
    ↓
attempt exhaustion
```

Both problematic targets had already been at or near the attempt ceiling under WP-040, before English-first existed. fileciteturn26file0L77-L84

**Do not weaken or remove English-first.**

---

## 3. Corpos Striatum — Root Problem

The clearest finding is that the target's `factual_focus` is simply:

```text
Corpos Striatum
```

with no function, location, relationship, or descriptive context.

This was confirmed independently from WP-039 data, WP-040 data, and WP-042's fresh diagnostic capture. fileciteturn26file0L62-L70

This means generation is being asked to produce a grounded question whose answer is `Corpos Striatum`, while the narrow evidence supplied to it contains essentially only the target name.

The failed attempt illustrates the consequence:

```text
Question:
Which of the following is part of Corpos Striatum?

Required answer:
Corpos Striatum
```

This is logically contradictory because X is not a part of X.

The validators correctly rejected it.

The successful second attempt instead used a question where `Corpos Striatum` can logically be the answer. All validators passed. fileciteturn26file0L42-L44

### Architectural conclusion

**The validator is not the problem.**

The evidence/context supplied to generation is insufficient.

---

## 4. Basillar Artery — Different Root Problem

`Basillar artery` has a different failure mode.

Its evidence is rich, but the relationship is effectively:

```text
Basillar artery
       ↓
feeds / supplies
       ↓
Superior Cerebellar Artery
       ↓
supplies the named area
```

Yet generation repeatedly produced questions equivalent to:

```text
Which artery supplies X?
```

while requiring:

```text
Basillar artery
```

as the answer.

The evidence instead supports `Superior Cerebellar Artery` as the artery supplying the named area.

The grounding validator correctly rejected the generated questions. fileciteturn26file0L46-L50

### Architectural conclusion

This is a **target-role / evidence-relationship problem**, not a language problem.

---

## 5. Two Different Problems Must Not Be Combined

### Problem A — Corpos Striatum

```text
Target:
Corpos Striatum

Anchored evidence:
"Corpos Striatum"
```

Problem:

> **Too little evidence/context.**

This points back to WP-037's narrow anchoring behavior.

### Problem B — Basillar artery

```text
Target:
Basillar artery

Evidence:
rich relationship structure
```

Problem:

> **The target participates as a source/upstream entity rather than the downstream entity assumed by the generated question.**

This points to the interaction between WP-037 evidence anchoring and WP-040 forced target-answer identity.

These require different solutions.

---

## 6. Do Not Change Validators

The validators did exactly what we want.

A question asking:

```text
Which is a part of Corpos Striatum?
```

with:

```text
Corpos Striatum
```

as the answer should fail.

Likewise, if the evidence supports `Superior Cerebellar Artery` as the supplier, a question asking which artery supplies that area should not accept `Basillar artery`.

Therefore:

> **Validation is protecting the architecture from invalid questions.**

Do not weaken it.

---

## 7. Do Not Increase the Retry Budget

The three-attempt limit should remain unchanged.

The issue is not:

```text
too few retries
```

but:

```text
the generator repeatedly attempts question forms
that are incompatible with the evidence/target relationship.
```

Increasing retries would spend more tokens without fixing the structural problem.

---

## 8. Do Not Change English-First

WP-041 should now be treated as an established architectural requirement:

> **If English exists, use English. Hebrew is allowed only when English does not exist.**

WP-042 found no evidence that this policy is the primary cause of the regression. fileciteturn26file0L94-L104

---

## 9. Important Architectural Insight

The system is not merely required to:

```text
find evidence containing target X
```

It must provide evidence that can support:

```text
a valid question
whose answer is X
```

WP-042 demonstrated two failure modes:

```text
Evidence contains almost nothing about X
```

and:

```text
Evidence contains X, but X plays a different semantic role
than the question generator assumes.
```

This is the key architectural finding.

---

## 10. Recommended WP-043

I recommend:

# WP-043 — Deterministic Evidence Sufficiency and Target-Role Handling

### Part A — Empty narrow anchor

Investigate a deterministic fallback when:

```text
factual_focus
```

contains only the concept name or otherwise has no useful descriptive content.

For `Corpos Striatum`, a broader existing evidence window may be used.

Rules:

- broader evidence must come from existing source evidence;
- no invented content;
- no semantic guessing;
- no fuzzy matching;
- no validator relaxation.

Desired flow:

```text
Target
  ↓
Narrow evidence anchor
  ↓
Is evidence sufficient?
  │
  ├── YES → generate
  │
  └── NO
       ↓
   deterministic broader fallback
       ↓
   re-evaluate
       ↓
   generate or fail safely
```

### Part B — Target semantic role

Investigate cases such as:

```text
Basillar artery → feeds → Superior Cerebellar Artery
```

The system must not automatically convert this into:

```text
Which artery supplies X?
```

if the target is the upstream/source entity.

Instead, generation must be able to formulate a question whose correct answer genuinely is the target and is supported by the evidence.

---

## 11. What WP-043 Must NOT Do

Do not:

- weaken grounding;
- weaken MCQ validation;
- weaken quality validation;
- increase retry count;
- remove target-answer identity;
- remove English-first;
- add fuzzy matching;
- add LLM semantic judging;
- invent evidence;
- make broad retrieval changes for the entire system.

The fix should be deterministic and localized.

---

## 12. Expansion Status

**Do not expand beyond the three pilot categories yet.**

This is no longer because of multilingual coverage.

That problem is solved for the concepts encountered by the pilot.

The current blocker is:

```text
evidence sufficiency
+
target semantic role
+
target-answer generation
```

These need to become robust for structurally atypical targets.

The completion report reaches the same conclusion. fileciteturn26file0L138-L153

---

## 13. WP-042 Assessment

| Area | Assessment |
|---|---|
| Diagnostic objective | **Fully achieved** |
| Root-cause analysis | **Strong** |
| Validator analysis | **Excellent** |
| English-first causality | **Resolved** |
| Corpos Striatum diagnosis | **Clear** |
| Basillar artery diagnosis | **Clear** |
| Production safety | **Excellent** |
| Scope discipline | **Excellent** |
| Need for follow-up | **Clear** |

### Final status: **ACCEPTED**

---

## 14. Final Architectural Position

After WP-042:

```text
Evidence
   ↓
Concept extraction
   ↓
Concept identity
   ↓
Concept selection
   ↓
Evidence anchoring
   ↓
Evidence sufficiency
   +
Target semantic role
   ↓
English-first target
   ↓
Target-aware generation
   ↓
Validation
   ↓
Coverage
```

The next architectural improvement should therefore be **before generation**, not inside validation.

That is the correct direction for WP-043.
