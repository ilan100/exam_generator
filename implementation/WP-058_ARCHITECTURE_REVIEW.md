# WP-058 Architecture Review

## Review Status

**ACCEPTED WITH DOCUMENTED LIMITATION**

WP-058 investigated the project's English-first language requirement using the actual repository rules and implementation history.

The investigation produced an important architectural correction:

> The project does **not** require the entire question to become English whenever an English representation exists.

The documented rule is narrower:

```text
General question prose:
    Hebrew

When the target is English-representable:
    correct answer → English
    in-question reference to the target's own name → English

Other question prose and distractors:
    remain governed by the general Hebrew rule
```

The WP-057 output:

```text
"איזה מהמבנים הבאים הוא Globus Pallidus?"
```

was therefore **compliant with the project's actual documented rule**. fileciteturn45file0L9-L15 fileciteturn45file0L23-L34

WP-058 nevertheless identified and closed a real enforcement gap: the correct-answer English requirement was previously enforced only through the LLM prompt and lacked deterministic post-generation enforcement. fileciteturn45file0L17-L21

---

# 1. Correction to WP-057 Architecture Review

The previous WP-057 architecture review characterized:

```text
איזה מהמבנים הבאים הוא Globus Pallidus?
```

as a language-policy violation.

That characterization was incorrect.

The actual project sources explicitly establish:

```text
Questions are in Hebrew
```

while permitting English anatomical terminology and mixed Hebrew/English terminology where appropriate. fileciteturn45file0L9-L15

WP-041's implementation further confirms that the English requirement was deliberately scoped to:

```text
1. correct answer
2. in-question reference to the target's own name
```

and explicitly did not change the rest of the question to English. fileciteturn45file0L11-L15

Therefore:

```text
Hebrew question prose
+
English target name
```

is expected project behavior.

---

# 2. WP-041 Architectural Interpretation

WP-041 was not an incomplete attempt at whole-question English generation.

It deliberately implemented a narrow carve-out from the general Hebrew rule.

The WP-041 prompt states that the target-language requirement governs:

```text
the correct answer
+
any reference to the target's own name within the question
```

and explicitly does not change:

```text
the rest of the question
+
the other three incorrect answer choices
```

fileciteturn45file0L11-L13

WP-041's live pilot achieved:

```text
9/9
100% compliance
```

for that exact scope. fileciteturn45file0L17-L21

The architecture should therefore preserve WP-041's interpretation.

---

# 3. Actual Language Policy After WP-058

The project language policy should now be understood as:

```text
                    LANGUAGE POLICY
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
      General question            Target-specific
          prose                    requirement
             │                         │
             ▼                         ▼
          Hebrew              English when available
             │                         │
             └────────────┬────────────┘
                          ▼
                   Final question
```

More precisely:

```text
Question stem prose:
    Hebrew

Correct answer:
    English when target is English-representable

Target name appearing in question:
    English when target is English-representable

Other distractors:
    Hebrew/general project rule

Hebrew-only target:
    Hebrew permitted
```

This is the policy that should be carried forward.

---

# 4. Real WP-058 Finding

Although the WP-057 example was compliant, WP-058 found a real general enforcement weakness.

Before WP-058:

```text
English target
    ↓
prompt instructs English correct answer
    ↓
LLM generates answer
    ↓
no deterministic language-policy check
```

The existing target-answer identity check already prevented a purely Hebrew answer from passing because the English target name had to be contained in the answer.

However, a mixed answer such as:

```text
גלובוס פאלידום Globus Pallidus
```

could theoretically satisfy the identity check while violating the English-only requirement for the correct answer.

WP-058 closes this residual gap. fileciteturn45file0L36-L42

---

# 5. WP-058 Implementation

The implementation adds:

```text
_validate_target_language_compliance()
```

in:

```text
src/exam_generator/generation/generator.py
```

It is invoked as a deterministic pre-validator generation check.

The rule is:

```text
named_entity_target = true
+
target is English-representable
+
correct answer contains non-ASCII
        ↓
reject generation attempt
```

The change is general and applies across named-entity targets, not just Globus Pallidus or identity-first targets. fileciteturn45file0L70-L84

---

# 6. Architectural Placement Is Correct

The check follows the existing pattern used by earlier deterministic generation-contract checks:

```text
LLM candidate
    ↓
generation-contract checks
    ↓
existing validators
    ↓
CandidateQuestion / final output
```

This is preferable to adding another LLM call or a separate language-repair loop.

The new check raises the existing:

```text
InvalidGeneratedOutputError
```

and therefore consumes one of the existing generation attempts without introducing a second retry mechanism. fileciteturn45file0L70-L74

---

# 7. No Prompt Rewrite Was Necessary

WP-058 correctly left the existing WP-041 prompt guidance unchanged.

This is important because the prompt already expresses the correct language policy.

The problem was:

```text
instruction
    +
no deterministic enforcement
```

not:

```text
incorrect instruction
```

The architecture now has:

```text
prompt guidance
+
deterministic enforcement
```

for the correct-answer half of the rule.

---

# 8. Test Coverage

WP-058 added eight tests covering:

```text
pure English correct answer
Hebrew-decorated English answer
pure Hebrew answer
Hebrew-only target exception
non-named-entity target
no additional LLM call
deterministic/non-LLM enforcement
coexistence with target-answer identity validation
```

fileciteturn45file0L90-L100

The test matrix confirms:

```text
Globus Pallidus
    English answer
    → PASS

גלובוס פאלידום Globus Pallidus
    mixed answer
    → FAIL

גלובוס פאלידום
    Hebrew answer
    → FAIL via existing WP-047 check

Hebrew-only target
    Hebrew answer
    → ALLOW
```

fileciteturn45file0L102-L110

---

# 9. Regression Result

The complete test suite now reports:

```text
1440 passed
0 failed
```

The WP-057 baseline was:

```text
1432 passed
```

Therefore:

```text
+8 tests
0 regressions
```

fileciteturn45file0L127-L134

This is a clean regression result.

---

# 10. End-to-End Verification

No new live API call was made.

Instead, WP-058 replayed the actual recorded WP-057 production output:

```text
איזה מהמבנים הבאים הוא Globus Pallidus?
```

with:

```text
correct answer:
Globus Pallidus
```

The new deterministic check accepted it. fileciteturn45file0L113-L123

This is appropriate because the purpose was to verify the new check against a known real production output without unnecessary API cost.

The negative path was tested using a mocked LLM provider at the actual `QuestionGenerator` integration level. fileciteturn45file0L123-L125

---

# 11. Hebrew-Only Exception

WP-058 preserved the explicit exception:

```text
If English representation does not exist:
    Hebrew may be used.
```

The current three pilot categories contain:

```text
141 concepts
0 non-ASCII concepts
```

so there is currently no verified real Hebrew-only pilot-category target.

The Hebrew-only positive test is therefore structural/synthetic rather than a real-data production example. fileciteturn45file0L123-L125

This limitation is correctly disclosed.

---

# 12. Known Remaining Limitation

The in-question target-name requirement remains primarily prompt-enforced.

For example, the architecture requires:

```text
target = Globus Pallidus

question:
Which of the following is Globus Pallidus?
```

rather than a Hebrew rendering of the target name.

WP-058 does not attempt to deterministically detect every possible Hebrew transliteration of an English target.

This is reasonable.

The project has explicitly rejected transliteration/fuzzy/semantic matching approaches as unsafe, and no canonical transliteration database currently exists. fileciteturn45file0L64-L69

This should remain a documented limitation rather than trigger another WP automatically.

---

# 13. No New Terminology Database

WP-058 correctly reused:

```text
target.named_entity_target
target.topic
```

and the existing ASCII-based English-representability logic.

It did not introduce:

```text
new terminology database
new model field
new configuration
external translation service
```

This keeps the architecture simple and consistent with previous WPs. fileciteturn45file0L64-L67

---

# 14. No Changes to Other Architecture

WP-058 correctly left unchanged:

```text
retrieval
strategy mapping
target representation
schemas
QuestionProducer
validators
retry budget
output models
```

The only production behavior change is the new deterministic correct-answer language check. fileciteturn45file0L194-L208

The WP-057 strategy therefore remains:

```text
Caudate Nucleus
    → IDENTITY_FIRST

Nucleus Accumbens
    → IDENTITY_FIRST

Globus Pallidus
    → IDENTITY_FIRST
```

with other targets/categories remaining `DEFAULT` unless explicitly mapped.

---

# 15. No Whole-Question English Policy

This is now explicitly closed.

We should **not** introduce a future WP that attempts to convert:

```text
איזה מהמבנים הבאים הוא Globus Pallidus?
```

into:

```text
Which of the following is Globus Pallidus?
```

unless the project owner explicitly changes the product requirement.

The current documented requirement is intentionally:

```text
Hebrew question prose
+
English target terminology where required
```

and that should be preserved.

---

# 16. Architectural Assessment

WP-058 achieved two things:

### Correction

It corrected the mistaken interpretation introduced by the WP-057 architecture review:

```text
Hebrew question prose + English target
    ≠
language violation
```

### Improvement

It added deterministic enforcement for the actual correct-answer English requirement:

```text
English-representable named target
+
non-English correct answer
    →
reject
```

This is a meaningful architectural improvement.

---

# 17. Final Acceptance Table

| Area | Decision |
|---|---|
| WP-057 language interpretation | **CORRECTED** |
| Whole-question English requirement | **NOT A PROJECT REQUIREMENT** |
| WP-041 interpretation | **CONFIRMED** |
| Correct-answer English enforcement | **PASS** |
| Mixed-language correct answer | **REJECTED** |
| Hebrew-only exception | **PRESERVED** |
| Target-name reference enforcement | **Prompt-only; documented limitation** |
| Strategy mapping | **UNCHANGED** |
| Retrieval | **UNCHANGED** |
| Schemas | **UNCHANGED** |
| Retry budget | **UNCHANGED** |
| Full regression | **PASS — 1440/1440** |
| API cost | **0 new calls** |
| Overall | **ACCEPT WITH DOCUMENTED LIMITATION** |

---

# 18. Final Architectural Decision

## WP-058 — ACCEPTED

The correct project language architecture is:

```text
General question prose
    → Hebrew

English-representable target:
    correct answer
        → English

English-representable target referenced by name in question:
    target name
        → English

Other question prose / distractors:
    → existing Hebrew rule

English-unavailable target:
    → Hebrew permitted
```

WP-058 now provides deterministic enforcement for the correct-answer portion of this rule.

The remaining target-name-reference limitation is explicitly documented and does not justify another WP at this time.

---

# 19. Language Thread Closure

The language thread should now be considered:

```text
CLOSED
```

unless the project owner explicitly decides to change the product policy.

There is no architectural justification for continuing to pursue:

```text
whole-question English
```

under the current requirements.

---

# 20. Recommended Next Step

Return to the main exam-generation architectural problem.

Do **not** create another language-focused WP solely because:

```text
Hebrew question prose
+
English anatomical terminology
```

appears in generated output.

That is expected behavior.

The next WP should address the next unresolved generation/reliability issue rather than continuing this language thread.

---

# 21. Final Summary

```text
WP-058 ARCHITECTURE REVIEW

Status:
ACCEPTED WITH DOCUMENTED LIMITATION

Key correction:
WP-057's observed Hebrew question prose was NOT a
language-policy violation.

Actual language rule:
Hebrew question prose
+
English target/correct answer when required.

WP-041 interpretation:
CONFIRMED

New deterministic enforcement:
English-representable named target
+
non-English correct answer
→ REJECT

Tests:
1440 passed
0 failed

New tests:
8

New API calls:
0

WP-057 strategy:
UNCHANGED

Retrieval:
UNCHANGED

Schemas:
UNCHANGED

Retry budget:
UNCHANGED

Remaining limitation:
In-question target-name language is still primarily
prompt-enforced because safe deterministic
transliteration/fuzzy matching is not available.

Whole-question English policy:
NOT REQUIRED

Language thread:
CLOSED

Next action:
Return to the main exam-generation architecture.
