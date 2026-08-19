# WP-060 Architecture Review

## Review Status

**ACCEPTED WITH DOCUMENTED LIMITATIONS**

WP-060 successfully investigated the evidence bottleneck identified by WP-059.

The central result is:

```text
17 remaining categories lack production deterministic target planning.

Of those:
    16 have technically extractable target/concept structure
    1 (מבוא) does not have a suitable deterministic structure

However:
    technical extractability ≠ production readiness
```

The correct architectural recommendation is:

```text
PARTIAL / HYBRID ARCHITECTURE

deterministic target inventory
    where source structure supports it

LLM target planning
    where deterministic extraction is not justified

production expansion:
    one category at a time
    with live validation
```

No new `IDENTITY_FIRST` mapping is justified by WP-060.

No blanket rollout of deterministic target planning is justified.

---

# 1. Objective Assessment

WP-060 correctly moved away from the previous question:

```text
Which target should receive IDENTITY_FIRST?
```

and investigated the deeper evidence-coverage problem:

```text
Why do only three categories currently have target-level
generation evidence, and can the remaining categories
obtain reliable target inventories?
```

WP-060 was explicitly defined as an offline architecture/evidence-gap analysis rather than a production strategy change. It required inspection of all 20 canonical categories and prohibited new LLM/API calls, production changes, fuzzy entity merging, and new `IDENTITY_FIRST` mappings.

**Assessment: PASS**

---

# 2. Most Important Finding

The existing deterministic extraction mechanism is **not inherently limited to the three pilot categories**.

The implementation:

```text
extract_concept_inventory()
refine_concept_inventory()
```

accepts source evidence and does not intrinsically require a particular category.

The current three-category restriction is imposed by the pilot routing/configuration rather than by the extraction mechanism itself.

Therefore:

```text
three current deterministic categories
```

does not mean:

```text
only three categories can technically use deterministic extraction
```

This is an important architectural discovery.

**Assessment: STRONG PASS**

---

# 3. The 16/17 Result

WP-060 ran the existing deterministic extraction mechanism against retrieved student-summary evidence for all 17 non-pilot categories.

The resulting feasibility picture was:

```text
16 / 17
    substantial plausible inventories

1 / 17
    SOURCE_STRUCTURE_INSUFFICIENT
    מבוא
```

The result demonstrates that most remaining categories have source structure that is potentially usable for deterministic target inventory construction.

However, this result is correctly treated as:

```text
technical feasibility
```

rather than:

```text
production readiness
```

**Assessment: PASS**

---

# 4. Why the 16 Categories Must Not Be Rolled Out Automatically

This is the most important limitation.

The analysis establishes:

```text
target inventory can probably be extracted
```

but does not establish:

```text
generation will reliably use the extracted target
```

The project has already learned from earlier target-planning work that deterministic inventory availability does not automatically eliminate:

```text
target drift
incorrect relationships
weak target anchoring
generation failures
```

The existing pilot categories required additional validation and architectural fixes after deterministic target planning was introduced.

Therefore:

```text
16 feasible
```

must **not** become:

```text
enable all 16
```

The established discipline should remain:

```text
one category
    ↓
narrow pilot
    ↓
real generation
    ↓
target-alignment validation
    ↓
architect review
```

**Decision: ACCEPT**

---

# 5. Hybrid Architecture

The correct architectural direction is:

```text
deterministic target inventory
    where source structure supports it

LLM target planning
    where deterministic extraction is not justified
```

This avoids forcing one target-planning mechanism across all categories.

The architecture should therefore be understood as:

```text
Category
   ↓
target-planning mode
   │
   ├── deterministic inventory
   │       ↓
   │   validated target set
   │
   └── LLM planning
           ↓
       provenance-validated targets
```

**Decision: ACCEPT**

---

# 6. `מבוא` as the Current Outlier

WP-060 identifies:

```text
מבוא
```

as the category where deterministic target extraction is not currently justified.

The source material is substantially narrative/historical rather than a clean enumeration of anatomical targets.

Therefore the correct architectural outcome is:

```text
מבוא
    → retain LLM target planning
```

This is preferable to manufacturing a deterministic inventory from incidental terms.

**Decision: ACCEPT**

---

# 7. Historical Exam-Level Evidence

WP-060 also identified an important distinction between two forms of historical evidence:

```text
historical accepted questions
```

versus:

```text
target-level, per-attempt, question-shape-classifiable evidence
```

The project has historical accepted exam-output coverage across the categories, but the richer target-level evidence required for strategy analysis is much narrower.

This does not contradict WP-059.

The architectural distinction is:

```text
historical question coverage
    ≠
target-level strategy evidence
```

This supports improving evidence collection rather than inventing strategy mappings.

---

# 8. Source Authority

WP-060 correctly preserves the established source hierarchy:

```text
student summaries
    = factual grounding authority

course_book.pdf
    = secondary consistency check

historical Excel
    = style / structure / terminology reference
```

The deterministic target analysis must therefore remain grounded in the student-summary source.

**Assessment: PASS**

---

# 9. Determinism and Reproducibility

The analysis is appropriately offline and deterministic.

It does not require:

```text
OpenAI
Claude
OpenRouter
external LLMs
```

for the feasibility classification.

This is important because WP-060 is intended to establish architectural facts about the existing system rather than introduce new model-dependent judgments.

**Assessment: PASS**

---

# 10. Manual Spot-Check Limitation

The feasibility analysis includes a manual qualitative component when assessing the quality/structure of retrieved evidence.

This is acceptable for:

```text
architecture feasibility analysis
```

but should not become an implicit production acceptance mechanism.

Before promoting a category to production deterministic target planning, the category should receive stronger validation through an actual controlled generation pilot.

Therefore:

```text
manual feasibility assessment
    ≠
production eligibility
```

**Assessment: ACCEPTABLE FOR THIS WP**

---

# 11. Inventory Size Is Not a Production Criterion

WP-060 uses inventory size as part of feasibility screening.

This is useful for identifying categories with:

```text
no meaningful inventory
```

but must not become a production rule such as:

```text
inventory >= N
    → production-safe
```

A large inventory can still contain:

```text
wrong entities
truncations
generic concepts
weak anchors
OCR artifacts
category-inappropriate concepts
```

Therefore inventory size is:

```text
screening evidence
```

not:

```text
generation-quality evidence
```

---

# 12. Existing Extraction Repairs

WP-060's investigation indicates that known extraction/truncation repair mechanisms are reusable across categories.

This supports the conclusion that the underlying extraction architecture is not intrinsically category-specific.

However, residual extraction noise remains possible.

Therefore:

```text
reusable extraction mechanism
```

does not mean:

```text
every generated inventory is automatically production-quality
```

Category-specific validation remains necessary.

---

# 13. Production Changes

WP-060 correctly leaves production strategy unchanged.

The required final state is:

```text
New IDENTITY_FIRST mappings:
NONE

Production strategy changes:
NONE

Generation prompt changes:
NONE

Validator changes:
NONE

Retrieval changes:
NONE

Schema changes:
NONE

Retry changes:
NONE
```

This is exactly the correct boundary for the WP.

**Assessment: PASS**

---

# 14. Regression

The WP-060 completion evidence reports:

```text
1440 passed
0 failed
```

The analysis was performed without introducing production behavior changes.

Any unrelated working-tree changes were identified as pre-existing rather than attributed to WP-060.

**Assessment: PASS**

---

# 15. Relationship to the Main Architectural Problem

WP-060 is meaningful progress.

The project previously reached:

```text
implicit LLM strategy selection
        ↓
uneven generation reliability
```

The project then established controlled strategy mappings for three targets.

WP-059 showed:

```text
no additional target had sufficient historical evidence
to justify another IDENTITY_FIRST experiment
```

WP-060 now identifies an important reason for the evidence gap:

```text
most remaining categories
    ↓
lack target-level deterministic inventory infrastructure
    ↓
therefore lack target-level strategy evidence
```

The new finding is especially important because:

```text
16/17
```

appear technically capable of obtaining deterministic inventories.

This converts part of the problem from:

```text
unknown whether possible
```

to:

```text
technically feasible,
but requiring controlled production validation
```

That is real architectural progress.

---

# 16. What We Should NOT Do

Do not:

```text
enable all 16 categories now
```

Do not:

```text
add all 16 to the deterministic pilot scope
```

Do not:

```text
create IDENTITY_FIRST mappings merely because
a deterministic inventory exists
```

Do not:

```text
replace LLM target planning globally
```

Do not:

```text
treat inventory size as generation quality
```

Do not:

```text
introduce fuzzy entity normalization
```

Do not:

```text
create another weak IDENTITY_FIRST experiment
```

Do not:

```text
change the language policy
```

The language-policy issue is now being handled separately by WP-061.

---

# 17. Recommended Next Step

The next meaningful implementation step should be:

```text
ONE CATEGORY
→ deterministic target-planning pilot
→ small live generation sample
→ target-alignment validation
→ architectural review
```

The next category should be selected explicitly by the architect.

WP-060 should not be interpreted as pre-authorizing a particular category.

---

# 18. Category Selection Criteria

When selecting the next category, evaluate:

```text
source structure quality
inventory quality
expected generation value
category importance
risk
ability to validate
```

Do not select purely by:

```text
largest inventory
```

or:

```text
first alphabetically
```

The goal is to maximize the information gained from the next controlled pilot.

---

# 19. Relationship to Language Policy

WP-060 itself does not change language behavior.

However, future deterministic target-planning pilots must obey the now-authoritative project language policy.

That policy is:

```text
Question prose:
    Hebrew

Professional/technical item:
    English whenever an English representation exists

Hebrew:
    permitted only when no English representation exists

Whole-question English:
    NOT REQUIRED
```

The language-policy architecture alignment document explicitly establishes this as the project-wide invariant.

Therefore future category pilots must not independently redefine language behavior.

---

# 20. Final Architectural Decision

## WP-060 — ACCEPTED WITH DOCUMENTED LIMITATIONS

```text
Technical deterministic-inventory feasibility:
    16/17 remaining categories

Production readiness:
    NOT ESTABLISHED

Current deterministic production categories:
    unchanged

מבוא:
    LLM planning remains appropriate

New IDENTITY_FIRST mappings:
    NONE

Production target-planning changes:
    NONE

Recommended architecture:
    HYBRID

Recommended next step:
    ONE CATEGORY PILOT
```

---

# 21. Final Architecture State

```text
                    TARGET PLANNING
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
      Deterministic                LLM planning
      inventory                    with provenance
             │                         │
       validated pilot          categories without
       categories               safe deterministic
             │                   inventory
             └────────────┬────────────┘
                          ▼
                    target selection
                          ↓
                    generation
                          ↓
                    validation
```

Current production state remains:

```text
existing deterministic pilot categories
    → unchanged

remaining categories
    → current planning mode unchanged
```

Future deterministic expansion must occur:

```text
one category at a time
```

---

# 22. Final Verdict

**WP-060 is ACCEPTED WITH DOCUMENTED LIMITATIONS.**

The key architectural result is not merely:

```text
16 categories have extractable concepts
```

The more important result is:

> **The existing deterministic target-inventory mechanism appears structurally reusable across most of the remaining category corpus, but extractability alone is not enough to justify production rollout.**

Therefore the project should proceed with:

```text
ONE CATEGORY
→ ONE NARROW PILOT
→ REAL GENERATION
→ REAL VALIDATION
→ ARCHITECT REVIEW
```

rather than:

```text
16-CATEGORY ROLLOUT
```

and rather than another unsupported `IDENTITY_FIRST` experiment.

**WP-060: ACCEPTED.**

**Next architectural decision: select the single category for the first post-WP-060 deterministic target-planning pilot.**
