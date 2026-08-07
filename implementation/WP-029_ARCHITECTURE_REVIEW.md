
# Architecture Review — WP-029

**Review Date:** 2026-08-07

**Reviewer:** Architecture Review

**WP Reviewed:** WP-029 — Distractor Synthesis Architecture

**Status:** ACCEPTED (Architecture Proposal)

---

# 1. Executive Summary

WP-029 is the strongest architectural design document produced so far in the project.

Unlike WP-028, it does not attempt to solve the problem immediately through implementation. Instead, it performs an evidence-based architectural investigation, identifies the dominant remaining bottleneck, evaluates several alternative designs, and proposes a phased migration path without modifying production behavior.

The proposal correctly concludes that the dominant remaining weakness is no longer retrieval, provenance, structured output, or validation architecture. The principal bottleneck is distractor synthesis.

The proposal is therefore accepted as the architectural foundation for future work.

---

# 2. Major Strengths

## 2.1 Correct Identification of the Bottleneck

The proposal correctly identifies distractor synthesis as the remaining dominant source of generation failures.

This matches all empirical observations gathered from WP-025 through WP-028.

The generator no longer primarily fails because of:

- provenance
- retrieval
- structured output
- validation architecture

Instead, failures are dominated by weak distractors.

This conclusion is strongly supported by the project's accumulated evidence.

---

## 2.2 Preserves Existing Architecture

One of the strongest aspects of the proposal is that it deliberately preserves every mature subsystem.

It does not require architectural changes to:

- QuestionProducer
- validators
- acceptance policy
- retry architecture
- retrieval
- orchestration

These components have become stable and should remain stable.

---

## 2.3 Avoids Additional Validation Layers

The proposal correctly rejects adding another validator or another LLM verification stage.

This is consistent with the project's long-standing architectural philosophy:

Improve candidate quality before validation.

Do not weaken validation.

Do not multiply reviewers.

---

## 2.4 Moves Intelligence into the Application

The proposal shifts responsibility away from unrestricted prompt engineering toward deterministic application guidance.

This is fully aligned with the evolution of the project from WP-020 onward.

Previous successful work packages consistently moved intelligence into deterministic application logic rather than relying on additional model reasoning.

---

# 3. Architectural Concerns

Although the proposal is accepted, several architectural observations should guide future work.

## 3.1 Distractor Archetypes Should Not Become the Main Abstraction

The proposal places considerable emphasis on distractor archetypes.

These labels are useful as implementation tools.

However, they should not become the primary architectural abstraction.

Knowing that a distractor is a "Sibling Substitution" does not significantly constrain generation.

The model still retains considerable freedom.

Archetypes should remain implementation details rather than central architectural concepts.

---

## 3.2 QuestionTarget Should Remain Focused

QuestionTarget currently answers one question:

"What should this question test?"

The proposal suggests expanding it with generation-oriented information.

Care should be taken not to overload QuestionTarget with generation policy.

If additional generation planning becomes necessary, a dedicated planning object may provide a cleaner separation of responsibilities.

---

## 3.3 Evidence Anchoring Alone Is Insufficient

The proposal correctly recommends evidence-anchored distractor construction.

However, evidence alone does not define the educational relationship being tested.

For example:

Correct concept:
Association fibers

Relationship:
connect

Property:
same hemisphere

The educational relationship ("connects") is more important than the evidence chunk itself.

Future work should explicitly represent relationships in addition to evidence.

---

# 4. Missing Architectural Layer

The proposal still thinks primarily in terms of distractors.

A stronger abstraction would be:

Concept

↓

Relationship

↓

Competing concepts

↓

Question

instead of

Evidence

↓

Distractor generation

The application should explicitly understand:

- the correct concept
- the tested relationship
- the competing concepts

Generation would then become substantially more constrained before the LLM begins producing text.

---

# 5. Preferred Evolution

Instead of focusing on increasingly sophisticated distractor archetypes, future work should progressively move toward:

Relationship-driven generation

Competitor-aware generation

Application-guided construction

The LLM should receive:

- correct concept
- relationship
- competing concepts
- supporting evidence

Its task then becomes expression rather than invention.

---

# 6. Diversity

One particularly attractive consequence of this evolution is diversity.

Today's diversity is mostly:

Topic diversity

Future diversity could naturally include:

- relationship diversity
- competitor diversity
- evidence diversity

without introducing additional validators or LLM calls.

---

# 7. Recommended Direction for WP-030

The proposal's migration plan is strong, but future implementation should place slightly greater emphasis on semantic relationships than on distractor archetypes.

A preferred implementation sequence would be:

Phase 1
- relationship extraction

Phase 2
- competitor extraction

Phase 3
- relationship-constrained generation

This provides stronger deterministic guidance than archetype selection alone.

---

# 8. Architectural Assessment

| Area | Assessment |
|------|------------|
| Problem identification | Excellent |
| Evidence-based reasoning | Excellent |
| Respect for existing architecture | Excellent |
| Cost awareness | Excellent |
| Migration roadmap | Very Good |
| Long-term architectural direction | Very Good |

Overall assessment: **9.5/10**

---

# 9. Decision

**Status: ACCEPTED**

WP-029 successfully fulfills its purpose as an architecture work package.

It correctly identifies the project's remaining bottleneck, evaluates realistic alternatives, and proposes a migration strategy that preserves the project's core architectural principles.

The only recommended refinement is to elevate future work from distractor-archetype thinking toward concept–relationship–competitor modeling, allowing the application—not the LLM—to increasingly control question construction.

This document should serve as the architectural basis for planning WP-030.
