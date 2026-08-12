# Architectural Decision Point After WP-040

## Main Problem

The main problem requiring a decision is no longer question generation.

WP-040 essentially solved target alignment.

The remaining problem is:

> **How can the system recognize that a generated answer represents the same concept as the selected concept when they are written in different languages/scripts — without introducing unsafe semantic or fuzzy matching?**

This matters because the system uses coverage to decide which concepts have already been tested.

---

## Concrete Example 1 — Corpos Striatum

The planner selects:

```text
Corpos Striatum
```

WP-040 now generates a correctly targeted question whose answer is:

```text
קורפוס סטריאטום
```

This is a good result. The answer identifies the selected concept, just in Hebrew.

However, the stored concept is:

```text
Corpos Striatum
```

and the coverage mechanism cannot deterministically establish that:

```text
Corpos Striatum
```

and:

```text
קורפוס סטריאטום
```

represent the same concept.

Therefore it effectively concludes:

```text
Corpos Striatum ≠ קורפוס סטריאטום
```

and the planner is allowed to select `Corpos Striatum` again.

This is what happened in WP-040: in the `גרעיני הבסיס` category, all four questions correctly targeted `Corpos Striatum`, but the concept was not recognized as already covered.

---

## Concrete Example 2 — Superior Cerebellar Artery

The selected concept is:

```text
Superior cerebellar artery
```

Generation produced correct target answers such as:

```text
עורק צרבלרי עליון
```

and:

```text
עורק סופריור צרבלרי
```

Both were manually judged to correctly identify the selected concept.

But the stored concept is:

```text
Superior cerebellar artery
```

The deterministic coverage system therefore cannot safely conclude that the Hebrew forms are the same canonical concept.

The result can again be repeated selection of the same concept.

---

## Why This Is Difficult

There are several tempting solutions, but each has architectural consequences.

### 1. Transliteration

We could try to convert:

```text
קורפוס סטריאטום
```

into something like:

```text
Corpus Striatum
```

and compare them.

The problem is that real generated Hebrew representations are not necessarily simple transliterations. The same concept can have different translations, transliterations, or mixed forms.

Therefore this can become increasingly complex and approximate.

---

### 2. Fuzzy Matching

We could say:

```text
if two strings are sufficiently similar:
    consider them the same concept
```

This is dangerous.

For example:

```text
Anterior cerebral artery
Anterior communicating artery
```

or:

```text
Medial lemniscus
Medial longitudinal fasciculus
```

are related anatomical terms but are not the same concept.

A permissive matcher could incorrectly mark a legitimate concept as already covered.

A false positive is worse than a false negative here.

---

### 3. Ask an LLM

We could ask an LLM:

```text
Are "Corpos Striatum" and "קורפוס סטריאטום"
the same anatomical concept?
```

This would probably work often, but it introduces nondeterminism into a mechanism that is currently deliberately deterministic.

The result could become:

```text
LLM says same
    → concept excluded

LLM says different
    → concept selected again
```

That is a significant architectural change and conflicts with the current fail-closed philosophy.

---

### 4. Maintain a Bilingual Terminology Dictionary

We could explicitly maintain mappings such as:

```text
Corpos Striatum
    ↔
קורפוס סטריאטום

Superior cerebellar artery
    ↔
עורק צרבלרי עליון
    ↔
עורק סופריור צרבלרי
```

This would be deterministic if the mappings were authoritative.

But it raises a new architectural question:

> Who provides and maintains the authoritative terminology?

For a large medical domain, this could become a substantial external knowledge resource rather than a small algorithmic change.

WP-038 already established that the current evidence corpus does not provide enough explicit bilingual pairing to derive such mappings safely.

---

# Why This Is Now the Main Problem

The latest pilot gives us a very clear comparison.

### מסילות עצביות

The system produced:

```text
Spinothalamic Tract
Medial Lemniscus Tract
Anterior Corticospinal Tract
Lateral Corticospinal Tract
```

Four different concepts were successfully selected and tested.

The answers used representations that coverage could recognize.

### גרעיני הבסיס

The system produced:

```text
Corpos Striatum
Corpos Striatum
Corpos Striatum
Corpos Striatum
```

The generation itself was correct every time.

The problem was that the correct answers were Hebrew representations, so coverage did not recognize them as the already-covered English concept.

Therefore:

> **Generation is no longer the reason for the poor rotation.**

The remaining problem is concept identity across languages/scripts.

---

# What Has Already Been Solved

The project has now isolated the major layers:

```text
Concept extraction          ✓
Trailing truncation         ✓
Concept identity            ✓ within supported representation
Concept selection           ✓
Evidence anchoring          ✓
Target-aware generation     ✓
Target alignment            ✓ 100% in WP-040
Validation/reliability      ✓ 11/12
```

The remaining problem is:

```text
Generated aligned answer
        ↓
Cross-language identity recognition
        ↓
Coverage update
```

That is why this decision is important now.

---

# The Architectural Decision

The question is not simply:

> "Should we make matching smarter?"

The real question is:

> **How much are we willing to change the deterministic/fail-closed architecture in order to support multilingual concept identity?**

There are two legitimate positions.

## Option A — Keep the Current Deterministic Model

Accept:

> If the answer is expressed in a representation that the deterministic identity system cannot recognize, the concept may be selected again.

Advantages:

- deterministic;
- safe;
- no false concept merging;
- no LLM dependency;
- no fuzzy matching;
- no terminology database.

Disadvantage:

- concept diversity can be poor in multilingual categories.

---

## Option B — Introduce an Authoritative Concept-Identity Mechanism

Find a genuinely deterministic and authoritative source for multilingual identity.

For example, an authoritative terminology resource could explicitly establish:

```text
Corpos Striatum
    =
קורפוס סטריאטום
```

Advantages:

- potentially supports multilingual rotation;
- can remain deterministic if the source is authoritative.

Disadvantages:

- additional architecture/data;
- maintenance;
- provenance questions;
- potentially significant scope.

Importantly, fuzzy matching or an LLM should not be treated as equivalent to an authoritative terminology source.

---

# Recommendation

I recommend **not immediately implementing multilingual matching**.

We have reached a valuable architectural point where the system is now understandable:

- Concept extraction: working.
- Concept identity within the same representation: working.
- Concept selection: working.
- Evidence anchoring: working.
- Target alignment: working at 100% in WP-040.
- Validation/reliability: stable at 11/12.
- Remaining major issue: cross-language concept identity.

WP-038 already investigated the obvious unsafe approaches.

Therefore the next step should be a **short architectural investigation and product decision**, not another implementation WP.

The question should be:

> **Is multilingual concept identity a hard product requirement, and if yes, what authoritative source can provide deterministic bilingual identity?**

If the answer is **yes**, design that mechanism properly.

If the answer is **no**, explicitly document the limitation and move toward broader evaluation rather than continually adding complexity.

---

# Current Architectural Position

The desired pipeline is now:

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

The only unresolved major step in the current pilot is:

```text
Aligned Question
       ↓
Cross-language Concept Identity
       ↓
Coverage Update
```

This is the architectural decision point reached after WP-040.
