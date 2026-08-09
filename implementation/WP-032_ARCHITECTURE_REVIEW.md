# Architecture Review — WP-032

**Review Date:** 2026-08-09

**Reviewer:** ChatGPT (Architecture Review)

**WP Reviewed:** WP-032 — Category Generation Architecture Refactoring

**Status:** **ACCEPTED**

---

# 1. Executive Summary

WP-032 represents the largest architectural refactoring performed since the project began.

Unlike previous work packages, its objective was not to improve generation quality but to redefine the project's primary abstraction.

The project has transitioned from:

```
Generate Exam
```

to

```
Generate Next Question For Category
```

This is the correct abstraction for the system that has gradually evolved over the previous thirty-one work packages.

The implementation successfully performs this transition while preserving:

- generation behavior,
- validation,
- retry mechanisms,
- grounding,
- relationship extraction,
- competitor discovery,
- backward compatibility.

The implementation follows the requested scope extremely well and introduces no unnecessary redesigns. :contentReference[oaicite:0]{index=0}

---

# 2. Overall Assessment

| Area | Assessment |
|------|------------|
| Architectural refactoring | Excellent |
| Separation of concerns | Excellent |
| Backward compatibility | Excellent |
| Code reuse | Excellent |
| API design | Excellent |
| Experimental honesty | Excellent |

**Overall assessment: 9.9 / 10**

---

# 3. Major Strengths

## 3.1 Correct New Primary Abstraction

The most important achievement of WP-032 is changing the project's public API.

Before WP-032:

```
Exam

↓

Question Loop

↓

Generation
```

After WP-032:

```
Category

↓

Existing Questions

↓

Generate Next Question
```

This is a significantly cleaner business abstraction.

The exam itself is no longer the primary product.

Instead, it becomes a client of the category-generation service.

This greatly simplifies future evolution of the system.

---

## 3.2 Excellent Architectural Separation

The new `CategoryGenerationService` owns exactly one responsibility:

> Generate one additional question for one category.

It does not attempt to own:

- retrieval,
- validation,
- retries,
- orchestration,
- exam planning.

Those responsibilities remain where they belong.

This produces a much cleaner layering than the previous architecture.

---

## 3.3 Excellent Code Reuse

One of the strongest aspects of WP-032 is that it deliberately avoids rewriting existing logic.

Instead it reuses:

- QuestionProducer
- QuestionTargetPlanner
- Relationship extraction
- Competitor discovery
- All validators
- Retry mechanisms
- Duplicate handling

The implementation is primarily a reorganization of responsibilities rather than a functional rewrite. :contentReference[oaicite:1]{index=1}

---

## 3.4 Existing Questions Became Part of the Public Contract

This is an important architectural improvement.

Previously, previously-generated questions existed only as internal orchestration state.

Now they become explicit input to the generation request.

That makes future improvements significantly easier.

Future work can reason about previous questions without introducing hidden dependencies inside orchestration.

---

## 3.5 Backward Compatibility

Keeping `ExamOrchestrator` as a compatibility layer is exactly the correct migration strategy.

Existing clients remain unchanged.

Internally, orchestration simply delegates to the new service.

This minimizes migration risk while allowing the architecture to evolve.

---

# 4. Most Important Architectural Discovery

The acceptance run produced an unexpected but extremely valuable result.

Generation quality remained stable.

Acceptance count improved.

However, diversity regressed significantly.

Initially this appears contradictory.

It is not.

The regression exposed an architectural dependency that had previously been hidden inside the exam-oriented planner.

This is the single most important finding of WP-032.

---

# 5. Hidden Coupling Revealed

Prior to WP-032, target planning operated on an entire category simultaneously.

Conceptually:

```
Need 2 Questions

↓

Plan Both Together

↓

Generate Both
```

The planner therefore performed an implicit optimization across the entire target set.

It could deliberately choose two different concepts before generation even began.

After WP-032:

```
Need One Question

↓

Plan One Target

↓

Generate

↓

Repeat
```

Each planning operation becomes independent.

The planner no longer has awareness of previous target choices.

This explains the observed diversity regression far better than prompt behavior or LLM randomness.

Importantly, this is **not a defect introduced by the refactoring**.

It is a hidden architectural dependency that the refactoring successfully exposed.

The completion report correctly identifies this as a hypothesis rather than claiming causality without sufficient evidence. :contentReference[oaicite:2]{index=2}

---

# 6. Why This Is Valuable

Good architectural refactorings often reveal hidden coupling.

WP-032 does exactly that.

Before the refactoring, the planner appeared to produce question targets.

After the refactoring we now understand that it was actually performing **joint optimization of multiple targets**.

Those are fundamentally different responsibilities.

Discovering this distinction is a successful architectural outcome.

---

# 7. Architectural Implications

The solution should **not** be returning to batch planning.

Doing so would undermine the new architecture.

Instead, the planner itself should evolve.

Rather than planning multiple questions simultaneously, it should reason about:

- previously tested concepts;
- previously tested relationships;
- remaining uncovered knowledge.

Conceptually:

```
Existing Questions

↓

Coverage Extraction

↓

Already Tested Concepts

↓

Already Tested Relationships

↓

Remaining Candidate Targets

↓

Choose Next Target
```

This approach preserves the new architecture while recovering diversity through deterministic planning.

---

# 8. Impact on the Roadmap

WP-032 changes the project roadmap.

Originally, the next architectural milestone appeared to be deterministic distinguishing facts.

After WP-032, a more fundamental requirement has emerged.

The next planner should become **coverage-aware**.

The application already receives previous questions.

It now needs to understand what knowledge those questions have already tested.

Only then can it intelligently choose the next target.

This evolution is fully compatible with the new CategoryGenerationService and does not require any further architectural refactoring.

---

# 9. Recommendations

## Freeze

The following components should now be considered stable:

- CategoryGenerationService
- request contract
- response contract
- validation pipeline
- retry mechanisms
- orchestration compatibility layer

Future work should build on these interfaces rather than redesigning them.

---

## Focus Future Work

The next architectural effort should focus exclusively on planning.

Specifically:

- knowledge coverage;
- concept coverage;
- relationship coverage;
- target selection using existing questions.

No further prompt engineering should be attempted until the planner becomes coverage-aware.

---

# 10. Final Decision

**Status: ACCEPTED**

WP-032 successfully completes the transition from an exam-oriented architecture to a category-oriented generation engine.

The implementation is:

- architecturally clean;
- highly reusable;
- backward compatible;
- well isolated;
- carefully evaluated.

Most importantly, it exposes the project's next genuine architectural bottleneck:

> **Target planning must evolve from planning multiple questions together to selecting the next uncovered knowledge target using previously generated questions as deterministic context.**

This discovery is the primary architectural outcome of WP-032 and establishes a clear direction for the next phase of the project.
