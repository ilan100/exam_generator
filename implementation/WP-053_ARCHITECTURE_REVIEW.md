# WP-053 Architecture Review

## Review Status

**ACCEPTED WITH SCOPE CAUTION**

WP-053 produced a meaningful result and justifies moving to WP-054.

The correct conclusion is:

> Identity-first is experimentally supported for the two tested targets, but this does **not** establish a general rule for sparse-evidence targets.

The experiment used the real `QuestionGenerator`, `QuestionProducer`, five real validators, the real OpenAI API, and the real three-attempt budget. The experimental change was only an in-memory identity-first instruction; the production prompt on disk was not changed. fileciteturn39file1L3-L20

---

## 1. Experimental Result

Fresh results:

| Target | Identity-first | Current control |
|---|---|---|
| Caudate Nucleus | attempt 1 accepted | 3 attempts rejected |
| Nucleus Accumbens | attempt 1 accepted | attempt 1 accepted, hybrid identity/membership |

Thus:

```text
IDENTITY-FIRST: 2/2 accepted, 2/2 on attempt 1
CURRENT CONTROL: 1/2 accepted, 1/2 on attempt 1
```

The completion report records these results directly. fileciteturn39file0L66-L88

The historical WP-052 baseline was:

```text
Caudate:
PROPERTY 0/8
IDENTITY 4/4

Nucleus Accumbens:
PROPERTY 1/8
IDENTITY 3/3
```

fileciteturn39file0L56-L62

This fresh experiment therefore supports the historical signal.

---

## 2. Attempt Efficiency

The fresh comparison produced:

```text
Identity-first:
2 attempts → 2 accepted rounds
1.0 attempt / accepted round

Current control:
4 attempts → 1 accepted round
```

The direct saving is therefore **2 generation attempts** in this fresh comparison. fileciteturn39file0L90-L92

This is especially important because the goal is not merely better-looking questions; it is to stop spending retry attempts on a strategy that repeatedly fails.

---

## 3. Strategy Compliance

The experimental instruction worked:

```text
2/2
100%
```

Both experimental questions were identity-shaped on their first attempt. fileciteturn39file0L94-L96

Therefore we do not need a more complicated prompt mechanism merely to make the model attempt identity first.

---

## 4. Validation and Grounding

No validators were weakened or bypassed.

Accepted experimental questions passed the normal validation pipeline, while rejected control attempts were rejected normally. fileciteturn39file0L98-L104

This preserves the correct architectural boundary:

```text
strategy selection
    ↓
generation
    ↓
existing validators
```

The strategy must never become a substitute for validation.

---

## 5. Globus Pallidus Safety Result

This is a strong positive result.

The experiment constructed a separate experimental prompt repository only for:

```text
Caudate Nucleus
Nucleus Accumbens
```

while Globus Pallidus always used the unmodified repository. fileciteturn39file1L17-L20

Globus Pallidus subsequently succeeded through a genuine location-based property question on attempt 3. fileciteturn39file0L112-L114

Therefore:

```text
Globus Pallidus must NOT be identity-forced.
```

---

## 6. Important Limitation

The experiment is small:

```text
2 rounds experimental
2 rounds current control
```

The completion report correctly states that this is not a statistically significant validation study. fileciteturn39file0L132-L134

Therefore we should **not** conclude:

```text
identity-first is generally better.
```

We can conclude:

```text
identity-first is sufficiently supported for these two specific
targets to justify a narrow permanent implementation.
```

The historical WP-052 evidence is important because it provides the larger retrospective context.

---

## 7. Different Strength of Evidence Per Target

### Caudate Nucleus

This is the strongest case:

```text
Historical:
PROPERTY 0/8
IDENTITY 4/4

Fresh:
CONTROL 0/1
IDENTITY-FIRST 1/1
```

A narrow identity-first rule is well justified.

### Nucleus Accumbens

Evidence is positive but weaker:

```text
Historical:
PROPERTY 1/8
IDENTITY 3/3

Fresh:
CONTROL 1/1 hybrid
IDENTITY-FIRST 1/1
```

The fresh control succeeded immediately, but its question was a hybrid identity/membership question. fileciteturn39file0L108-L118

Therefore the evidence still supports identity-first, but we should not claim that the experiment independently proves property-first failure for Nucleus Accumbens.

---

## 8. Diversity

Both experimental successes were identity-shaped:

```text
0% property diversity
```

in the tiny experimental sample.

This is an expected tradeoff.

Historical property success was already:

```text
Caudate: 0/8
Nucleus Accumbens: 1/8
```

so the evidence suggests that much of the sacrificed property diversity was not productive.

Nevertheless, diversity should be monitored after implementation. fileciteturn39file0L106-L110

---

## 9. Coverage

Coverage was deliberately outside the experiment because targets were constructed directly rather than through the coverage planner. fileciteturn39file0L52-L54

Therefore the correct statement is:

```text
NO COVERAGE REGRESSION OBSERVED
```

not:

```text
coverage was experimentally proven.
```

WP-054 must add regression tests for the strategy lookup without changing coverage behavior.

---

## 10. Hard-Coded Scope Is Acceptable for WP-054

WP-053 deliberately tested:

```text
Caudate Nucleus
Nucleus Accumbens
```

and did not attempt to solve general target classification.

That is the correct scope.

Do **not** generalize using:

```text
chunk_count
sparse evidence
historical failure count
```

as a general identity-first selector.

Those signals are not validated at scale.

---

## 11. Recommended Permanent Architecture

WP-054 should implement a small explicit strategy preference:

```text
(category, target)
        ↓
strategy preference
        ↓
IDENTITY_FIRST or DEFAULT
```

Initial mapping:

```text
גרעיני הבסיס + Caudate Nucleus
    → IDENTITY_FIRST

גרעיני הבסיס + Nucleus Accumbens
    → IDENTITY_FIRST

everything else
    → DEFAULT
```

Then:

```text
strategy preference
        ↓
generation context/prompt
        ↓
existing QuestionGenerator
        ↓
existing QuestionProducer
        ↓
existing validators
```

Do not add a validator, retry mechanism, target filter, retrieval system, or schema change.

---

## 12. Prefer an Explicit Strategy Abstraction

Avoid burying:

```text
if target == ...
```

inside the generator or prompt.

A small explicit abstraction such as:

```text
GenerationStrategyPreference
    DEFAULT
    IDENTITY_FIRST
```

with a narrowly scoped resolver is preferable.

The reason is architectural clarity:

```text
strategy preference
```

is a generation policy, not an intrinsic property of the target model.

This makes the exception visible, testable, and removable.

---

## 13. WP-054 Regression Requirements

At minimum:

```text
Caudate + גרעיני הבסיס
    → IDENTITY_FIRST

Nucleus Accumbens + גרעיני הבסיס
    → IDENTITY_FIRST

Globus Pallidus + גרעיני הבסיס
    → DEFAULT

another target + גרעיני הבסיס
    → DEFAULT

Caudate/Nucleus Accumbens + another category
    → DEFAULT
```

This proves the rule is neither:

```text
target-global
```

nor:

```text
category-global.
```

---

## 14. Language Compliance Issue

There is one important issue that WP-054 must explicitly address.

The project rule is:

```text
If English exists, use English.
Use Hebrew only when no English representation exists.
```

Yet the experimental generated questions contain Hebrew around English target names, for example:

```text
"...הנקרא Caudate Nucleus?"
"...הגרעין הנקרא Nucleus Accumbens?"
```

fileciteturn39file0L66-L69

If the project-wide language rule remains as previously established, these outputs are **not compliant** with that rule.

The fact that the existing validators accepted them does not prove language compliance.

This does **not** invalidate the identity-first experiment, because the experiment tested strategy selection. But WP-054 must explicitly verify and preserve the English-first/no-Hebrew-when-English-exists requirement.

Do not silently carry the experimental language behavior into production.

---

## 15. What WP-054 Should NOT Do

Do not implement:

```text
if sparse evidence:
    identity-first
```

Do not implement:

```text
if <= 2 chunks:
    identity-first
```

Do not implement:

```text
if property failed historically:
    identity-first
```

Do not implement:

```text
all named entities → identity-first
```

Do not implement:

```text
all targets in גרעיני הבסיס → identity-first
```

Only the two empirically studied targets are approved at this point.

---

# Final Decision

**WP-053 — ACCEPTED.**

Decision:

```text
Proceed to permanent implementation.
```

But with a strict boundary:

```text
Caudate Nucleus
+
Nucleus Accumbens
+
גרעיני הבסיס
```

only.

No generalization.

---

# Recommended WP-054

## WP-054 — Narrow Permanent Identity-First Strategy Implementation

Implement the smallest permanent mechanism that:

```text
selects IDENTITY_FIRST for the two approved target/category pairs
```

while leaving:

```text
all other targets
all other categories
Globus Pallidus
```

on the current behavior.

Preserve:

```text
three-attempt budget
existing validators
existing JSON schemas
existing source authority
target coverage
existing retrieval
English-first rule
```

Add regression tests for all scope boundaries.

The implementation should be explicit, isolated, and easy to extend later if future evidence supports additional targets.

---

# Final Architectural State

```text
WP-051
Target filtering
    ↓
CLOSED

WP-052
Historical strategy analysis
    ↓
Identity-first hypothesis supported

WP-053
Fresh controlled experiment
    ↓
Identity-first experimentally supported
for two named targets
    ↓
NARROW IMPLEMENTATION JUSTIFIED

WP-054
Permanent narrow implementation
    ↓
NEXT
```

**WP-053: ACCEPTED WITH SCOPE CAUTION.**

**Recommended next step: WP-054 — Narrow Permanent Identity-First Strategy Implementation.**
