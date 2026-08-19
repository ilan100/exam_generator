# Language Policy Architecture Alignment and Correction

## Status

**AUTHORITATIVE ARCHITECTURE CLARIFICATION**

This document resolves a terminology/policy inconsistency identified between the project's original language requirement, earlier WP definitions, and the WP-058 architecture review.

The latest explicit project-owner requirement is authoritative:

```text
Questions are written in Hebrew.

Professional terms, symbols, acronyms, named entities,
and other specific terminology/items:
    use English whenever an English representation exists.

Use Hebrew for a specific item only when no English
representation exists for that same item.
```

This is **not** a whole-question English requirement.

It is also **not** limited to:
- the correct answer;
- the target's own name;
- anatomical target names.

The English-first rule applies to **every applicable professional/technical/terminological item in the question and generated output**.

---

# 1. Problem Identified

The WP-058 architecture review contains this narrower definition:

```text
General question prose:
    Hebrew

English-representable target:
    correct answer → English
    in-question reference to target → English

Other question prose / distractors:
    existing Hebrew rule
```

That definition is too narrow for the current project requirement.

It reduces the English-first rule to target terminology, while the project-owner requirement is broader:

```text
any professional term / symbol / acronym / named item
    with an English representation
        → English
```

Therefore WP-058 must not be treated as the final authoritative definition of the language rule.

---

# 2. What Is NOT Being Changed

This clarification does **not** change the language of ordinary question prose.

The intended architecture remains:

```text
Question prose:
    Hebrew
```

when Hebrew is the product's normal question language.

For example, a question may have Hebrew grammatical prose around English professional terminology.

The following is therefore conceptually valid:

```text
איזה מבנה אחראי ל...
```

provided that any professional terminology embedded in the question follows the English-first rule.

This clarification does **not** mean:

```text
convert every question to English
```

and does not authorize whole-question English generation.

---

# 3. The Correct Rule

The authoritative rule is:

```text
For every specific professional/technical/terminological item:

    English representation exists
        ↓
    MUST use English

    English representation does not exist
        ↓
    Hebrew MAY be used
```

The rule is mandatory, not preferential.

Do not interpret:

```text
use English
```

as:

```text
prefer English when convenient
```

The correct interpretation is:

```text
English exists
    →
Hebrew must not be used for that item.
```

---

# 4. Scope of "Item"

The term "item" is intentionally broad.

It includes, where applicable:

```text
professional terminology
anatomical names
medical terminology
technical terminology
symbols
acronyms
abbreviations
named entities
scientific names
standard notation
domain-specific labels
target names
correct-answer terminology
terminology appearing in distractors
terminology appearing inside the question stem
terminology appearing in generated metadata when that metadata is user-visible
```

The rule is **not** restricted to the target.

---

# 5. Examples

## Example A — English anatomical name exists

Use:

```text
Caudate Nucleus
```

not a Hebrew equivalent.

---

## Example B — English acronym exists

Use:

```text
CNS
```

rather than a Hebrew expansion/abbreviation when `CNS` is the established English representation.

---

## Example C — English professional term exists inside Hebrew prose

The grammatical sentence may remain Hebrew, but the professional term must remain English.

Conceptually:

```text
איזה אזור של the Cerebral Cortex ...
```

The exact final phrasing must follow the project's generation style, but:

```text
Cerebral Cortex
```

must not be replaced by Hebrew merely because it occurs inside Hebrew prose.

---

## Example D — English symbol/notation exists

Use the established English/international notation.

Do not replace a standard professional symbol with a Hebrew textual equivalent when an English/international representation exists.

---

## Example E — Only Hebrew representation exists

If a specific domain item genuinely has no English representation:

```text
Hebrew is permitted.
```

The system must not invent an English translation.

---

# 6. Target Names Are a Subset, Not the Whole Rule

The previous WP language work correctly established:

```text
English-representable target
    → English target name
```

but this is only one application of the broader rule.

The correct hierarchy is:

```text
GLOBAL LANGUAGE POLICY
        ↓
specific professional/technical item
        ↓
English representation exists?
        │
        ├── YES → English
        │
        └── NO  → Hebrew permitted
```

Target-name compliance is therefore:

```text
one case of the global rule
```

not:

```text
the complete definition of the rule
```

---

# 7. Question Prose vs Professional Terminology

This distinction must be explicit in all future architecture documents.

```text
Question prose
    → Hebrew

Professional/technical terminology embedded in that prose
    → English if an English representation exists
```

Therefore:

```text
Hebrew question
+
English professional terminology
```

is expected architecture.

But:

```text
Hebrew professional terminology
```

when an English representation exists is a language-policy violation.

---

# 8. Distractors

The WP-058 wording:

```text
Other question prose / distractors:
    existing Hebrew rule
```

must be interpreted carefully.

The grammatical prose of distractors may follow the Hebrew question language.

However, professional terminology inside distractors is still governed by:

```text
English if an English representation exists.
```

Therefore the language rule is not waived for distractors.

---

# 9. Acronyms and Symbols

Acronyms and symbols require special attention because they are easy to lose during generation.

For example, if the project uses:

```text
CNS
PNS
MRI
CT
```

as the established English representations, generated questions should retain those forms.

Do not silently transliterate or translate them into Hebrew.

If no established English representation exists, do not invent one.

---

# 10. No Invented Terminology

The English-first rule does **not** authorize the system to invent English terminology.

The system must distinguish:

```text
known English representation
```

from:

```text
possible translation
```

Only the former satisfies the rule.

If the architecture cannot establish that an English representation exists:

```text
do not invent one
```

and do not silently replace the project's source terminology.

---

# 11. Source Authority

This language clarification does not change factual source authority.

Preserve:

```text
student summaries
    = sole factual grounding authority

course_book.pdf
    = secondary consistency check

historical Excel
    = style / structure / terminology reference
```

Language selection must not introduce facts or terminology from external medical sources.

---

# 12. No Fuzzy Transliteration

This clarification does not authorize:

```text
fuzzy matching
semantic translation
automatic transliteration
external terminology APIs
UMLS
SNOMED
MeSH
web translation
```

unless a future architect-approved WP explicitly introduces such a capability.

The existing project's conservative approach remains:

```text
known English representation
    → use it

unknown English representation
    → do not invent it
```

---

# 13. Required Future Architecture Terminology

All future WP documents must use this definition:

```text
Language Policy:

Questions are written in Hebrew.

For every professional/technical/terminological item,
including symbols, acronyms, abbreviations, named entities,
and domain-specific terminology:

    if an English representation exists:
        English MUST be used.

    if no English representation exists:
        Hebrew MAY be used.

This rule applies to:
    question stem terminology
    target names
    correct answers
    distractors
    relevant user-visible generated terminology

It does not require the entire question to be written in English.
```

---

# 14. Required Correction to Existing Architecture Interpretation

The following WP-058 interpretation:

```text
Other question prose / distractors
    → Hebrew/general project rule
```

must be replaced by:

```text
Other question prose
    → Hebrew as the normal question language

Professional/technical terminology inside that prose
    → English whenever an English representation exists

Distractor terminology
    → same English-first rule
```

This is the precise reconciliation.

---

# 15. Relationship to WP-058

WP-058 made a valid architectural correction in one respect:

```text
Hebrew question prose + English target name
    ≠
whole-question language violation
```

That correction remains valid.

However, its resulting language definition was too narrow because it treated the English requirement as target-specific.

The corrected interpretation is:

```text
Hebrew prose
+
English professional terminology wherever an English
representation exists
```

This supersedes the narrower target-only wording.

---

# 16. Relationship to Earlier WPs

Earlier WPs already contain the stronger wording:

```text
If an English representation exists:
    use English.

Use Hebrew only when no English representation exists.
```

This appears explicitly in WP-054 and WP-056 and was therefore already part of the intended architecture.

The problem is that WP-058's architecture review later narrowed the interpretation to target-specific terminology.

The present document restores the broader rule without changing the intended Hebrew question-prose language.

---

# 17. Required Future Validation

Future language validation must test more than:

```text
correct answer language
```

and:

```text
target name language
```

It should cover at least:

```text
English anatomical terms
English professional terms
acronyms
symbols
named entities
terms in question stems
terms in distractors
correct-answer terminology
```

The exact implementation should remain proportional to the repository's existing terminology architecture.

Do not create a large terminology subsystem merely for testing unless the repository already requires one.

---

# 18. Architectural Invariant

The project-wide invariant is:

```text
For every generated professional/technical item:

English exists?
    YES → English is mandatory.
    NO  → Hebrew is permitted.
```

This invariant must hold regardless of:

```text
category
target
generation strategy
IDENTITY_FIRST / DEFAULT
retrieval path
target-planning mode
question shape
```

Strategy selection must never override language policy.

---

# 19. Final Decision

The architecture should now treat the following as authoritative:

```text
QUESTION LANGUAGE
    Hebrew

PROFESSIONAL / TECHNICAL TERMINOLOGY
    English whenever an English representation exists

HEBREW TERMINOLOGY
    permitted only when no English representation exists

WHOLE QUESTION ENGLISH
    NOT REQUIRED

TARGET-SPECIFIC ENGLISH
    required, but only one application of the broader rule

ACRONYMS / SYMBOLS
    English/international representation when established

INVENTED ENGLISH TRANSLATIONS
    forbidden
```

---

# 19a. Conflict-Resolution Rule (WP-061)

This document is the authoritative, project-wide language policy.

```text
If a current or future WP, architecture document, prompt, or
implementation instruction conflicts with this document:

    this document wins.

Claude must stop and report the conflict before implementing
the conflicting instruction.
```

Historical WP documents remain historical records of what was decided *at the time* - they are not silently rewritten to match this document, but they must not be treated as current authoritative guidance where they conflict with it. Where a specific historical document is known to conflict (e.g. the WP-058 architecture review's target-only scoping - see `implementation/WP-061_LANGUAGE_POLICY_AUDIT.md`), the current architecture explicitly supersedes it, and that supersession is recorded in `docs/ARCHITECTURE.md` rather than by editing the historical file itself.

# 20. Action Required Before Future WPs

Before producing future implementation WPs that affect:

```text
generation
prompts
target planning
question normalization
validation
output
```

their language sections must be checked against this document.

No future WP should reintroduce the narrower definition:

```text
only target names must be English
```

and no future WP should accidentally interpret the requirement as:

```text
the whole question must be English
```

The correct architecture is the middle position:

```text
Hebrew question prose
+
English professional terminology whenever English exists
+
Hebrew only for items with no English representation
```

---

# Final Architectural Statement

**This document supersedes the narrower language interpretation in WP-058's architecture review.**

The project language policy is:

> **Questions are written in Hebrew. Professional and technical items—including symbols, acronyms, named entities, and terminology—must be written in English whenever an English representation exists. Hebrew may be used for a specific item only when no English representation exists for that item.**

This is the definition that must be used consistently in all future architecture documents, WPs, implementation prompts, tests, reviews, and completion reports.
