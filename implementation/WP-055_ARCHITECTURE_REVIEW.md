# WP-055 Architecture Review

## Review Status

**ACCEPTED — DIAGNOSTIC FINDINGS ARE VALID**

WP-055 successfully completed its intended purpose: it investigated the Globus Pallidus classification/membership failure without changing production behavior, reconstructed the relevant deterministic pipeline, compared generated propositions with authoritative evidence, and separated confirmed findings from remaining uncertainty.

The key conclusion is:

> The three WP-054 Globus Pallidus failures were correctly rejected. The immediate problem is a generation-reliability issue: the model repeatedly chose a bare group-membership/classification framing even though the current prompt explicitly tells it to avoid that framing. A target/evidence granularity mismatch is a contributing architectural weakness because the strongest distinguishing evidence belongs to GPi/GPe sub-structures rather than cleanly to the flat `Globus Pallidus` target.

The report correctly leaves the WP-054 strategy mapping unchanged. fileciteturn41file0L127-L143

---

## 1. Was WP-055 the Right Investigation?

**Yes.**

The WP followed the correct diagnostic chain:

```text
recorded failures
    ↓
retrieved evidence
    ↓
generated proposition
    ↓
validator decision
    ↓
historical successful examples
    ↓
prompt behavior
    ↓
target/evidence representation
```

It also avoided unnecessary LLM/API calls and used deterministic reconstruction of the existing application logic. fileciteturn41file0L13-L19

**Architectural assessment: correct.**

---

## 2. The Three Failures Were Correctly Characterized

All three fresh Globus Pallidus attempts used essentially the same semantic shape:

```text
Which structure is part of the basal nuclei?
```

or:

```text
Which structure is a nucleus found within the basal nuclei?
```

The first additionally attached a group-level motor-regulation property.

All three were rejected by grounding while the other validators passed. fileciteturn41file0L21-L29

Thus the immediate problem is not:

```text
invalid MCQ
wrong category
poor quality
textbook inconsistency
```

It is grounding/uniqueness.

---

## 3. The Key Finding: True Does Not Mean Unique

This is the strongest part of the investigation.

The generated proposition was approximately:

```text
Globus Pallidus is part of the basal nuclei.
```

The authoritative evidence supports the same proposition for the distractors.

Therefore:

```text
SUPPORTED = true
```

but:

```text
UNIQUELY SUPPORTED = false
```

The report explicitly shows that the evidence supports the group-level property for all four answer choices. fileciteturn41file0L45-L52

The grounding validator is therefore doing its job correctly.

---

## 4. Grounding Validator Is Not the Problem

WP-055 investigated the possibility of a validator false positive and found none.

All three failures genuinely violate the uniqueness requirement. fileciteturn41file0L54-L56

Therefore:

```text
VALIDATOR_PROBLEM = NO
```

**Do not weaken the grounding validator to make these questions pass.**

---

## 5. Retrieval Is Not the Immediate Problem

The investigation found that the distinguishing facts for Globus Pallidus remain present in the retrieved evidence:

```text
GPi → thalamus suppression
GPe → indirect-pathway relationship
```

The report confirms that the relevant evidence remains reachable in the eight retrieved chunks. fileciteturn41file0L35-L43

Therefore the diagnosis should not be:

```text
TF-IDF cannot find Globus Pallidus evidence.
```

The actual observed pattern is:

```text
evidence exists
    ↓
generation does not select/use target-specific facts
    ↓
generation falls back to group membership
```

---

## 6. Retrieval Context Is Broad, Not Target-Specific

There is nevertheless an architectural weakness.

The current retrieval is category-level:

```text
גרעיני הבסיס
    ↓
8 chunks
```

rather than:

```text
Globus Pallidus
    ↓
target-specific evidence
```

The report confirms that useful Globus Pallidus/GPi/GPe evidence is present in the broader context, while the target's own narrow anchor does not surface the distinguishing facts cleanly. fileciteturn41file0L99-L102

Therefore the precise diagnosis is:

```text
retrieval availability = adequate
target-specific evidence presentation = weak
```

Do not redesign retrieval yet.

---

## 7. Target/Evidence Granularity Is the Most Important Structural Finding

The report identifies a significant mismatch:

```text
Target:
Globus Pallidus
```

while the strongest distinguishing evidence belongs to:

```text
GPi
GPe
```

with different factual roles.

The reconstructed target's `factual_focus` is also near-empty enumeration noise, while the concept inventory identifies GPi/GPe separately. fileciteturn41file0L87-L90

This is explicitly an **inference**, not a proven direct cause of the three failures.

That distinction is correct and must remain.

However, architecturally this is the most interesting longer-term issue exposed by WP-055.

---

## 8. Do Not Conflate Globus Pallidus With GPi/GPe

This boundary is critical.

The system currently has:

```text
Globus Pallidus
```

as a target.

The evidence contains:

```text
Globus Pallidus Internus (GPi)
Globus Pallidus Externus (GPe)
```

with different factual roles.

We must not silently transform:

```text
GPi facts → facts about entire Globus Pallidus
GPe facts → facts about entire Globus Pallidus
```

That could create the opposite grounding problem:

```text
fact true for GPi
    ↓
system treats it as true for Globus Pallidus
```

The current grounding strictness is protecting us from that mistake.

---

## 9. Prompt Problem: Guidance Exists

The investigation found that the existing generation prompt already explicitly warns against the exact framing:

```text
"Which of the following is part of the basal nuclei?"
```

The prompt uses this as its own worked example. fileciteturn41file0L91-L97

Therefore:

```text
missing instruction = NO
```

The observed issue is:

```text
instruction exists
    ↓
LLM does not reliably follow it
```

This is a reliability problem, not a missing-guidance problem.

Do not simply repeat the same instruction in a new prompt without experimental evidence that the change helps.

---

## 10. Competitor Selection Is Ruled Out

The deterministic reconstruction found:

```text
competitors = []
```

because the target relationship was `UNSPECIFIED`.

Therefore competitor selection could not have caused these failures. fileciteturn41file0L58-L60

Leave competitor selection unchanged.

---

## 11. Historical Evidence Supports a Specific Identity Pattern

The historical comparison is highly informative.

Successful Globus Pallidus generations used either:

```text
property/function
```

or:

```text
reverse-framed identity:
"Which of the following IS Globus Pallidus?"
```

The fresh WP-054 failures instead used:

```text
"Which structure is part of the basal nuclei?"
```

The report notes that none of the historical successes used the bare membership framing. fileciteturn41file0L62-L73

This makes a reverse-framed identity hypothesis credible.

But it remains a hypothesis until experimentally tested.

---

## 12. WP-047 Created an Important Cross-WP Constraint

WP-055 discovered that a historical WP-045 Globus Pallidus property question was accepted with an answer like:

```text
suppresses the thalamus and reduces movement
```

without the target name appearing in the answer.

WP-047 later introduced a target-answer identity requirement.

The deterministic reconstruction proves that this historical answer would now be rejected. fileciteturn41file0L75-L85

This does **not** cause the three WP-054 failures because those attempts were membership questions.

But it materially narrows future repair options.

A future property question must satisfy the current target-answer identity rule and must also be supported specifically for the target being tested.

---

## 13. Identity-First Is Now a Reasonable Hypothesis

The historical evidence supports:

```text
reverse-framed identity successes
=
3 of 5 historical live-pilot successes
```

while the fresh WP-054 run produced:

```text
bare membership
=
3/3 rejected
```

fileciteturn41file0L158-L162

This is enough to justify an experiment.

It is **not** enough to change production strategy.

---

## 14. Recommended WP-056

**WP-056 — Globus Pallidus Identity-First Controlled Experiment**

The experiment should specifically test the historical successful pattern:

```text
reverse-framed identity
```

rather than merely using a vague generic identity instruction.

Recommended comparison:

```text
CONTROL
current DEFAULT generation

vs.

EXPERIMENT
explicit reverse-framed identity preference
```

Use:

```text
one target:
Globus Pallidus

one category:
גרעיני הבסיס

real QuestionGenerator
real QuestionProducer
real validators
real OpenAI API
existing 3-attempt budget
```

Do not modify the production prompt file or WP-054 strategy mapping.

---

## 15. WP-056 Must Distinguish Identity From Membership

A successful experimental question must be classified correctly.

Count as identity:

```text
Which of the following IS Globus Pallidus?
```

Do not count as identity:

```text
Which structure is part of the basal nuclei?
```

The latter is exactly the failure shape already demonstrated.

WP-056 should record:

```text
question shape
correct answer
answer contains target identity
grounding result
attempt number
validator results
identity vs membership classification
```

---

## 16. No Production Change From WP-055

The diagnostic script is prototype-only and imported by nothing in `src/`. fileciteturn41file1L1-L23

The completion report confirms:

```text
Production changes:
NONE
```

and:

```text
1426 passed
0 failed
```

fileciteturn41file0L141-L150

This is exactly the correct outcome for a diagnostic WP.

---

## 17. Final Acceptance Decision

**WP-055 — ACCEPTED.**

The root-cause classification:

```text
F — Multiple interacting causes
```

is acceptable with the following hierarchy:

### Primary confirmed issue

```text
Generation reliability:
the model repeatedly selected a known-invalid/non-unique
membership framing despite explicit prompt guidance.
```

### Contributing structural issue

```text
Target/evidence granularity:
Globus Pallidus is represented as a flat target while
strong distinguishing evidence belongs to GPi/GPe.
```

### Important cross-WP constraint

```text
WP-047's target-answer identity requirement
closed the historical bare property-answer path.
```

The report appropriately assigns **MEDIUM confidence**. fileciteturn41file0L125-L139

---

## 18. Current Architecture Must Remain

Do not modify WP-054.

Current mapping remains:

```text
גרעיני הבסיס + Caudate Nucleus
    → IDENTITY_FIRST

גרעיני הבסיס + Nucleus Accumbens
    → IDENTITY_FIRST

גרעיני הבסיס + Globus Pallidus
    → DEFAULT

everything else
    → DEFAULT
```

The completion report explicitly confirms that WP-054 was not changed. fileciteturn41file0L170-L179

---

## 19. Future Decision Tree

```text
WP-056
    ↓
Does reverse-framed identity improve Globus Pallidus generation?
```

### If YES

```text
controlled evidence
    ↓
architectural review
    ↓
narrow permanent Globus Pallidus strategy
```

### If NO

```text
do not force identity-first
    ↓
investigate target/evidence granularity
```

### If MIXED

```text
analyze failure modes
    ↓
possibly investigate target planning/concept representation
```

This preserves the project's established:

```text
evidence
    ↓
experiment
    ↓
architectural decision
    ↓
implementation
```

discipline.

---

# Final Decision

**WP-055 — ACCEPTED.**

No production changes should be made from WP-055 itself.

The next meaningful task is:

**WP-056 — Globus Pallidus Identity-First Controlled Experiment**

with one important refinement:

> Test the **specific reverse-framed identity pattern** that has historically succeeded, rather than merely testing a generic "identity-first" instruction.

Only after that experiment should we decide whether Globus Pallidus deserves a permanent `IDENTITY_FIRST` mapping.
