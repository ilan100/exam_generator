# WP-035 Architecture Investigation — Concept Ownership Investigation

**Type:** Investigation only. No production code was modified. All measurements were performed by read-only scripts run against the real, already-built retrieval index and the real production `CategoryResolver`/`FactualRetrievalIndex`/`retrieve_for_category()` pipeline (`src/exam_generator/retrieval`, unchanged) - never a shortcut or synthetic corpus. No LLM call was made anywhere in this investigation; every measurement below is fully reproducible offline, without `OPENAI_API_KEY`.

## Question

**Can concept selection be owned by the application instead of the LLM?**

**Short answer: Partially, and only for a minority of categories with clean list-structured source material - but even there, "owned" should mean *constraining what the planner can choose from*, not merely *informing* it, which is exactly what WP-034 already showed does not work.** For the majority of categories, the source material does not contain a reliably parseable inventory of discrete concepts, so full deterministic ownership is not currently achievable without either new preprocessing investment or accepting materially lower granularity than the LLM currently provides.

---

## 1. Method

Real student-summary evidence was retrieved (offline, using the exact production TF-IDF retrieval pipeline, zero LLM calls) for three representative categories, per section 3's own requirement:

| Category | Label | Why chosen |
|---|---|---|
| `מסילות עצביות` (neural tracts) | content-rich | Multiple distinct named entities (tracts) with parallel structure across chunks |
| `מבוא` (introduction) | weak | Lowest retrieval confidence scores (top score 0.088 vs. 0.377-0.430 for the other two); generically-named category |
| `אספקת דם` (blood supply) | known diversity problem | The exact category that duplicated on "Superior Cerebellar Artery" in every one of WP-032/033/034's live evaluations |

8 chunks were retrieved per category (the production `top_k` default). Every chunk quoted below is real corpus text, not paraphrased or reconstructed.

## 2. Candidate Concept Study (Section 3)

### 2.1 `מסילות עצביות` (content-rich) - concepts ARE cleanly extractable here

The top-scoring chunks are structured as bullet/numbered lists of capitalized, multi-word English tract names, repeated near-verbatim across at least three different source PDFs:

```
מסילות עולות:
  o Medial Lemniscus Tract
  o Spinothalamic Tract

מסילות יורדות (Descending Tracts):
  o Corticobulbar (=Corticonuclear) Tract
  o Corticospinal Tract
      - Lateral Corticospinal Tract
      - Anterior Corticospinal Tract
```

Six distinct named tracts are identifiable this way, appearing consistently across `student_summary_1.pdf`, `student_summary_2.pdf`, and `student_summary_3.pdf`, always as capitalized English proper-noun phrases set off from surrounding Hebrew prose (either by bullet markers `o`/numbers, or simply by capitalization against Hebrew text). **This is the best case observed**: a genuinely list-structured category where a simple heuristic (capitalized multi-word English phrase, optionally following a bullet/list marker) would reliably recover the concept inventory.

### 2.2 `מבוא` (weak) - concepts exist but retrieval is noisier

Despite its low retrieval confidence, the top chunk is itself a clean historical list:

```
Edwin Smith Papyrus (1600 BC) - first written record of the word "brain"
Aristotle - brain as a cooling system
Galen - identified some brain functions via battlefield injuries
Andreas Vesalius - founded the dissection theater
Santiago Ramón y Cajal ("סנטיאגו רמון קחל") - stained neural tissue
Korbinian Brodmann ("קורבניאן ברודמן") - cortical layer-based area mapping
```

Six distinct named historical figures/facts, each independently testable - **and yet all four live evaluation runs (WP-032 through WP-034) that touched this category converged on the same one (Edwin Smith Papyrus)**, every time. This is direct, concrete evidence that the diversity problem is not "insufficient distinct concepts exist" - the concepts were there in the very first retrieved chunk. The problem is *selection*, not *availability*.

A second, lower-confidence chunk (`student_summary_2.pdf:0002`) covers a completely different sub-topic (nervous-system evolution: Foramen Magnum, brain-volume increase, *Australopithecus afarensis*/"Lucy") - more usable concepts, further confirming availability isn't the bottleneck. A third, even-lower-confidence chunk (`student_summary_3.pdf:0080`) is actually about a *different* category's content ("מבוא למיפוי מוחי" - introduction to brain mapping, which belongs under `מיפוי ודימות מוחי`) that TF-IDF retrieval pulled in because "מבוא" (introduction) is a generic word appearing as a subsection header across many unrelated chapters - a genuine retrieval-precision limitation specific to generically-named categories, which any concept-extraction approach inherits (garbage in, garbage out).

### 2.3 `אספקת דם` (known diversity problem) - the richest evidence set, and the clearest explanation for the observed convergence

This category's evidence contains at least **10 distinct named arteries** across its 8 chunks: Superior Cerebellar Artery, AICA, PICA, Anterior Spinal Artery, Posterior Spinal Artery, Vertebral Artery, Basilar Artery, PCA, MCA, ACA, Communicating Artery, Ophthalmic Artery, Superior/Inferior Hypophyseal Artery, Anterior Choroidal Artery, Posterior Choroidal Artery, Labyrinthine Artery, Pontine Arteries. Diversity is not remotely a content-availability problem here.

**But the chunk that actually drives the repeated convergence is identifiable, and it explains the failure precisely**: the single highest-scoring chunk (score 0.430) is nearly *empty* - a page-header fragment ("מבנה המוח– אספקת הדם למערכת העצבים המרכזית... נל רכבי 11") with no substantive content at all. The **second**-highest chunk (score 0.264) is a tight, cleanly-structured 3-item list:

```
עורקים מספקים דם לצרבלום (arteries supplying the cerebellum):
  Superior Cerebellar Artery - source: Basilar Artery; supplies: superior cerebellar surface, ...
  Anterior Inferior Cerebellar Artery (AICA) - source: Basilar Artery; supplies: ...
  Posterior Inferior Cerebellar Artery (PICA) - source: Vertebral Artery; supplies: ...
```

Notably, this chunk's own page header reads **"המוח הקטן, צרבלום" (cerebellum)** - it is not even primarily filed under the blood-supply chapter; it is a "blood supply to the cerebellum" subsection embedded inside the *cerebellum* chapter of the source PDF, retrieved into the `אספקת דם` category only because the subsection heading itself contains "אספקת דם." The remaining, more clearly on-topic chunks (anterior/posterior circulation, spinal arteries, Circle of Willis - chunks 3/4/6/7) are longer, denser, and structurally messier (see Section 6 below on PDF-extraction corruption), and this exact 3-artery list is independently repeated in a *second*, unrelated source PDF (`student_summary_1.pdf:0043`, chunk 8) with near-identical wording - meaning it is the single most redundantly-repeated, most compactly-structured, most confidently-scored substantive fact in the entire evidence set for this category. **The repeated LLM convergence on "Superior Cerebellar Artery" is not evidence of a lazy or unaware model - it is exactly what a "pick the strongest, cleanest, most corroborated evidence" strategy would produce**, consistent with WP-034's own architecture review's diagnosis ("the model is following the strongest evidence available rather than optimizing long-term educational coverage").

## 3. Candidate Extraction Strategies (Section 4)

| # | Approach | Complexity | Expected accuracy | Runtime cost | Maintainability | LLM dependence | Hebrew suitability | Architecture fit |
|---|---|---|---|---|---|---|---|---|
| A | Pure deterministic parsing (regex/rule-based over raw chunk text) | Low-medium | **Low-medium, uneven** - reliable for capitalized-English-phrase lists (§2.1/§2.3), unreliable for Hebrew-only prose (see §6 on RTL/LTR corruption) | Negligible (pure Python, no I/O) | Medium - rules need per-category tuning as corpus quirks surface | None | **Uneven** - strong for English proper nouns embedded in Hebrew text (the dominant case for named anatomical structures in this corpus), weak for pure-Hebrew concept phrases | Fits cleanly as a new deterministic module, same pattern as `generation/relationship.py`/`generation/competitors.py` |
| B | Heading-based extraction (structural markers: bullets `o`/`•`, numbered lists `1.`/`2.`, indentation) | Medium | **Medium-high where markers survive extraction** - both §2.1 and §2.3's best chunks are marker-delimited lists; degrades sharply on chunks where the source PDF's visual structure was lost during text extraction (common - see §6) | Negligible | Medium-high - marker patterns are corpus-format-specific and would need revalidation if new source PDFs are added | None | Same strength profile as A, slightly better since markers are format signals independent of language | Same fit as A |
| C | Repeated noun-phrase extraction (frequency/n-gram based, no external NLP model) | Medium-high | **Uncertain without implementation** - would need Hebrew-aware tokenization; the corpus's dominant "concepts" are proper nouns (mostly English), which frequency-based extraction over mixed-language, corrupted text would likely both over- and under-match | Low-medium (pure computation, no I/O, but more CPU than A/B) | Lower - statistical thresholds are corpus-dependent and opaque to reason about | None | **Weakest fit** - Hebrew morphology (prefixes, construct forms) makes naive n-gram frequency counting unreliable without a Hebrew-specific tokenizer/lemmatizer, which is a new dependency this project does not currently have | Would require a new dependency; higher risk than A/B |
| D | Offline corpus preprocessing (a one-time or periodic batch job producing a concept inventory file, independent of per-request retrieval) | Medium-high (one-time) | Same ceiling as whichever extraction technique the batch job uses (A/B/C/E) - the "offline" part is a *deployment* strategy, not an accuracy improvement in itself | **Zero at request time** (the expensive part is amortized offline) - the strongest option if extraction itself turns out to be at all costly | **Higher long-term burden** - the inventory must be regenerated whenever source PDFs change, and drift between the live corpus and a stale inventory is a real, silent-failure risk | None (assuming A/B/C underneath) | Inherits whatever technique is chosen | Requires a new artifact (the inventory file) and a new build/regeneration step - the first approach here that meaningfully changes the project's operational surface, not just its code |
| E | Small, application-maintained concept inventory (a hand-curated list per category, checked into the repo like `config/category_mapping.yaml` already is) | Low (to build initially, once per category) | **Highest per-category accuracy for the categories it covers** - a human already knows "אספקת דם" has ~15 distinct arteries; encoding that directly sidesteps every extraction-reliability question above | Negligible at request time | **Highest ongoing burden** - stops scaling once the corpus changes (new PDFs, new categories) or the number of categories grows; every future work package touching evidence would also need to remember to touch this file | None | N/A - hand-curated, so language is not an obstacle | Cleanest immediate fit (a static data file, exactly like `category_mapping.yaml`), but the least architecturally honest long-term - it reintroduces a human-maintained ground truth the rest of this project has deliberately avoided everywhere else (the project's whole trajectory since WP-020 has been *away* from hand-authored domain knowledge and *toward* deriving everything from the actual evidence) |
| F | Hybrid: heading/bullet-based extraction (B) as the primary signal, falling back to leaving a chunk's content un-extracted (not guessed at) when no structural marker is found | Medium | **Best realistic ceiling given the evidence observed**: high precision (only extracts where structure clearly exists, matching this project's established "never fabricate, prefer honest absence" philosophy - e.g. `UNSPECIFIED_RELATIONSHIP_TYPE`, `NO_COMPETITOR_CONCEPTS_TEXT`), at the cost of leaving prose-only chunks contributing nothing to the inventory | Negligible | Medium - same marker-fragility concern as B, but the honest-fallback design means a maintainer only needs to *add* new marker patterns as gaps are found, never fix incorrect guesses | None | Same as B for the marker-covered portion; the fallback (skip, don't guess) removes the failure mode of C entirely | Best architectural fit of the six - directly extends the project's existing deterministic-extraction pattern (WP-030/031) rather than introducing a new paradigm |

**Evidence-grounded takeaway**: strategies A/B/F all work reasonably well on `מסילות עצביות` and the cerebellum-arteries sub-chunk of `אספקת דם` - both are marker-delimited English-name lists. None of them would reliably extract concepts from `מבוא`'s prose-heavy paragraphs once past the first, cleanly-listed chunk, or from the corrupted-text regions observed throughout (Section 6). Strategy C was not empirically tested (it would require writing and running a Hebrew tokenizer, out of this investigation's read-only scope) but is judged the weakest fit for the reasons in the table. Strategy E was rejected on architectural-philosophy grounds even though it would "work" - see Section 8.

## 4. Existing Data (Section 5)

Every existing model that touches "what a question is about" was examined for whether it already constitutes a deterministic concept identity:

| Model | Deterministic? | Suitable as a concept-identity source? |
|---|---|---|
| `QuestionTarget.topic`/`.factual_focus` (WP-025) | **No** - both are free-text fields *generated by the target-planning LLM call itself* | No - this is exactly the thing under investigation, not a source of truth for it. Using it to define "concepts" would be circular (the LLM's own uncontrolled output would define the constraint meant to control the LLM). |
| `QuestionRelationship.relationship_type` (WP-030) | **Yes** - `classify_relationship_type()` is a pure keyword classifier over already-existing text | Only relationship *type* (one of ~10 coarse categories: SUPPLIES, CONNECTS, CONTAINS, ...), not concept *identity*. Useful as one signal, not sufficient alone - "SUPPLIES" appears for both the cerebellum-artery chunk and the CNS-circulation chunks, so it cannot by itself distinguish "Superior Cerebellar Artery" from "MCA." |
| `CompetitorCandidate.concept` (WP-031) | **Yes** - a deterministic, fixed-width text-window extraction around a keyword match (`_extract_snippet()`, `generation/competitors.py`) | **The closest existing precedent to what a concept-extraction mechanism would need to look like** - already proves the project has working infrastructure for "find a deterministic text snippet describing something evidence-adjacent." Its current scope (finding *other* passages sharing the target's own relationship, only within already-retrieved evidence, only after a target is already chosen) is narrower than "enumerate every concept in a category up front," but the underlying technique (keyword-anchored snippet extraction) is directly reusable. |
| `SourceEvidenceChunk.text` (retrieval, WP-006) | Yes (raw, unstructured) | Necessary but not sufficient - this is the raw material every strategy in Section 3 would operate on; it is not itself a concept list. |
| `CandidateQuestion`/`ExamQuestion` question text | Yes (raw, unstructured) | This is what WP-034's `extract_category_coverage()` already uses (correct-answer text as a "tested concept") - deterministic, but coarse (one string per already-generated question, not a structured entity). |
| `CategoryCoverage` (WP-034) | Yes | Already exists, already deterministic, already wired into planning as *information*. WP-034's finding is precisely that this is insufficient on its own (Section 5 above explains why, with a concrete mechanism: the "already tested" facts remain visible and dominant in the same evidence the planner also sees). |

**Conclusion**: existing data is **not sufficient** for deterministic concept ownership today. `QuestionRelationship` and `CompetitorCandidate` are useful *building blocks* (both already deterministic, already evidence-derived, already proven in production), but neither identifies discrete named concepts within a category's evidence. That capability does not exist anywhere in the current codebase and would need to be built (Section 3's strategies) if this direction is pursued.

## 5. Coverage Simulation (Section 6)

Using `אספקת דם` (the category with the richest, most concretely-understood evidence) and WP-034's own real acceptance-run data (`evaluation/live_outputs/wp034_acceptance_records.json`), a manual, non-production-code simulation of deterministic coverage tracking:

**Step 0 - deterministic concept inventory** (manually extracted from Section 2.3's evidence, simulating what Strategy F would plausibly produce):
```
{Superior Cerebellar Artery, AICA, PICA, Anterior Spinal Artery, Posterior Spinal Artery,
 Vertebral Artery, Basilar Artery, PCA, MCA, ACA, Communicating Artery, Ophthalmic Artery,
 Superior Hypophyseal Artery, Inferior Hypophyseal Artery, Anterior Choroidal Artery,
 Posterior Choroidal Artery, Labyrinthine Artery}
```
17 distinct concepts identified by inspection - all clearly present in the evidence, all extractable by Strategy B/F (each is a bulleted or numbered capitalized English term).

**Step 1 - Question 1 generated** (as actually happened in WP-034's real run): correct answer = "Superior Cerebellar Artery." **Mark as tested.** Remaining candidate set: 16 concepts.

**Step 2 - Question 2**: if target selection were constrained to draw only from the **remaining 16** (rather than merely being *told* Superior Cerebellar Artery was already used, as WP-034 actually did), the model could not have re-selected it - a hard exclusion, not a soft preference. This is the structural difference WP-034's own architecture review identified (Section 6/7 of that review) and this simulation confirms is mechanically achievable: excluding one item from a known 17-item list is trivial set arithmetic, requiring no LLM judgment at all for the exclusion step itself (the LLM would still be needed to phrase a *question* about whichever remaining concept is chosen, and to determine which of the 16 the *evidence actually supports well enough* for a clean single-answer question - a real, separate difficulty explored in Section 7 below).

**Step 3 - Question 3, 4, ...**: the same mechanism continues, concept set shrinking by one (or more, if a single question's correct answer maps to multiple listed concepts) each round.

**Feasibility verdict**: deterministic coverage *tracking* is straightforward once a concept inventory exists (this is exactly the "mark tested / remaining concepts" bookkeeping `CategoryCoverage` already does at the level of whole correct-answer strings - Section 4 above). The genuinely hard, **not yet solved** part is producing the inventory itself reliably across all 20 categories, and - a subtlety this simulation surfaces that the WP's own framing does not fully anticipate - **not every remaining concept is equally well-evidenced for question generation**. Several of the 16 "remaining" arteries above (e.g. `Superior Hypophyseal Artery`, `Inferior Hypophyseal Artery`) have only a single terse sentence of supporting evidence each; forcing target selection onto one of these without also checking evidence-sufficiency could trade the diversity problem for a new grounding-failure problem (more `QuestionAttemptsExhaustedError`s), which would show up as exactly the kind of regression already seen in WP-034's own acceptance run (33/40 vs. WP-032's 36/40).

## 6. Interaction with Current Architecture (Section 7)

| Component | Change needed under a "concept-constrained planning" architecture? |
|---|---|
| `CategoryQuestionSetService`/`CategoryGenerationService` (`category_generation/`) | **Unchanged** - still receives `existing_questions`, still calls `plan_targets(coverage=...)`; the shape of what `coverage` carries would need to grow (from "tested concepts as strings" to "tested + remaining concept inventory"), but the service's own control flow (`_run_generation_cycle()`) would not change |
| `QuestionTargetPlanner.plan_targets()` | **Would need extension** - currently accepts `coverage: CategoryCoverage` as *prompt input only*; a concept-constrained design would need it to also accept (or internally look up) a *candidate set* to constrain generation/selection against, and a policy for what happens when the candidate set is exhausted (mirrors today's already-existing `InsufficientDistinctTargetsError` question-local-failure path - a natural, already-proven extension point, not a new failure mode) |
| Relationship extraction (`generation/relationship.py`) | **Unchanged** - `classify_relationship_type()` already operates on arbitrary text; would be directly reusable for classifying entries in a new concept inventory too, exactly as WP-034 already reused it |
| Competitor discovery (`generation/competitors.py`) | **Unchanged in mechanism**, likely reusable as the extraction primitive itself - `_extract_snippet()`'s keyword-anchored window technique is a strong candidate implementation for whatever "find named concepts in evidence" function a future WP would need to write (Section 4 above) |
| Validators (grounding/MCQ/category/quality/textbook) | **Unchanged** - concept constraint happens strictly before generation; validators continue to see only the final candidate question, exactly as today |
| Retry mechanisms (WP-013 attempt budget, WP-014 duplicate replacement) | **Unchanged** - these operate after a target is chosen, regardless of how the target was chosen |
| Retrieval (`exam_generator.retrieval`, TF-IDF) | **Unchanged in mechanism** - a concept inventory would be built as a deterministic **read** over already-retrieved chunks (the exact same `retrieve_for_category()` call already made for planning), not a new retrieval query or index |
| Request/response contracts (`CategoryQuestionSetRequest`/`Response`) | **Unchanged** - a concept inventory is derivable entirely from information the contract already carries (`category` → retrieval → evidence; `existing_questions` → tested concepts), so WP-033's stable contract would not need a new field, consistent with WP-034's own precedent |

**Summary**: the components that would need to change are narrowly confined to the planning layer (`planning/`) - exactly where WP-034's own changes already live. Nothing downstream of target selection (generation, validation, retry, output) would be touched, and nothing about the public API would change. This is a favorable finding: the blast radius of attempting this direction is small and well-isolated, regardless of which extraction strategy is eventually chosen.

## 7. Risks (Section 8)

| Risk | Evidence from this investigation |
|---|---|
| **Insufficient corpus structure** | Directly observed - `מבוא`'s later, lower-confidence chunks and most Hebrew prose paragraphs (see below) lack any reliable structural marker; extraction there would either miss real concepts or require accepting much lower recall than the `מסילות עצביות`/`אספקת דם` best-case chunks showed |
| **Hebrew/English PDF-extraction corruption** | Directly observed in the retrieved text - e.g. `student_summary_3.pdf:0148` renders as `"ר ה א י ש ה ת ת... כ תחושו עולו..."`, clearly bidi/word-order-scrambled Hebrew, likely from mixed-direction (Hebrew RTL + English LTR + numerals) content colliding during PDF text extraction (WP-004, unrelated to this investigation - a pre-existing, already-known corpus characteristic). English proper-noun phrases (the arteries, tracts, historical names) consistently survive this corruption intact, since they are short, unidirectional runs; surrounding Hebrew explanatory prose frequently does not. This is strong evidence *for* strategies that key on capitalized-English-phrase structure (A/B/F) and *against* anything depending on parsing full Hebrew sentences (C, and any future distinguishing-facts work operating on prose) |
| **Synonym/naming-variant handling** | Observed directly: the same artery appears as `Superior Cerebellar Artery`, `superior cerebellar artery`, and (once) `SCA` across different chunks/PDFs; `Posterior Inferior Cerebellar Artery` also appears abbreviated `PICA` and reordered `"Inferior Cerebellar Artery (PICA) Posterior"` (a PDF-extraction word-order artifact, not a real variant). A concept inventory would need at least case-insensitive matching and would benefit from abbreviation-awareness; without it, `AICA` and `Anterior Inferior Cerebellar Artery` would incorrectly count as two different concepts, undermining the exclusion mechanism in Section 5 |
| **Hebrew terminology** | Most named concepts observed across all three categories were **English** terms embedded in Hebrew prose (anatomical/medical convention), not Hebrew terms - somewhat mitigating the Hebrew-NLP-tooling gap this project has (no lemmatizer/tokenizer dependency today), but not eliminating it: Hebrew-only concepts do exist (e.g. `מבוא`'s "אבולוציה של מערכת העצבים" sub-topics have partially-Hebrew phrasing) and would be extracted with lower confidence by any English-leaning heuristic |
| **Concept granularity** | Not resolved by this investigation, and genuinely ambiguous from the evidence alone: is "Superior Cerebellar Artery" one concept, or is "arteries supplying the cerebellum" (the whole 3-item list) one concept with three instances? The `אספקת דם` category's evidence supports either framing, and the choice materially affects how aggressively coverage exclusion would narrow future targets. This is a design decision a future implementation WP would need to make explicitly, not something Section 3's strategies resolve on their own |
| **Maintenance burden** | Strategy E (hand-maintained inventory) has the highest, clearest burden (Section 3). Strategies A/B/F have a real but lower burden: marker patterns would need occasional revalidation if new source PDFs are added (WP-004/005's existing corpus-ingestion pipeline is unchanged and would not automatically flag a pattern regression) |
| **Ambiguous concepts** | The evidence-sufficiency concern raised in Section 5 (some remaining concepts have only thin supporting text) is itself a risk: constraining the planner toward a thinly-evidenced concept could increase `QuestionAttemptsExhaustedError`/grounding-rejection rates, trading a diversity problem for a reliability regression - exactly the kind of trade-off WP-034's own acceptance run already showed is easy to hit accidentally (accepted count fell from 36/40 to 33/40 even under WP-034's much gentler, information-only change) |

## 8. Recommendation (Section 9)

**C. Hybrid deterministic extraction** (Strategy F from Section 3, applied selectively) - **but explicitly scoped as a future implementation WP's decision, not something this investigation authorizes building now.**

Reasoning, weighing the evidence above:

- **Option D ("Remain with LLM planning") is not supported by the evidence.** WP-034 already showed that informing the LLM is insufficient, and Section 2's real-evidence study shows the LLM's convergence is a rational consequence of evidence salience/redundancy, not a wording problem a better prompt would fix. Staying with pure LLM planning means accepting the diversity ceiling WP-032/033/034 already measured (~41-47% DISTINCT), indefinitely.
- **Option A ("application-owned concept inventory," i.e. Strategy E) is not recommended**, despite being the fastest to build and highest-precision for the categories it would cover. It reintroduces exactly the kind of hand-maintained domain knowledge this project has deliberately moved away from since WP-020 ("move intelligence from prompts into deterministic application logic" has consistently meant *derived from evidence*, never *hand-authored*, in every WP from WP-025 through WP-034). It also does not scale: 20 categories today, each needing its own curated list, with no mechanism to detect drift if the underlying student-summary PDFs change.
- **Option B ("offline preprocessing") is an implementation/deployment detail, not a distinct extraction strategy** - it would be the right way to *ship* whichever technique (A/B/F) is chosen if per-request extraction cost turns out to matter, but Section 3's cost analysis suggests it currently would not (pure-Python text scanning over already-retrieved, already-in-memory chunks is negligible compared to the LLM calls already being made). This should be revisited only if a future WP's implementation shows measurable per-request extraction cost, not decided speculatively now.
- **A hybrid, structure-first, honest-fallback approach (extract only where clear structural markers exist; never guess at unstructured prose) is the only option consistent with both the evidence in Section 2 (structure survives corruption; prose often does not) and this project's established fail-honest philosophy** (`UNSPECIFIED_RELATIONSHIP_TYPE`, `NO_COMPETITOR_CONCEPTS_TEXT`, `InsufficientDistinctTargetsError` never fabricating - see `docs/ARCHITECTURE.md`'s repeated "never fabricate" language across WP-025/030/031/033).

**However**, this recommendation comes with an explicit caveat the evidence itself demands: concept EXTRACTION being feasible (Section 2/3) does not by itself guarantee concept CONSTRAINT would fix diversity without new side effects (Section 5's evidence-sufficiency concern, Section 7's granularity/synonym risks). A future implementation WP pursuing this direction should be scoped narrowly - e.g. a focused pilot on 2-3 categories with clean list structure (`מסילות עצביות`, `אספקת דם`, and one or two similarly-structured others), measuring both diversity **and** acceptance-rate impact together, before any broader rollout - mirroring exactly the incremental, measure-before-expanding discipline WP-025 through WP-034 have already established as this project's working method.

## 9. What This Investigation Does Not Answer

- Whether granularity should be "one artery = one concept" or "one list = one concept" (Section 7) - needs an explicit design decision informed by live evaluation, not resolvable from static evidence alone.
- Whether a synonym/abbreviation-normalization step (Section 7) is worth its own complexity, or whether case-insensitive exact matching is sufficient in practice - would need to be measured against a larger sample than this investigation's 3 categories.
- Whether extraction accuracy holds up across all 20 categories, not just the 3 studied here (chosen specifically as a content-rich/weak/known-problem spread, not a random or exhaustive sample).

---

WP-035 complete.

Investigation complete.

Report:
implementation/WP-035_ARCHITECTURE_INVESTIGATION.md

Waiting for architect review.
