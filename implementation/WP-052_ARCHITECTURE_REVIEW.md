# WP-052 Architecture Review

## Review Status

**ACCEPTED — CONTROLLED EXPERIMENT JUSTIFIED**

WP-052 produced a meaningful architectural result.

The central conclusion is:

> **Do not implement a permanent strategy selector yet, but proceed to a controlled identity-first generation experiment.**

WP-051 closed target filtering. WP-052 now provides evidence that a narrower intervention — changing the question-generation strategy while retaining the target — is worth testing.

The historical reconstruction covered **31 real generation attempts across 15 rounds**. The strongest result is:

| Target | Property attempts | Property accepted | Identity attempts | Identity accepted |
|---|---:|---:|---:|---:|
| Globus Pallidus | 4 | 1 (25%) | 4 | 3 (75%) |
| Caudate Nucleus | 8 | **0 (0%)** | 4 | **4 (100%)** |
| Nucleus Accumbens | 8 | 1 (12.5%) | 3 | **3 (100%)** |

These are the real historical counts reported by WP-052. fileciteturn38file0L27-L36

---

## 1. Main Architectural Finding

The current system has no explicit question-strategy selector.

The LLM implicitly decides what type of question/predicate to attempt on each generation attempt, with the existing prompt guidance tending toward specific properties. fileciteturn38file0L15-L17

This produces the pattern:

```text
Target
  ↓
PROPERTY attempt
  ↓
failure
  ↓
PROPERTY attempt
  ↓
failure
  ↓
IDENTITY
  ↓
success
```

The potential improvement is therefore not:

```text
skip target
```

but:

```text
choose a better initial question strategy
```

---

## 2. Why This Is Real Progress

For Caudate Nucleus:

```text
PROPERTY = 0/8
IDENTITY = 4/4
```

This is the cleanest signal found so far.

For Nucleus Accumbens:

```text
PROPERTY = 1/8
IDENTITY = 3/3
```

This also strongly favors identity, although the one property success has unresolved grounding concerns.

For Globus Pallidus:

```text
PROPERTY = 1/4
IDENTITY = 3/4
```

and there is a genuinely evidence-supported distinguishing property.

Therefore the data does **not** justify:

```text
always identity
```

It supports a conditional hypothesis:

```text
some targets → identity-first
some targets → retain property generation
```

---

## 3. Critical Caveat: Historical Identity Success Is Retrospective

The 100% identity success for Caudate and Nucleus Accumbens must not be interpreted as:

```text
identity always succeeds
```

The identity attempts were often made **after property attempts had already failed**.

Therefore the historical data does not prove that an explicit identity-first instruction will also succeed at 100%.

This is the central unanswered causal question.

WP-052 explicitly identifies this limitation and recommends a controlled experiment. fileciteturn38file0L84-L88

---

## 4. Directly Observed Attempt Savings

WP-052 identifies:

```text
8 directly observed attempts
```

that could have been avoided in rounds that eventually reached identity.

These are not hypothetical: they are property attempts that actually preceded an identity attempt in the same historical round. fileciteturn38file0L84-L88

This gives us a concrete optimization opportunity.

There are also:

```text
up to 9 additional attempts
```

from three exhausted property-only rounds, but that is explicitly a hypothesis because identity was never attempted there. fileciteturn38file0L84-L88

---

## 5. The Three Exhausted Rounds

The most interesting hypothetical cases are:

```text
WP-047 r2 — Nucleus Accumbens
WP-047 r3 — Nucleus Accumbens
WP-049 r1 — Caudate Nucleus
```

All exhausted their available attempts on PROPERTY.

The hypothesis is:

```text
IDENTITY first
    ↓
possibly accepted
```

But this must be tested rather than assumed.

---

## 6. Globus Pallidus Is the Safety Counterexample

Globus Pallidus has real target-specific evidence:

```text
thalamus suppression via GPi in the direct pathway
```

and the report identifies this as corroborated across independent evidence chunks. fileciteturn38file0L40-L44

Therefore we must not implement:

```text
weak evidence → identity
```

as a universal rule.

The future mechanism must preserve:

```text
Globus Pallidus → property generation remains available
```

---

## 7. Nucleus Accumbens Must Remain Cautious

The Nucleus Accumbens property success is:

```text
1/8
```

and is the previously flagged reward-system question.

WP-052 correctly leaves the property availability status as:

```text
UNKNOWN / uncertain
```

because the supplied evidence appears category-level rather than clearly target-specific. fileciteturn38file0L40-L44

Therefore:

```text
IDENTITY-preferred
```

is an experimental hypothesis, not a permanent fact.

---

## 8. The Chunk-Count Signal Is Not Yet Production-Ready

WP-051's distinct-chunk signal remains interesting:

```text
Globus Pallidus       = 5
Caudate Nucleus       = 2
Nucleus Accumbens     = 2
```

It is deterministic and automatable, but it has only been observed on:

```text
one category
three targets
```

The accurate signal — full manual evidence analysis — is not currently automatable without introducing semantic extraction or per-target hard-coding, both of which are outside the approved direction. fileciteturn38file0L50-L60

Therefore:

```text
chunk count = experimental signal
```

not:

```text
production rule
```

---

## 9. The Retrospective Probe Was Appropriate

The uploaded `wp052_strategy_probe.py` is explicitly prototype-only.

It reads the real historical pilot records and classifies generated questions deterministically as PROPERTY or IDENTITY; it is never imported by `src/` and makes no LLM calls. fileciteturn38file1L1-L19

That is appropriate for this investigation.

It must not be promoted into production strategy selection.

Its role is:

```text
measure what happened
```

not:

```text
decide what should happen
```

---

## 10. Three-State Strategy Concept

A future strategy mechanism should conceptually allow:

```text
PROPERTY
IDENTITY
UNKNOWN
```

rather than forcing every target into PROPERTY or IDENTITY.

The important distinction is:

```text
property not detected
        ≠
property does not exist
```

The Globus Pallidus evidence outside its narrow factual focus demonstrates why this matters. WP-052 re-confirmed that the useful property is reachable through full cross-chunk evidence rather than its narrow/broad anchor. fileciteturn38file0L46-L48

---

## 11. Desired Future Architecture

If the controlled experiment succeeds, the conceptual architecture should become:

```text
Target
   ↓
Strategy assessment
   ↓
 ┌──────────────────────────────┐
 │                              │
PROPERTY                    IDENTITY
 │                              │
 ↓                              ↓
property generation        identity generation
 │                              │
 └──────────────┬───────────────┘
                ↓
        existing validators
```

With uncertainty:

```text
UNKNOWN
    ↓
current/default behavior
```

The exact permanent mechanism must wait until the experiment is complete.

---

## 12. No Production Change Yet

WP-052 correctly made:

```text
NO production code changes
NO prompt changes
NO new validator
NO target filtering
NO schema changes
NO external knowledge
```

The completion report records the implementation as prototype-only and regression as not applicable. fileciteturn38file0L146-L152

This is the correct decision.

---

## 13. Question Diversity

Identity-first generation may reduce question-shape diversity for:

```text
Caudate Nucleus
Nucleus Accumbens
```

because property attempts would be reduced.

This is a real tradeoff and must be measured in the next experiment.

However, it does not affect target coverage because the target itself remains selected. WP-052 explicitly reports no coverage impact. fileciteturn38file0L94-L100

---

## 14. Existing Validators Remain Mandatory

Strategy selection must never mean:

```text
identity question = automatically valid
```

The existing validation pipeline remains the safety boundary.

Any future strategy must still pass the existing grounding, MCQ, category, quality, textbook, and relevant target-identity/containment checks.

---

## 15. Recommended WP-053

# WP-053 — Identity-First Generation Controlled Experiment

The exact question should be:

> **If Caudate Nucleus and Nucleus Accumbens are explicitly instructed to attempt an identity-based question on the first attempt, does first-attempt acceptance improve without reducing accepted output or violating existing validation rules?**

Experimental scope:

```text
EXPERIMENTAL:
    Caudate Nucleus
    Nucleus Accumbens

CONTROL:
    current generation behavior

EXCLUDED FROM IDENTITY-FIRST:
    Globus Pallidus
```

Use:

```text
one fresh live pilot
no reruns
same three-attempt budget
same source evidence
same validators
same output schema
no production implementation
```

This matches WP-052's explicit recommendation. fileciteturn38file0L161-L163

---

## 16. WP-053 Must Measure

At minimum:

```text
first-attempt acceptance rate
final acceptance rate
attempts per accepted question
identity-question rate
property-question rate
validation failures
grounding failures
question diversity
```

The key causal test is:

```text
Does identity-first actually work immediately?
```

rather than merely:

```text
Does identity work eventually?
```

---

## 17. WP-053 Success Criteria

The strategy becomes a serious production candidate only if the experiment demonstrates:

```text
1. materially improved first-attempt acceptance;
2. no meaningful loss of accepted output;
3. fewer attempts per accepted question;
4. no validation regression;
5. no grounding regression;
6. no coverage regression;
7. acceptable diversity impact.
```

Token/API savings alone are not sufficient.

---

## 18. What Happens After WP-053

If successful:

```text
WP-054
→ design permanent strategy-selection implementation
```

If unsuccessful:

```text
close identity-first direction
```

If mixed:

```text
investigate a narrower conditional strategy
```

No permanent architecture should be chosen before seeing the experiment.

---

# Final Architectural State

```text
WP-046
parent/child ambiguity
        ↓
SOLVED

WP-047
target identity substitution
        ↓
SOLVED for current scope

WP-048
classification ambiguity
        ↓
existing validators detect it

WP-049
prompt avoidance
        ↓
INCONCLUSIVE

WP-050
candidate uniqueness
        ↓
no safe general uniqueness mechanism

WP-051
target evidence sufficiency
        ↓
target filtering would discard valid output
        ↓
TARGET FILTERING CLOSED

WP-052
question strategy selection
        ↓
strong empirical signal found
        ↓
production implementation NOT YET JUSTIFIED
        ↓
CONTROLLED EXPERIMENT JUSTIFIED

WP-053
identity-first controlled experiment
        ↓
NEXT
```

# Final Decision

**WP-052 — ACCEPTED.**

```text
TARGET FILTERING
    CLOSED

STRATEGY SELECTION
    PROMISING

PRODUCTION IMPLEMENTATION
    NOT YET

CONTROLLED EXPERIMENT
    APPROVED
```

The main issue is now much more clearly defined.

We are no longer asking:

```text
"How do we force the LLM to find a unique property?"
```

or:

```text
"Which targets should we discard?"
```

We are asking:

```text
"For targets where property generation appears empirically futile,
can we safely choose a better question strategy before generation?"
```

That is a meaningful next step.

**WP-052: ACCEPTED.**

**Recommended next WP: WP-053 — Identity-First Generation Controlled Experiment.**
