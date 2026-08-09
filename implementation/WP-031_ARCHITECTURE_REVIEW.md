# Architecture Review — WP-031

**Review Date:** 2026-08-07

**Reviewer:** ChatGPT (Architecture Review)

**WP Reviewed:** WP-031 — Deterministic Competitor Discovery

**Status:** **ACCEPTED**

---

# 1. Executive Summary

WP-031 is accepted.

This is one of the strongest implementation work packages since WP-027.

The implementation introduces exactly one new architectural concept—**deterministic competitor discovery**—while preserving the existing generation architecture.

Most importantly, the implementation is disciplined:

- exactly one architectural concept introduced;
- clean subsystem boundaries;
- no unnecessary refactoring;
- honest evaluation;
- no exaggerated claims.

Although the measured improvements are encouraging, the report correctly avoids claiming that competitor discovery alone caused those improvements.

That engineering discipline significantly increases confidence in both the implementation and the reported results.

---

# 2. Major Strengths

## 2.1 Excellent Architectural Isolation

Competitor discovery is implemented as an independent subsystem.

No architectural changes were required to:

- validators
- retrieval
- orchestration
- retry logic
- diversity planner
- QuestionTarget
- QuestionRelationship

This preserves the clean separation established throughout the project.

---

## 2.2 Correct Separation of Responsibilities

The application now determines:

- the tested concept
- the tested relationship
- competing concepts

The LLM remains responsible only for expressing the final MCQ.

This continues the architectural philosophy adopted since WP-020:

> Move intelligence from prompts into deterministic application logic.

This direction remains correct.

---

## 2.3 Competitor Discovery Is the Right Abstraction

I strongly agree with introducing competitors as a first-class application concept.

Competitors are objective.

They exist independently of prompts, wording, or distractor generation.

Unlike distractor archetypes, competitor discovery creates reusable application knowledge.

That makes it a significantly stronger architectural abstraction.

---

## 2.4 Honest Prompt Integration

The prompt receives competitors as information—not instructions.

The application constrains the search space.

The LLM still chooses how to construct the final distractors.

This preserves flexibility while providing much better guidance.

---

## 2.5 Correct Trust Boundary

The implementation stores evidence-derived text windows rather than inferred semantic concepts.

The application therefore never pretends to understand neuroanatomy.

Instead, it exposes verified evidence in a deterministic way.

This remains fully aligned with the project's trust philosophy.

---

# 3. Acceptance Run

The acceptance run demonstrates meaningful progress.

Compared with WP-030:

- grounding failures caused by "another answer also supported" decreased;
- first-attempt acceptance reached the best measured level so far;
- average attempts per accepted question became the best measured so far;
- zero confirmed false acceptances were maintained.

Although the overall acceptance count remained similar, generation efficiency improved.

These are meaningful improvements.

---

# 4. Engineering Discipline

The strongest aspect of WP-031 is not the numerical improvement.

It is the quality of the evaluation.

The completion report explicitly distinguishes:

- measured improvement

from

- proven causality.

This is exactly the correct scientific conclusion.

The report correctly states that current evidence does **not** prove competitor discovery itself caused the observed improvements.

Future work packages should continue maintaining this standard of evidence.

---

# 5. Remaining Architectural Gap

WP-031 substantially improves the information available to generation.

The generator now knows:

- correct concept
- tested relationship
- competing concepts

However, one important piece of information is still missing:

**Why each competitor is incorrect.**

This now appears to be the dominant remaining architectural gap.

Competitors define the search space.

They do **not** yet define the distinguishing knowledge that separates the correct answer from plausible alternatives.

---

# 6. Recommended Next Architectural Direction

The next architectural layer should introduce **deterministic distinguishing facts**.

Conceptually:

```text
Correct Concept

↓

Relationship

↓

Competitors

↓

Distinguishing Facts

↓

Question Generation
```

The application—not the LLM—should determine these distinguishing facts.

The LLM should then express them naturally within the generated question.

This continues the project's successful evolution toward deterministic application guidance.

---

# 7. Architectural Assessment

| Area | Assessment |
|------|------------|
| Implementation quality | Excellent |
| Architectural isolation | Excellent |
| Runtime cost | Excellent |
| Engineering discipline | Excellent |
| Evaluation methodology | Excellent |
| Long-term architectural value | Excellent |

**Overall assessment: 9.8 / 10**

---

# 8. Decision

**Status: ACCEPTED**

WP-031 successfully introduces a reusable architectural subsystem while preserving the integrity of the existing generation pipeline.

The implementation is:

- clean;
- deterministic;
- inexpensive;
- well tested;
- honestly evaluated.

The measured improvements are encouraging, but the report correctly avoids attributing causality beyond what the data supports.

This work package establishes competitor discovery as a permanent architectural component.

Future work should build upon this foundation by introducing deterministic **distinguishing facts**, rather than returning to additional prompt engineering or new validation layers.
