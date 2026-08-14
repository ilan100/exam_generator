# WP-056 Architecture Review

## Review Status

**ACCEPTED — EXPERIMENTAL RESULT SUPPORTS A NARROW GLOBUS PALLIDUS IDENTITY-FIRST STRATEGY**

WP-056 completed the controlled experiment requested by the architecture review of WP-055.

The experiment used:

```text
CONTROL:
current DEFAULT behavior

EXPERIMENT:
temporary reverse-framed identity instruction
```

for:

```text
Category:
גרעיני הבסיס

Target:
Globus Pallidus
```

using the real production generation path, real OpenAI API, real validators, and the existing three-attempt budget. No production prompt, strategy mapping, validator, retrieval, schema, or retry behavior was changed. fileciteturn42file0L18-L25

The experimental result is sufficiently strong to justify the next architectural step:

> **Add Globus Pallidus to the permanent narrow `IDENTITY_FIRST` mapping, subject to implementation in a separate WP.**

This is not a claim of mathematical proof or generalization beyond this target/category pair.

---

# 1. Executive Assessment

The result is unusually clean for an engineering-scale LLM experiment:

```text
CONTROL
    0 / 7 valid identity successes
    1 / 3 rounds eventually accepted
    3 grounding failures
    2 membership-classification attempts

EXPERIMENT
    3 / 4 primary-success attempts
    3 / 3 rounds eventually accepted
    0 grounding failures
    0 membership-classification attempts
```

The completion report explicitly records these results. fileciteturn42file0L118-L130

The experimental condition therefore did exactly what WP-055 hypothesized:

```text
DEFAULT
    ↓
mixed question shapes
    ↓
membership/classification failures

REVERSE-FRAMED IDENTITY
    ↓
identity-shaped questions
    ↓
grounding-safe and accepted
```

The result corroborates:

```text
WP-055 diagnostic findings
+
historical Globus Pallidus successes
+
WP-052/WP-053 identity-first evidence
```

The appropriate next step is now implementation, not another diagnostic WP.

---

# 2. Experimental Isolation Was Correct

The experiment was properly isolated.

The control prompt was verified to be byte-identical to the production prompt, while the experimental prompt received only the temporary reverse-framed identity instruction. fileciteturn42file0L20-L24

The implementation also explicitly asserts:

```text
control has no experimental instruction
experimental has experimental instruction
control == real production template
target == Globus Pallidus
category == גרעיני הבסיס
```

and the self-check passed. fileciteturn42file1L131-L143

This is a strong experimental-control mechanism.

---

# 3. Correct Use of the Real Pipeline

The experiment did not create a fake generation path.

The script constructs:

```text
QuestionGenerator
QuestionProducer
GroundingValidator
MCQValidator
CategoryValidator
QualityValidator
TextbookValidator
```

using the normal production constructors/configuration. fileciteturn42file1L161-L176

It also uses the real OpenAI provider and configured retry budget. fileciteturn42file1L263-L284

This makes the result materially more useful than a unit-test-only experiment.

---

# 4. Correct Experimental Sample

The experiment used:

```text
3 CONTROL rounds
3 EXPERIMENT rounds
3-attempt production budget
```

with no reruns and no "run until success" behavior. fileciteturn42file0L54-L60

This matches the WP-056 design.

The sample is still small.

Therefore:

```text
engineering evidence = strong enough for a narrow implementation decision
statistical generalization = not established
```

The completion report correctly assigns `MEDIUM-HIGH` confidence to the narrow claim and explicitly avoids claiming statistical significance. fileciteturn42file0L147-L153

---

# 5. The Main Result Is Strong

The most important result is:

```text
CONTROL:
0 / 7 primary-success attempts

EXPERIMENT:
3 / 4 primary-success attempts
```

and:

```text
CONTROL:
1 / 3 rounds eventually accepted

EXPERIMENT:
3 / 3 rounds eventually accepted
```

fileciteturn42file0L118-L130

This is not merely an improvement in wording.

The experimental questions passed the complete validation boundary.

That is the important architectural signal.

---

# 6. Identity vs Membership Was Correctly Measured

The deterministic classifier explicitly distinguishes:

```text
VALID_IDENTITY_SHAPE
```

from:

```text
MEMBERSHIP_CLASSIFICATION
```

and was self-checked against six known examples before the live experiment. fileciteturn42file1L74-L83 fileciteturn42file1L110-L128

The experiment found:

```text
CONTROL:
2 membership attempts
3 identity attempts
2 other/property attempts

EXPERIMENT:
3 identity attempts
1 generation-contract failure
0 membership attempts
```

fileciteturn42file0L82-L96

This directly supports the hypothesis that the experimental instruction changes the generated question shape.

---

# 7. Grounding Result Is Especially Important

The strongest safety-related result is:

```text
0 / 6 identity-shaped attempts
    failed grounding
```

while:

```text
3 / 3 grounding failures
```

were non-identity attempts. fileciteturn42file0L108-L114

This directly reinforces WP-055's diagnosis.

The experiment did not make the grounding validator weaker.

Instead, it caused generation to select propositions that naturally satisfy the uniqueness requirement.

This is the correct architectural direction.

---

# 8. The One Experimental Failure Is Acceptable

Experiment round 2 attempt 1 generated:

```text
Globbus Pallidus
```

instead of:

```text
Globus Pallidus
```

The existing WP-047 target-answer identity check rejected it, and the existing retry mechanism recovered on the next attempt. fileciteturn42file0L108-L112

This should **not** be treated as evidence against the strategy.

It demonstrates that:

```text
strategy
+
existing validation
+
existing retry
```

works together.

However, the implementation WP should preserve the existing strict target-identity validation rather than weakening it.

---

# 9. Control Identity Attempts Are Important Nuance

The control condition did produce three identity-shaped attempts.

Two were rejected for quality, and one was rejected by MCQ validation. fileciteturn42file0L100-L106

This means the result must not be described as:

```text
DEFAULT never generates identity questions.
```

That would be false.

The correct conclusion is:

```text
DEFAULT does not reliably produce a valid identity question.

REVERSE-FRAMED IDENTITY reliably shifted the observed generation
distribution toward identity questions and, in this sample,
produced accepted identity questions consistently.
```

The completion report itself correctly recognizes this nuance. fileciteturn42file0L134-L148

---

# 10. Important Interpretation Boundary

The experiment demonstrates:

```text
strategy improves Globus Pallidus generation
under the tested category and architecture
```

It does **not** demonstrate:

```text
identity-first should be used for all targets.
```

It does not demonstrate:

```text
identity-first solves all Globus Pallidus failures.
```

It does not demonstrate:

```text
identity-first is superior to property generation in every case.
```

It only supports the narrow mapping:

```text
גרעיני הבסיס + Globus Pallidus
    → IDENTITY_FIRST
```

That narrowness is exactly what we want.

---

# 11. The Experiment Supports a Permanent Mapping

The WP-054 precedent was:

```text
historical evidence
    ↓
controlled experiment
    ↓
architectural review
    ↓
permanent narrow mapping
```

WP-056 now provides the corresponding evidence for Globus Pallidus.

Therefore the next WP should implement:

```text
גרעיני הבסיס + Globus Pallidus
    → IDENTITY_FIRST
```

using the same permanent mechanism already established by WP-054.

---

# 12. The Permanent Instruction Must Preserve the Tested Semantic

The experimental instruction was not simply:

```text
identity-first
```

It specifically requested:

```text
Which of the following IS TARGET CONCEPT?
```

and explicitly prohibited:

```text
Which structure is part of the basal nuclei?
```

fileciteturn42file0L26-L42

Therefore the permanent implementation should preserve the tested semantic:

```text
reverse-framed identity
```

rather than inventing a broader new identity strategy.

Do not generalize the wording unnecessarily.

---

# 13. No Need for Another Experiment

I do **not** recommend WP-057 as another experiment on the same question.

We now have:

```text
WP-055:
diagnostic evidence

WP-056:
fresh controlled evidence
```

and the results agree.

A third experiment would have diminishing architectural value unless a new concern appears.

The correct next step is implementation.

---

# 14. Recommended WP-057

The next WP should be:

# WP-057 — Permanent Globus Pallidus Identity-First Mapping

Objective:

```text
promote the experimentally validated
Globus Pallidus reverse-framed identity strategy
from prototype-only behavior into the permanent
narrow strategy mapping.
```

It should mirror WP-054's implementation pattern.

---

# 15. WP-057 Scope

The implementation should modify only the narrow strategy mapping required for:

```text
גרעיני הבסיס + Globus Pallidus
```

The resulting mapping should become:

```text
Caudate Nucleus
    → IDENTITY_FIRST

Nucleus Accumbens
    → IDENTITY_FIRST

Globus Pallidus
    → IDENTITY_FIRST
```

All other targets/categories remain unchanged.

---

# 16. WP-057 Must Not Redesign Identity-First

Do not use WP-057 to redesign:

```text
identity-first architecture
```

It already exists.

Do not change:

```text
strategy resolver
QuestionTarget
QuestionGenerator
QuestionProducer
validators
retrieval
schemas
retry semantics
```

unless a directly necessary implementation detail requires it.

The implementation should be a narrow data/configuration-level extension of the already accepted mechanism.

---

# 17. Preserve the DEFAULT Fallback

The permanent strategy resolver must retain:

```text
explicit target mapping
    → IDENTITY_FIRST

otherwise
    → DEFAULT
```

Therefore:

```text
unknown target
    → DEFAULT
```

must remain true.

This prevents accidental broadening of the identity-first behavior.

---

# 18. Required Tests for WP-057

Add deterministic tests proving:

```text
גרעיני הבסיס + Caudate Nucleus
    → IDENTITY_FIRST

גרעיני הבסיס + Nucleus Accumbens
    → IDENTITY_FIRST

גרעיני הבסיס + Globus Pallidus
    → IDENTITY_FIRST

גרעיני הבסיס + another target
    → DEFAULT
```

Also preserve existing tests proving that unrelated categories remain:

```text
DEFAULT
```

---

# 19. Regression Requirement

WP-057 must run the full test suite.

Expected result:

```text
0 failures
```

The current baseline is:

```text
1426 passed
```

according to the WP-056 completion report. fileciteturn42file0L157-L164

WP-057 should record the new total and explain any added tests.

---

# 20. WP-057 Should Not Reuse the Experimental Prompt File

The experimental instruction was intentionally:

```text
in-memory only
prototype-only
```

The permanent implementation should use the project's already-established permanent strategy infrastructure.

Do not leave:

```text
WP-056 experimental prompt text
```

as a hidden runtime dependency.

---

# 21. WP-056 Experimental Artifact Status

The following remain valid as historical evaluation artifacts:

```text
implementation/wp056_experiment.py
evaluation/live_outputs/wp056_experiment_records.json
```

They should not be imported by production code.

The experiment script explicitly confirms that it is not production code and that the temporary instruction is never written to the permanent prompt file. fileciteturn42file1L1-L16

Do not delete the evidence merely because the strategy is promoted.

It is useful architectural provenance.

---

# 22. One Important Cleanup Check for WP-057

Before implementation, verify whether the prototype artifacts are expected to remain in the repository under the project's existing conventions.

Do not delete them automatically.

If the project normally retains evaluation artifacts:

```text
keep them.
```

If architectural conventions require temporary prototypes to be removed after promotion:

```text
remove only after preserving the experiment record/report.
```

This is a repository hygiene decision, not a strategy decision.

---

# 23. Language Rule Remains Unchanged

The project language rule remains absolute:

```text
If an English representation exists:
    use English.

Use Hebrew only when Hebrew is the only available representation.
```

The target remains:

```text
Globus Pallidus
```

The category remains whatever canonical project representation is already required.

Do not introduce new Hebrew terminology merely because experimental output contained Hebrew wording.

---

# 24. Important Observation About Generated Hebrew

The actual LLM outputs contained mixed Hebrew/English wording, for example:

```text
איזה מהמבנים הבאים הוא Globus Pallidus?
```

This does not change the project's architectural language rule.

The permanent implementation should continue to enforce the project's English-first instruction.

WP-056 was testing strategy behavior, not changing the language policy.

If WP-057 modifies prompt text, ensure the English-first rule remains explicit and is not weakened.

---

# 25. No Need to Change Grounding

WP-056 provides additional evidence that grounding is working correctly.

Do not modify the grounding validator.

The desired behavior is:

```text
membership proposition
    → rejected when non-unique

identity proposition
    → accepted when properly grounded
```

This is exactly what we want.

---

# 26. No Need to Change Retry Budget

The experiment showed:

```text
one spelling error
    ↓
existing target-identity validation rejects
    ↓
retry
    ↓
valid identity question
```

The existing three-attempt budget handled this.

No retry change is justified.

---

# 27. No Need to Change Retrieval

WP-055 already established that useful evidence exists.

WP-056 demonstrates that the identity strategy can use the existing architecture successfully.

Therefore:

```text
retrieval redesign
```

is not justified as the next step.

---

# 28. Architectural Interpretation of GPi/GPe

The WP-055 target/evidence granularity concern remains valid.

WP-057 should **not** attempt to solve it.

The permanent identity strategy avoids needing to ask a target-specific GPi/GPe property question as the primary generation strategy.

This does not mean the representation issue disappears.

It remains a future architectural concern if later requirements demand richer property questions for Globus Pallidus.

---

# 29. Acceptance Decision

**WP-056 — ACCEPTED.**

The experiment has answered the question it was designed to answer.

The evidence is sufficient for:

```text
architectural approval to implement
a permanent narrow Globus Pallidus identity-first mapping.
```

It is not a license to generalize the strategy.

---

# 30. Final Architecture State After WP-056

Before WP-057:

```text
גרעיני הבסיס + Caudate Nucleus
    → IDENTITY_FIRST

גרעיני הבסיס + Nucleus Accumbens
    → IDENTITY_FIRST

גרעיני הבסיס + Globus Pallidus
    → DEFAULT
```

After the recommended WP-057:

```text
גרעיני הבסיס + Caudate Nucleus
    → IDENTITY_FIRST

גרעיני הבסיס + Nucleus Accumbens
    → IDENTITY_FIRST

גרעיני הבסיס + Globus Pallidus
    → IDENTITY_FIRST

everything else
    → DEFAULT
```

This is the only architectural change currently justified by WP-056.

---

# 31. Final Recommendation

Proceed directly to:

**WP-057 — Permanent Globus Pallidus Identity-First Mapping**

The implementation should be:

```text
narrow
deterministic
explicit
test-covered
backward-compatible
```

and should use the already accepted WP-054 strategy infrastructure.

Do not create another diagnostic WP for the same hypothesis.

Do not broaden identity-first to additional targets.

Do not weaken validators.

Do not change retrieval.

Do not change retry semantics.

Do not redesign the architecture.

---

# Final Decision

**WP-056 — ACCEPTED.**

**Architectural decision: APPROVE the permanent narrow mapping**

```text
גרעיני הבסיס + Globus Pallidus
    → IDENTITY_FIRST
```

**Next WP: WP-057 — Permanent Globus Pallidus Identity-First Mapping**

WP-057 should implement only this narrow promotion and prove through deterministic tests and the full regression suite that all previously accepted mappings and DEFAULT fallbacks remain intact.
