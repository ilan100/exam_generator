# WP-050 Architecture Review

## Review Status

**ACCEPTED — DIAGNOSTIC / ARCHITECTURAL OUTCOME**

WP-050 was executed correctly and produced an important architectural result.

The central finding is stronger than the conclusion reached in WP-048:

> For `Caudate Nucleus` and `Nucleus Accumbens`, the current authoritative evidence does not contain a safely identifiable target-specific property that distinguishes either target from the relevant sibling concepts.

Therefore, this is not simply a missing data structure or a missing deterministic uniqueness algorithm.

For these targets, the evidence itself is insufficient.

The completion report explicitly reaches architectural decision **C**:

```text
Existing architecture cannot safely establish uniqueness;
do not implement; document the required future capability.
```

This is the correct decision for the current scope. fileciteturn36file0L193-L200

---

# 1. Executive Assessment

WP-050 successfully answered the question it was designed to investigate:

```text
Can the existing candidate/evidence architecture provide
structured TRUE/FALSE/UNKNOWN information that allows generation
to select a genuinely unique predicate?
```

The answer is:

```text
NOT GENERALLY
```

More precisely:

```text
Caudate Nucleus
    ↓
no evidence-supported unique property found

Nucleus Accumbens
    ↓
no evidence-supported unique property found

Globus Pallidus
    ↓
a genuinely unique property DOES exist
    ↓
already reachable through the existing full evidence
    ↓
no new architecture is required
```

This distinction is critical.

The problem is therefore not one uniform architectural defect.

---

# 2. The Most Important Finding

WP-050 discovered that the planning layer already computes the full category concept inventory:

```text
~53 concepts
```

for `גרעיני הבסיס`.

However, after selecting a target, the sibling inventory is discarded and only the selected target is passed forward.

The report states:

> the full sibling/candidate concept set is computed once per category during planning but is discarded after one target is selected. fileciteturn36file0L21-L29

This is an important architectural observation.

However:

**Do not conclude that simply passing the 52 siblings to the LLM solves the problem.**

WP-050 correctly rejects that as a sufficient solution because the LLM already receives the full evidence and still generated non-unique predicates.

---

# 3. The Existing Competitor Mechanism Is Not Solving This

`discover_competitors()` initially looked like the natural mechanism for this problem.

But the direct probe demonstrated:

```text
Caudate Nucleus
    relationship = UNSPECIFIED
    competitors = 0

Nucleus Accumbens
    relationship = UNSPECIFIED
    competitors = 0

Globus Pallidus
    relationship = UNSPECIFIED
    competitors = 0
```

The reason is that the target's narrow `factual_focus` contains enumeration noise rather than a relationship-bearing sentence.

The completion report confirms this was directly observed, not inferred. fileciteturn36file0L43-L67

Therefore:

```text
discover_competitors()
```

cannot currently provide candidate uniqueness information for these targets.

---

# 4. The Actual Generation Context Is Important

The probe confirmed that the LLM receives:

```text
full source evidence
```

but receives no structured cross-candidate uniqueness information.

The current situation is effectively:

```text
Target:
Caudate Nucleus

Evidence:
large undifferentiated evidence blob

Candidates:
not explicitly supplied

Candidate properties:
not supplied

Relationships:
UNSPECIFIED
```

Thus the LLM is expected to perform the semantic comparison itself.

The completion report calls this:

> zero deterministic, structured signal distinguishing the target from its siblings. fileciteturn36file0L65-L67

This is a very useful architectural finding.

---

# 5. The Three Real Failure Cases Confirm the Pattern

The report reconstructs three real rejected predicates.

### Caudate Nucleus

The generated question tested:

```text
influences decision-making
```

but the evidence supported both:

```text
Caudate Nucleus
Nucleus Accumbens
```

Therefore the grounding validator correctly rejected it. fileciteturn36file0L74-L80

### Nucleus Accumbens

The generated predicate combined:

```text
motor function
+
reward system
```

but multiple answer choices were supported. fileciteturn36file0L84-L91

### Globus Pallidus

The generated question asked which structure was a basal nucleus.

All four choices were supported.

A later attempt asking about the Globus Pallidus role succeeded. fileciteturn36file0L95-L106

These examples strongly support the architectural distinction:

```text
generic/shared predicate
        ↓
failure

genuinely target-specific predicate
        ↓
possible success
```

---

# 6. The TRUE/FALSE/UNKNOWN Analysis Is the Core Artifact

The most valuable part of WP-050 is the explicit property matrix.

For example:

```text
Member of Striatum

Caudate Nucleus       TRUE
Nucleus Accumbens     TRUE
Putamen               TRUE
Globus Pallidus       FALSE

→ SHARED
```

and:

```text
Member of Basal Nuclei

Caudate Nucleus       TRUE
Nucleus Accumbens     TRUE
Putamen               TRUE
Globus Pallidus       TRUE

→ SHARED
```

The report also correctly records:

```text
decision-making / reward
```

as category-level support rather than incorrectly assigning it to one specific nucleus. fileciteturn36file0L122-L135

This is exactly the kind of epistemic discipline we wanted.

---

# 7. The Globus Pallidus Case Is Different

The report found a genuine unique property:

```text
Globus Pallidus
    ↓
acts as a thalamus suppressor
```

The evidence supports this through:

```text
GPi
direct pathway
thalamus suppression
```

while the corresponding property was not stated for the other candidates in the retrieved evidence. fileciteturn36file0L126-L132

This demonstrates that the evidence corpus **can** contain uniquely identifying properties.

Therefore we cannot say:

```text
the corpus never contains unique properties
```

The correct statement is:

```text
the corpus does not contain a safely identifiable unique property
for every target.
```

---

# 8. Caudate Nucleus Is the Strongest Negative Case

The report searched all 16 real historical rounds and found:

```text
Caudate Nucleus
```

never succeeded through a property-based question.

Every accepted example used an identity/naming form.

The report found:

```text
no property-based success
```

for this target. fileciteturn36file0L116-L120

This is significant.

It means the problem is not merely:

```text
LLM does not know how to find the right property
```

There may simply be no sufficiently distinguishing property in the supplied evidence.

---

# 9. Nucleus Accumbens Must Be Treated Carefully

The report identifies one accepted:

```text
Nucleus Accumbens
```

question involving:

```text
reward system
```

but correctly refuses to treat it as proof of an evidence-grounded unique property.

The supplied evidence describes the reward-system function at the level of the basal nuclei collectively rather than explicitly attributing it to Nucleus Accumbens. fileciteturn36file0L116-L120

This is exactly the right conservative interpretation.

An accepted question is not automatically proof that the source evidence uniquely supports its predicate.

---

# 10. This Reveals a Potential Validator-Fidelity Question

The `Nucleus Accumbens` accepted case raises a separate question:

```text
Did the validator accept information that is not actually
explicitly supported by the supplied authoritative evidence?
```

WP-050 correctly does not resolve this.

This should remain a separate future investigation.

Do not contaminate the candidate-uniqueness problem with it.

The completion report explicitly lists it as an unresolved validator-fidelity question. fileciteturn36file0L185-L187

---

# 11. False-Positive Risk Was Correctly Identified

A tempting implementation would be:

```text
target evidence contains property P
+
distractor anchor does not contain P
=
P is unique
```

This is unsafe.

Why?

Because:

```text
absence from a narrow anchor
```

does not establish:

```text
property is false for the distractor
```

The report demonstrates exactly this with the reward-system example.

Therefore:

```text
UNKNOWN ≠ FALSE
```

must remain a hard architectural rule. fileciteturn36file0L137-L143

---

# 12. False-Negative Risk Was Also Correctly Identified

The reverse problem is:

```text
unique property exists in full evidence
```

but:

```text
property is not in the target's narrow factual_focus
```

The Globus Pallidus example demonstrates this.

The thalamus-suppression property is present in the full evidence but not in the narrow target anchor.

Therefore a uniqueness mechanism based only on:

```text
target.factual_focus
```

would incorrectly miss a real useful property. fileciteturn36file0L141-L143

This rules out a simplistic:

```text
anchor-only uniqueness
```

mechanism.

---

# 13. Option A — Give the LLM the Sibling List

This is technically easy because the sibling inventory already exists.

However, WP-050 correctly gives it only marginal value.

Why?

Because for:

```text
Caudate Nucleus
Nucleus Accumbens
```

the authoritative evidence itself does not provide a safe unique property.

Giving the LLM a longer list of candidates cannot manufacture missing evidence.

The report correctly rates this option as marginal. fileciteturn36file0L151-L163

---

# 14. Option B — Deterministic Property Matrix

At first glance this appears attractive:

```text
Concept × Property
```

with:

```text
TRUE / FALSE / UNKNOWN
```

But building such a matrix for arbitrary natural-language properties requires semantic extraction from raw prose.

That introduces exactly the kind of semantic/NLP machinery the architecture has intentionally avoided.

The report therefore rejects it as a general solution. fileciteturn36file0L159-L164

I agree.

---

# 15. Option C — Extend Relationship Keywords

This is technically clean but narrow.

The existing relationship system is deterministic and safe.

Adding something like:

```text
SUPPRESSES
INHIBITS
```

could help detect the Globus Pallidus-type relation.

However:

```text
Caudate Nucleus
Nucleus Accumbens
```

still have no target-specific relationship-bearing evidence in their current anchors.

Therefore this would not solve the main problem.

The report correctly identifies this as only a narrow optional improvement. fileciteturn36file0L151-L164

---

# 16. Option E — No New Mechanism

For:

```text
Caudate Nucleus
Nucleus Accumbens
```

this is currently the safest architectural choice.

The reason is fundamental:

```text
No unique evidence-supported property
        ↓
No deterministic representation can manufacture one
        ↓
No safe generation mechanism can guarantee uniqueness
```

This is an **evidence-content limitation**, not merely a software limitation.

The report explicitly reaches this conclusion. fileciteturn36file0L167-L173

---

# 17. This Changes Our Understanding of the Main Problem

We started with:

```text
classification ambiguity
```

and asked:

```text
How can we make the generator avoid it?
```

WP-049 suggested:

```text
better prompt guidance
```

WP-050 now shows that for some targets:

```text
the evidence itself may not contain a target-unique property
```

Therefore the real problem is partly:

```text
CONTENT COVERAGE
```

not just:

```text
GENERATION QUALITY
```

This is an important architectural advancement.

---

# 18. The Problem Is Not "The LLM Is Bad"

We should not conclude:

```text
LLM cannot generate good questions
```

The evidence shows something more precise.

For:

```text
Globus Pallidus
```

a unique property exists and the system can successfully generate a question from it.

For:

```text
Caudate Nucleus
Nucleus Accumbens
```

the available evidence does not provide a safely distinguishable property.

Therefore:

```text
LLM generation quality
+
available evidence content
```

are both relevant, but the evidence boundary is decisive for these targets.

---

# 19. No Production Implementation Was Correct

WP-050 made:

```text
no production code changes
```

and only used a read-only probe against real functions.

The probe made:

```text
zero LLM calls
zero new production logic
```

and did not modify validators, retry budget, or schemas. fileciteturn36file0L173-L181

This was exactly the right engineering behavior for an architecture-investigation WP.

---

# 20. Regression Status

The report correctly marks:

```text
NOT APPLICABLE
```

because no production code changed.

It also confirms:

```text
src/
tests/
```

were not modified. fileciteturn36file0L179-L181

No action is required.

---

# 21. Important Architectural Decision

**Do not create WP-051 to implement candidate uniqueness.**

The report explicitly recommends:

```text
No implementation WP-051 is recommended
for candidate uniqueness itself.
```

I agree.

The problem has now been investigated through:

```text
WP-048
detection analysis

WP-049
prompt avoidance experiment

WP-050
candidate/evidence architecture analysis
```

We should not keep producing increasingly complicated mechanisms for a problem that the authoritative corpus itself cannot always solve. fileciteturn36file0L189-L200

---

# 22. But There Is Still a Meaningful Next Problem

Although candidate uniqueness itself should not become WP-051, the project still has meaningful unresolved issues.

The strongest one is:

## Evidence adequacy for target selection

We currently select targets from the category concept inventory.

But WP-050 has shown that:

```text
not every selected target has enough target-specific evidence
to support a good question.
```

This suggests a potentially important architectural improvement:

```text
Target selection
        ↓
Evidence sufficiency check
        ↓
Can this target support a target-specific question?
        ↓
YES → generate
NO  → select another target
```

This is a much more promising direction than trying to force the generator to invent uniqueness.

---

# 23. This Could Be WP-051

I recommend:

**WP-051 — Target Evidence Sufficiency / Questionability Study**

The question should be:

> **Before generation, can the system deterministically determine whether a selected target has enough authoritative, target-specific evidence to support at least one valid question?**

This is different from:

```text
"Does the target have a unique property?"
```

It asks:

```text
"Does this target have enough evidence to be worth generating a question about?"
```

---

# 24. Why This Is Better

For:

```text
Caudate Nucleus
```

WP-050 currently says:

```text
no target-specific property found
```

Instead of:

```text
generate
→ fail
→ retry
→ fail
→ fail
```

we could potentially have:

```text
target selection
→ evidence sufficiency check
→ insufficient
→ choose another target
```

This attacks the waste directly.

It also respects:

```text
fail closed
```

rather than trying to weaken validation.

---

# 25. WP-051 Should Not Become a New Semantic Judge

The next investigation should remain deterministic.

It should use information already available in:

```text
concept inventory
evidence anchors
source chunks
category coverage
```

The first question is simply whether a deterministic evidence-sufficiency signal can be defined.

Do not immediately build:

```text
LLM evaluator
semantic property extractor
ontology
```

---

# 26. Possible Simple Signals to Investigate

These are hypotheses, not decisions:

```text
Does the target have non-enumerative evidence?

Does the target have a factual_focus longer than enumeration noise?

Does the target have at least one target-specific sentence?

Does the target have a source relationship?

Does the target have evidence that names a function, location,
connection, role, or other specific property?

Does the target have more than one independent evidence occurrence?
```

The investigation should determine whether any of these are safe and useful.

Do not assume they are sufficient.

---

# 27. The Globus Pallidus / Caudate Contrast Is Valuable

WP-050 gives us an excellent test pair.

```text
Globus Pallidus
    ↓
target-specific evidence exists
    ↓
successful property question possible
```

versus:

```text
Caudate Nucleus
    ↓
only enumeration evidence found
    ↓
property question repeatedly ambiguous
```

This suggests that an **evidence sufficiency signal** may be feasible.

This should be investigated before adding any more generation logic.

---

# 28. Nucleus Accumbens Remains an Important Test Case

`Nucleus Accumbens` is particularly useful because:

```text
some apparently specific facts
```

are actually:

```text
category-level facts
```

This means a simple text-presence test may not be enough.

WP-051 should therefore explicitly test whether:

```text
target-specific evidence
```

can be distinguished from:

```text
category-level evidence mentioning the target.
```

This is the difficult case.

---

# 29. Do Not Use the Accepted Reward-System Question as Ground Truth

The report correctly flags:

```text
Nucleus Accumbens — center of reward system
```

as uncertain.

Do not use that accepted example as proof that the target has a unique evidence-supported property.

It should be treated as:

```text
open validator-fidelity case
```

until independently established.

---

# 30. Basillar Artery Remains Separate

Continue to keep:

```text
Basillar artery
```

out of this thread.

It remains the separate WP-048 issue:

```text
possible grounding interpretation problem
```

It should not influence the target-evidence-sufficiency investigation.

---

# 31. Final Architectural State

The project is now at:

```text
WP-046
parent/child distractor problem
        ↓
SOLVED

WP-047
target identity substitution
        ↓
SOLVED for current scope

WP-048
classification ambiguity detection
        ↓
existing validators already detect it

WP-049
prompt-based avoidance
        ↓
INCONCLUSIVE

WP-050
candidate/evidence uniqueness investigation
        ↓
NO SAFE GENERAL UNIQUENESS MECHANISM
        ↓
evidence-content limitation identified
```

The remaining productive question is:

```text
Can we avoid selecting targets that lack sufficient
target-specific evidence in the first place?
```

---

# 32. Final Decision

**WP-050: ACCEPTED.**

It is a successful architectural investigation.

The decision is:

```text
Do NOT implement candidate uniqueness machinery.

Do NOT add another validator.

Do NOT keep blindly expanding the generation prompt.

Do NOT add an ontology.

Do NOT add an LLM judge.

Do NOT increase retries.
```

Instead, investigate whether target selection can become:

```text
evidence-aware
```

before generation.

---

# 33. Recommended WP-051

**WP-051 — Target Evidence Sufficiency / Questionability Study**

Primary question:

> **Can the existing authoritative evidence be used to determine, before generation, whether a target has sufficient target-specific information to support a valid and non-ambiguous question?**

Scope:

```text
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens
```

The investigation should compare:

```text
successful target
vs.
repeatedly failing target
```

and determine whether a safe deterministic signal exists.

No production implementation should occur until the architectural investigation is complete.

---

# Final Review Conclusion

WP-050 is one of the more important WPs in the recent sequence because it changes the diagnosis.

The original interpretation was:

```text
LLM generates ambiguous classification question
        ↓
need better generation strategy
```

WP-050 shows the deeper reality:

```text
some targets have genuinely distinguishing evidence
some targets do not
        ↓
a generator cannot safely manufacture a missing distinction
```

The strongest concrete finding is:

```text
Globus Pallidus
→ unique evidence-supported property exists

Caudate Nucleus
→ no evidence-supported unique property found

Nucleus Accumbens
→ no evidence-supported unique property found
```

The completion report supports this directly through its candidate matrix and reconstruction of the real evidence. fileciteturn36file0L116-L135

Therefore the correct architectural move is **not another generation trick**.

It is to investigate whether the system should become **evidence-aware when selecting targets**.

**WP-050: ACCEPTED.**

**Recommended next WP: WP-051 — Target Evidence Sufficiency / Questionability Study.**
