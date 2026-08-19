# WP-057 Architecture Review

## Review Status

**IMPLEMENTATION ACCEPTED — LANGUAGE-COMPLIANCE FOLLOW-UP REQUIRED**

WP-057 correctly implemented the architect-approved permanent strategy change:

```text
גרעיני הבסיס + Globus Pallidus
    → IDENTITY_FIRST
```

The existing mappings were preserved:

```text
גרעיני הבסיס + Caudate Nucleus
    → IDENTITY_FIRST

גרעיני הבסיס + Nucleus Accumbens
    → IDENTITY_FIRST
```

and unmapped targets/categories remain on:

```text
DEFAULT
```

The production implementation is narrow and reuses the existing WP-054 strategy mechanism. The full regression suite passed:

```text
1432 passed
0 failed
```

The real production-path verification also confirmed that the permanent resolver returns `IDENTITY_FIRST` for Globus Pallidus and that the normal `QuestionGenerator` / `QuestionProducer` / validator pipeline is wired to that mapping. fileciteturn43file0L94-L101 fileciteturn43file1L78-L105

However, the live verification exposed a separate project-level language-compliance problem:

```text
"איזה מהמבנים הבאים הוא Globus Pallidus?"
```

was accepted even though an English representation exists.

Under the project's explicit language rule, this is not compliant.

Therefore the strategy implementation is accepted, but the language requirement should be addressed in the next WP.

---

# 1. Architectural Decision Being Reviewed

WP-056 approved the permanent mapping:

```text
גרעיני הבסיס + Globus Pallidus
    → IDENTITY_FIRST
```

WP-057 implemented exactly that decision.

The intended final strategy state is:

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

This is the correct architectural outcome of WP-056.

---

# 2. Implementation Scope Was Correct

WP-057 made the change through the existing permanent strategy mechanism rather than introducing another strategy abstraction.

The production mapping was extended to include Globus Pallidus in the existing identity-first set. fileciteturn43file0L24-L37

There was no unnecessary redesign of:

```text
QuestionGenerator
QuestionProducer
retrieval
validators
schemas
retry semantics
target representation
```

The completion report confirms that these areas were left unchanged. fileciteturn43file0L160-L172

**Assessment: correct.**

---

# 3. Existing Identity-First Mappings Were Preserved

The implementation explicitly preserved:

```text
Caudate Nucleus
    → IDENTITY_FIRST

Nucleus Accumbens
    → IDENTITY_FIRST
```

and added:

```text
Globus Pallidus
    → IDENTITY_FIRST
```

The focused tests verified all three mappings. fileciteturn43file0L58-L68

---

# 4. DEFAULT Fallback Was Preserved

The tests verified that unrelated and related-but-distinct targets remain `DEFAULT`, including:

```text
Putamen
    → DEFAULT

Globus Pallidus Externus
    → DEFAULT

Globus Pallidus in another category
    → DEFAULT
```

This proves that the strategy is not matched globally by target name. fileciteturn43file0L58-L68

The architectural rule remains:

```text
explicit category + target mapping
    → IDENTITY_FIRST

otherwise
    → DEFAULT
```

---

# 5. Regression Suite Passed

The complete test suite result is:

```text
1432 passed
0 failed
```

The WP added six focused tests while preserving previous behavior. fileciteturn43file0L94-L101

This satisfies the production regression requirement.

---

# 6. Real Production-Path Verification Passed

The verification script explicitly resolves:

```text
resolve_strategy_preference(
    category=canonical_category,
    topic="Globus Pallidus"
)
```

and asserts:

```text
IDENTITY_FIRST
```

before constructing the normal production objects. fileciteturn43file1L78-L89

It then creates the normal:

```text
QuestionGenerator
QuestionProducer
GroundingValidator
MCQValidator
CategoryValidator
QualityValidator
TextbookValidator
```

using the normal project configuration. fileciteturn43file1L91-L105

Therefore the permanent mapping is genuinely wired into the production generation pipeline.

---

# 7. Live Production Verification Passed

The verification completed successfully with:

```text
accepted = true
attempt_count = 1
```

for the live Globus Pallidus verification. fileciteturn43file0L84-L92

The production integration therefore works:

```text
permanent mapping
    ↓
IDENTITY_FIRST
    ↓
real generation pipeline
    ↓
real validators
    ↓
accepted output
```

---

# 8. Important Language-Compliance Problem

The live accepted question was:

```text
"איזה מהמבנים הבאים הוא Globus Pallidus?"
```

The identity-first semantic shape is correct. However, the project's explicit language rule is stricter:

```text
If an English representation exists:
    use English.

Use Hebrew only when Hebrew is the only available representation.
```

For this question, an English representation clearly exists.

Therefore the output should have been entirely English, for example:

```text
Which of the following is Globus Pallidus?
```

The mixed Hebrew/English question is therefore a genuine language-policy violation. fileciteturn43file0L84-L92

---

# 9. Why This Is Not a Globus Pallidus Strategy Problem

The language problem is separate from:

```text
Globus Pallidus → IDENTITY_FIRST
```

The strategy selection was correct.

The generated semantic shape was also correct:

```text
identity
```

The problem is:

```text
strategy selection
        ≠
language enforcement
```

Therefore we should not undo or weaken the new Globus Pallidus mapping.

The correct architectural response is to preserve:

```text
Globus Pallidus → IDENTITY_FIRST
```

and investigate language enforcement separately.

---

# 10. The Verification Script Does Not Enforce the Language Rule

The live verification script records:

```text
question
answers
correct_answer_text
grounding
mcq
category
quality
textbook
```

but it does not perform a language-policy validation. fileciteturn43file1L53-L73

Therefore:

```text
all five validators passed
```

does not mean:

```text
all project requirements passed
```

because the English-first rule is not represented as one of those five validation checks.

This is how an output can be accepted by the current validation pipeline while still violating an explicit project-level language requirement.

---

# 11. Architectural Significance

This should not be treated as cosmetic wording.

The project requirement is deterministic:

```text
English exists
    →
English must be used
```

A language requirement of this type should ideally be enforced as a system invariant rather than relying only on LLM instruction-following.

WP-057's live verification provides concrete evidence that the current system does not guarantee this invariant.

Therefore the issue is architectural.

---

# 12. Recommended Next WP

The next WP should be:

# WP-058 — English-Only Generation Compliance

Objective:

> Determine where the English-first language requirement is currently enforced, why an accepted generated question can still contain Hebrew when an English representation exists, and implement the smallest justified mechanism that makes the requirement reliable.

This should be a general solution.

It must not be:

```text
Globus Pallidus-specific
```

or:

```text
identity-first-specific
```

---

# 13. WP-058 Should Begin With Diagnosis

Before changing prompts or adding validators, trace:

```text
project language rule
    ↓
generation prompt
    ↓
target representation
    ↓
LLM generation
    ↓
candidate normalization
    ↓
validation
    ↓
final output
```

The key question is:

> Is the English-first rule currently only an instruction to the LLM, or is it actually enforced as a deterministic invariant?

The WP-057 live result strongly suggests that it is not currently guaranteed at the final-output boundary.

---

# 14. Do Not Immediately Rewrite Prompts

Do not start WP-058 by simply adding more language instructions to the prompt.

First determine:

```text
where the rule currently exists
```

and:

```text
where it can fail.
```

Possible enforcement points include:

```text
prompt construction
candidate normalization
validation
output sanitization
domain model constraints
```

The correct architectural location should be determined from the existing implementation.

---

# 15. Do Not Weaken Existing Validation

WP-057 demonstrated that the existing validators are functioning correctly for the identity-first strategy.

Do not weaken them.

The language requirement should be added/enforced without compromising:

```text
grounding
uniqueness
MCQ correctness
category correctness
quality
textbook consistency
target-answer identity
```

---

# 16. Do Not Undo WP-057

The permanent mapping remains approved:

```text
גרעיני הבסיס + Globus Pallidus
    → IDENTITY_FIRST
```

The language issue does not invalidate the strategy experiment or its implementation.

The architecture should now treat:

```text
strategy selection
    +
language compliance
```

as separate concerns.

---

# 17. Source Authority Remains Unchanged

WP-057 did not change the authority hierarchy.

Continue using:

```text
student summaries
    = sole factual grounding authority

course_book.pdf
    = secondary consistency check

historical Excel
    = style / structure / terminology reference
```

The language-compliance follow-up must not introduce external factual sources.

---

# 18. Language Rule Must Be Preserved Exactly

The project rule should be carried forward unchanged:

```text
If an English representation exists:
    use English.

Use Hebrew only when Hebrew is the only available representation.
```

This means:

```text
Globus Pallidus
```

must remain English.

A generated question containing Hebrew around that term is not compliant when the corresponding English wording exists.

---

# 19. WP-057 Production Changes

The final production change is:

```text
YES:
גרעיני הבסיס + Globus Pallidus
    → IDENTITY_FIRST
```

No other production behavior was intentionally changed.

The completion report confirms no changes to:

```text
validators
retrieval
schemas
retry budget
target representation
```

and related architecture. fileciteturn43file0L160-L172

---

# 20. Experimental Artifacts

WP-056 experimental artifacts remain separate from production logic.

The WP-057 verification script explicitly exists only to verify the permanent mapping and uses the real production pipeline. fileciteturn43file1L1-L8

Do not make experimental code a runtime dependency.

Preserve experiment records as architectural provenance according to repository conventions.

---

# 21. Final Architecture State

After WP-057:

```text
                    ┌─────────────────────┐
                    │   גרעיני הבסיס      │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   Caudate Nucleus     Nucleus Accumbens    Globus Pallidus
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
                       IDENTITY_FIRST

All other targets/categories
            │
            ▼
          DEFAULT
```

This is the approved strategy state.

---

# 22. Final Acceptance Table

| Area | Decision |
|---|---|
| Globus Pallidus permanent mapping | ACCEPTED |
| Caudate Nucleus mapping | PRESERVED |
| Nucleus Accumbens mapping | PRESERVED |
| DEFAULT fallback | PRESERVED |
| Category isolation | ACCEPTED |
| Exact target matching | ACCEPTED |
| Full regression | PASS — 1432 passed |
| Production resolver wiring | PASS |
| Real production-path verification | PASS |
| Validator changes | NONE |
| Retrieval changes | NONE |
| Schema changes | NONE |
| Retry changes | NONE |
| Target representation changes | NONE |
| Language compliance | FOLLOW-UP REQUIRED |
| WP-057 overall | IMPLEMENTATION ACCEPTED |

---

# 23. Final Decision

## WP-057 — ACCEPTED

The approved permanent strategy is now:

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

The implementation is correct, tested, and wired into the real production pipeline.

However:

```text
English-first language compliance
    → NOT CLOSED
```

because the live accepted output contained Hebrew despite an available English representation.

---

# 24. Recommended Next Step

Proceed to:

# WP-058 — English-Only Generation Compliance

WP-058 should investigate and then implement the smallest general mechanism required to enforce:

```text
English exists
    ↓
English must be used
```

without:

```text
changing the Globus Pallidus strategy
changing identity-first architecture
weakening validators
changing retrieval
changing schemas
changing retry semantics
```

After WP-058, perform an architect review before closing the language requirement.

---

# 25. Terminal Summary

```text
WP-057 ARCHITECTURE REVIEW COMPLETE

Strategy implementation:
ACCEPTED

Globus Pallidus:
IDENTITY_FIRST

Caudate Nucleus:
IDENTITY_FIRST

Nucleus Accumbens:
IDENTITY_FIRST

Unmapped targets/categories:
DEFAULT

Focused regression:
PASS

Full regression:
1432 passed
0 failed

Production resolver wiring:
PASS

Real production-path verification:
PASS

Validator changes:
NONE

Retrieval changes:
NONE

Schema changes:
NONE

Retry changes:
NONE

Target representation changes:
NONE

Language compliance:
FOLLOW-UP REQUIRED

Observed language issue:
Accepted question contained Hebrew although
an English representation exists.

Recommended next WP:
WP-058 — English-Only Generation Compliance

WP-057:
IMPLEMENTATION ACCEPTED

Waiting for next architect decision.
```
