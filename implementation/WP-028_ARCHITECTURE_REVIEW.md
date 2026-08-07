# Architecture Review — WP-028

**Review Date:** 2026-08-07

**Reviewer:** Architecture Review

**WP Reviewed:** WP-028 — Blueprint-Driven Question Generation

**Status:** NOT ACCEPTED (implementation correct, architectural hypothesis rejected)

---

# 1. Executive Summary

WP-028 implemented exactly what was requested.

Generation now constructs an explicit internal blueprint before producing the final MCQ while preserving the existing architecture:

- no additional LLM calls;
- no validator changes;
- no orchestration changes;
- no retrieval changes;
- no pipeline changes.

The implementation itself is clean, localized, and respects the project's architectural boundaries.

However, the measured results demonstrate that the architectural hypothesis behind WP-028 is incorrect.

The objective of WP-028 was to improve first-pass generation quality while leaving the validation architecture unchanged.

Instead, the live evaluation showed:

- fewer accepted questions,
- more total candidate attempts,
- more grounding rejections,
- more MCQ rejections,
- more quality rejections.

The blueprint increased generation complexity but did not improve generation quality.

This should be viewed as a successful engineering experiment that disproved an architectural idea rather than as an implementation failure.

---

# 2. Positive Architectural Aspects

## 2.1 Architectural Isolation

The implementation respected every major architectural boundary.

No modifications were made to:

- validation
- orchestration
- production
- retrieval
- planning
- acceptance policy

This level of architectural discipline is excellent and should remain the project's standard.

---

## 2.2 Consistent Internal Model Pattern

The blueprint follows the architectural pattern already established elsewhere in the project:

LLM-facing model

↓

deterministic conversion

↓

stable public model

The generator automatically discards blueprint information before constructing CandidateQuestion.

Therefore the blueprint cannot leak downstream.

This is a clean design.

---

## 2.3 Honest Evaluation

The completion report deserves special credit.

Rather than highlighting isolated improvements, it explicitly states that the primary success metric moved in the wrong direction.

This project has consistently benefited from evidence-driven decision making, and WP-028 continues that standard.

---

# 3. Architectural Hypothesis

WP-028 was based on the following hypothesis:

More explicit internal planning

↓

better generated MCQs

↓

fewer validation failures

↓

higher first-pass acceptance

The implementation faithfully realized this hypothesis.

The live measurements do not support it.

---

# 4. Why the Idea Failed

The blueprint exists entirely inside the same LLM call that generates the question.

Therefore:

the generator verifies itself.

This is fundamentally different from the architectural direction established throughout previous work packages.

Earlier successful WPs repeatedly moved responsibility away from self-reported model claims toward independently verified application logic.

Examples include:

- provenance verification
- deterministic evidence resolution
- independent grounding
- deterministic grounding derivation

WP-028 moves in the opposite direction.

The model now states:

"I checked the evidence."

Nothing independently confirms that this actually occurred.

---

# 5. Self-Reported Planning Is Not Architectural Constraint

The blueprint documents reasoning.

It does not constrain reasoning.

The model is still free to produce:

excellent blueprint

↓

poor distractors

↓

validator rejection

There is no deterministic relationship between blueprint quality and generated question quality.

Consequently the blueprint functions as documentation rather than control.

---

# 6. Comparison with Previous Successful WPs

The strongest work packages in the project shared one important property:

They changed application behavior.

Examples:

- WP-020 – Provider-level structured-output recovery.
- WP-021 – Validator provenance recovery.
- WP-022 – Deterministic evidence-reference resolution.
- WP-023 – Partial exam semantics.
- WP-027 – Deterministic grounding derivation from per-answer evidence.

Each of these altered the system's behavior independently of what the LLM happened to claim.

WP-028 instead attempts to improve the model's internal reasoning.

The results suggest this is a significantly weaker lever.

---

# 7. What Should Not Be Done

Based on WP-028's results, the following directions are not recommended:

- richer blueprints;
- additional blueprint fields;
- blueprint persistence;
- blueprint auditing;
- blueprint validation;
- more distractor archetypes;
- larger planning sections inside the prompt.

These changes would almost certainly increase prompt complexity without providing corresponding improvements in correctness.

---

# 8. The Real Bottleneck

WP-027 revealed the dominant remaining problem:

Grounding rejected many candidates because another answer was also supported.

WP-028 did not significantly reduce that failure mode.

This indicates that the core problem is not planning.

The core problem is distractor synthesis.

Generation still struggles to produce distractors that are:

- educationally plausible;
- factually incorrect;
- unique;
- evidence-consistent.

That is now the primary architectural bottleneck.

---

# 9. Recommended Future Direction

Rather than investing further in blueprint-driven generation, the project should move toward:

**Evidence-Constrained Distractor Synthesis.**

The key idea is:

Do not ask the model to invent distractors freely.

Instead, generate distractors by systematically transforming the supplied evidence.

Possible transformation strategies include:

- sibling substitution;
- hierarchy inversion;
- function substitution;
- location substitution;
- developmental-stage substitution;
- terminology substitution.

Candidate distractors should then be filtered against the authoritative evidence before finalization.

This directly targets the dominant rejection cause identified by WP-027.

---

# 10. Lessons Learned

WP-028 demonstrates an important architectural principle.

Prompt engineering has diminishing returns.

The project's largest improvements have consistently resulted from:

- deterministic application logic;
- independent validation;
- explicit trust boundaries;
- structured contracts.

Future work should continue strengthening these areas rather than increasing prompt complexity.

---

# 11. Decision

**Implementation Quality:** PASS

**Architectural Discipline:** PASS

**Architectural Hypothesis:** FAIL

**Production Adoption:** DO NOT ADOPT as the long-term architectural direction.

The implementation is clean and harmless and should remain in the repository as part of the project's history.

However, it should not become the basis for future work.

Future improvements should focus on evidence-constrained distractor synthesis rather than blueprint-driven planning.

---

# Overall Verdict

**Status: NOT ACCEPTED**

The implementation faithfully executed the WP specification.

The measurements clearly demonstrate that the architectural premise was incorrect.

This is therefore considered a successful engineering experiment that disproved an architectural idea through objective evidence.

The next work package should build on this new knowledge rather than extending blueprint-driven generation.
