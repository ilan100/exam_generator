# WP-049 Architecture Review

## Review Status

**INCONCLUSIVE — DO NOT ACCEPT AS A SOLVED PROBLEM**

WP-049 was executed correctly as a controlled generation-strategy experiment, but the evidence is insufficient to conclude that the prompt intervention solves the classification-ambiguity problem.

The most important result is:

> The prompt change produced some encouraging behavioral evidence, but it did **not demonstrate a reduction in classification-ambiguity failures**.

The completion report itself correctly concludes `INCONCLUSIVE`. fileciteturn35file0L232-L236

The correct architectural decision is therefore **not to declare the problem solved and not to keep iterating blindly on prompt wording**.

---

# 1. Executive Assessment

WP-049 tested a very small change to the existing generation prompt:

1. a second worked example based on the real basal-nuclei failure shape;
2. an explicit escape-hatch instruction telling the model what to do when it cannot find a distinguishing property.

No production source code was changed. The existing validators, retry budget, retrieval, coverage, WP-044, WP-046, and WP-047 mechanisms remained intact. fileciteturn35file0L60-L68

This was the right experimental design.

However, the fresh experiment contained only:

```text
4 primary-target rounds
3 accepted
3 rejected attempts
```

and therefore cannot establish a reliable improvement or regression.

The report appropriately recognizes this limitation. fileciteturn35file0L168-L178

---

# 2. What WP-049 Actually Tested

The existing prompt already contained classification/enumeration guidance.

It already instructed the model to:

- recognize enumeration/classification targets;
- avoid generic list/member questions;
- use one distinguishing property;
- prefer a specific function, location, relationship, alternate name, or similarly narrow fact. fileciteturn35file0L13-L35

The identified gap was more specific:

```text
model cannot find an obvious distinguishing property
        ↓
existing prompt does not explicitly say what to do
        ↓
model may fall back to generic membership
```

WP-049 therefore added:

```text
one domain-close worked example
+
one explicit fallback/escape-hatch instruction
```

This is a sensible hypothesis and a minimal intervention.

---

# 3. Prompt Modification Quality

The prompt modification was architecturally disciplined.

It changed only the existing:

```text
Testing enumeration or classification targets
```

section.

It did not modify:

```text
validators
retrieval
candidate discovery
coverage
retry budget
schemas
LLM configuration
source authority
```

The report confirms that only:

```text
prompts/generation/question.txt
```

was changed. fileciteturn35file0L120-L124

**Assessment: GOOD.**

---

# 4. The New Basal-Nuclei Example Was Justified

The second example was based on the actual observed failure shape:

```text
Caudate Nucleus
Putamen
Nucleus Accumbens
Globus Pallidus
```

rather than inventing an unrelated example.

It explicitly explains why:

```text
Which of the following is part of the basal nuclei?
```

or:

```text
Which of the following is part of the Corpus Striatum?
```

can have multiple correct answers. fileciteturn35file0L83-L99

This is preferable to adding a generic abstract instruction.

---

# 5. The Escape Hatch Is Architecturally Useful

The second addition is also sensible:

```text
Before committing to a classification-membership predicate,
ask whether a specific evidence-supported fact about the target
is not equally true of the other members.
```

If no such property can be found, the model is instructed to choose another evidence-supported aspect rather than fall back to generic membership. fileciteturn35file0L100-L110

This directly addresses the failure mode identified in WP-048.

The problem is not that the instruction is poorly designed.

The problem is that **one small experiment cannot tell us whether it works reliably**.

---

# 6. Baseline

The baseline reconstruction is useful:

```text
11 primary-target rounds
9 accepted
81.8% acceptance

25 total attempts
16 rejected

14/16 rejected attempts
87.5%
classification-ambiguity-shaped

2/9 accepted rounds
22.2%
succeeded on attempt 1
```

The report also notes that many successful rounds required 2–3 attempts, commonly after an initial generic classification failure. fileciteturn35file0L39-L46

This supports the original architectural diagnosis:

```text
classification ambiguity
        ↓
validator correctly rejects
        ↓
retry often needed
```

---

# 7. The Revised Pilot

The revised pilot produced:

```text
4 primary-target rounds
3 accepted
75% acceptance

3 rejected attempts
3/3 classification-ambiguity-shaped
```

The full pilot across the three categories produced:

```text
9/12 accepted
9/9 target aligned
9/9 English-first
```

fileciteturn35file0L126-L132

The primary comparison is therefore:

| Metric | Baseline | Revised |
|---|---:|---:|
| Primary-target rounds | 11 | 4 |
| Accepted rounds | 9 | 3 |
| Acceptance | 81.8% | 75% |
| Rejected attempts | 16 | 3 |
| Classification-shaped rejections | 14 | 3 |
| First-attempt success among accepted | 22.2% | 100% |

The sample sizes are too different to support a strong statistical conclusion.

---

# 8. Primary Metric Did Not Improve

This is the most important negative result.

The report measures:

```text
classification-ambiguity-shaped rejections
```

as:

```text
baseline: 14/16 = 87.5%
revised:   3/3 = 100%
```

The revised percentage is actually higher.

However, this is based on only three rejected attempts.

Therefore the correct conclusion is:

```text
NO DEMONSTRATED IMPROVEMENT
```

not:

```text
prompt made things worse
```

The report correctly calls the result statistically/experimentally inconclusive. fileciteturn35file0L166-L174

---

# 9. The Interesting Positive Signal

There is one genuinely interesting result:

```text
First-attempt success among accepted rounds

Baseline: 2/9 = 22.2%
Revised:  3/3 = 100%
```

This is a large observed difference.

But:

```text
n = 3
```

for the revised condition.

Therefore it cannot yet be treated as evidence that the prompt reliably improves first-attempt success.

The correct architectural interpretation is:

> **Promising signal, insufficient evidence.**

The completion report handles this appropriately. fileciteturn35file0L176-L178

---

# 10. The Most Valuable Qualitative Evidence

The actual revised generation sequence is informative.

For `Caudate Nucleus`, the revised prompt produced:

### Attempt 1

```text
influences decision-making
```

This was more specific than bare category membership, but still failed because:

```text
Caudate Nucleus
Nucleus Accumbens
```

were both supported.

### Attempt 2

Another specific-property formulation was attempted.

### Attempt 3

The model reverted to:

```text
Which of the following is part of the basal nuclei?
```

and all four choices were supported.

### Successful later round

```text
Which structure is a basal nucleus also called Caudate Nucleus?
```

was accepted.

fileciteturn35file0L137-L159

This is useful evidence that the new prompt **did influence generation behavior**, but did not reliably solve the semantic uniqueness problem.

---

# 11. Important Architectural Observation

The revised prompt appears to have changed the **order of candidate strategies**:

```text
specific property
        ↓
specific property
        ↓
generic classification fallback
```

rather than:

```text
generic classification
        ↓
generic classification
        ↓
generic classification
```

This is a meaningful behavioral shift.

But it does not yet establish:

```text
specific property
        ↓
unique specific property
```

That distinction is critical.

The model can obey:

```text
"find a specific property"
```

and still select a property shared by multiple concepts.

The report explicitly demonstrates this with the `decision-making` example. fileciteturn35file0L143-L154

---

# 12. This Reveals a Deeper Problem

The prompt now effectively asks:

```text
find a distinguishing property
```

But the model must still determine:

```text
is this property actually unique among the answer candidates?
```

That is harder.

The current architecture deliberately does not deterministically parse arbitrary question semantics.

Therefore:

```text
Prompt says "find a unique property"
```

does not guarantee:

```text
LLM actually selects a unique property
```

This is the key limitation revealed by WP-049.

---

# 13. Question Diversity

The completion report correctly flags an important concern.

All three accepted revised primary-target questions used:

```text
identity-by-name
```

or:

```text
named-alias framing
```

The more semantically interesting property-based attempts failed.

fileciteturn35file0L196-L199

This creates a possible risk:

```text
prompt avoids ambiguity
        ↓
by increasingly favoring identity questions
```

That would technically improve safety while degrading question diversity and pedagogical quality.

There is not enough evidence to say this happened systematically.

But it is a valid risk and must remain visible.

---

# 14. Safety Criteria

The completion report assessed 15 criteria.

The important result is:

```text
13 clearly met
2 uncertain
```

The uncertain criteria are:

```text
question diversity
demonstrated improvement in primary metric
```

No criterion clearly failed. fileciteturn35file0L212-L230

This supports:

```text
INCONCLUSIVE
```

rather than:

```text
REJECTED
```

---

# 15. Regression

The regression result is clean:

```text
1396 passed
0 failed
```

Schemas remained byte-identical.

No source code changed.

Only the generation prompt changed. fileciteturn35file0L200-L204

This is strong evidence that the intervention did not damage the surrounding architecture.

---

# 16. WP-046 and WP-047 Remain Intact

WP-046 fired six times during the full pilot, all for `Corticospinal Tract`, and continued to operate correctly.

WP-047 fired zero times because no target-identity violation occurred.

fileciteturn35file0L184-L190

Therefore the new prompt intervention did not interfere with either safety mechanism.

---

# 17. English-First and Target Alignment

The revised full pilot achieved:

```text
Target alignment: 9/9 = 100%
English-first:     9/9 = 100%
```

These mechanisms remain intact. fileciteturn35file0L180-L182

No architectural action is needed here.

---

# 18. Important Decision: Do Not Keep Prompt-Tuning Blindly

I strongly agree with the completion report's own conclusion:

> Do not keep adding prompt instructions until the prompt becomes a rule system.

WP-049 already tested the most natural small intervention:

```text
domain-close example
+
explicit fallback instruction
```

It did not produce decisive evidence.

Therefore the next step should **not** simply be:

```text
WP-050:
add three more examples
add five more rules
add more wording
```

That would risk prompt overfitting.

---

# 19. The Real Architectural Question Now

WP-049 leaves us with a sharper question:

```text
Can the system provide the LLM with enough structured information
about candidate uniqueness during generation to help it choose
a truly distinguishing predicate?
```

This is different from asking the LLM to:

```text
"please be more specific"
```

The model already received that instruction.

The failure was:

```text
specific ≠ unique
```

For example:

```text
"participates in decision-making"
```

is specific enough linguistically but not unique enough semantically.

---

# 20. Recommended WP-050

I recommend that WP-050 **not immediately modify the prompt again**.

Instead:

## WP-050 — Generation Candidate Uniqueness Study

Investigate whether the existing architecture can expose structured information during generation such as:

```text
target
candidate answer concepts
evidence-supported properties
properties shared with candidate distractors
```

The objective is to determine whether we can help the generator select:

```text
property(target) = true
property(distractor_i) = false
```

before the final question is generated.

This is an architectural investigation, not yet an implementation mandate.

---

# 21. Why This Is the Logical Next Step

The progression is now:

```text
WP-046
detect structural parent/child collision
        ↓
solved

WP-047
detect target identity substitution
        ↓
solved for current scope

WP-048
determine whether classification ambiguity needs a detector
        ↓
existing validators already detect it
        ↓
problem is generation reliability

WP-049
try prompt-based avoidance
        ↓
behavior changes somewhat
        ↓
not enough evidence of actual improvement
        ↓
specific ≠ necessarily unique

WP-050
investigate structured candidate uniqueness
```

This is a logical architectural progression rather than another ad-hoc patch.

---

# 22. WP-050 Must Not Become an Ontology Project

The next WP should not immediately introduce:

```text
UMLS
SNOMED
external ontology
knowledge graph
LLM judge
```

The first question is whether the existing evidence and candidate structures already contain enough information.

We should reuse what the system already knows before adding a new knowledge subsystem.

---

# 23. WP-050 Should Inspect the Existing Candidate Architecture

The investigation should examine:

```text
candidate discovery
competitor discovery
retrieved evidence
QuestionBlueprint
QuestionTarget
QuestionRelationship
generation prompt context
```

The key question is:

> Can the existing candidate/evidence structures be used to identify properties that distinguish the target from the candidate distractors?

If yes, we may have a safer generation-time mechanism.

If no, document the architectural gap.

---

# 24. Do Not Change Production Code Yet

WP-050 should initially be:

```text
ARCHITECTURAL INVESTIGATION
```

not:

```text
implementation
```

Do not modify production code until the architecture establishes:

```text
what information is available
what information is missing
what deterministic computation is possible
what additional information would be required
```

---

# 25. Keep the Current Prompt Change for Now

The completion report recommends leaving the revised prompt in place because:

```text
no measured regression
```

and:

```text
some positive behavioral signal
```

exists.

I agree, with one qualification:

**Treat it as provisional, not as an accepted solution.**

It should not be described in the architecture as "solving classification ambiguity."

It is simply the current experimental prompt version.

---

# 26. Basillar Artery Remains Separate

The `Basillar artery` / `AICA` issue remains unresolved.

WP-049 correctly did not use it as evidence for or against the classification-avoidance strategy. fileciteturn35file0L192-L194

Keep it as a separate architectural thread.

Do not allow it to distort the classification-ambiguity investigation.

---

# 27. Category Scope

Do not expand beyond:

```text
אספקת דם
גרעיני הבסיס
מסילות עצביות
```

yet.

The current problem remains insufficiently understood.

More categories would increase noise before we know what structured uniqueness information we need.

---

# 28. Final Architectural State

After WP-049:

```text
WP-046
parent/child distractor ambiguity
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
PROMISING BUT INCONCLUSIVE

Current primary issue:
        ↓
how to reliably generate a truly target-unique predicate
```

---

# 29. Final Decision

**WP-049: INCONCLUSIVE — ACCEPT AS AN EXPERIMENT, NOT AS A SOLUTION.**

The prompt modification may remain in the repository as the current experimental version because:

- it caused no measured regression;
- it preserved all safety mechanisms;
- it produced some positive behavioral signal;
- it did not clearly solve the primary problem.

But it must not be declared successful.

---

# 30. Recommended WP-050

Proceed to:

**WP-050 — Generation Candidate Uniqueness Study**

Primary question:

> **Can the existing candidate and evidence architecture provide structured information that allows generation to select a property that is true for the target and false for the plausible distractors, rather than merely asking the LLM to "be more specific"?**

WP-050 should:

1. inspect the existing candidate/evidence structures;
2. identify what information about candidate properties is already available;
3. reconstruct the three basal-nuclei failure cases;
4. identify why their "specific" generated properties were still shared;
5. determine whether target-vs-candidate property uniqueness can be represented deterministically;
6. determine whether this information can be supplied to generation;
7. avoid implementation until justified;
8. avoid adding an ontology or LLM judge;
9. preserve WP-046/WP-047;
10. keep the three-category scope.

---

# Final Review Conclusion

WP-049 was executed responsibly.

It:

```text
identified a precise prompt gap
        ↓
made a minimal prompt change
        ↓
kept all other architecture constant
        ↓
ran one controlled live pilot
        ↓
measured the result honestly
        ↓
reported INCONCLUSIVE
```

The most important learning is:

```text
more specific
        ≠
uniquely identifying
```

The revised prompt succeeded in pushing generation toward more specific predicates in at least one observed sequence, but those predicates could still be shared by multiple concepts. fileciteturn35file0L143-L165

Therefore we should **not continue adding prompt instructions blindly**.

The next architectural investigation should determine whether the system can expose **structured target-vs-candidate uniqueness information** during generation.

**WP-049: INCONCLUSIVE. Proceed to WP-050 — Generation Candidate Uniqueness Study.**
