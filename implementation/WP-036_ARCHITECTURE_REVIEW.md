# Architecture Review — WP-036

**Review Date:** 2026-08-10

**Reviewer:** ChatGPT (Architecture Review)

**WP Reviewed:** WP-036 — Deterministic Concept Inventory Pilot

**Status:** **ACCEPTED — PILOT SUCCESSFUL AS AN EXPERIMENT, NOT READY FOR EXPANSION**

---

# 1. Executive Summary

WP-036 implemented a limited deterministic concept-inventory pilot for three categories:

- אספקת דם
- מסילות עצביות
- גרעיני הבסיס

The implementation successfully demonstrated that:

1. concepts can be extracted deterministically from suitable evidence;
2. concepts can be selected deterministically;
3. previously tested concepts can be excluded;
4. the LLM can be removed from the concept-selection step;
5. generation and validation can remain completely unchanged.

The implementation was technically clean and remained within scope.

However, the primary objective was not achieved:

> **Changing the selected concept did not reliably change the actual knowledge tested by the generated question.**

This is the most important finding of WP-036.

The problem has now been narrowed considerably.

The system has successfully solved:

```text
Which concept should we try to test?
```

It has not yet solved:

```text
How do we make the generated question actually test that concept?
```

Therefore the deterministic concept-selection approach should **not yet be expanded to additional categories**. :contentReference[oaicite:1]{index=1}

---

# 2. Overall Assessment

| Area | Assessment |
|------|------------|
| Implementation quality | Excellent |
| Scope discipline | Excellent |
| Deterministic planning | Successful |
| Extraction quality | Partial |
| Target diversification | Successful |
| Actual question diversification | Not yet successful |
| Reliability impact | No demonstrated regression |
| Experimental value | Very high |

**Overall assessment: 9.5 / 10**

---

# 3. Implementation Quality

WP-036 is technically well controlled.

The implementation:

- added an internal `InventoryConcept` model;
- added deterministic extraction;
- restricted the feature to three categories;
- reused WP-034 coverage;
- avoided LLM calls during concept selection;
- preserved the existing generation pipeline;
- preserved validators;
- preserved retrieval;
- preserved relationships and competitors;
- preserved public contracts.

The full regression suite passed:

**1235 / 1235**

No public schema changed. :contentReference[oaicite:2]{index=2}

This is exactly the right level of isolation for a pilot.

---

# 4. What Actually Worked

This distinction is extremely important.

## Target selection worked.

The planner correctly changed the selected target as coverage accumulated.

For example, `אספקת דם` moved from:

```text
Superior cerebellar artery
```

to:

```text
Basilar artery
```

after the first question.

Therefore the deterministic planner is doing its job.

The problem happens later.

---

# 5. What Did Not Work

The generated question frequently returned to the dominant fact from the evidence rather than the assigned concept.

Therefore the actual pipeline is effectively:

```text
Application

↓

Select concept A

↓

LLM receives concept A + evidence

↓

LLM notices stronger fact B

↓

Question tests B
```

This means deterministic target selection alone is insufficient.

The LLM still retains too much freedom over the factual subject of the question.

This explains why diversity did not improve even though target selection demonstrably changed. :contentReference[oaicite:3]{index=3}

---

# 6. The Most Important Architectural Discovery

WP-036 has revealed a new boundary.

Previously we believed:

```text
Concept Selection
        ↓
Question Generation
```

was sufficient.

It is not.

The generated question must be **anchored to the selected concept**.

The architecture therefore needs:

```text
Evidence
   ↓
Concept Inventory
   ↓
Concept Selection
   ↓
Concept-Specific Evidence
   ↓
Question Generation
   ↓
Validation
```

The missing component is:

> **Concept-specific evidence anchoring.**

---

# 7. Root Cause #1 — Context-Window Ambiguity

This is the most important immediate problem.

The current `factual_focus` is apparently broad enough to include multiple related facts.

For example:

```text
Superior Cerebellar Artery
        ↓
source: Basilar Artery
```

If the selected concept is:

```text
Basilar Artery
```

but the context contains a stronger statement about:

```text
Superior Cerebellar Artery
```

the LLM can reasonably construct a question about the latter.

The application technically selected the right concept.

But the evidence supplied to the LLM did not sufficiently constrain the factual focus.

This is a very actionable problem. :contentReference[oaicite:4]{index=4}

---

# 8. Root Cause #2 — Extraction Artifacts

The second problem is different.

Examples:

```text
edial Lemniscus Tract
```

instead of:

```text
Medial Lemniscus Tract
```

and:

```text
The Basal Gang
```

instead of:

```text
The Basal Ganglia
```

These are not merely cosmetic problems.

They affect coverage.

The system believes it selected:

```text
edial Lemniscus Tract
```

but generation correctly produces:

```text
Medial Lemniscus Tract
```

The coverage mechanism then fails to recognize that the concept was already tested.

Consequently, the same concept is selected again.

The loop becomes:

```text
Bad extraction

↓

Bad target identity

↓

Correct generation

↓

Coverage doesn't recognize it

↓

Same target again
```

This is an architectural loop that must be broken.

---

# 9. Root Cause #3 — Category Self-Restatement

`גרעיני הבסיס` revealed another important problem.

The inventory extracted:

```text
The Basal Gang
```

which is effectively the category itself.

This is not a useful sub-concept.

The generator consequently produced broad category-level questions instead of questions about a distinct subtopic.

Therefore the inventory needs a distinction between:

```text
Category identity
```

and:

```text
Actual sub-concept
```

This should be addressed before broader rollout. :contentReference[oaicite:5]{index=5}

---

# 10. Important Positive Finding: Reliability Did Not Regress

This is important.

The deterministic pilot did not introduce an observable reliability regression.

Results:

| Category | Accepted |
|---|---:|
| אספקת דם | 4/4 |
| מסילות עצביות | 4/4 |
| גרעיני הבסיס | 3/4 |

The one failure was an ordinary:

```text
QuestionAttemptsExhaustedError
```

There were:

- no generation-contract failures;
- no new validator failures caused by the pilot;
- no retrieval failures;
- no new retry mechanism.

Therefore the architecture can continue evolving without evidence that deterministic concept selection itself damages reliability. :contentReference[oaicite:6]{index=6}

---

# 11. Critical Architectural Decision

**Do not expand the pilot yet.**

The completion report correctly recommends against expansion.

I agree.

Expanding from three categories to twenty would multiply the currently observed problems:

- concept extraction artifacts;
- broad context windows;
- category self-restatement;
- coverage mismatches.

The correct response is to fix the boundary between:

```text
Selected Concept
```

and

```text
Generation Evidence
```

before expanding coverage.

---

# 12. What We Should NOT Do Next

We should NOT:

- return to LLM-based concept selection;
- add more prompt instructions saying "use the selected concept";
- increase generation attempts;
- add a diversity validator;
- reject questions after generation merely because they differ from the target;
- expand deterministic concept extraction to all categories;
- introduce semantic matching yet.

In particular, I do **not** recommend adding a new diversity validator at this point.

That would treat the symptom after generation.

The architectural problem occurs **before generation**.

---

# 13. Recommended Next Architecture

The next pipeline should become:

```text
Category
   ↓
Evidence Retrieval
   ↓
Concept Inventory
   ↓
Coverage Filtering
   ↓
Select Concept
   ↓
Extract Narrow Concept Evidence
   ↓
Construct Target
   ↓
Generate Question
   ↓
Existing Validation
```

The important new stage is:

```text
Extract Narrow Concept Evidence
```

The LLM should receive evidence that is specifically about the selected concept rather than a broad context containing several competing facts.

---

# 14. Proposed Next Work Package

The next WP should therefore be:

# WP-037 — Concept-Anchored Evidence

Objective:

> Given a deterministically selected concept, construct a minimal, concept-specific evidence context for generation.

The first implementation should remain a pilot.

It should operate only on the three WP-036 categories.

It should:

1. locate the selected concept in its source evidence;
2. identify the sentence/clause containing the concept;
3. avoid unnecessarily including neighboring facts;
4. preserve the genuine canonical evidence chunk ID;
5. construct a narrow factual focus;
6. pass that focus to the existing generation pipeline;
7. leave generation and validation unchanged.

---

# 15. Extraction Artifact Handling

WP-037 should also address the clearly observed extraction corruption.

However, this should be done conservatively.

Do NOT attempt general OCR/PDF repair.

Instead:

- detect obviously truncated fragments;
- reject unusable concepts;
- only repair when the evidence provides an unambiguous local reconstruction;
- otherwise omit the concept.

The principle remains:

> **Never guess.**

A smaller inventory of trustworthy concepts is preferable to a larger inventory containing corrupted concepts.

---

# 16. Category Self-Restatement

WP-037 should also introduce a deterministic exclusion rule for concepts that are effectively identical to the category name.

For example:

```text
category = גרעיני הבסיס

concept = The Basal Ganglia
```

should not automatically become a sub-concept.

The exact rule should be carefully designed and tested.

Do not use semantic similarity yet.

---

# 17. Acceptance Method for WP-037

Do not run a 40-question exam.

Continue with the successful experimental methodology established in WP-036.

Use exactly the same three pilot categories.

Generate four sequential questions per category.

Compare:

### WP-036

Target changed?

Yes.

Actual tested concept changed?

Mostly no.

### WP-037

Target changed?

Yes.

Actual tested concept changed?

This is the primary question.

---

# 18. Success Criteria

WP-037 should be considered successful only if:

1. selected concepts remain diverse;
2. generated questions actually test those concepts;
3. previously tested concepts are not repeatedly regenerated;
4. acceptance/reliability does not materially deteriorate.

The key metric is no longer merely:

```text
Target diversity
```

It is:

```text
Target-to-question alignment
```

That should become an explicit evaluation metric.

---

# 19. New Metric: Target Alignment

I recommend introducing a diagnostic metric:

```text
target_alignment =
    whether the accepted question actually tests
    the deterministically selected concept
```

For every generated question, record:

- selected concept;
- expected factual focus;
- actual correct answer;
- actual tested concept;
- alignment result.

This can initially be evaluated manually.

Do not create an LLM-based alignment validator yet.

First establish the phenomenon and measurement methodology.

---

# 20. Final Decision

**Status: ACCEPTED — DO NOT EXPAND**

WP-036 is accepted as a successful architectural pilot and a highly valuable diagnostic experiment.

It proved:

> Deterministic concept selection is technically possible.

It also proved:

> Deterministic concept selection alone does not guarantee diverse generated questions.

The new problem is now precisely localized:

> **The generation stage is not sufficiently anchored to the selected concept.**

This is substantially more actionable than the conclusion from WP-034.

The next work package should therefore focus on **concept-specific evidence anchoring**, not on broader concept extraction, additional retries, or further prompt-based diversity instructions.

The deterministic concept-inventory approach should remain limited to the current three pilot categories until WP-037 demonstrates reliable target-to-question alignment.
