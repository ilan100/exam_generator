# Architecture Review — WP-030

**Review Date:** 2026-08-07

**Reviewer:** Architecture Review

**WP Reviewed:** WP-030 — Relationship-Constrained Generation

**Status:** PARTIALLY ACCEPTED

---

# 1. Executive Summary

WP-030 faithfully implemented the architecture selected in WP-029 Phase 1.

The implementation introduced an explicit, deterministic relationship model computed entirely by the application before generation. No additional LLM calls, validators, retrieval logic, orchestration, or retry mechanisms were added.

This is architecturally clean and aligns with the long-term direction of moving application intelligence into deterministic code.

However, the principal hypothesis of WP-030 was not validated by the live acceptance run.

The primary success criterion was to reduce grounding failures caused by "another answer also supported".

Instead, those failures doubled compared with the WP-027 baseline, while MCQ and Quality validation improved substantially.

WP-030 should therefore be viewed as a successful architectural step whose primary hypothesis remains unproven.

---

# 2. What Was Successful

## Architectural isolation

The implementation correctly avoided changes to:

- validators
- retrieval
- orchestration
- planning
- retries
- QuestionTarget

The relationship layer is additive and deterministic.

## Separation of responsibilities

The architecture now clearly separates:

- QuestionTarget → WHAT is tested
- QuestionRelationship → WHICH relationship is tested
- Generation policy → HOW the question is constructed

This is a cleaner long-term model than continually expanding QuestionTarget.

## Runtime cost

The relationship classifier introduces:

- zero additional LLM calls
- zero additional retrieval
- negligible runtime cost

## Better structural quality

Although the primary grounding metric regressed, MCQ and Quality validation improved.

This indicates that explicit relationship framing helps the model produce structurally cleaner questions.

---

# 3. Where WP-030 Fell Short

The dominant grounding failure ("another answer also supported") increased significantly rather than decreasing.

Relationship awareness alone is therefore insufficient to produce unique distractors.

Knowing the tested relationship does not automatically eliminate competing correct answers.

---

# 4. Architectural Interpretation

The relationship classifier itself does not appear to be responsible for the regression.

Coverage was limited, and the reported data does not support abandoning the relationship layer.

Instead, the results suggest that relationship information is necessary but not sufficient.

---

# 5. Missing Architectural Layer

The generator now knows:

- concept
- relationship
- evidence

It still does not know:

- competing concepts

That is now the dominant architectural gap.

Without competitor awareness, the model continues to generate distractors that legitimately satisfy the same relationship.

---

# 6. Recommendation

Do not remove WP-030.

Do not continue prompt tuning around relationship wording.

Instead, build the next phase around deterministic competitor discovery.

The application should identify competing concepts before generation and provide:

- correct concept
- tested relationship
- competing concepts
- supporting evidence

The LLM should focus on expression rather than inventing the distractor space.

---

# 7. Decision

Implementation Quality: PASS

Architectural Discipline: PASS

Primary Hypothesis: NOT VERIFIED

Production Direction: KEEP

The relationship layer should remain because it is clean, deterministic and inexpensive, even though it did not achieve its primary evaluation goal.

---

# Overall Verdict

**Status: PARTIALLY ACCEPTED**

WP-030 establishes an important architectural building block.

Its greatest contribution is introducing the relationship model as a stable application concept.

The next work package should build upon this layer by introducing deterministic competitor discovery rather than further prompt engineering.
