# WP-047 Architecture Review

## Review Status

**ACCEPTED**

WP-047 is accepted as a successful architectural and implementation work package.

The central result is stronger than originally expected: after examining the real historical data, the system established a deterministic target-to-answer contract for the current scope of named-entity pilot-category targets, and implemented it without weakening the existing architecture.

The completion report examined 54 real accepted pilot-category questions, identified 7 real target-substitution defects, and found **0 legitimate related-entity answer cases**. fileciteturn33file0L61-L87

---

## 1. What WP-047 Established

WP-047 correctly began by refusing to assume:

```text
correct_answer == target
```

Instead it searched the historical data for legitimate cases where a related entity could be the correct answer.

The result was:

```text
54 real accepted pilot-category questions
7 confirmed invalid target substitutions
0 legitimate related-entity answers
```

This is strong empirical justification for a simpler identity contract within the investigated scope. fileciteturn33file0L61-L87

---

## 2. Existing Architecture

WP-047 inspected `QuestionTarget`, `QuestionRelationship`, `extract_relationship()`, `ConceptIdentity`, generation, formatting, diagnostics, and coverage.

The important finding is that there was **no general deterministic target-alignment gate** before this WP.

WP-040 expressed target identity as prompt prose. WP-044 had a deterministic check, but only for `is_source_role`. fileciteturn33file0L11-L21

Therefore WP-047 closes a real architectural gap.

---

## 3. Relationship-Type Finding

The investigation of all ten existing `relationship_type` values produced an important secondary result:

> `relationship_type` is not a reliable predictor of target alignment in the current dataset.

Most pilot targets classify as `UNSPECIFIED`, and the classifier operates on `factual_focus`, not on the actual generated question.

The same nominal relationship can therefore produce aligned or misaligned answers depending on the LLM output. fileciteturn33file0L23-L34

**Decision:** do not make target-alignment enforcement depend on the current relationship classifier.

---

## 4. Known Failure Was Correctly Reconstructed

The critical real failure was:

```text
Target:
Corticospinal Tract

Question:
where does the Corticospinal Tract motor pathway begin in the brain?

Correct answer:
Precentral Gyrus
```

It was factually grounded and passed all five validators, but it did not answer with the requested target.

The existing validators could not catch this because they do not receive the target as an input. fileciteturn33file0L36-L59

This confirms that the missing check was architectural, not merely prompt quality.

---

## 5. Historical Evidence

WP-047 found seven confirmed target-substitution defects:

1. `Basillar artery` → `Superior Cerebellar Artery`
2. `The Basal Gang` → functional description
3. `Corpos Str` → functional description
4. `Corpos Str` → `Caudate Nucleus`
5. `Corticospinal Tract` → `Precentral Gyrus`
6. `Globus Pallidus` → functional description
7. `Corticospinal Tract` → `Precentral Gyrus` again

No uncertain cases were found. fileciteturn33file0L73-L87

Most importantly:

```text
legitimate related-entity answers = 0
```

in the examined real dataset.

This is the evidence that justifies the simpler contract.

---

## 6. Target-to-Answer Contract

WP-047 defines:

```text
TARGET_ALIGNED :=
    target.named_entity_target is True
    AND
    normalize(target.topic)
        is contained within
    normalize(correct_answer_text)
```

This is correctly **one-directional**.

It accepts:

```text
Corticospinal Tract
The Corticospinal Tract
```

but rejects:

```text
Precentral Gyrus
Tract
```

The implementation deliberately does not use bare equality and does not use reverse containment. fileciteturn33file0L105-L115

---

## 7. Alias and Language Handling

`ConceptIdentity` was investigated and found insufficient as a general alias system.

However, WP-041's English-first rule changes the situation: current named-entity generation is required to use the English representation, so the legitimate cross-script answer scenario that would otherwise complicate this check is no longer expected in the current scope. fileciteturn33file0L117-L123

**Decision:** do not introduce a new alias subsystem now.

Keep normalization deterministic and simple.

---

## 8. Enforcement Location

WP-047 correctly evaluated:

```text
planning
generation prompt
validation
post-generation deterministic check
```

The post-generation deterministic check is the correct location because the actual generated answer is available there, while the target is already known.

It also follows the established WP-044/WP-046 pattern and avoids changing the five existing validators. fileciteturn33file0L124-L130

---

## 9. Implementation

The new:

```text
_validate_target_answer_identity()
```

is placed after `_validate_distractor_containment()` and before the existing validators.

It uses the existing:

```text
InvalidGeneratedOutputError
```

and therefore preserves retry/attempt semantics.

No validators, schemas, coverage, retry budget, English-first mechanism, WP-044 mechanism, or WP-046 mechanism were changed. fileciteturn33file0L148-L157

This is the correct minimal implementation.

---

## 10. Tests and Regression

WP-047 added 10 focused tests covering:

- direct target identity;
- normalization;
- target plus surrounding text;
- the real `Corticospinal Tract` → `Precentral Gyrus` regression;
- the `Globus Pallidus` functional-description case;
- the `Corpos Striatum` sibling substitution;
- non-named-entity targets;
- no additional LLM call;
- deterministic implementation;
- coexistence with WP-046.

Regression:

```text
1396 passed
0 failed
```

Public schemas remained byte-identical. fileciteturn33file0L152-L160

**Implementation quality: strong.**

---

## 11. Pilot Interpretation

The fresh pilot produced:

```text
7/12 accepted
58.3%
```

This is lower than WP-046's 11/12, but the report correctly investigated causality.

The critical fact is:

```text
WP-047 identity check fired: 0 times
```

The five failed/exhausted rounds were caused by:

- WP-046's existing distractor-containment mechanism;
- ordinary validator-level stochastic failures.

Therefore there is no evidence that WP-047 caused the lower acceptance rate. fileciteturn33file0L162-L185

---

## 12. Most Important Pilot Result

Despite the lower acceptance:

```text
Target alignment = 7/7 = 100%
```

among accepted questions.

This is the first pilot in which every accepted question was target-aligned with a structural guarantee rather than only a favorable observed sample. fileciteturn33file0L181-L189

That is the meaningful success criterion for WP-047.

---

## 13. WP-046 and WP-047 Coexist Correctly

In the fresh pilot:

```text
WP-047 check: 0 fires
WP-046 check: 5 fires
```

WP-046 continued to block the known parent/child distractor problem, while WP-047 remained independent.

This demonstrates that the two mechanisms address separate failure classes without interfering with each other. fileciteturn33file0L176-L180

---

## 14. Main Remaining Problem

WP-047 correctly did not attempt to solve classification ambiguity.

Instead, it strengthened the evidence.

A third real instance appeared:

```text
Nucleus Accumbens
```

showing the same generic classification-ambiguity family previously observed with:

```text
Globus Pallidus
Caudate Nucleus
```

The pilot also produced a new classification-adjacent signal for:

```text
Basillar artery
```

where multiple-supported-answer behavior appeared. fileciteturn33file0L199-L207

The problem has therefore evolved from:

```text
Why does Globus Pallidus fail?
```

to:

```text
Why does the generator sometimes create a question
whose predicate is satisfied by multiple candidate answers?
```

---

## 15. Current Architectural State

### Problem A — Parent/child distractor ambiguity

**Status: solved narrowly by WP-046.**

```text
_validate_distractor_containment()
```

### Problem B — Target identity substitution

**Status: solved for the current named-entity pilot scope by WP-047.**

```text
_validate_target_answer_identity()
```

### Problem C — Generic classification ambiguity

**Status: unresolved and now the primary architectural problem.**

Current real examples include:

```text
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens
Basillar artery
```

---

## 16. Important Scope Boundary

The target-answer contract should currently be described as:

> Safe for named-entity pilot-category targets under the current post-WP-041 English-first architecture.

It should **not** silently be promoted to a universal claim about every possible target and relationship.

The completion report explicitly keeps this scope boundary. fileciteturn33file0L128-L148

---

## 17. Recommendation for WP-048

I agree with the completion report:

**WP-048 should investigate the generic classification-ambiguity family.**

Start with:

```text
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens
Basillar artery
```

but do not assume that all four have exactly the same cause.

The objective should be:

```text
determine the common structural property, if one exists,
that makes a generated question's predicate apply to
multiple candidate answers
```

not:

```text
find a rule that rejects these four targets
```

The investigation should distinguish:

```text
OBSERVED
INFERENCE
HYPOTHESIS
```

and must be allowed to conclude:

```text
No safe deterministic mechanism exists.
```

---

## 18. Recommended WP-048 Investigation

WP-048 should:

1. reconstruct every real classification-ambiguity failure;
2. collect successful controls for the same targets;
3. compare the actual generated questions;
4. compare the supporting evidence;
5. compare the actual answer choices;
6. identify the semantic predicate being tested;
7. determine whether multiple answer choices satisfy that predicate;
8. determine whether the failure can be recognized deterministically;
9. test candidate signals against false positives;
10. implement only if a safety criterion comparable to WP-046/WP-047 is met.

The key distinction should remain:

```text
target relationship
```

versus:

```text
actual question predicate
```

The second appears to be the more relevant level for this problem.

---

## 19. Do Not Redesign `relationship_type` Yet

WP-047 found that the current `relationship_type` classifier is weak for this corpus.

That is useful architectural information, but it is not yet sufficient justification for redesigning `generation/relationship.py`.

First determine whether classification ambiguity can be understood from:

```text
target
+
evidence
+
candidate answers
+
actual question predicate
```

Only then decide whether the relationship abstraction itself needs change.

---

## 20. Do Not Expand the Pilot Categories Yet

Remain with:

```text
אספקת דם
גרעיני הבסיס
מסילות עצביות
```

for WP-048.

The current three categories already contain enough real examples to investigate the classification-ambiguity family.

Expanding now would add breadth before the failure mechanism is understood.

---

## 21. Final Architectural Decision

**WP-047: ACCEPTED.**

The target-to-answer identity problem is now structurally addressed for:

```text
named_entity_target
+
current post-WP-041 English-first architecture
+
pilot-category scope
```

The new check should remain in production.

The generation safety path is now:

```text
Target
   ↓
LLM generates question + answers
   ↓
target-answer identity check
   ↓
distractor-containment check
   ↓
existing validators
```

with the two deterministic checks addressing different failure classes.

---

## 22. Final Recommendation

Proceed to:

**WP-048 — Classification Ambiguity Investigation**

Do not:

- broaden the pilot categories yet;
- redesign `relationship_type` yet;
- introduce an LLM judge;
- create target-specific exceptions;
- weaken WP-046 or WP-047.

Instead, investigate whether:

```text
question predicate
+
evidence-supported candidate set
```

can deterministically reveal that more than one answer choice is correct.

If a safe deterministic signal exists, implement the smallest possible mechanism.

If no safe signal exists, document that architectural limit rather than inventing a heuristic.

---

## Final Review Conclusion

WP-047 is a **successful and meaningful WP**.

It converted target identity from:

```text
prompt instruction
```

into:

```text
deterministic structural contract
```

for the investigated scope.

The strongest evidence is:

```text
7/7 accepted questions target-aligned
0 legitimate related-entity cases found
7 historical target-substitution defects identified
1396/1396 tests passing
WP-046 preserved
```

The lower 7/12 acceptance number was investigated and found not to be caused by WP-047.

The main remaining architectural issue is now clearly:

```text
generic classification ambiguity
```

with an expanding real evidence base.

**WP-047 is accepted. Proceed to WP-048.**
