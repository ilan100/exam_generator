# Architecture Review — WP-035

**Review Date:** 2026-08-09

**Reviewer:** ChatGPT (Architecture Review)

**WP Reviewed:** WP-035 — Concept Ownership Investigation

**Status:** **ACCEPTED**

---

# 1. Executive Summary

WP-035 is one of the most valuable architectural investigations completed in the project.

Unlike implementation work packages, its objective was to answer a strategic architectural question:

> Can concept selection move from the LLM into deterministic application logic?

The investigation answers this honestly:

> **Partially.**

Concept ownership is technically feasible for a meaningful subset of categories, but not universally with the current corpus.

Most importantly, the report correctly distinguishes between:

- extracting concepts;
- selecting concepts;
- generating questions.

These are separate responsibilities and should remain separate in the architecture.

---

# 2. Overall Assessment

| Area | Assessment |
|------|------------|
| Investigation methodology | Excellent |
| Scientific rigor | Outstanding |
| Evidence quality | Excellent |
| Architectural reasoning | Excellent |
| Scope discipline | Excellent |
| Long-term impact | Outstanding |

**Overall assessment: 10 / 10**

---

# 3. Major Strengths

## 3.1 Correct Question

The investigation asks exactly the right question.

Not:

> "Can we improve diversity?"

Instead:

> "Who should own concept selection?"

This reframing is architecturally significant.

---

## 3.2 Evidence Before Opinion

The report bases its conclusions on three representative categories:

- content-rich;
- weak;
- known diversity problem.

This is a much stronger methodology than reasoning from a single failure case. :contentReference[oaicite:1]{index=1}

---

## 3.3 Excellent Separation of Responsibilities

One of the strongest conclusions is that the application should increasingly own:

- concept inventory;
- coverage tracking;
- candidate restriction.

The LLM should continue owning:

- natural-language generation;
- educational phrasing;
- distractor writing.

This is fully consistent with the architectural evolution since WP-020.

---

## 3.4 Honest Limits

The report does not claim that deterministic concept ownership is universally achievable.

Instead it identifies categories where structural extraction works well and categories where it becomes unreliable because of generic headings, prose-heavy material or PDF extraction artifacts. :contentReference[oaicite:2]{index=2}

That honesty significantly increases confidence in the recommendation.

---

# 4. Most Important Finding

The investigation explains the repeated diversity failures much better than any previous work package.

The critical observation is:

The corpus often contains many distinct concepts.

The LLM repeatedly chooses the same one because it is simultaneously:

- highest scoring;
- cleanest;
- most frequently repeated;
- easiest to ground.

The application merely observes this afterwards.

The real issue is therefore not concept availability.

It is concept selection.

This is a major architectural insight. :contentReference[oaicite:3]{index=3}

---

# 5. Architectural Discovery

WP-035 introduces an important distinction.

There are now four separate stages:

```
Evidence

↓

Concept Inventory

↓

Concept Selection

↓

Question Generation
```

Previously these stages were effectively collapsed inside the LLM.

Separating them is likely to produce the next major improvement in system quality.

---

# 6. Evaluation of Candidate Strategies

The comparison of extraction strategies is particularly valuable.

The report evaluates:

- deterministic parsing;
- heading-based extraction;
- statistical extraction;
- offline preprocessing;
- manual inventories;
- hybrid extraction.

Rather than recommending the highest-accuracy solution, it recommends the solution most consistent with the project's architectural philosophy:

- deterministic;
- evidence-derived;
- fail-honest;
- no hand-authored knowledge.

I strongly agree with this direction. :contentReference[oaicite:4]{index=4}

---

# 7. Interaction with Existing Architecture

One of the best findings is that concept ownership has a very small blast radius.

The investigation concludes that:

- public API remains unchanged;
- validators remain unchanged;
- retries remain unchanged;
- retrieval remains unchanged;
- generation remains largely unchanged.

The primary change would occur inside the planning layer.

This is excellent architectural news because it localizes future implementation work. :contentReference[oaicite:5]{index=5}

---

# 8. Remaining Risks

The investigation correctly identifies several unresolved questions:

- synonym handling;
- concept granularity;
- evidence sufficiency;
- Hebrew/English extraction artifacts;
- categories with weak structure.

These are genuine engineering risks rather than reasons to reject the direction.

Most importantly, the report recommends validating any implementation on a limited set of structurally clean categories before broader rollout. :contentReference[oaicite:6]{index=6}

---

# 9. Architectural Recommendation

I agree with the report's recommendation.

The project should **not** introduce a manually maintained concept database.

Instead it should pursue:

1. deterministic extraction where the corpus structure supports it;
2. honest fallback where extraction is unreliable;
3. application-owned concept selection;
4. LLM-owned question generation.

This preserves the project's guiding principles:

- derive knowledge from evidence;
- never fabricate;
- fail honestly.

---

# 10. Impact on the Roadmap

WP-035 changes the roadmap.

I would now recommend:

- **WP-036 — Deterministic Concept Inventory (pilot implementation)**  
  Implement concept extraction for a small number of structurally suitable categories using the hybrid strategy identified in WP-035.

- **WP-037 — Concept-Constrained Planning**  
  Make the planner choose only from the remaining eligible concepts rather than from the entire evidence set.

- **WP-038 — Evidence-Constrained Question Generation**  
  Pass the selected concept to the LLM and evaluate whether diversity improves without reducing acceptance.

This staged rollout mirrors the project's successful "measure before expanding" approach.

---

# 11. Final Decision

**Status: ACCEPTED**

WP-035 successfully answers the architectural question it set out to investigate.

It demonstrates that deterministic concept ownership is feasible for a meaningful subset of categories while honestly documenting its limitations.

Most importantly, it establishes a clear separation between:

- concept extraction;
- concept selection;
- question generation.

I believe this is the correct long-term architecture for the project.

Future work should proceed incrementally, beginning with a limited pilot implementation on categories whose evidence structure already supports reliable deterministic concept extraction.
