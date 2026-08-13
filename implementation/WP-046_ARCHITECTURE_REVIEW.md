# WP-046 Architecture Review

## Review Status

**ACCEPTED WITH REQUIRED FOLLOW-UP**

WP-046 is a strong architectural WP.

It moved from diagnosis to a narrowly scoped implementation only after expanding the evidence base and testing the proposed mechanism against real failures, successful controls, and the mandatory PICA false-positive case. The report states that the mechanism passed all ten safety criteria and was implemented. fileciteturn30file0L107-L122

The key result is:

> A narrow deterministic post-generation distractor-containment check is justified for one specific structural failure class, but it is **not** a general ambiguity solution.

At the same time, WP-046 exposed a second important problem for `Corticospinal Tract`: after the containment pathway was blocked, generation produced a different target-identity violation. fileciteturn30file0L154-L160

## 1. What WP-046 Proved

The strongest result is not the 11/12 acceptance number.

The strongest result is this confirmed pattern:

```text
Corticospinal Tract
+
child selected as actual distractor
+
question tests property shared by parent and child
=
multiple supported answers
```

This was repeatedly observed in real rejected generations. fileciteturn30file0L46-L50

The corpus also confirms that:

```text
Corticospinal Tract
    ↓
Anterior/Lateral Corticospinal Tract
```

is a genuine parent/child relationship based on explicit corpus structure, not string inference. fileciteturn30file0L58-L64

## 2. The Implementation Is Correctly Scoped

The new:

```text
_validate_distractor_containment()
```

runs after generation and before the existing validators.

It checks normalized answer/distractor text for containment, only for `named_entity_target` targets, and uses the existing generation-contract exception/attempt behavior. fileciteturn30file0L124-L128

This is preferable to creating a new ambiguity subsystem.

Existing validators, coverage, retry budget, schemas, and previous WP mechanisms remain unchanged. fileciteturn30file0L124-L136

## 3. Why the PICA Control Matters

WP-045 showed that naive textual containment could create a false positive because:

```text
Inferior Cerebellar Artery (PICA)
Posterior inferior cerebellar artery (PICA)
```

were different extracted representations of the same real-world artery.

WP-046 tested this case at the **actual answer-choice level** and confirmed that the new mechanism does not flag it when the duplicate is not an actual competing answer. fileciteturn30file0L94-L105

This establishes the important architectural distinction:

```text
textual relationship somewhere in the corpus
```

is not enough.

The relevant safety question is:

```text
relationship between the actual correct answer
and an actual generated distractor
```

That is a much safer scope.

## 4. Generalization Result

WP-046 correctly reached **Outcome 2**:

```text
a narrower mechanism was demonstrated
for a well-defined structural class
```

It did **not** establish a general ambiguity detector. fileciteturn30file0L182-L184

This distinction must remain explicit.

## 5. Globus Pallidus Was Properly Separated

WP-046 discovered that `Caudate Nucleus` also exhibits the same generic basal-nuclei classification problem.

This changes the interpretation from:

```text
Globus Pallidus is a special problem
```

to:

```text
basal-nuclei sparse-evidence targets are vulnerable
to generic classification questions
```

No safe deterministic candidate-level signal was found for this family. fileciteturn30file0L40-L44

This is an important correction to the WP-045 understanding.

## 6. Important New Finding: Corticospinal Tract Is Still Not Safe

After the containment check blocked the known failure path, `Corticospinal Tract` generated:

```text
correct answer = Precentral Gyrus
target = Corticospinal Tract
```

The question was grounded and passed the five existing validators, but the answer was not the requested target. fileciteturn30file0L154-L160

Therefore:

```text
containment ambiguity
```

was successfully blocked, but:

```text
target identity substitution
```

remained possible.

This is not a failure of WP-046. It demonstrates that fixing one invalid-generation pathway can expose another.

## 7. Acceptance Is Not Enough

The fresh pilot achieved:

```text
11/12 accepted
91.7%
```

but:

```text
target alignment = 10/11
```

among accepted questions. fileciteturn30file0L144-L164

Therefore we should continue treating these as separate dimensions:

```text
validator acceptance
target alignment
English-first
concept rotation
```

A question can pass all existing validators and still violate the target contract.

## 8. English-First

WP-046 achieved:

```text
11/11 English-first
100%
```

among accepted questions. fileciteturn30file0L166-L168

No new language-specific mechanism is needed.

## 9. Regression

Regression:

```text
1386 passed
0 failed
```

with seven new tests. Public schemas remained unchanged and the existing validation, coverage, retry budget, and previous mechanisms were preserved. fileciteturn30file0L130-L136

## 10. Test Quality

The seven new tests cover:

- containment in one direction;
- reverse containment;
- unrelated distractors;
- the real PICA false-positive control;
- non-named-entity targets;
- no additional LLM call;
- deterministic implementation boundaries. fileciteturn30file0L130-L134

This is appropriate for the narrow mechanism.

## 11. Pilot Interpretation

The new mechanism actually fired in the fresh live pilot:

```text
Corticospinal Tract
round 3
attempts 1–3
```

and blocked the intended containment pattern. The report states that it fired three times and produced zero false positives elsewhere in that run. fileciteturn30file0L124-L128

This is stronger evidence than unit tests alone.

However, the pilot remains small, so this is not evidence of universal safety across the full exam.

## 12. Do Not Broaden the Mechanism Yet

Freeze the current containment mechanism.

Do not turn it into:

```text
generic semantic relationship detector
```

Do not add:

```text
parent/child ontology
classification detector
fuzzy matching
LLM judge
```

The current rule has earned its place because its scope is narrow and demonstrable.

## 13. The Three Current Architectural Problems

After WP-046 we should explicitly distinguish:

### A. Resolved narrowly

```text
parent/child distractor containment
```

Status:

**Handled by WP-046.**

### B. Unresolved

```text
generic classification ambiguity
```

Examples:

```text
Globus Pallidus
Caudate Nucleus
```

Status:

**No safe deterministic mechanism found.**

### C. Unresolved and important

```text
target identity substitution
```

Example:

```text
target:
Corticospinal Tract

accepted answer:
Precentral Gyrus
```

Status:

**Repeatedly demonstrated and now deserves direct investigation.**

## 14. Recommended WP-047

I agree with the completion report's recommendation, with one important refinement:

**WP-047 should primarily investigate target-identity enforcement, not immediately implement it.**

The issue is now stronger than a single observation:

```text
WP-043:
Corticospinal Tract → Precentral Gyrus

WP-046:
Corticospinal Tract → Precentral Gyrus
```

The same substitution has now appeared independently twice. fileciteturn30file0L156-L160

WP-047 should determine:

1. what exactly defines the requested target;
2. what constitutes an acceptable answer identity;
3. which target types have explicit identity information;
4. whether existing `ConceptIdentity` infrastructure can support this;
5. whether some valid question types intentionally ask about a related entity;
6. whether a deterministic identity check can be generalized without rejecting valid questions.

Only after this diagnosis should implementation begin.

## 15. Do Not Simply Require `correct_answer == target`

This would be too simplistic.

Some valid questions may ask about:

```text
source
origin
location
function
relationship
```

and therefore legitimately have an answer that is a related concept.

The architectural question is:

> When the system is asked to generate a question for a specific concept, what deterministic evidence establishes that the accepted answer actually identifies that concept rather than merely describing a related concept?

That must be answered before implementing a general identity validator.

## 16. Globus Pallidus / Caudate Nucleus

Do not make this the primary implementation target of WP-047.

WP-046 found that the classification problem is broader and lacks a safe deterministic signal. fileciteturn30file0L176-L177

A legitimate future outcome may be:

```text
this evidence shape is insufficient
for safe deterministic generation
```

and therefore:

```text
skip / choose another target
```

But that requires its own focused investigation.

## 17. Pilot Expansion

Do **not** expand beyond:

```text
אספקת דם
גרעיני הבסיס
מסילות עצביות
```

The completion report's recommendation here is correct. fileciteturn30file0L188-L190

We still have unresolved target identity and classification problems.

## 18. Architectural State After WP-046

Conceptually:

```text
Target selection
      ↓
Evidence / planning
      ↓
LLM generation
      ↓
Target-role consistency
      ↓
Distractor containment check  ← WP-046
      ↓
Existing validators
      ↓
Accepted question
```

But there is still a missing contract:

```text
Does correct_answer identify the requested target?
```

The `Precentral Gyrus` example proves that this contract is not guaranteed.

## 19. Final Decision

**WP-046: ACCEPTED.**

The implementation is justified and should remain.

Current status:

| Problem | Status |
|---|---|
| Parent/child distractor containment | **Handled narrowly by WP-046** |
| Generic classification ambiguity | **Unresolved** |
| Target identity substitution | **Unresolved and repeatedly demonstrated** |

## 20. Recommended Next Step

Proceed with:

**WP-047 — Target Identity Enforcement Generalization Study**

Keep the scope to:

```text
אספקת דם
גרעיני הבסיס
מסילות עצביות
```

Use real failures and successful controls.

Do not expand the pilot.

Do not weaken existing validators.

Do not remove the WP-046 containment check.

Do not assume:

```text
correct_answer == target
```

is always the correct rule.

First determine the actual target-identity contract and whether it can be enforced deterministically without rejecting valid related-entity questions.

## Final Architectural Conclusion

WP-046 is accepted because it did exactly what a good architectural WP should do:

```text
broaden evidence
    ↓
identify a real generalizable structural class
    ↓
test successful controls
    ↓
test known false positive
    ↓
implement only the narrow safe mechanism
    ↓
observe what problem remains
```

The next architectural priority is no longer the parent/child containment problem.

It is **target identity enforcement**, while the broader classification ambiguity remains a separate open problem.
