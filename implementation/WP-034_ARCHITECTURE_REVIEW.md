# Architecture Review — WP-034

**Review Date:** 2026-08-09

**Reviewer:** ChatGPT (Architecture Review)

**WP Reviewed:** WP-034 — Coverage-Aware Target Planning

**Status:** **ACCEPTED (Negative Experimental Result)**

---

# 1. Executive Summary

WP-034 is one of the most valuable work packages completed so far, despite **not achieving its intended improvement**.

That is not a contradiction.

The purpose of WP-034 was to determine whether providing deterministic coverage information from previously generated questions would improve target planning.

The implementation successfully introduced deterministic coverage extraction, integrated it into the planning pipeline, and experimentally evaluated its impact.

The conclusion is clear:

> **The mechanism works. The hypothesis does not.**

Coverage is correctly extracted.

Coverage is correctly passed into planning.

Coverage is correctly rendered into the prompt.

The planner nevertheless continues selecting essentially the same knowledge target.

This is an excellent scientific outcome.

The project now has evidence rather than intuition.

The implementation remained completely within scope, changing only planning while leaving generation, retrieval, validation, retries, and public contracts unchanged. :contentReference[oaicite:0]{index=0}

---

# 2. Overall Assessment

| Area | Assessment |
|------|------------|
| Architectural discipline | Excellent |
| Experimental methodology | Excellent |
| Scientific honesty | Outstanding |
| Scope control | Excellent |
| Code quality | Excellent |
| Knowledge gained | Extremely high |

**Overall assessment: 10 / 10**

---

# 3. Major Strengths

## 3.1 Correct Separation Between Mechanism and Outcome

One of the strongest aspects of WP-034 is that it clearly distinguishes:

- implementation correctness;
- experimental success.

The implementation is correct.

The hypothesis failed.

Those are not the same thing.

Too many projects would have declared success because the code worked.

Instead, WP-034 honestly concludes that the intended behavioral improvement did not materialize. :contentReference[oaicite:1]{index=1}

---

## 3.2 Deterministic Coverage Model

The new internal `CategoryCoverage` model is well designed.

It is:

- deterministic;
- internal;
- immutable;
- independent of the public API.

Most importantly, it avoids introducing any new contract fields.

That decision keeps WP-033's API stable.

---

## 3.3 Excellent Scope Discipline

The implementation strictly respected the requested scope.

It did **not** modify:

- retrieval;
- validators;
- generation;
- competitors;
- relationships;
- retries;
- request contracts.

Only planning changed.

That isolation makes the experiment trustworthy. :contentReference[oaicite:2]{index=2}

---

## 3.4 Excellent Evaluation Design

The evaluation is significantly stronger than simply running another full exam.

Using one category repeatedly isolates the planner's behavior.

This removes many confounding variables.

The result is therefore much easier to interpret than previous acceptance runs.

---

# 4. Most Important Finding

The central result is remarkably simple.

The planner now knows:

```
Already Tested

↓

Superior Cerebellar Artery

↓

Relationship:

SUPPLIES
```

Yet it still plans another target using exactly the same knowledge.

This demonstrates that merely **informing** the LLM about previous coverage is insufficient.

The model continues choosing the dominant fact anyway. :contentReference[oaicite:3]{index=3}

---

# 5. Why This Happened

The completion report itself provides the correct explanation.

Coverage currently acts only as:

```
Information
```

It does **not** influence:

- retrieval;
- candidate space;
- evidence ranking.

The planner therefore still sees the strongest evidence first.

The LLM naturally selects it again.

This is entirely consistent with modern LLM behavior.

The model is following the strongest evidence available rather than optimizing long-term educational coverage.

---

# 6. The Architectural Discovery

This work package changes our understanding of where diversity should be enforced.

Originally we assumed:

```
Coverage

↓

Prompt

↓

Better Target
```

WP-034 demonstrates that this assumption is false.

Instead, the architecture must become:

```
Coverage

↓

Candidate Space

↓

Planner

↓

Prompt
```

Coverage must shape **what can be chosen**, not merely describe what has already been chosen.

That is a fundamentally different architecture.

---

# 7. Why This Is Important

This finding immediately explains several previous observations.

Categories such as:

- אספקת דם
- חומר לבן
- מבוא

have one dominant fact.

If that fact remains available during planning, the LLM will repeatedly choose it.

No amount of prompt wording is likely to change that consistently.

The planner needs stronger deterministic influence over the search space.

---

# 8. Architectural Consequences

WP-034 strongly suggests that future diversity improvements should move earlier in the pipeline.

Instead of:

```
Retrieve

↓

Prompt

↓

Ask model to avoid repetition
```

the architecture should evolve toward:

```
Retrieve

↓

Remove / De-weight Covered Knowledge

↓

Planner

↓

Generation
```

This would reduce the planner's exposure to already-tested knowledge before generation begins.

Importantly, this remains deterministic.

---

# 9. Scientific Value

One aspect deserves special recognition.

WP-034 is a **negative experiment**.

Negative experiments are often the most valuable architectural work because they eliminate entire solution classes.

This work package demonstrates that:

> "Adding deterministic coverage information to the planning prompt alone is not sufficient to produce reliable diversity."

That is now an evidence-based conclusion rather than an opinion.

Future work no longer needs to revisit this approach.

---

# 10. Recommendations

The current `CategoryCoverage` model should be retained.

It is useful.

The planner should continue computing coverage.

However, future work should not invest further effort in improving prompt wording around coverage.

Instead, future work should focus on deterministic mechanisms that influence candidate selection before planning.

Coverage should become an application-level constraint rather than advisory information for the LLM.

---

# 11. Roadmap Impact

WP-034 changes the direction of the roadmap.

The next architectural milestone should no longer focus on making the planner "more aware."

Instead, it should make the planner **more authoritative**.

The application—not the LLM—should increasingly decide which parts of the knowledge space remain eligible for selection.

Only then should the LLM perform generation within that constrained space.

---

# 12. Final Decision

**Status: ACCEPTED**

WP-034 successfully answers the architectural question it set out to investigate.

The implementation is technically correct.

The experimental methodology is sound.

The conclusion is honest.

Most importantly, the project now has strong evidence that:

> **Coverage awareness, when implemented purely as additional prompt context, is insufficient to meaningfully improve target diversity.**

This is not a failed work package.

It is a successful experiment with a negative result.

That result significantly clarifies the future architectural direction of the project and should be treated as one of the project's most valuable findings.
