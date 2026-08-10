# WP-036 Completion Report — Deterministic Concept Inventory Pilot

## 1. Objective and Scope

WP-035 (investigation only) concluded that deterministic concept ownership is technically feasible for categories with clean, list-structured evidence, and recommended a narrow, measured pilot before any broader rollout. WP-036 implements exactly that pilot - three categories only, chosen from WP-035's own evidence study plus one additional real-evidence check performed at the start of this WP: `אספקת דם`, `מסילות עצביות`, and `גרעיני הבסיס` (basal ganglia - its top-scoring retrieved chunk is an equally clean bulleted list of six named sub-structures, verified against the real production retrieval index before selection). Every other category is completely unaffected. No prompt file, validator, retrieval mechanism, competitor-discovery logic, relationship-extraction logic, or request contract was touched.

## 2. Inventory Model

`InventoryConcept` (new, `planning/concept_inventory.py`) - a deliberately internal-only model, never part of any public request/response contract (the same precedent `CategoryCoverage` established in WP-034):

```python
concept: NonBlankStr             # the extracted concept text, verbatim
evidence_chunk_id: NonBlankStr   # genuine canonical SourceEvidenceChunk.chunk_id, never invented
factual_focus: NonBlankStr       # deterministic context window around the concept's occurrence
extraction_reason: NonBlankStr   # plain-text description of the structural signal matched
```

No numeric confidence field was added (section 4 suggested one) - every extraction here is a clean structural match or it does not happen at all (WP-035's "never guess" principle admits no partial-confidence middle ground), so a confidence score would be false precision.

## 3. Extraction Algorithm

`extract_concept_inventory()` (new, `planning/concept_inventory.py`) implements WP-035's recommended hybrid strategy - structure-first, marker-based, honest fallback. **Zero LLM calls, zero embeddings, zero semantic search.** A line is extracted as a concept candidate only if, after stripping whitespace, it: (a) consists entirely of `[A-Za-z0-9()/,\-.\s]` characters (pure ASCII - deliberately not a language preference but a corruption filter, see Section 9), (b) contains at least 2 alphabetic characters, (c) contains at least one uppercase letter, and (d) contains at most 6 alphabetic words. Concepts are deduplicated across chunks by normalized text (case-fold, whitespace-collapse - the same shape already established for exact-duplicate question text in WP-014 and reused for coverage in WP-034), keeping the first (highest-retrieval-rank) occurrence.

**One evidence-driven refinement was made during development, before any live run**: an initial version without condition (b) extracted large amounts of single-letter noise ("A", "M", "P", "V", "L", "N" - PDF line-wrap artifacts where a word like "Anterior" or "Medial" was split across two lines, stranding one letter alone). This was caught by inspecting real extraction output against the three pilot categories' real evidence and fixed before any test was written or any live call was made - not a post-hoc tuning-after-results adjustment.

## 4. Planner Changes

`QuestionTargetPlanner.__init__` gained an optional `pilot_categories: frozenset[str] = PILOT_CATEGORIES` parameter (defaulting to the real WP-036 set in `from_default_configuration()`, injectable for test isolation). `plan_targets()` branches immediately after evidence retrieval:

- **Pilot categories**: extract the concept inventory, exclude every concept already in `coverage.tested_concepts` (WP-034, reused unchanged, exact text match only per section 6), take up to `count` of whatever remains in deterministic first-occurrence order, and construct `QuestionTarget`s directly - `topic`/`factual_focus` from the concept's own deterministic data, `supporting_evidence_chunk_ids` the concept's genuine source chunk. **No LLM call is made.**
- **Every other category**: the exact same LLM-based path documented in `docs/ARCHITECTURE.md`'s WP-025/034 sections, byte-for-byte unchanged - confirmed by the full regression suite passing unchanged and by a dedicated test (`test_non_pilot_category_behavior_is_completely_unchanged`).

Inventory exhaustion (fewer remaining concepts than requested, including zero) returns fewer targets - never invented, never a silent fallback to the LLM path (directly tested: `test_pilot_category_exhaustion_yields_empty_list_not_llm_fallback`). The existing `InsufficientDistinctTargetsError` question-local-failure path (already handling "planner returned fewer targets than requested" for the LLM path since WP-025) handles this identically - WP-036 deliberately reuses this existing failure type rather than inventing a new one, since both represent the same observable outcome to every caller.

## 5. Existing Questions / Coverage Reuse (Section 6)

`coverage.tested_concepts` (WP-034's `CategoryCoverage`, entirely unmodified) is reused directly for exclusion. **Exact text matching only** (case-fold, whitespace-collapse) - no synonym handling, no semantic matching, per section 6's explicit instruction. This is directly, deliberately tested (`test_no_synonym_matching_a_differently_worded_tested_concept_is_not_excluded`) - and, as Section 8 below describes, this exact-match-only design is also what made the pilot's central finding visible rather than silently masking it.

## 6. Generation (Section 7)

Unchanged. Generation continues to receive `target` (now sometimes concept-derived rather than LLM-derived), the deterministically-extracted `relationship` (WP-030, applied to whichever `factual_focus` the target carries - unaffected by whether that target came from the LLM path or the pilot path), `competitors` (WP-031, same), and the retrieved evidence. `QuestionProducer`, `QuestionGenerator`, all five validators, retry mechanisms, and acceptance policy are byte-for-byte unchanged (Section 8's regression suite confirms this).

## 7. Tests

- New `tests/unit/test_concept_inventory.py` (20 tests): clean extraction, determinism, genuine chunk-id provenance, first-occurrence ordering across chunks; malformed/noisy evidence (single stray letters, pure-digit lines, overly-long lines rejected; short real abbreviations like `MCA`/`VL` correctly kept; pure-Hebrew prose and no-evidence both yield an empty inventory without error); inventory deduplication across repeated chunks, case/whitespace-insensitive; coverage-based exclusion including the deliberate no-synonym-matching case; `PILOT_CATEGORIES` content; no LLM/embedding call anywhere in the module.
- 9 new tests in `tests/unit/test_planning.py`: pilot category makes zero LLM calls; target built correctly from the inventory; genuine evidence-chunk provenance; coverage exclusion works; exhaustion never falls back to the LLM path; a category with no extractable concepts yields an empty list, not an error; non-pilot behavior is explicitly, directly confirmed unchanged; the pilot-category constructor default is the real `PILOT_CATEGORIES` set; an injected (e.g. empty) pilot set genuinely disables the deterministic path, confirming it is configurable rather than hard-coded.
- **Full regression suite: 1235 passed, 0 failed** (up from 1206 before this WP), zero network access, no `OPENAI_API_KEY` required.
- `scripts/generate_schemas.py` re-run: all three schema files **byte-identical** (`InventoryConcept` is internal-only, never schema-exported; no public contract was touched).

## 8. Evaluation and Acceptance Run (Sections 10/11 - One Combined Live Test)

WP-036's own sections 10 and 11 describe the same shape of live test (four sequential questions per pilot category via `CategoryQuestionSetService`, comparing with WP-034). One combined live run was performed, satisfying both, with no reruns and no manual inventory adjustment.

### Results

| Category | Round 1 | Round 2 | Round 3 | Round 4 | Accepted |
|---|---|---|---|---|---|
| `אספקת דם` | Superior cerebellar artery ✓ | Basillar artery ✓* | Basillar artery ✓* | Basillar artery ✓* | 4/4 |
| `מסילות עצביות` | Spinothalamic Tract ✓ | edial Lemniscus Tract ✓* | edial Lemniscus Tract ✓* | edial Lemniscus Tract ✓* | 4/4 |
| `גרעיני הבסיס` | The Basal Gang ✓* | The Basal Gang ✓* | The Basal Gang ✗ (`QuestionAttemptsExhaustedError`) | The Basal Gang ✓* | 3/4 |

`*` = the assigned concept's name and the accepted question's actual correct-answer text differ (see Section 9). Accepted counts: `אספקת דם` 4/4, `מסילות עצביות` 4/4, `גרעיני הבסיס` 3/4 - each comparable to or better than that category's own WP-034 baseline (2/2, 2/2, 1/2 respectively, on half as many planned questions). **No reliability regression.** Raw data: `evaluation/live_outputs/wp036_pilot_records.json`.

## 9. Architectural Evaluation (Section 14 - Required)

**Was deterministic inventory extraction reliable?** Partially. Clean, well-isolated list items extracted cleanly (`Spinothalamic Tract`, `Superior cerebellar artery`, `Basilar Artery`). Extraction was unreliable at two boundaries, both directly observed: PDF line-wrap truncation (`"edial Lemniscus Tract"` missing its leading `M`; `"The Basal Gang"` missing `"lia"`), and category-name restatement (the very first extracted concept for `גרעיני הבסיס` was effectively a re-statement of the category itself, not a genuine sub-concept).

**Did concept-constrained planning improve diversity? No - and the reason is now specific and evidence-grounded, not merely repeated from WP-034.** Target *selection* worked exactly as designed: every round was correctly assigned a different, coverage-filtered concept (confirmed directly via `plan_history` inspection - `אספקת דם` correctly rotated from "Superior cerebellar artery" to "Basillar artery" after round 1). **But the actual tested content did not follow the assignment.** Two distinct, concretely-identified mechanisms, both confirmed against the raw round-by-round data (Section 8):

1. **Context-window ambiguity.** `אספקת דם`'s concept "Basillar artery" was extracted from a passage whose real subject is a *different*, more salient entity ("Superior Cerebellar Artery, source: Basilar Artery"). The resulting `factual_focus` context window did not unambiguously anchor generation to "Basilar Artery" as the answer - the model, given latitude in what to actually test and designate correct, wrote about "Superior Cerebellar Artery" in all three subsequent rounds regardless of which concept was nominally assigned. `מסילות עצביות` shows a related but distinct variant: the assigned concept text itself was truncated (`"edial Lemniscus Tract"`), so even though generation correctly tested the right underlying fact and wrote the properly-spelled answer ("Medial Lemniscus Tract"), that correctly-spelled answer never *exact-text-matched* the truncated assigned name - so coverage never recognized it as tested, and the same truncated concept was reassigned every subsequent round.
2. **Concept-inventory quality.** `גרעיני הבסיס`'s first extracted concept, "The Basal Gang" (truncated from "The Basal Ganglia"), is not a genuine sub-concept at all - it is the category's own name. Generation, given this as the assigned target, produced broad category-level questions (CNS/PNS membership, definition, primary motor function) whose correct answers never textually matched "The Basal Gang" in any round - so it was never excluded, and was reassigned in all four rounds without exception.

**Both mechanisms share one root cause**: coverage exclusion, by WP-034's own deliberate design, can only see what generation *actually produced* (the real accepted-question text - never a target's own unverified claim, since that would reintroduce exactly the kind of self-reported-and-unverified trust WP-028 already demonstrated fails). When generation's actual answer diverges from the assigned target's nominal identity - whether from context-window ambiguity or extraction truncation - the assigned concept is never marked tested, and since assignment always proceeds by fixed inventory order, the identical concept is deterministically reassigned next round, reproducing the identical failure indefinitely.

**Did reliability regress? No.** Accepted counts matched or exceeded each pilot category's own WP-034 baseline; zero generation-contract failures; the one failure observed (`גרעיני הבסיס` round 3) was an ordinary `QuestionAttemptsExhaustedError`, the same failure type already expected under the pre-existing, unmodified WP-013 production cycle.

**Which implementation difficulties appeared?** Both identified above are specific, actionable, and were not visible from WP-034's own (broader, softer-signal) acceptance run: (a) target `factual_focus` construction needs to more surgically isolate the assigned concept's own supporting sentence, minimizing bleed-through from a more salient neighboring entity in the same source passage; (b) extraction-truncation artifacts need either a repair heuristic (e.g. re-joining a short fragment with an immediately-preceding capitalized line) or a stricter minimum-quality filter that would have excluded "The Basal Gang" as too close to the category's own name.

**Should this approach expand beyond the pilot? No, not as currently designed.** The pilot's primary success criterion (section 12: "question diversity improves because concept selection changes") was not met - selection changed; tested content mostly did not. Expanding to more categories would only compound the same two failure modes at larger scale without addressing their now-identified root cause. **Recommendation: any future work continuing this direction should first address context-window anchoring (Section 9, mechanism 1) - most plausibly by tightening `factual_focus` extraction to end at the first sentence/clause boundary after the concept, rather than a fixed character window that can span into a neighboring entity's description - and should re-run this exact three-category pilot methodology afterward, before considering broader rollout.** This is a genuinely more specific, more actionable finding than WP-034's own conclusion, consistent with the "negative experiments are often the most valuable architectural work" principle WP-034's own architecture review articulated.

## 10. Limitations

- Extraction noise beyond what Section 3's single evidence-driven refinement addressed remains (e.g. mid-word truncation, occasional garbled fragments from bidi corruption surviving the ASCII-only filter when corruption happens to produce an all-ASCII-looking run) - documented, not eliminated, consistent with "keep the implementation intentionally small" (section 13).
- Concept granularity was not resolved (WP-035 already flagged this as unresolved): whether "Basilar Artery" and "Superior Cerebellar Artery" should be treated as one related concept or two independent ones is a genuine design question this pilot's simple line-based extraction does not address.
- Attempt-level validator rejection detail (which specific validator rejected `גרעיני הבסיס` round 3's failed attempts) was not captured by the evaluation script - only the terminal `QuestionAttemptsExhaustedError` outcome is known; a future live run intending to diagnose *why* attempts failed should capture full `attempt_history`, as WP-032/034's acceptance-run scripts did.

## 11. Confirmations

- No prompt file was modified.
- No validator was modified.
- No retrieval/chunking/TF-IDF logic was modified.
- No relationship/competitor logic was modified.
- No synonym or semantic matching was implemented (exact text match only, as required).
- `CategoryQuestionSetRequest`/`Response`/`CategoryGenerationRequest`/`Response` (WP-032/033) were not modified - no new field was added.
- `InventoryConcept` is internal-only, never schema-exported.
- Full regression suite passes: **1235/1235**.
- Pilot evaluation/acceptance run performed exactly once, no reruns, no manual inventory adjustment, honest exhaustion reporting.

## 12. Files Created/Modified

**Created:**
- `src/exam_generator/planning/concept_inventory.py`
- `tests/unit/test_concept_inventory.py`

**Modified:**
- `src/exam_generator/planning/planner.py` (pilot-category branch, `_select_remaining_concepts()`, `pilot_categories` constructor parameter)
- `tests/unit/test_planning.py` (9 new pilot-category tests)
- `docs/ARCHITECTURE.md` (new "Deterministic Concept Inventory Pilot" section)
- `docs/PROJECT_STATUS.md` (Tests count, new Live Evaluation Baseline section, Next WP Context updated)
- `evaluation/live_outputs/README.md` (new row)

---

WP-036 complete.

Tests:
1235 passed, 0 failed

Pilot evaluation:
אספקת דם 4/4, מסילות עצביות 4/4, גרעיני הבסיס 3/4 accepted (comparable to or better than WP-034 baselines); target selection correctly diversified every round but tested content did not - generation repeatedly drifted back to the same dominant fact regardless of the deterministically-assigned concept (see section 9 for the evidence-grounded root cause and explicit non-expansion recommendation)

Completion report:
implementation/WP-036_COMPLETION_REPORT.md

Waiting for architect review.
