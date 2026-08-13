# WP-048 Architecture Review

## Review Status

**ACCEPTED — DIAGNOSTIC / ARCHITECTURAL OUTCOME**

WP-048 is accepted as a successful diagnostic and architectural work package.

The key result is that the dominant classification-ambiguity problem is **not a missing safety check**. The existing `GroundingValidator` and `MCQValidator` already rejected every genuine `QUESTION_PREDICATE` ambiguity observed in the real dataset.

The remaining problem is therefore primarily a **generation reliability problem**:

```text
LLM generates an under-specified classification predicate
        ↓
multiple answer choices satisfy the predicate
        ↓
existing validators correctly reject it
        ↓
retry
        ↓
LLM may generate the same failure again
        ↓
3-attempt budget may be exhausted
```

The report examined 19 real rejected attempts across four mandatory targets and found three targets with genuine evidence-supported predicate ambiguity, while `Basillar artery` appears to represent a separate and not-yet-proven validator/evidence-interpretation issue. fileciteturn34file0L13-L24

---

## 1. The Most Important Finding

WP-048 changed our understanding of the remaining problem.

Previously the question was:

> Can we build another deterministic safety check to catch classification ambiguity?

The better question is now:

> How do we make generation reliably avoid producing classification questions whose predicate is not unique for the selected target?

This distinction is critical.

WP-046 and WP-047 solved genuine **detection gaps**:

```text
WP-046
parent/child distractor containment
        ↓
new deterministic detection

WP-047
target identity substitution
        ↓
new deterministic detection
```

WP-048 shows that the dominant classification problem is different:

```text
classification ambiguity
        ↓
already detected by existing validators
        ↓
generation repeatedly produces it
```

Therefore adding another post-generation validator would not address the underlying problem.

---

## 2. Evidence Base

The investigation used real production data from:

```text
wp045_pilot_records.json
wp046_pilot_records.json
wp047_pilot_records.json
```

Mandatory cases:

| Target | Rejected attempts |
|---|---:|
| `Globus Pallidus` | 9 |
| `Caudate Nucleus` | 2 |
| `Nucleus Accumbens` | 2 |
| `Basillar artery` | 6 |
| **Total** | **19** |

No additional classification-ambiguity cases were found. `Corticospinal Tract` failures were correctly separated into the already-solved WP-046 family or an unrelated MCQ defect. fileciteturn34file0L13-L24

This is a sufficiently strong evidence base for the current decision.

---

## 3. The Problem Is Actually Multiple Subclasses

WP-048 correctly concluded:

```text
MULTIPLE_SUBCLASSES
```

### Subclass A

```text
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens
```

These are genuine `QUESTION_PREDICATE` ambiguity cases.

### Subclass B

```text
Basillar artery
```

This appears to be a different issue involving grounding's interpretation of shared-parent evidence. The report correctly labels this as an **INFERENCE**, not a proven validator defect. fileciteturn34file0L100-L106

This separation must be preserved.

---

## 4. Formal Predicate Analysis

WP-048 did the right thing by formalizing the actual question predicate.

For the real `Caudate Nucleus` case:

```text
P(x) = x is a member of the Corpus Striatum
```

The authoritative evidence gives:

```text
P(Caudate Nucleus)  = true
P(Putamen)           = true
P(Nucleus Accumbens) = true
P(Globus Pallidus)   = false
```

Therefore:

```text
count(P(x) = true) = 3
```

This is genuine MCQ ambiguity. fileciteturn34file0L62-L68

This formalization is much stronger than simply relying on the validator's wording.

---

## 5. What the Three Basal-Nuclei Cases Show

The recurring pattern is:

```text
target is one member of a broader category
        ↓
LLM asks a generic membership/classification question
        ↓
several answer choices are members of that category
        ↓
there is no unique answer
```

For example, the real `Caudate Nucleus` question asks about membership in the Corpus Striatum, while multiple answer choices satisfy that property.

The `Globus Pallidus` and `Nucleus Accumbens` cases exhibit the same broader failure family. fileciteturn34file0L74-L82

This is now a well-established failure class.

---

## 6. Strongest Control Finding

The same target can succeed when the question predicate is target-specific.

Successful examples use:

```text
identity-by-name
```

or:

```text
specific functional/anatomical property
```

instead of:

```text
bare category membership
```

Even more importantly, the same or near-identical answer-choice set can occur in successful and failing cases.

Therefore:

```text
candidate set
```

is not the decisive factor.

The semantic content of:

```text
the generated question
```

is the decisive factor. fileciteturn34file0L84-L91

This is the central architectural finding of WP-048.

---

## 7. Why WP-046 Does Not Generalize

WP-046 worked because the failure could be tied to an observable structural relationship:

```text
target
+
specific child selected as distractor
=
dangerous candidate
```

WP-048 tested whether the same idea could work here.

It cannot.

The same candidate set can appear in:

```text
successful question
```

and:

```text
ambiguous question
```

depending on the generated predicate.

Therefore:

> The WP-046 distractor-difference mechanism cannot be generalized to this classification family.

fileciteturn34file0L107-L115

---

## 8. Candidate Deterministic Signals Were Correctly Rejected

### Signal 1 — Multiple candidates in the same category

Rejected because this is normal for realistic distractor sets and therefore has no discriminating power. fileciteturn34file0L109-L112

### Signal 2 — Distractor-set difference

Rejected because successful and failing cases can have essentially the same candidate set. fileciteturn34file0L111-L113

### Signal 3 — Parse the question for classification phrases

Rejected because equivalent predicates use different wording and a phrase classifier would create the kind of brittle free-text heuristic this architecture has deliberately avoided. fileciteturn34file0L113-L115

Therefore no deterministic signal justified implementation.

---

## 9. Deterministic Feasibility

For the dominant `QUESTION_PREDICATE` family:

**NO safe deterministic mechanism was found using the currently available deterministic inputs and current architectural constraints.**

The important reason is:

```text
the decisive information is the semantic content
of the generated question predicate
```

while the architecture deliberately does not parse arbitrary generated prose for this purpose. fileciteturn34file0L137-L143

This is a valid negative architectural result.

---

## 10. Existing Validators Are Doing Their Job

This is the most important finding of the WP.

For:

```text
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens
```

the existing:

```text
GroundingValidator
MCQValidator
```

already correctly reject the genuine ambiguous candidates.

The report found no genuinely ambiguous candidate that was incorrectly accepted. fileciteturn34file0L121-L125

Therefore the architecture does **not** have a missing safety barrier here.

It has:

```text
generation reliability problem
```

---

## 11. Architectural Consequence

We should no longer ask:

```text
How do we catch classification ambiguity after generation?
```

We should ask:

```text
How do we make the generator avoid producing
this known-invalid question shape?
```

The validators remain the final safety net.

The problem is that repeated invalid generation can exhaust the fixed three-attempt budget.

---

## 12. Existing Prompt Guidance Is Already Relevant

The report found that the generation prompt already contains guidance around:

```text
Testing enumeration or classification targets
```

Yet the LLM does not reliably follow it.

This strongly suggests that the next architectural lever is:

```text
generation guidance
```

rather than:

```text
another validator
```

The report explicitly recommends improving how reliably this guidance is followed. fileciteturn34file0L175-L187

---

## 13. Basillar Artery Must Stay Separate

The `Basillar artery` case must not be merged into the basal-nuclei classification family.

The report's analysis says the explicit corpus labeling supports:

```text
Basillar artery = source of Superior Cerebellar Artery
```

while `AICA` is also shown as having `Basillar artery` as its own source.

Thus the evidence does not clearly establish:

```text
AICA = source of Superior Cerebellar Artery
```

Yet grounding repeatedly treats AICA as also supported. fileciteturn34file0L64-L68

The report correctly labels this:

```text
INFERENCE, not certainty
```

and does not change the validator. fileciteturn34file0L133-L136

This is the right decision.

---

## 14. No Production Code Change Was Correct

WP-048 changed:

```text
no production code
```

That is correct.

Regression remained:

```text
1396 passed
0 failed
```

and schemas remained byte-identical. fileciteturn34file0L145-L155

This is a good example of a work package where **not coding is the correct engineering result**.

---

## 15. No Fresh Pilot Was Necessary

Because there was no production code change, the report did not run another live pilot.

The analysis was based on real, already-captured production data with full per-attempt information. fileciteturn34file0L157-L167

This is reasonable and avoids spending additional API budget without a code or prompt change to test.

---

## 16. Important Epistemic Qualification

The report states:

```text
No safe deterministic mechanism exists
```

I recommend documenting this slightly more precisely as:

> **No safe deterministic mechanism was identified using the currently available deterministic inputs and the project's current architectural constraints.**

This avoids claiming that no future architecture could ever expose enough structured information to solve the problem.

For the current system, however, the practical decision is unchanged:

**Do not implement a deterministic post-generation classifier.**

---

## 17. Current Architecture After WP-048

The effective safety path is now:

```text
Target
   ↓
generation planning / prompt
   ↓
LLM generation
   ↓
WP-047 target-answer identity
   ↓
WP-046 distractor containment
   ↓
GroundingValidator
   ↓
MCQValidator
   ↓
other validators
   ↓
accepted question
```

For classification ambiguity:

```text
LLM generates generic predicate
        ↓
existing validator detects ambiguity
        ↓
candidate rejected
        ↓
retry
```

The missing capability is therefore:

```text
generation avoidance
```

not:

```text
detection
```

---

## 18. Current Problem Inventory

### Problem A — Parent/child distractor ambiguity

**SOLVED**

WP-046.

### Problem B — Target identity substitution

**SOLVED for current named-entity pilot scope**

WP-047.

### Problem C — Generic classification ambiguity

**UNRESOLVED GENERATION-RELIABILITY PROBLEM**

Existing validators already detect it.

### Problem D — Basillar artery grounding interpretation

**UNRESOLVED / NEEDS SEPARATE INVESTIGATION**

Do not merge it with Problem C.

---

## 19. Recommended WP-049

I agree with the direction in the completion report.

### WP-049 — Classification-Avoidance Generation Strategy

Objective:

> Determine whether the existing generation prompt can be strengthened so that classification/enumeration targets preferentially generate target-unique predicates, while preserving the current validators and without adding a new deterministic ambiguity detector.

The next WP should investigate:

```text
current generation prompt
        ↓
small evidence-based modification
        ↓
same targets
same evidence
same candidate architecture
        ↓
measure whether generic classification failures decrease
```

This is the correct next architectural lever.

---

## 20. What WP-049 Must Not Do

Do not:

- add an LLM judge;
- add a phrase classifier;
- add target-specific rules;
- add category-specific rejection lists;
- increase the retry budget;
- weaken grounding or MCQ validation;
- change WP-046;
- change WP-047;
- introduce external medical knowledge;
- expand to all categories.

---

## 21. WP-049 Experimental Design

The experiment should isolate the prompt effect.

Do not simultaneously change:

```text
prompt
retrieval
model
validators
retry count
temperature/configuration
candidate selection
```

The primary comparison should be:

```text
current generation guidance
vs.
candidate revised generation guidance
```

using the same real target/evidence conditions.

Otherwise we cannot attribute improvement correctly.

---

## 22. WP-049 Metrics

Do not use overall acceptance rate as the only metric.

Measure specifically:

```text
classification-ambiguity rejection rate
```

before and after the prompt change.

Also measure:

```text
target alignment
English-first
WP-046 firing
WP-047 firing
other validator failures
attempt count
acceptance
```

A prompt change that reduces classification ambiguity but creates another failure class is not automatically an improvement.

---

## 23. WP-049 Initial Scope

Remain focused on:

```text
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens
```

The `Basillar artery` case should remain separate because WP-048 identified it as a different unresolved subclass.

Do not expand the pilot categories yet.

---

## 24. Final Architectural Decision

**WP-048: ACCEPTED.**

No production mechanism should be added for `QUESTION_PREDICATE` ambiguity at this stage.

The dominant classification-ambiguity family is now understood as:

```text
generation reliability problem
```

rather than:

```text
missing safety detection
```

The existing validators remain the correct safety boundary.

The `Basillar artery` finding remains separate and unconfirmed.

---

## Final Review Conclusion

WP-048 is a **successful diagnostic WP**.

Its most important achievement is that it prevented us from implementing the wrong solution.

We now know:

```text
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens
```

produce a genuine classification-ambiguity family in which the generated predicate can have multiple evidence-supported answers.

We also know:

```text
GroundingValidator
MCQValidator
```

already detect the observed failures.

Therefore:

```text
classification ambiguity
        ↓
not a missing safety barrier
        ↓
generation reliability problem
```

And separately:

```text
Basillar artery
        ↓
different unresolved subclass
        ↓
possible grounding interpretation issue
        ↓
needs dedicated investigation
```

No production code change was justified, and the 1396-test regression remained clean. fileciteturn34file0L137-L155

**WP-048 is accepted. Proceed to WP-049, focused on improving generation avoidance of generic classification predicates rather than adding another post-generation detector.**
