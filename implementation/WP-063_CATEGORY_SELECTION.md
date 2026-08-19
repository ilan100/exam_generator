# WP-063 Category Selection

## 1. Objective

Select exactly one additional canonical category to receive deterministic target-inventory planning (`PILOT_CATEGORIES`, `planning/concept_inventory.py`), per WP-060's own recommended "single-category narrow pilot" next step. This selection is made **before** any production code change, per WP-063 section 4's explicit ordering.

## 2. Candidate Pool

Per WP-063 section 4, the category must come from the 16 non-pilot categories WP-060 classified `SAFE_GENERALIZATION_POSSIBLE` (`implementation/WP-060_CATEGORY_TARGET_INVENTORY_FEASIBILITY_REPORT.md`). WP-060 itself already directly spot-checked three of those 16 for list-structured evidence quality beyond inventory size alone: `עצבים קרניאליים`, `המערכת הלימבית`, and `מערכת העצבים ההיקפית`. This selection re-verifies all three directly against the current repository state (fresh execution, not reuse of the WP-060 snapshot JSON alone) and evaluates them against WP-063's 9 required criteria, rather than picking by inventory size or list order.

## 3. Direct Re-Verification (OBSERVED)

`refine_concept_inventory()` (the real, unmodified, already-production function) was run directly against each candidate's real, freshly-retrieved student-summary evidence:

| Category | Retrieved chunks | Inventory size | Matches WP-060 snapshot |
|---|---:|---:|---|
| `עצבים קרניאליים` | 8 | 34 | Yes |
| `המערכת הלימבית` | 8 | 36 | Yes |
| `מערכת העצבים ההיקפית` | 8 | 15 | Yes |

All three reproduced exactly, confirming the mechanism remains deterministic and the WP-060 findings still hold.

## 4. Full Inventory Content Inspection (OBSERVED)

Full inventories were printed and inspected (not merely counted), per WP-063 section 8's explicit inspection list (duplicates, truncation, generic concepts, non-anatomical noise, weak concepts, ambiguity, unsupported concepts, category leakage, poor anchors).

**`עצבים קרניאליים` (34 concepts)**: mostly genuine, relevant cranial-nerve terminology (`Olfactory Nerve`, `Trigeminal`, `Vagus`, `Hypoglossal Nerve`, `Edinger-Westphal nucleus`, etc.), but with real, disclosed quality problems: (a) **near-duplicate forms of the same nerve** appear as separate concepts early in inventory order - `Optic` vs `Optic Nerve`, `Oculomotor` vs `Oculomotor Nerve`, `Cranial Nerves` vs `Cranial Nerves (CN)` vs `12 Cranial Nerves`; (b) **numbering-fragment junk entries**, a category-specific extraction artifact from the source's own cranial-nerve-numbering convention - `(3CN`, `(4CN`, `1CN`, `0 or CN N`, `Nerve` (bare), `Terminal` - six entries that are not testable concepts at all, starting around inventory position 23. A target-selection pass reaching that far into the list would assign a nonsense fragment (e.g. `"(3CN"`) as `target.topic`, a foreseeable, category-specific special case this WP-063 pilot would then have to absorb rather than measure.

**`המערכת הלימבית` (36 concepts)**: overwhelmingly clean, genuine named limbic-system entities (`Hippocampus`, `Amygdala`, `Fornix`, `Hypothalamus`, `Cingulate Gyrus`, `Parahippocampal Gyrus`, `Mammillary Body`, `Dentate gyrus`, etc.). Two minor, disclosed near-duplicate acronym forms (`ENT (entorhinal cortex)` / `(ENT)` / `Entorhinal Cortex`; `(DG)` / `Dentate gyrus`) - the same class of harmless alternate-form duplication already tolerated in the three existing pilot categories' own inventories, not a new problem class. A cluster of cortical-landmark terms (`Cingulate Sulcus`, `Paracentral Sulcus`, `Cuneus`, `Precuneus`, `Parieto-occipital sulcus`, `Occipitotemporal sulcus`) was directly checked against its source chunk text (not merely assumed to be leakage) - **confirmed genuine, on-topic evidence**: the retrieved chunk explicitly uses these landmarks to describe the boundaries of `Cingulate Gyrus`/`Parahippocampal Gyrus`/`Uncus`, core limbic structures, not leakage from an unrelated category. No numbering-fragment or nonsense-token entries were found anywhere in this inventory.

**`מערכת העצבים ההיקפית` (15 concepts)**: the smallest inventory, and the only one with a **directly confirmed category-leakage problem** - `Alvear path`, `Perforant path`, `Mossy fibers`, and `DG` are hippocampal/limbic-system terms, not peripheral-nervous-system terms, and `Australopithecus aafersnsi` is non-anatomical historical/paleoanthropology noise (misspelled in the source). Roughly a third of this small inventory is therefore either off-topic or non-anatomical.

## 5. Evaluation Against the 9 Required Criteria

| Criterion | `עצבים קרניאליים` | `המערכת הלימבית` | `מערכת העצבים ההיקפית` |
|---|---|---|---|
| 1. Source structure quality | Good, list-structured | Best - clean, list-structured, directly verified against source | Weakest - some leaked/foreign content |
| 2. Concept-inventory quality | Real noise: near-duplicates + 6 numbering-fragment junk entries | Best - minimal noise, no junk tokens | Weakest - real category leakage + non-anatomical noise |
| 3. Target distinctiveness | Good (12 individually named nerves) | Good (individually named structures: Hippocampus, Amygdala, Fornix, etc.) | Moderate, but confounded by leaked terms |
| 4. Deterministic-anchor quality | Same mechanism as pilot categories; degraded by junk entries | Same mechanism; no observed degradation | Same mechanism; degraded by leakage |
| 5. Expected usefulness for target-specific questions | High (well-known, individually testable nerves) | High (well-known, individually testable structures) | Moderate (small inventory, some entries untestable) |
| 6. Ability to validate target alignment objectively | Good - existing grounding/validators apply unchanged | Good - same | Good - same, but leaked concepts would fail grounding by construction, confounding the measurement |
| 7. Category importance (historical question volume, `HistoricalQuestionRepository.counts_per_category`) | **26** historical questions - highest of the three | **7** historical questions - lowest of the three | 13 historical questions |
| 8. Experimental information value | Confounded - a failure could be the mechanism or the numbering-fragment artifact, not cleanly separable | Cleanest - isolates the target-planning mechanism itself, least confounding | Confounded - a failure could be genuine leakage, not the mechanism |
| 9. Low risk of category-specific special cases | Real, disclosed risk (numbering-fragment junk) | Lowest observed risk | Real, disclosed risk (leakage) |

## 6. The One Genuine Trade-off

`עצבים קרניאליים` has substantially more historical exam volume (26 vs. `המערכת הלימבית`'s 7), a real, honestly-weighed consideration under criterion 7. This is **not treated as decisive**: WP-063 section 4 explicitly warns against selecting "merely by inventory size" and requires weighing all 9 criteria together, and this WP's own purpose is a controlled experiment measuring the *target-planning mechanism itself* - a category whose own inventory carries a disclosed, category-specific extraction defect (numbering-fragment junk tokens that a live 4-question sample has a real chance of reaching, given the deterministic first-occurrence target-selection order) would risk conflating a corpus-specific extraction bug with the mechanism's own merit, exactly the confound criterion 8 asks to avoid. `מערכת העצבים ההיקפית`'s directly-confirmed category leakage is a comparable, independent reason to exclude it. Neither rejected alternative is disqualified by a close call requiring architect input - both lose to `המערכת הלימבית` on a majority of criteria (7 of 9) and on the specific criteria (2, 8, 9) most relevant to running a clean, interpretable pilot experiment, so no `STOP` condition (WP-063 section 4) applies here.

## 7. Selected Category

**`המערכת הלימבית`** (the Limbic System).

## 8. Rejected Alternatives

- **`עצבים קרניאליים`**: rejected due to a real, disclosed, category-specific inventory-extraction defect (numbering-fragment junk entries from the source's own cranial-nerve-numbering convention) that would confound the experiment, despite its higher historical importance.
- **`מערכת העצבים ההיקפית`**: rejected due to a directly-confirmed category-leakage problem (hippocampal/limbic terms and non-anatomical noise present in its own inventory) and its small inventory size (15).

## 9. Selection Rationale

`המערכת הלימבית` has the cleanest, most directly-verified evidence structure of the three spot-checked candidates: a 36-concept inventory of genuine, individually-named limbic structures, no numbering-fragment or nonsense-token entries, and its one apparent ambiguity (a cluster of neighboring cortical-landmark terms) was directly checked against source text and confirmed to be genuine, on-topic evidence rather than leakage. It is a core, established neuroanatomy subsystem (not a peripheral or administrative category, unlike `מבוא`), comparable in structural kind to the three already-piloted categories. Its lower historical question volume (7) is a disclosed, accepted cost of prioritizing a clean, low-confound experimental read over raw curricular importance for this specific, narrow pilot - consistent with WP-060's own conclusion that no specific category was recommended and selection should weigh evidence quality, and consistent with this WP's own purpose (measure the mechanism, not maximize curricular coverage in one step).
