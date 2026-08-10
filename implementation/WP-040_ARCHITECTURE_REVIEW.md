# Architecture Review — WP-040

**Review Date:** 2026-08-10  
**WP Reviewed:** WP-040 — Target-Aware Generation for Named Concepts  
**Status:** **ACCEPTED — DECISIVE SUCCESS ON TARGET ALIGNMENT; CROSS-SCRIPT COVERAGE REMAINS THE SOLE PILOT ROTATION BLOCKER**

## 1. Executive Summary

WP-040 is accepted.

It achieved the primary objective decisively:

> When a deterministic planner selects a named concept, generation now produces a question whose correct answer identifies that selected concept rather than merely describing its function, property, or a related entity.

The live pilot achieved **11/11 manually aligned accepted questions (100%)**, compared with approximately 45% in WP-039, 80% in WP-038, and 87.5% in WP-037. Acceptance remained **11/12 (91.7%)**, identical to WP-039. fileciteturn24file0L88-L112

The offline evaluation independently produced **4/4 aligned named-entity answers**, including Hebrew representations of English concepts. fileciteturn24file0L63-L74

This is exactly the source-level architectural fix we wanted rather than another downstream rejection/retry mechanism.

---

## 2. Overall Assessment

| Area | Assessment |
|---|---|
| Primary objective | Excellent |
| Root-cause identification | Excellent |
| Architectural ownership | Excellent |
| Prompt change discipline | Excellent |
| Target alignment | Excellent |
| Acceptance/reliability | Stable |
| Attempt budget | Acceptable, monitor |
| Concept rotation | Partially blocked by known coverage limitation |
| Safety / fail-closed behavior | Excellent |
| Scope discipline | Excellent |

**Overall assessment: 9.7 / 10**

---

## 3. Root Cause Was Correctly Identified

The strongest part of WP-040 is that the target drift was traced directly to the existing production prompt.

The prompt explicitly allowed narrowing a target to:

> “one function”

when producing a clearer question.

That was legitimate for general targets, but too permissive when the selected target itself was a named entity.

Thus:

```text
Selected:
Corpos Striatum

Generated answer:
involved in executing planned motor movements
```

was not simply arbitrary model behavior. It was allowed by the existing prompt contract. fileciteturn24file0L11-L20

This is an excellent example of fixing the actual architectural cause rather than compensating downstream.

---

## 4. The Fix Is Correctly Located

WP-040 places the change at the generation-contract layer:

```text
Concept Selection
       ↓
Target-Aware Generation
       ↓
Question
```

rather than:

```text
Generate
       ↓
Target Validator
       ↓
Retry
```

The report confirms that QuestionGenerator, QuestionProducer, OpenAIProvider, validators, WP-037 anchoring, WP-038 ConceptIdentity/coverage, and WP-039 truncation recovery were unchanged. No new retry loop was introduced. fileciteturn24file0L5-L6

This is exactly the architectural direction we want.

---

## 5. Target Type Was Not Artificially Invented

The implementation correctly found that a new classifier was unnecessary.

The deterministic concept-inventory path already produces named entities by construction.

Therefore:

```text
QuestionTarget.named_entity_target = True
```

can be set directly for that pilot path.

No LLM classifier, semantic classifier, or large manual taxonomy was needed. The existing deterministic information was simply surfaced. fileciteturn24file0L22-L26

---

## 6. Prompt Change Is Appropriately Small

The production prompt was not rewritten.

The implementation added:

- deterministic `format_target_answer_requirement()`;
- one rendered answer-requirement block;
- limited cross-referencing text;
- one checklist item.

The report states that the rest of the approximately 85-line production prompt remained untouched. fileciteturn24file0L28-L47

I strongly approve this approach.

---

## 7. Educational Diversity Was Preserved

The restriction applies to the **correct answer**, not to the wording or educational angle of the question.

The question may still test:

- role;
- location;
- connections;
- distinguishing characteristics;
- other supported properties.

But when the selected target is a named entity, the answer must identify that entity.

This avoids reducing the system to trivial “What is X?” questions. fileciteturn24file0L40-L45

---

## 8. Offline Evaluation Is Strong Evidence

Four real generation calls were made using the exact production context.

Results:

| Target | Answer | Alignment |
|---|---|---|
| Corpos Striatum | Corpos Striatum | ALIGNED |
| Medial Lemniscus Tract | Medial Lemniscus Tract | ALIGNED |
| Superior cerebellar artery | עורק סופריור צרבלרי | ALIGNED |
| Anterior Corticospinal Tract | מסילה קדמית של הקורטיקוספינלית | ALIGNED |

**4/4 aligned.** fileciteturn24file0L63-L74

This is useful because it demonstrates the prompt change before sequential coverage/rotation effects enter the experiment.

---

## 9. Live Target Alignment Is the Decisive Result

The live pilot achieved:

**11/11 manually aligned accepted questions = 100%.**

The most important case is `Corpos Striatum`.

Previous pilots had repeatedly generated a functional description for this target. In WP-040, all four rounds produced a genuine Hebrew representation of the target concept itself.

Likewise, `Superior cerebellar artery` was correctly answered using Hebrew target representations. fileciteturn24file0L92-L108

This is the strongest evidence in the WP.

---

## 10. Acceptance Remained Stable

The live result was:

```text
11/12 accepted = 91.7%
```

matching WP-036 and WP-039.

The one failure was an ordinary `QuestionAttemptsExhaustedError`, not a newly introduced target-alignment mechanism failure. fileciteturn24file0L110-L112

This satisfies the important project constraint:

> Improve alignment without causing the bounded generation/validation budget to collapse.

---

## 11. Attempt Count Increased — Monitor It

There is one real caveat.

Average attempts increased:

```text
WP-039: ~1.09
WP-040: ~1.45
```

with `גרעיני הבסיס` averaging 2.25 attempts. fileciteturn24file0L114-L123

The report correctly does not claim causality.

A plausible hypothesis is that the stricter answer requirement adds another condition candidates must satisfy, but this remains unconfirmed.

This should be monitored in subsequent evaluation.

For now it is a **watch item**, not a blocking regression, because:

- the attempt budget did not change;
- the budget was not systematically exhausted;
- acceptance remained 11/12.

---

## 12. Concept Rotation Now Isolates the Remaining Problem

The categories behave differently:

### אספקת דם

```text
Superior cerebellar artery
Superior cerebellar artery
Superior cerebellar artery
Basillar artery → failed
```

### גרעיני הבסיס

```text
Corpos Striatum
Corpos Striatum
Corpos Striatum
Corpos Striatum
```

### מסילות עצביות

```text
Spinothalamic Tract
Medial Lemniscus Tract
Anterior Corticospinal Tract
Lateral Corticospinal Tract
```

The important observation is:

> Generation is no longer the reason the first two categories are stuck.

For `גרעיני הבסיס`, all four questions correctly targeted `Corpos Striatum`; coverage simply did not recognize the Hebrew answers against the English stored concept.

For `מסילות עצביות`, English answers matched and rotation worked perfectly. fileciteturn24file0L125-L139

---

## 13. Cross-Script Coverage Is Now the Sole Pilot Rotation Blocker

WP-038 already investigated this area.

WP-040 now provides stronger evidence that the problem is not generation:

```text
Corpos Striatum
        ↓
קורפוס סטריאטום
```

is a correct target answer.

The remaining failure is:

```text
correct answer
        ↓
coverage does not recognize identity
```

Thus we have cleanly separated:

### Generation

**Solved for named targets in the pilot.**

### Cross-script coverage identity

**Still unresolved.**

This is a major architectural clarification. fileciteturn24file0L141-L152

---

## 14. Do Not Return to Unsafe Matching

I agree with the continued rejection of:

- fuzzy matching;
- broad transliteration matching;
- proximity matching;
- embeddings;
- LLM identity judges;
- large manual bilingual dictionaries.

WP-038 already investigated the obvious approaches and found them unsafe.

The fact that WP-040 now produces good Hebrew target answers makes the limitation more visible, but does not make unsafe matching acceptable.

---

## 15. The Project Has Reached an Important Milestone

The architecture is now:

```text
Evidence
   ↓
Clean Concept Inventory
   ↓
Concept Identity
   ↓
Coverage
   ↓
Deterministic Concept Selection
   ↓
Concept-Anchored Evidence
   ↓
Target-Aware Generation
   ↓
Aligned Question
   ↓
Validation
   ↓
Coverage Update
```

WP-040 has established that:

```text
Target-Aware Generation
        ↓
Aligned Question
```

is now reliable in the three-category pilot.

The remaining failure is:

```text
Aligned Question
        ↓
Coverage Update
```

when the answer uses a different language/script.

---

## 16. Recommended Next Step: Architectural Decision Before More Code

I do **not** recommend automatically creating an implementation WP-041 to attack cross-script coverage.

WP-038 already investigated this and found no safe evidence-derived mechanism for the concepts encountered.

Before another implementation, we should make an explicit architectural decision between:

### Option A — Accept the limitation

Cross-script rotation remains a known, disclosed limitation.

The system can still generate high-quality aligned questions and rotate concepts when the answer representation is recognized by the existing identity mechanism.

### Option B — Investigate a genuinely new safe mechanism

Only proceed if a method is materially different from the already rejected:

- fuzzy matching;
- transliteration guessing;
- semantic matching;
- external terminology;
- large manual mapping.

We should not retry the same unsafe approaches under different names.

---

## 17. What We Should Measure Before That Decision

The current pilot is only three categories.

Before adding another mechanism, determine:

```text
How often does generation produce an answer
in a different language/script from the stored concept?
```

and:

```text
How often does that actually prevent
meaningful concept rotation?
```

The WP-040 results show that this is already materially affecting two of the three pilot categories.

The next architectural decision should determine whether that limitation is acceptable for the intended product.

---

## 18. Expansion Is Still Premature — But We Are Close

I agree with the continuing “do not expand yet” recommendation.

However, the situation is now materially better than after WP-039.

We have demonstrated:

```text
selection       ✓
anchoring       ✓
generation      ✓
truncation      ✓
same-language identity ✓
```

The remaining problem is isolated much more cleanly.

Before expanding beyond the pilot, we should resolve or explicitly accept the cross-script coverage limitation.

---

## 19. Regression and Scope Discipline

The regression result is excellent:

**1313/1313 passed.**

The report also confirms:

- no public/shared contract changes;
- no validators changed;
- no retrieval changes;
- no concept extraction changes;
- no ConceptIdentity semantic changes;
- no embeddings;
- no fuzzy matching;
- no new retry loop. fileciteturn24file0L158-L169

This is exactly the level of regression discipline expected.

---

## 20. Final Decision

**STATUS: ACCEPTED**

WP-040 is a **decisive success**.

It solved the target-answer generation problem at the correct architectural layer.

The strongest comparison is:

```text
WP-039:
~45% target alignment

WP-040:
100% target alignment
```

while:

```text
WP-039:
11/12 accepted

WP-040:
11/12 accepted
```

Therefore the change achieved the desired outcome:

> **Higher target alignment without sacrificing bounded generation/validation reliability.**

The increase in average attempts from ~1.09 to ~1.45 should be monitored, but it does not currently constitute a blocking regression.

---

## 21. Recommended Next Architectural Decision

The next step should **not automatically be another implementation WP**.

The remaining question is now:

> **Can, and should, the planner recognize a correctly generated named concept across languages/scripts without violating the project's fail-closed architecture?**

WP-038 established that the obvious approaches are unsafe.

WP-040 established that generation itself can now reliably produce the correct named target, including Hebrew representations.

Therefore the next discussion should decide whether:

1. the current cross-script rotation ceiling is acceptable and we should proceed toward broader evaluation; or
2. there is a genuinely new, safe deterministic approach worth investigating.

Only after that decision should WP-041 be defined.
