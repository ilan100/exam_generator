# Architecture Review — WP-038

**Review Date:** 2026-08-10  
**Reviewer:** ChatGPT (Architecture Review)  
**WP Reviewed:** WP-038 — Deterministic Concept Identity and Coverage Matching  
**Status:** **ACCEPTED — INVESTIGATION SUCCESSFUL, CROSS-SCRIPT PROBLEM NOT SOLVED, NEXT DIRECTION SHOULD CHANGE**

---

## 1. Executive Summary

WP-038 is accepted as a technically disciplined and valuable work package.

The implementation correctly introduced a deterministic `ConceptIdentity` mechanism and replaced raw concept-text coverage comparison with identity-based matching, while preserving the fail-closed architecture.

However, the live experiment demonstrates that the specific cross-language problem motivating WP-038 cannot be safely solved from the current corpus using evidence-derived identity.

The key evidence is decisive:

- the three live-pilot concepts had no usable explicit bilingual pairing;
- the new evidence-derived identity mechanism produced 0 cross-script identity matches in 12 pilot rounds;
- the LLM generated multiple inconsistent Hebrew renderings for the same English concept;
- broad transliteration, fuzzy matching, proximity matching, or a large manual bilingual mapping would violate the project's safety principles.

The report therefore correctly reaches Outcome C:

> Safe deterministic cross-language identity is not feasible for the concepts actually encountered by the pilot.

This is not an implementation failure. It is an architectural discovery.

---

## 2. Overall Assessment

| Area | Assessment |
|---|---|
| Implementation quality | Excellent |
| Scope discipline | Excellent |
| Safety discipline | Excellent |
| Evidence-based investigation | Excellent |
| Same-language coverage | Preserved |
| Cross-language coverage | Not solved |
| False-positive protection | Excellent |
| Architectural value | Very high |

**Overall assessment: 9.5 / 10**

---

## 3. What WP-038 Successfully Implemented

The new internal `ConceptIdentity` abstraction is architecturally appropriate.

It separates:

- canonical concept;
- deterministic normalized forms;
- explicitly supported alternate language forms.

The implementation preserved existing deterministic normalization and added only tightly controlled transformations.

The report confirms:

- no public schema changes;
- no validator changes;
- no generation changes;
- no retrieval changes;
- no semantic matching;
- no embeddings;
- no fuzzy/edit-distance matching;
- full regression success: 1286/1286. fileciteturn22file0L22-L32 fileciteturn22file0L53-L57

---

## 4. The Pre-Implementation Investigation Was Correct

Claude inspected the real evidence before implementing the proposed cross-language mechanism.

The investigation found:

- no Hebrew rendering for `Superior cerebellar artery`;
- a Hebrew rendering of `Spinothalamic Tract`, but in a different unrelated chunk;
- a Hebrew rendering of `Corpus Striatum`, but not as an explicit pair with the English concept.

Therefore the required safe evidence-derived bilingual relationship was absent from all three live concepts. fileciteturn22file0L9-L15

This is strong evidence that the limitation is in the available corpus, not merely in the implementation.

---

## 5. Concept Identity Design Is Correct

The identity model is appropriately conservative.

The important distinction is:

```text
canonical concept
+
deterministic normalization
+
explicitly supported alternate forms
```

rather than:

```text
concept
+
anything that looks semantically similar
```

The normalization strategy uses:

- whitespace normalization;
- case normalization;
- Unicode NFKC;
- a small fixed punctuation variant.

It deliberately avoids generalized fuzzy matching and edit-distance inference. fileciteturn22file0L22-L32

I agree with this design.

---

## 6. Cross-Language Decision Is Correct

The most important architectural decision in WP-038 is what it did **not** implement.

The report correctly rejected:

- general transliteration matching;
- broad proximity/co-occurrence matching;
- large bilingual dictionaries;
- manually authored concept mappings.

The live data strongly supports that decision.

The same concept was rendered three different ways in Hebrew during one run:

```text
עורק סופריאורי צרבלרי
עורק צרבלרי עליון
עורק סופריור צרבלרי
```

These include both transliteration and translation.

Trying to reverse-engineer such variation deterministically would either become a fuzzy matching system or require an external terminology resource.

Both are contrary to the current architectural principles. fileciteturn22file0L38-L41

---

## 7. Safety Result

The safety result is excellent.

Zero false-positive identity matches were observed in the live pilot, and dedicated tests verify that related concepts do not collapse merely because they are related. fileciteturn22file0L47-L50

This is especially important because false-positive coverage is more dangerous than false-negative coverage.

A false negative may cause a duplicate attempt.

A false positive can permanently remove a legitimate concept from the question-generation pool.

The conservative choice is therefore correct.

---

## 8. Live Pilot Result

| Category | Accepted |
|---|---:|
| אספקת דם | 4/4 |
| גרעיני הבסיס | 2/4 |
| מסילות עצביות | 4/4 |
| **Total** | **10/12** |

This is between:

- WP-036: 11/12
- WP-037: 8/12

The report correctly refuses to attribute the `אספקת דם` improvement to WP-038 because the new identity mechanism never fired there. fileciteturn22file0L64-L72

That is exactly the level of experimental honesty we want.

---

## 9. Target Alignment Remains Strong

The live run produced:

**8/10 manually aligned accepted questions = 80%.**

This is close to WP-037's 87.5%.

Therefore WP-038 did not damage the important WP-037 improvement.

The two misaligned questions occurred in `גרעיני הבסיס`, consistent with the earlier observation that this category has weaker concept structure. fileciteturn22file0L74-L91

The conclusion is important:

> Concept anchoring remains valuable and should be preserved.

---

## 10. New Finding: Trailing Truncation Is Now a Real Blocking Problem

This is the most important new discovery in WP-038.

The concept:

```text
Anterior Corticospinal T
```

was a truncated form of:

```text
Anterior Corticospinal Tract
```

The generated question correctly answered:

```text
Anterior Corticospinal Tract
```

but coverage could not recognize the answer as the same concept because the stored concept itself was incomplete.

Consequently:

```text
Concept extraction truncates
        ↓
Question generation reconstructs correctly
        ↓
Coverage sees different strings
        ↓
Concept remains uncovered
        ↓
Same concept selected again
```

This is a genuine system-level issue. fileciteturn22file0L101-L105

---

## 11. Why This Is More Promising Than Cross-Script Matching

The trailing-truncation problem is fundamentally different from the Hebrew/English problem.

For example:

```text
Anterior Corticospinal T
```

versus:

```text
Anterior Corticospinal Tract
```

has a structurally detectable relationship.

Likewise:

```text
Corpos Str
```

versus:

```text
Corpus Striatum
```

is an extraction-quality problem.

This gives us a much safer engineering opportunity.

We can potentially improve the **inventory itself** rather than weakening coverage matching.

That is architecturally preferable.

---

## 12. The Project Should Stop Trying to Solve Cross-Script Coverage for Now

WP-038 has provided enough evidence.

The architecture should not add:

- transliteration engines;
- fuzzy matching;
- LLM identity judges;
- external terminology APIs;
- large bilingual mapping tables.

The live data demonstrates that the problem is too variable to solve safely under the current constraints. fileciteturn22file0L120-L125

This should be documented as a known limitation, not endlessly optimized.

---

## 13. Recommended Next WP

The next WP should focus on:

# WP-039 — Deterministic Trailing-Truncation Recovery

Objective:

> Improve concept extraction so that obvious trailing truncation does not create false concept identities and subsequent coverage failures.

The work should focus on:

```text
raw evidence
    ↓
concept extraction
    ↓
detect suspicious incomplete concept
    ↓
deterministic reconstruction if unambiguous
    ↓
otherwise reject/exclude concept
```

The key principle remains:

> **Never guess.**

---

## 14. Important Constraint for WP-039

The next WP must **not** introduce general text correction.

It should handle only structurally identifiable truncation.

For example, investigate cases where:

```text
Anterior Corticospinal T
```

can be unambiguously completed from the same evidence context.

Likewise:

```text
Corpos Str
```

should only be repaired if the evidence provides an unambiguous deterministic basis.

If reconstruction is ambiguous:

```text
do not repair
exclude the concept
```

A smaller inventory is preferable to a corrupted inventory.

---

## 15. Why Fix Extraction Rather Than Coverage

This is an important architectural ownership decision.

We could attempt to make coverage recognize:

```text
Corpos Str
```

as:

```text
Corpus Striatum
```

but that would put knowledge about malformed strings into the coverage layer.

The correct ownership is:

```text
Extraction
    ↓
valid ConceptIdentity
    ↓
Coverage
```

Coverage should assume that the concept identity is valid.

Therefore:

> **Repair the identity at extraction time, not after generation at coverage time.**

This keeps responsibilities clean.

---

## 16. Revised Architecture

The architecture is now:

```text
Evidence Retrieval
        ↓
Concept Extraction
        ↓
Concept Quality / Completeness
        ↓
Concept Identity
        ↓
Coverage
        ↓
Concept Selection
        ↓
Concept-Anchored Evidence
        ↓
Question Generation
        ↓
Validation
```

This is stronger than adding more intelligence to the coverage layer.

---

## 17. What We Should NOT Do Next

Do not:

- expand to all 20 categories;
- implement fuzzy coverage;
- implement transliteration matching;
- add LLM concept matching;
- increase generation retries;
- add a diversity validator;
- widen concept anchors;
- modify validators;
- change the public API.

We should first make the three-category pilot loop robust.

---

## 18. Proposed Next Experiment

For WP-039 use exactly the same:

- three pilot categories;
- four sequential questions;
- one live run;
- no reruns;
- no manual intervention.

Compare against WP-038.

Primary metrics:

1. accepted count;
2. manual target alignment;
3. target rotation;
4. concept extraction quality;
5. repeated selection caused by truncation.

Do not judge success by acceptance count alone.

---

## 19. Expansion Gate

Before expanding beyond the three pilot categories, require:

```text
Reliable concept extraction
        +
Reliable coverage
        +
High target alignment
        +
Meaningful concept rotation
        +
No material reliability regression
```

Only then should a larger category sample be attempted.

---

## 20. Final Decision

**STATUS: ACCEPTED**

WP-038 is accepted.

It successfully implemented deterministic concept identity and, more importantly, provided strong evidence that the proposed cross-script solution cannot safely solve the current Hebrew/English coverage problem under the project's architectural constraints.

The correct architectural response is to **stop pursuing cross-script coverage matching for now** rather than weaken the fail-closed design.

The newly surfaced trailing-truncation problem is more promising because it has a bounded, deterministic shape and belongs naturally to concept extraction rather than coverage.

### Recommended next WP

**WP-039 — Deterministic Trailing-Truncation Recovery**

Focus on improving concept extraction quality for obvious incomplete/truncated concept strings, while preserving the strict rule:

> **Never guess.**

After WP-039, rerun the same three-category pilot and reassess the complete loop before considering expansion.
