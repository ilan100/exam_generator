# WP-061 Architecture Review — Language Policy Architecture Alignment

## Review Status

**ACCEPTED WITH REQUIRED FOLLOW-UP IMPLEMENTATION**

WP-061 successfully completed the architecture/documentation alignment task.

The repository now has a single authoritative language policy at:

```text
docs/LANGUAGE_POLICY.md
```

The active Claude and GPT handoff documents reference that policy, the historical WP-058 contradiction has been explicitly superseded at the active architecture level, and the repository-wide audit identified the two remaining real enforcement gaps.

The important architectural distinction is:

```text
POLICY
    aligned and authoritative

IMPLEMENTATION
    not yet fully aligned
```

Therefore WP-061 should be accepted, but the language-policy implementation gap must now be treated as a real future engineering task rather than considered completely solved.

---

# 1. Objective Assessment

WP-061's objective was architecture/documentation alignment only:

```text
make the authoritative language policy discoverable
make it authoritative
align active architecture/implementation instructions
identify contradictions
avoid production behavior changes
```

The completion report confirms that no production code, prompts, or tests were changed by WP-061. fileciteturn53file0L3-L5

**Assessment: PASS**

---

# 2. Authoritative Language Policy

The correct project-wide policy is now explicitly:

```text
Questions are written in Hebrew.

For every professional/technical/terminological item:

    if an English representation exists:
        English MUST be used.

    if no English representation exists:
        Hebrew MAY be used.

This applies to:
    question-stem terminology
    target names
    correct answers
    distractors
    relevant user-visible terminology

This does NOT require the entire question to be written in English.
```

This is the correct resolution of the earlier ambiguity.

The completion report records this policy as the authoritative current definition. fileciteturn53file0L7-L28

**Assessment: PASS**

---

# 3. Correct Repository Location

WP-061 correctly discovered that:

```text
docs/architecture/
```

does not exist.

The existing project convention is:

```text
docs/LANGUAGE_POLICY.md
```

The WP correctly used the existing user-supplied document rather than creating a duplicate hierarchy.

This is preferable to introducing a new directory solely to satisfy an earlier assumption in WP-061.

**Assessment: PASS**

---

# 4. Active Architecture Alignment

The repository audit found two genuine architectural/documentation contradictions:

```text
docs/ARCHITECTURE.md
    WP-058 section

implementation/WP-058_ARCHITECTURE_REVIEW.md
    historical narrow interpretation
```

The first was corrected with an explicit superseding annotation.

The second was deliberately left untouched because it is a historical architecture-review record.

This is the correct distinction:

```text
current architecture
    → corrected

historical record
    → preserved
```

The audit confirms this classification. fileciteturn53file1L11-L24

**Assessment: PASS**

---

# 5. Historical Records Must Remain Historical

I agree with the decision not to rewrite the historical WP-058 architecture review.

It is important that the project preserve:

```text
what WP-058 actually implemented
```

while separately establishing:

```text
what the architecture now requires
```

The correct mechanism is:

```text
historical WP
    → remains unchanged

current authoritative policy
    → supersedes historical interpretation
```

This preserves architectural traceability.

**Assessment: PASS**

---

# 6. Claude Instruction Alignment

WP-061 correctly updated:

```text
docs/CLAUDE_HANDOFF.md
```

so that Claude must read:

```text
docs/LANGUAGE_POLICY.md
```

before implementing WPs that can affect:

```text
generation
prompts
target planning
normalization
validation
output
terminology
```

It also requires Claude to stop and report if a WP conflicts with the authoritative policy.

The completion report explicitly confirms this change. fileciteturn53file0L51-L54

This is important because relying on conversation memory is not an adequate architectural control.

**Assessment: STRONG PASS**

---

# 7. GPT Instruction Alignment

WP-061 also updated:

```text
docs/GPT_HANDOFF.md
```

with a language-policy pointer.

This was not strictly necessary for Claude implementation, but it is architecturally appropriate because GPT is responsible for producing future architecture/WP instructions.

This reduces the probability that a future WP will accidentally reintroduce the narrower definition.

**Assessment: PASS**

---

# 8. The Most Important Remaining Issue

WP-061 correctly discovered that the architecture is now aligned at the **policy/documentation level**, but the implementation is not yet fully aligned.

There are two enforcement gaps.

### Gap 1

```text
prompts/generation/question.txt
```

still tells the generator to apply English only to:

```text
correct answer
in-question target-name reference
```

rather than to all professional/technical terminology.

The audit explicitly identifies missing coverage for:

```text
distractor terminology
general question-stem terminology
acronyms
symbols
other professional terminology
```

fileciteturn53file1L22-L24

### Gap 2

```text
_validate_target_language_compliance()
```

still enforces only the narrower WP-058 scope.

It does not validate:

```text
distractors
general stem terminology
acronyms
symbols
non-target professional terminology
```

and it only applies to named-entity target cases.

fileciteturn53file1L22-L24

These are **real implementation gaps**, not documentation issues.

---

# 9. This Is Not a Failure of WP-061

The gaps should not be considered a failure of WP-061.

WP-061 explicitly prohibited silently expanding production enforcement and reserved broader enforcement for a separate architect-approved implementation WP.

The completion report correctly records that both gaps remain open. fileciteturn53file0L76-L92

Therefore:

```text
WP-061 objective
    → achieved

broader language-policy enforcement
    → still required
```

This is the correct outcome.

---

# 10. Important Architectural Consequence

We now have three distinct layers:

```text
1. Policy
   docs/LANGUAGE_POLICY.md

2. Active instructions
   CLAUDE_HANDOFF.md
   GPT_HANDOFF.md
   future WP instructions

3. Runtime enforcement
   generation prompt
   deterministic validation
   future broader validation
```

Layer 1 and Layer 2 are now aligned.

Layer 3 is not.

This distinction should be preserved in future architecture discussions.

---

# 11. Do Not Fix This by Rejecting Hebrew Globally

A future implementation must **not** implement the policy as:

```text
reject Hebrew characters
```

That would be incorrect because:

```text
Hebrew question prose
```

is explicitly allowed.

The enforcement problem is semantic:

```text
specific professional/technical item
        ↓
English representation exists?
        ↓
YES → English required
NO  → Hebrew permitted
```

The challenge is identifying the relevant item, not detecting whether a character belongs to Hebrew.

---

# 12. Do Not Invent an External Terminology System Yet

The remaining enforcement gap does not automatically justify:

```text
UMLS
SNOMED
MeSH
external terminology APIs
LLM terminology classification
web translation
```

That would be a major architectural expansion.

The next implementation WP should first inspect what terminology/evidence infrastructure already exists in the project.

The project's existing source-authority rules remain unchanged.

---

# 13. The Key Architectural Question for the Next WP

The next task should answer:

> **How can the broader language policy be enforced reliably without creating an oversized terminology subsystem or incorrectly rejecting legitimate Hebrew prose?**

This is now a meaningful implementation problem.

It is more important than creating another documentation-only WP.

---

# 14. Recommended Next WP

I recommend a dedicated implementation WP for the language enforcement gap.

Its scope should be approximately:

```text
current language policy
        ↓
identify professional/technical items
        ↓
determine whether an English representation exists
        ↓
enforce English representation
        ↓
preserve Hebrew ordinary prose
```

The WP should cover at least:

```text
question stem
correct answer
distractors
target references
acronyms
symbols
professional terminology
```

It should also cover both:

```text
named-entity targets
```

and:

```text
non-named-entity targets
```

because the current deterministic validator does not cover the latter.

---

# 15. The Next WP Must Not Become a Giant Terminology Project

The scope should be controlled.

The next WP should first investigate whether the project already contains enough structured terminology information to enforce the rule.

Potential existing sources may include:

```text
student-summary terminology
target inventories
historical terminology
question-format definitions
existing target language metadata
```

Only if those are insufficient should a new terminology mechanism be considered.

The next WP should explicitly compare:

```text
minimal deterministic enforcement
```

against:

```text
more complex terminology infrastructure
```

before implementation.

---

# 16. Tests Are Now Required in the Next Implementation WP

WP-061 correctly added no tests because it did not change runtime behavior.

That should change in the next implementation WP.

The future implementation must establish regression coverage for at least:

```text
Hebrew question prose
    → accepted

English professional term
    → accepted

Hebrew professional term where English exists
    → rejected

English acronym
    → accepted

Hebrew substitute for established acronym
    → rejected

English target
    → accepted

Hebrew target where English exists
    → rejected

professional terminology in distractor
    → checked

professional terminology in question stem
    → checked

professional terminology unrelated to target
    → checked
```

The exact test mechanism should follow the repository's architecture.

---

# 17. Important Limitation: "English Representation Exists"

This phrase remains the hardest part of the policy.

The future implementation must define how the system knows:

```text
English representation exists
```

It must not assume that:

```text
any plausible English translation
```

is sufficient.

The architecture should distinguish:

```text
established English representation
```

from:

```text
model-generated translation
```

The latter must not automatically be accepted as authoritative.

This should be an explicit design decision in the next WP.

---

# 18. Source Authority Remains Unchanged

Nothing in WP-061 changes:

```text
student summaries
    = factual grounding authority

course_book.pdf
    = secondary check

historical Excel
    = style/structure/terminology reference
```

The next language-enforcement WP must preserve these boundaries.

---

# 19. No Strategy Impact

WP-061 correctly confirms:

```text
IDENTITY_FIRST mappings:
UNCHANGED

DEFAULT strategy:
UNCHANGED

target planning:
UNCHANGED
```

The language policy is orthogonal to generation strategy.

This must remain true.

---

# 20. Regression

WP-061 reports:

```text
1440 passed
0 failed
```

and confirms that production behavior remained unchanged. fileciteturn53file0L59-L74

**Assessment: PASS**

---

# 21. Final Architecture State

The correct current architecture is:

```text
                    LANGUAGE POLICY
                          │
                          ▼
                docs/LANGUAGE_POLICY.md
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
       Claude/GPT instructions     Runtime implementation
             │                         │
             │                    CURRENTLY PARTIAL
             │                         │
             ▼                         ▼
      future WPs obey policy      WP-058 enforcement
                                      │
                                      ▼
                              narrower than policy
```

This is not yet the final runtime state.

---

# 22. Final Verdict

**WP-061 — ACCEPTED WITH REQUIRED FOLLOW-UP IMPLEMENTATION**

The architecture/documentation alignment is complete.

The policy is now authoritative and discoverable:

```text
docs/LANGUAGE_POLICY.md
```

Active Claude instructions now point to it and require conflict detection.

The historical WP-058 interpretation remains preserved as history but is no longer authoritative.

However, two runtime enforcement gaps remain:

```text
1. generation prompt
2. deterministic language validator
```

Both currently enforce only the older target/correct-answer scope. fileciteturn53file1L28-L49

These gaps should be addressed by **one dedicated implementation WP**, not by modifying WP-061.

---

# 23. Recommended Next Direction

The next WP should be:

```text
Language Policy Runtime Enforcement
```

with the explicit goal of bringing:

```text
runtime behavior
```

into alignment with:

```text
docs/LANGUAGE_POLICY.md
```

without turning the project into a full external medical terminology system.

The next WP should first design the minimal reliable enforcement mechanism, then implement it, then add comprehensive tests.

After that, we can return to the deterministic target-planning category pilot identified by WP-060.

---

# Final Decision

```text
WP-061:
    ACCEPTED

Architecture policy:
    ALIGNED

Active instructions:
    ALIGNED

Historical records:
    PRESERVED

Runtime enforcement:
    PARTIALLY ALIGNED

Open enforcement gaps:
    2

Next required WP:
    LANGUAGE POLICY RUNTIME ENFORCEMENT

IDENTITY_FIRST:
    UNCHANGED

Target planning:
    UNCHANGED

Regression:
    1440 passed, 0 failed
```

**WP-061 is complete and architecturally successful, but the language-policy issue is not yet fully closed at runtime.**

The next meaningful task is to close the two identified enforcement gaps in a controlled implementation WP.
