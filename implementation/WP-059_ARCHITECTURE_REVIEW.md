# WP-059 Architecture Review

## Review Status

**ACCEPTED WITH DOCUMENTED LIMITATIONS**

WP-059 completed its intended candidate-discovery analysis and reached the correct high-level architectural conclusion:

```text
No Tier A candidate found.
No new controlled IDENTITY_FIRST experiment is currently justified.
```

The production strategy mapping was unchanged, no production prompts/validators/retrieval/schemas/retry behavior were modified, and the full regression suite remained green at **1440 passed, 0 failed**. This matches the WP-059 completion report. fileciteturn48file0L81-L98

## 1. Objective

WP-059 correctly treated itself as:

```text
historical evidence
    ↓
candidate discovery
    ↓
architect review
    ↓
future controlled experiment
```

rather than immediately expanding `IDENTITY_FIRST`. Its stated objective was specifically to identify DEFAULT target/category pairs deserving a future controlled experiment, not to decide permanent mappings. fileciteturn48file0L3-L11

**Assessment: PASS**

## 2. Candidate Population

The analysis found **19 distinct recorded (category, target) pairs**, of which three are already permanently `IDENTITY_FIRST`, leaving **16 candidates**. The analysis also found that the available evidence is concentrated in three pilot categories. fileciteturn48file0L13-L25

This is architecturally sound because candidates were derived from actual historical generation evidence rather than manually selected.

However, an important distinction must remain explicit:

```text
all project categories
    ≠
categories with historical target-generation evidence
```

Seventeen canonical categories have neither deterministic target inventories nor historical pilot-generation evidence. Therefore WP-059 did not evaluate all possible targets in those categories; it correctly reported them as insufficient-data at the category level. fileciteturn48file1L23-L27

**Assessment: PASS WITH LIMITATION**

## 3. Historical Evidence Handling

The analysis correctly handled the evolution of historical record schemas. It distinguished full per-attempt records from earlier round-level-only records and did not fabricate missing per-attempt information. The analysis script explicitly preserves UNKNOWN when attempt-level information is unavailable. fileciteturn48file2L20-L33

**Assessment: PASS**

## 4. Terminology Limitation: "Attempts"

The completion report describes 175 total recorded attempts, including 65 round-level-only records. The implementation itself makes clear that those older records are not expanded into fabricated per-attempt records; only the final accepted question is represented when available, while the historical attempt count is retained as informational context. fileciteturn48file2L98-L149

Therefore, for future architectural reporting, the safer terminology is:

```text
175 normalized historical evidence records / observations
```

rather than automatically calling all 175 individual generation attempts.

This does not invalidate the negative conclusion, but it does affect how sample sizes should be described.

**Assessment: DOCUMENTATION CORRECTION REQUIRED**

No production code change is required.

## 5. Strategy Classification

WP-059 correctly reused the existing WP-056 `classify_question_shape()` implementation instead of creating a competing taxonomy. The four resulting categories are:

```text
IDENTITY
CLASSIFICATION_MEMBERSHIP
PROPERTY
OTHER_UNKNOWN
```

The analysis explicitly states that no new classifier or LLM classification was introduced. fileciteturn48file1L29-L38

The limitation is that this remains a deterministic textual heuristic, not an independent semantic judgment.

**Assessment: PASS WITH KNOWN LIMITATION**

## 6. Retrospective-Bias Handling

This is one of the strongest aspects of WP-059.

It distinguishes:

```text
FIRST_ATTEMPT
AFTER_PRIOR_FAILURE
UNKNOWN
```

and refuses to guess when historical schema information is missing. The resulting evidence is particularly important:

```text
0 candidates have a confirmed first-attempt identity success
```

The strongest candidate, Basillar artery, has its confirmed identity success only after prior failures. fileciteturn48file0L69-L79

This directly preserves the central caveat from WP-052: retrospective identity success does not prove that identity-first would have succeeded if selected initially.

**Assessment: PASS**

## 7. Candidate Scoring

The deterministic scoring heuristic was fixed before candidate inspection and applied uniformly:

```text
2 * min(identity_accepted, 3)
+ min(property_rejected, 4)
+ 2 if identity_rate - property_rate >= 0.4
+ 1 if total_attempts >= 4
+ 1 if first_attempt_identity_count >= 1
- 2 if identity_accepted == 0
```

It is explicitly described as a prioritization heuristic rather than a probability or significance measure. fileciteturn48file1L40-L63

**Assessment: PASS**

## 8. Scoring Limitation

The Tier-A gate requires:

```text
score >= 6
AND
identity_accepted >= 2
AND
total_attempts >= 4
```

The implementation correctly counts accepted identity-shaped historical attempts, but it does **not** establish statistical independence between those attempts.

Therefore future documentation should say:

```text
at least two accepted identity-shaped historical attempts
```

rather than:

```text
two independent successful identity experiments
```

unless independence is actually demonstrated.

This limitation does not affect the current negative conclusion because no candidate reached the required two accepted identity examples anyway.

**Assessment: DOCUMENTATION LIMITATION — NO CURRENT PRODUCTION IMPACT**

## 9. Strongest Candidate: Basillar artery

The strongest current candidate is:

```text
אספקת דם + Basillar artery
```

with score 7.

But it remains Tier B, not Tier A:

```text
property: 5/11 accepted
identity: 1/2 accepted
confirmed identity order: after prior failure
```

The analysis correctly notes that its DEFAULT/property path is already substantially workable, unlike the much stronger property-failure pattern that preceded the approved identity-first mappings. fileciteturn48file1L90-L96

Therefore:

```text
monitor
```

is appropriate; a dedicated experiment is not currently justified.

**Assessment: PASS**

## 10. Other Tier-B Candidates

`Corpos Striatum` and `Medial Lemniscus Tract` each have one accepted identity example, but their order is UNKNOWN because the relevant historical records are round-level-only.

`Corticospinal Tract` reaches Tier B despite having no identity evidence, because the scoring heuristic also rewards sample size and rejected property attempts. fileciteturn48file1L67-L75

This means:

```text
TIER_B_MONITOR
```

must not be interpreted as:

```text
evidence that IDENTITY_FIRST works
```

It means only:

```text
worth monitoring for future evidence.
```

**Assessment: PASS WITH INTERPRETATION LIMITATION**

## 11. Target-String Fragmentation

WP-059 correctly identifies historical target-string fragmentation such as:

```text
Corpos Str
Corpos Striatum

Anterior Corticospinal T
Anterior Corticospinal Tract

edial Lemniscus Tract
Medial Lemniscus Tract
```

and deliberately does not merge them because the project has explicitly rejected fuzzy/substring target matching. fileciteturn48file1L110-L112

This is the correct behavior for WP-059.

It does mean that evidence for a real anatomical entity can be split across literal target strings. Therefore the current conclusion should be interpreted as:

```text
no exact-record candidate has sufficient evidence
```

rather than:

```text
no real anatomical entity could possibly qualify.
```

A future data-quality WP could investigate this separately, but it should not be mixed into the strategy-selection decision.

**Assessment: PASS WITH DATA-QUALITY LIMITATION**

## 12. Production Safety

WP-059 made no production strategy changes:

```text
Caudate Nucleus     → IDENTITY_FIRST
Nucleus Accumbens   → IDENTITY_FIRST
Globus Pallidus     → IDENTITY_FIRST
everything else     → DEFAULT
```

It also made no prompt, validator, retrieval, schema, or retry changes. fileciteturn48file0L81-L104

**Assessment: PASS**

## 13. Regression

The reported full regression is:

```text
1440 passed, 0 failed
```

and is identical to the WP-058 baseline. fileciteturn48file0L91-L98

**Assessment: PASS**

## 14. Main Architectural Finding

The most important result is not that Basillar artery ranked first.

The important result is:

```text
No remaining DEFAULT candidate has sufficiently strong
evidence to justify another controlled identity-first experiment.
```

The remaining 16 candidates have materially weaker evidence than the three already-approved mappings. In particular, there is no order-confirmed first-attempt identity success among them. fileciteturn48file1L102-L105

This is a valid architectural stopping point.

The architecture should **not** expand `IDENTITY_FIRST` merely because it has already worked for three targets.

**Assessment: STRONG POSITIVE RESULT**

## 15. Architectural Decision

### WP-059 — ACCEPTED WITH DOCUMENTED LIMITATIONS

The decision is:

```text
No new IDENTITY_FIRST mapping.
No WP-060 controlled experiment at this time.
```

Preserve:

```text
גרעיני הבסיס + Caudate Nucleus
    → IDENTITY_FIRST

גרעיני הבסיס + Nucleus Accumbens
    → IDENTITY_FIRST

גרעיני הבסיס + Globus Pallidus
    → IDENTITY_FIRST

all other targets
    → DEFAULT
```

The current evidence does not justify expanding this set.

## 16. What Should Happen Next

Do **not** create WP-060 as an identity-first experiment now.

Allow normal live generation/evaluation to accumulate additional evidence.

The strongest monitoring candidate is:

```text
אספקת דם + Basillar artery
```

but it should be reconsidered only if future evidence provides stronger signals such as:

```text
additional accepted identity attempts
first-attempt identity successes
clear attempt-order information
continued property-generation failure
meaningful strategy contrast
```

The current report explicitly recommends no new experiment. fileciteturn48file0L106-L112

## 17. Separate Data-Quality Thread

Historical target-string fragmentation is a separate architectural concern.

If the project later decides that historical evidence must be consolidated across truncated/variant target strings, that should be handled by a dedicated diagnostic WP with explicit normalization and collision rules.

It should **not** be silently fixed inside the strategy-selection branch.

## 18. Final Architecture State

```text
WP-052
Historical strategy analysis
        ↓
WP-053
Controlled experiment
        ↓
WP-054
Caudate + Nucleus Accumbens permanent mapping
        ↓
WP-055
Globus Pallidus failure investigation
        ↓
WP-056
Globus Pallidus controlled experiment
        ↓
WP-057
Globus Pallidus permanent mapping
        ↓
WP-058
Language architecture correction
        ↓
WP-059
Remaining-target candidate discovery
        ↓
NO NEW EXPERIMENT JUSTIFIED
```

The identity-first expansion branch should therefore pause.

## 19. Final Decision

**WP-059 — ACCEPTED WITH DOCUMENTED LIMITATIONS**

```text
Production mapping:
UNCHANGED

New IDENTITY_FIRST mappings:
NONE

WP-060:
NOT JUSTIFIED

Strongest monitor candidate:
אספקת דם + Basillar artery

Regression:
1440 passed, 0 failed

Language thread:
CLOSED

Strategy-expansion thread:
PAUSED pending new evidence
```

WP-059 is a successful architectural stopping point. The negative result is evidence-based and preferable to speculative strategy expansion.

**WP-059: ACCEPTED WITH DOCUMENTED LIMITATIONS.**

**Wait for architect-approved next direction.**
