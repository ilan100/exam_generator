# WP-051 Architecture Review

## Review Status

**ACCEPTED — DIAGNOSTIC RESULT / TARGET-SELECTION FILTERING CLOSED**

WP-051 produced a clear architectural decision:

> **Do not implement target-selection filtering based on evidence sufficiency.**

The investigation found one interesting deterministic signal — distinct-chunk mention count — but it answers a narrower question than target selection actually needs. It correlates with the presence of distinguishing-property evidence, but it does not establish that a target is incapable of producing **any** valid question.

This distinction is decisive because `Caudate Nucleus` and `Nucleus Accumbens` still produced **8 accepted questions in 11 real historical rounds (72.7%)**, all through the bare-identity/naming question shape. fileciteturn37file1L94-L106

A hard pre-generation skip would therefore discard valid product output.

---

## 1. What WP-051 Established

The current target-selection flow is:

```text
category
  ↓
retrieve_for_category()
  ↓
refine_concept_inventory()
  ↓
coverage filtering
  ↓
per-concept evidence checks
  ↓
QuestionTarget
  ↓
generation
```

The existing planner already has pre-generation skip checks for factual-focus sufficiency and enumeration insufficiency. A future check would technically fit into the same loop. fileciteturn37file1L15-L38

However, the investigation shows that adding another skip condition is **not justified**.

---

## 2. Full Evidence Is Already Available

At target-selection time the system already has:

```text
concept evidence_chunk_id
factual_focus
source_line_indices
full retrieved source_evidence
CategoryCoverage
existing questions
```

What it does not have is a structured cross-candidate property representation or a per-concept multi-chunk count. fileciteturn37file1L40-L44

Therefore the problem is not a missing retrieval call.

---

## 3. Existing Signals Do Not Solve It

Six of the seven investigated signals had no discriminating power across:

```text
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens
```

These included:

```text
non-enumerative evidence
non-empty factual_focus
relationship != UNSPECIFIED
explicit target property
target-specific relationship
full-evidence keyword proximity
```

The direct probe confirmed that these signals either returned the same result for all three targets or were confounded by the shared enumeration passage. fileciteturn37file1L79-L88

Do not turn these into production rules.

---

## 4. The Interesting Signal

The one signal that separated the three targets was:

```text
distinct retrieved chunks mentioning the target
```

Observed:

```text
Globus Pallidus       = 5
Caudate Nucleus       = 2
Nucleus Accumbens     = 2
```

This is a legitimate research observation. fileciteturn37file1L64-L68

But it is only a **correlate**, not a semantic guarantee.

A target can appear in multiple chunks because of repeated enumeration, while a useful property can exist in a single chunk.

The report correctly keeps this as a research finding rather than a production rule. fileciteturn37file1L155-L156

---

## 5. The Decisive Historical Test

Suppose we implement:

```text
distinct_chunk_count <= 2
    ↓
skip target
```

Historical replay shows:

```text
Globus Pallidus:
4/4 accepted
count = 5
→ not skipped

Caudate + Nucleus Accumbens:
8/11 accepted
count = 2
→ all would have been skipped
```

Those eight accepted questions would be lost.

The same rule would save only the three exhausted rounds, corresponding to nine failed attempts. fileciteturn37file1L90-L116

Therefore:

```text
9 wasted attempts avoided
vs.
8 valid accepted questions lost
```

is clearly not an acceptable product tradeoff.

---

## 6. The Key Architectural Distinction

WP-051 exposes the distinction we were missing:

```text
insufficient for a distinguishing-property question
        ≠
insufficient for any valid question
```

For:

```text
Caudate Nucleus
Nucleus Accumbens
```

the evidence may be insufficient for a safe target-specific property predicate, but the system can still generate:

```text
identity / naming questions
```

successfully.

Therefore the target itself remains eligible.

The thing that may need to change is the **question strategy**, not target selection.

---

## 7. Why Target Filtering Must Be Closed

The architectural decision is:

```text
NO target-selection filtering
```

This should now be considered a **closed production direction** unless substantially new evidence appears.

Do not create future WPs that repeatedly revisit:

```text
"Should we skip targets with sparse evidence?"
```

The current answer is:

```text
No.
```

The measured historical data is sufficient to reject that approach for the current architecture.

---

## 8. The Better Next Question

The completion report identifies the more promising direction:

> Can generation be told, deterministically and safely, when a target is known to lack a distinguishing property, so it skips directly to a bare-identity question instead of spending attempts on a doomed property-based one? fileciteturn37file1L155-L161

I agree.

This changes:

```text
TARGET SELECTION
```

into:

```text
QUESTION STRATEGY SELECTION
```

The target is not discarded.

Only the strategy is changed.

---

## 9. Desired Future Flow

Potential future architecture:

```text
Target
  ↓
Evidence analysis
  ↓
Known distinguishing property?
  ├── YES → property-based generation
  │
  └── NO → identity-based generation
```

This is preferable to:

```text
Target
  ↓
evidence insufficient
  ↓
SKIP TARGET
```

because it preserves the 8/11 accepted outputs already demonstrated by the real historical data.

---

## 10. Do Not Implement This Yet

WP-051 does **not** establish that the system can safely determine:

```text
"No distinguishing property is known."
```

The Globus Pallidus case is an important warning: its useful distinguishing fact is present in broader/full evidence but not its narrow factual focus.

Therefore a simplistic rule based on:

```text
factual_focus
```

could incorrectly conclude that Globus Pallidus has no useful property.

No production implementation is justified yet.

---

## 11. Do Not Add More Prompt Rules

WP-049 already tested prompt-based avoidance and was inconclusive.

WP-050 investigated candidate uniqueness.

WP-051 investigated target evidence sufficiency.

The next step should **not** be another large prompt expansion.

The architectural question is now narrower:

```text
Can we select the generation strategy before generation?
```

---

## 12. Do Not Add a New Validator

This is not a final-question correctness condition.

The existing validators should remain responsible for:

```text
grounding
MCQ correctness
target identity
distractor containment
quality
```

A future strategy-selection mechanism would operate **before** generation.

---

## 13. Do Not Add an LLM Judge

Do not implement:

```text
LLM A → generate
LLM B → decide whether a property exists
```

The current investigation is explicitly about whether existing evidence can provide a deterministic signal.

---

## 14. Do Not Use External Medical Knowledge

Keep the existing authority model:

```text
student summaries
    = factual authority

course_book.pdf
    = secondary consistency check

historical Excel
    = style/structure reference
```

Do not introduce:

```text
web
UMLS
SNOMED
external knowledge graph
external medical database
```

to solve this problem.

---

## 15. Bare-Identity Questions Are a Legitimate Strategy

WP-051 gives us important evidence that identity questions should not be treated as merely failed property questions.

For the difficult targets:

```text
Caudate Nucleus
Nucleus Accumbens
```

the historical data shows:

```text
8 accepted / 11 rounds
```

using the identity/naming shape. fileciteturn37file1L94-L106

Therefore identity generation is a legitimate product strategy.

However, we must not overcorrect and force identity questions for every target.

---

## 16. Preserve Question Diversity

The opposite risk is:

```text
avoid ambiguity
    ↓
always use identity questions
```

That would reduce question diversity.

`Globus Pallidus` demonstrates that a target-specific property question can exist.

Therefore a future mechanism must distinguish:

```text
known useful property
```

from:

```text
no known useful property
```

rather than simply preferring identity questions.

---

## 17. Full Evidence Must Be Considered

Any future strategy-selection study must inspect:

```text
full authoritative evidence
```

not only:

```text
narrow factual_focus
```

WP-051 confirmed that the useful Globus Pallidus evidence is not exposed by its narrow/broad anchor in the current form. fileciteturn37file1L64-L68

This is a critical constraint.

---

## 18. Production Changes

WP-051 correctly made:

```text
NO production changes
```

The signal probe was:

```text
prototype-only
read-only
zero LLM calls
zero new production logic
```

and the report confirms no source/test modifications. fileciteturn37file1L11-L13

Regression is therefore:

```text
NOT APPLICABLE
```

fileciteturn37file1L147-L151

---

## 19. Final Architectural State

The current progression is:

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
existing validators already detect it

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
TARGET-SELECTION FILTERING CLOSED
```

This is meaningful progress: several tempting architectural directions have now been investigated and ruled out for concrete reasons.

---

## 20. Final Decision

**WP-051 — ACCEPTED.**

Decision:

```text
NO target-selection filtering.
NO new evidence-sufficiency validator.
NO production changes.
```

The distinct-chunk signal remains:

```text
RESEARCH FINDING
```

not:

```text
PRODUCTION RULE
```

---

## 21. Recommended WP-052

I recommend:

# WP-052 — Property-vs-Identity Strategy Selection Study

Primary question:

> **Can the system safely determine, from the existing authoritative evidence, when a target has no known distinguishing property and therefore should bypass property-based generation and go directly to a bare-identity question strategy?**

Initial scope:

```text
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens
```

Compare:

```text
CURRENT

target
  ↓
property attempt
  ↓
possible ambiguity
  ↓
retry
  ↓
eventual identity fallback
```

against the hypothetical strategy:

```text
target
  ↓
known distinguishing property?
  ├── YES → property question
  └── NO  → identity question
```

But WP-052 should initially remain an **investigation**, not implementation.

---

## 22. What WP-052 Must Prove

It must determine:

1. whether "no known distinguishing property" can be established safely;
2. whether the decision can use existing authoritative evidence;
3. whether it can avoid wasting attempts;
4. whether it preserves accepted output;
5. whether it preserves question diversity;
6. whether it avoids forcing identity questions when a useful property exists;
7. whether it preserves WP-046 and WP-047;
8. whether it preserves English-first;
9. whether it preserves the three-attempt budget.

The key success condition is:

```text
same or better accepted output
+
fewer wasted attempts
```

not simply:

```text
higher acceptance percentage
```

---

# Final Review Conclusion

WP-051 is a **successful diagnostic architecture WP**.

Its most important result is that the apparently attractive solution:

```text
"target has insufficient evidence → skip target"
```

is demonstrably wrong for the current product.

Real historical evidence shows:

```text
Caudate Nucleus
Nucleus Accumbens
    ↓
poor candidates for distinguishing-property questions
    BUT
    ↓
still valid candidates for identity questions
```

Therefore:

```text
TARGET SELECTION
```

should remain unchanged.

The productive next direction is:

```text
TARGET
  ↓
QUESTION STRATEGY
  ├── distinguishing property known → property question
  └── no distinguishing property    → identity question
```

and even that must first be investigated safely.

**WP-051: ACCEPTED.**

**Target-selection filtering: CLOSED.**

**Recommended next WP: WP-052 — Property-vs-Identity Strategy Selection Study.**
