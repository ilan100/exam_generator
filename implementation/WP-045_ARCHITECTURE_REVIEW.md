# WP-045 Architecture Review

## Review Status

**ACCEPTED WITH REQUIRED FOLLOW-UP**

WP-045 is accepted as a successful diagnostic work package.

The 11/12 pilot result must **not** be interpreted as an improvement caused by WP-045, because no production code was changed. The important result is the architectural diagnosis and the rejection of an unsafe deterministic solution.

## 1. Executive Assessment

WP-045 established four important facts:

1. `Globus Pallidus` and `Corticospinal Tract` do not share one safely identifiable root cause.
2. `Corticospinal Tract` has a confirmed parent/child ambiguity.
3. The proposed `has_named_child` pre-generation rule is unsafe because it produces a real false positive.
4. The next investigation should therefore examine the candidate/distractor layer rather than automatically skipping targets before generation.

No production code was changed, and the existing architecture remains intact.

## 2. Globus Pallidus

The dominant observed failure mode is broad classification/membership ambiguity.

The investigation found that `Globus Pallidus` has essentially the same sparse/noisy local anchored evidence shape as successful siblings such as `Caudate Nucleus` and `Nucleus Accumbens`.

Therefore no safe deterministic property of the target's local evidence was demonstrated that predicts:

```text
Globus Pallidus → unsafe
```

while allowing:

```text
Caudate Nucleus → safe
Nucleus Accumbens → safe
```

### Decision

Do not create a `Globus Pallidus`-specific heuristic.

Do not broaden the enumeration detector merely to catch this case.

The deterministic root cause remains unresolved.

## 3. Corticospinal Tract

This case is substantially better understood.

The evidence contains:

```text
Corticospinal Tract
Anterior Corticospinal Tract
Lateral Corticospinal Tract
```

General properties of the parent can also be properties of the children.

Therefore a question about a general property can have multiple correct answers when one of the children appears as a distractor.

The same target and essentially the same question can succeed or fail depending on which distractors are selected.

This indicates:

```text
target evidence
    ↓
question generation
    ↓
distractor selection
    ↓
child selected as distractor
    ↓
multiple supported answers
    ↓
validation rejection
```

rather than:

```text
target evidence
    ↓
target is inherently unsafe
```

## 4. Rejection of `has_named_child`

The candidate diagnostic signal looked attractive because it identified both problematic targets.

However, it also flagged:

```text
Inferior Cerebellar Artery (PICA)
```

because the corpus contained differently extracted versions of the same real-world structure.

The investigation considered:

1. plain substring containment;
2. same-originating-chunk restriction;
3. restricted anatomical qualifier vocabulary.

None safely separated genuine hierarchy from extraction duplication.

### Architectural decision

Do not ship the `has_named_child` rule.

This was the correct decision.

## 5. Pre-Generation Skip Is Too Aggressive

For `Corticospinal Tract`, the target itself may be usable.

The ambiguity arises when a particular child is selected as a distractor.

Therefore:

```text
target has child
        ↓
skip target
```

is too aggressive.

The next investigation should determine whether:

```text
target
+
candidate distractor
+
question predicate
```

can be evaluated deterministically.

## 6. Pilot Interpretation

WP-045 produced:

```text
11/12 accepted
91.7%
```

but production code was unchanged.

Therefore the result cannot be attributed to WP-045.

It demonstrates useful run-to-run variance and confirms that the same architectural pipeline can sometimes produce an acceptable and sometimes an ambiguous `Corticospinal Tract` question.

## 7. Target Identity Remains Open

WP-045 also surfaced an accepted `Globus Pallidus` answer that was a functional description rather than the requested target identity.

This is not a WP-045 regression.

It is a live reproduction of the known target-identity weakness.

It also affected coverage because coverage identity did not recognize the functional description as the requested target.

The architectural relationship remains:

```text
target identity
    ↓
accepted answer identity
    ↓
coverage identity
    ↓
future target selection
```

This must remain visible in subsequent architecture work.

## 8. English-First

The pilot recorded one accepted answer that was not English-first.

This was the same `Globus Pallidus` functional-description case.

No new language-specific architecture is recommended.

The underlying issue is target identity/semantic alignment.

## 9. Regression

Regression status:

```text
1379 passed
0 failed
```

Public schemas remained unchanged and production source was unchanged.

This is the expected result for a diagnostic WP.

## 10. Concept Rotation

The pilot showed:

```text
אספקת דם:      4/4 distinct
גרעיני הבסיס:  3/4 distinct
מסילות עצביות: 3/4 distinct
```

No coverage redesign is recommended at this point.

## 11. Source-Role Follow-Up

The WP-044 source-role extraction limitation remains.

`extract_source_relationship_entity()` can encounter truncated names when operating on raw text.

This is separate from the current ambiguity investigation.

Do not broaden the next WP into a general source-role refactor unless the investigation demonstrates that it is required.

## 12. What We Should NOT Do

Do not:

- expand the enumeration detector;
- add a general ambiguity classifier;
- add an LLM ambiguity judge;
- add embeddings;
- add a medical ontology;
- automatically skip targets with children;
- automatically skip `Corticospinal Tract`;
- create a `Globus Pallidus` special case;
- loosen grounding;
- increase retries;
- expand the pilot yet.

## 13. Architectural Direction

The next WP should **not** immediately implement a distractor detector.

It should first determine whether the distractor-level mechanism is actually generalizable.

Use the existing three pilot categories as the controlled dataset:

```text
אספקת דם
גרעיני הבסיס
מסילות עצביות
```

The objective is to find:

```text
problematic cases
+
successful controls
+
false-positive controls
```

and determine whether a deterministic structural rule can safely distinguish them.

## 14. Final Decision

**WP-045: ACCEPTED.**

The key architectural conclusion is:

```text
Do not try to predict all ambiguity from target evidence before generation.

Investigate whether specific unsafe candidate answers/distractors
can be identified deterministically during candidate selection
or after candidate generation.
```

At the same time:

```text
Globus Pallidus remains unresolved.
```

It must not be forced into the `Corticospinal Tract` solution.

## 15. Recommended WP-046

**WP-046 — Generalization Study of Evidence-Supported Ambiguity**

WP-046 should be diagnostic first.

It should:

1. inspect the existing candidate/distractor architecture;
2. build a deliberate case set from the three existing pilot categories;
3. include known failures;
4. include successful controls;
5. include parent/child candidates;
6. include classification/sibling candidates;
7. include textual-containment false positives;
8. compare evidence relationship, candidate relationship, and actual question ambiguity;
9. determine whether a deterministic candidate-level mechanism generalizes;
10. implement only if the mechanism passes explicit safety criteria.

The full WP-046 instruction is provided separately.
