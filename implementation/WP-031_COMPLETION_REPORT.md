# WP-031 Completion Report — Deterministic Competitor Discovery

## 1. Implementation Summary

WP-030's live evidence and its architecture review identified the specific missing layer: generation knew the correct concept and the tested relationship (WP-030), but nothing about what *else* in the evidence might also satisfy that relationship - "relationship information is necessary but not sufficient." WP-031 is Phase 2 of the WP-029 migration: deterministically discover other evidence-supported concepts sharing the tested relationship, before generation runs, and present them to the model as information - never as an instruction about which to use, and never generating distractor text itself.

The implementation is exactly as scoped: a pure, deterministic, zero-LLM-call, zero-new-retrieval function scans the evidence generation already received; its output is threaded into the prompt as one new section. No validator, retrieval, orchestration, diversity planner, `QuestionTarget`, or `QuestionRelationship` field was touched.

**The live acceptance run showed real, partial progress** on the metric WP-030 failed to move - grounding rejections from "another answer also supported" fell substantially, though not fully back to WP-027's original baseline. This report documents the result exactly as measured, including an honest architectural evaluation of whether the improvement is attributable to competitor discovery specifically.

## 2. Competitor Model

`CompetitorCandidate` (new, `src/exam_generator/models/competitor.py`):

```python
class CompetitorCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    concept: NonBlankStr                  # short deterministic text window, never a parsed entity
    source_evidence_chunk_id: NonBlankStr
    relationship_relevance: NonBlankStr
    similarity_reason: NonBlankStr
```

Per WP-031 section 3's explicit boundary, `concept` deliberately contains **no** parsed/invented entity name and **no** distractor text - it is the exact evidence substring (a fixed-width window around the matched keyword) that led to the candidate's discovery, so a reader (or the model) can judge relevance from the source text itself rather than trust a summarization.

## 3. Deterministic Competitor Discovery

`discover_competitors()` (new, `src/exam_generator/generation/competitors.py`) is a pure function: `(QuestionTarget, QuestionRelationship, source_evidence) -> tuple[CompetitorCandidate, ...]`.

- Reuses `extract_relationship()`'s own keyword table via a new `keywords_for(relationship_type)` accessor (`generation/relationship.py`) - no duplicated vocabulary.
- Scans every supplied evidence chunk **except** the target's own `supporting_evidence_chunk_ids` for a case-insensitive match of any keyword for the target's classified relationship type.
- Returns an empty tuple when `relationship_type` is `UNSPECIFIED` (nothing to search for) or when no other chunk matches - never a guess, matching the fail-honest philosophy already established for `extract_relationship()` itself.
- **Zero LLM calls, zero new retrieval calls, zero embeddings, zero vector database, zero ontology** - verified directly by test (`test_discovery_makes_no_llm_or_retrieval_call`) and by the function's own signature (three plain arguments, no client/index dependency).

**Ranking policy (WP-031 section 5, documented rather than tuned)**: candidates are returned in `source_evidence`'s own existing order - which is already the retrieval index's TF-IDF relevance rank (WP-006), an already-computed deterministic signal. No new ranking computation was introduced; verified directly by test (`test_ranking_preserves_source_evidence_order`).

## 4. QuestionTarget / QuestionRelationship Changes

**None.** Both remain exactly as WP-025/WP-030 left them (confirmed by test - `test_question_target_still_gained_no_new_field`, `test_question_relationship_still_unchanged`). The competitor list is computed transiently in `QuestionGenerator.generate_candidate_question()` and threaded through `GenerationPromptContext`, which gained a new required `competitors: tuple[CompetitorCandidate, ...]` field.

## 5. Prompt Changes

`prompts/generation/question.txt` gained one new section, "Possible competing concepts," placed after "Tested relationship" (WP-030) and before "Testing enumeration or classification targets," plus one new template variable, `{competitor_concepts}`, rendered right after the existing target block. The new prose:

- Explicitly states the list is **information, not an instruction** - it does not tell the model which distractors to use.
- Ties the list back to the existing (WP-027) evidence-based distractor check: before finalizing, check whether any listed competitor would also correctly answer the exact question, using the same check already required.
- Explains an empty list means "none found by this check," not "no competitor exists" - continue applying the existing distractor-correctness requirements regardless.

No other prompt content was rewritten - WP-026/027's enumeration/hierarchy/distractor-correctness guidance, WP-028's frozen blueprint section, and WP-030's relationship section remain completely untouched.

## 6. Files Created/Modified

**Created:**
- `src/exam_generator/models/competitor.py`, `src/exam_generator/generation/competitors.py`
- `tests/unit/test_competitors.py`
- `implementation/WP-031_COMPLETION_REPORT.md` (this file)
- `evaluation/live_outputs/wp031_focused_eval_results.json`, `wp031_acceptance_exam.json`, `wp031_acceptance_audit.json`, `wp031_acceptance_targets.json`

**Modified:**
- `src/exam_generator/models/__init__.py`, `src/exam_generator/generation/__init__.py`, `src/exam_generator/prompts/__init__.py` - new exports
- `src/exam_generator/generation/relationship.py` - new `keywords_for()` accessor (pure refactor, no behavior change to `extract_relationship()`)
- `src/exam_generator/generation/generator.py` - calls `discover_competitors()`, threads the result into `GenerationPromptContext`
- `src/exam_generator/prompts/context.py` - `GenerationPromptContext` gained required `competitors` field
- `src/exam_generator/prompts/formatting.py` - new `format_competitors()`, new BEGIN/END markers and honest-empty-list sentinel
- `prompts/generation/question.txt` - new "Possible competing concepts" section, new `{competitor_concepts}` variable
- `tests/unit/test_prompts.py` - 7 direct `GenerationPromptContext(...)` constructions updated to supply `competitors`; 6 new prompt-content tests

**No changes:** any of the five validators, `src/exam_generator/planning/*`, `src/exam_generator/orchestration/*`, `src/exam_generator/retrieval/*`, `src/exam_generator/production/*`, `schemas/*.schema.json` (confirmed byte-identical).

## 7. Tests

- **`tests/unit/test_competitors.py`** (new, 14 tests): discovers a competitor sharing the same relationship keyword; the target's own supporting evidence is never a competitor of itself; unrelated evidence yields nothing; `UNSPECIFIED` relationship yields nothing; empty evidence yields nothing; ranking preserves `source_evidence`'s own order (both forward and reversed inputs, proving it is a pass-through, not a re-sort); determinism (same input twice → same output); purity (no mutation of target or chunk); no-LLM/no-retrieval signature check; `CompetitorCandidate` immutability/unknown-field-rejection/blank-field-rejection; `QuestionTarget`/`QuestionRelationship` backward compatibility.
- **`tests/unit/test_prompts.py`** (+6): the `competitor_concepts` template variable is required; the honest "none found" sentinel renders by default; a real discovered competitor renders with its `[Competitor N]` label; the "information, not an instruction" wording is present; the "empty list is not a guarantee" wording is present; the section explicitly ties back to the existing evidence-based check.

## 8. Full Regression Result

**1131 / 1131 passing** (up from the 1111 baseline entering WP-031; +20 net), zero network access, no `OPENAI_API_KEY` in the offline test shell. `scripts/generate_schemas.py` re-run: all three schema files byte-identical - competitor models are never schema-exported.

## 9. Focused Live Evaluation

6 candidates (2 per category) across `מערכת העצבים ההיקפית`, `אספקת דם`, `תאי מערכת העצבים` - the same categories and methodology as WP-030's own focused evaluation.

**Result: 5/6 accepted, avg 2.00 attempts.** The recurring PNS-divisions target (hard across WP-025A, WP-026, WP-027, WP-028's focused eval, and now here) exhausted again. Its `factual_focus` uses the Hebrew verb form "מחולק ל" ("divides into"), which is **not** in the current `CONTAINS` keyword table (already flagged as a known coverage gap in WP-030's own completion report) - so it classified `UNSPECIFIED`, and competitor discovery had nothing to search for either. This is an honest, expected, unresolved limitation, not a WP-031-caused regression - fixing it would require prompt/keyword-table tuning informed by this exact result, which the WP's "no tuning after results" discipline forbids doing here.

## 10. Full Acceptance Run

- **Planned: 40 | Accepted: 32 | Failed: 8 | Status: PARTIAL**
- **Runtime: ~26.9 minutes** (1612.0 seconds)
- **Exit code: 0**; both `exam.json` (32 questions) and `exam_audit.json` written successfully on the first attempt.

### Every failed planned question and reason

| Position | Category | Mode |
|---|---|---|
| 10 | מיפוי ודימות מוחי | INDEPENDENT |
| 13 | המערכת הלימבית | STYLE_SIMILAR |
| 18 | קרומים וסינוסים דוראליים | INDEPENDENT |
| 19 | גזע המוח | STYLE_SIMILAR |
| 28 | מערכת העצבים ההיקפית | INDEPENDENT |
| 30 | דיאנצפלון | INDEPENDENT |
| 33 | טופוגרפיה של ההמיספרות | STYLE_SIMILAR |
| 40 | מבוא | INDEPENDENT |

All 8 are `QuestionAttemptsExhaustedError`, each in a **different** category - unlike WP-030, no category lost both its planned positions this run. **Generation-contract failures observed: 0.**

### Accepted-attempt distribution

**28 accepted on attempt 1, 3 on attempt 2, 1 on attempt 3** (37 accepted-path attempts, avg **1.156**/accepted question - the best of any run measured: WP-027 1.26, WP-028 1.35, WP-030 1.34) plus 24 attempts across the 8 failed questions (3 each) = **61 total candidate attempts**.

### Validator rejection counts (all rejected attempts)

mcq: 14, quality: 10, category: 9, grounding: 16, textbook: 0.

### Grounding rejection breakdown (the WP's own primary metric)

**Designated answer unsupported: 0. Another answer also supported: 16. Other grounding reasons: 0.**

## 11. Comparison with WP-027/WP-028/WP-030

| Metric | WP-027 | WP-028 | WP-030 | WP-031 | Direction (vs. WP-030) |
|---|---|---|---|---|---|
| Accepted / planned | 34/40 | 31/40 | 32/40 | 32/40 | flat |
| Accepted on attempt 1/2/3 | 27/5/2 | 23/5/3 | 25/3/4 | **28/3/1** | **best yet** |
| Avg attempts per accepted | 1.26 | 1.35 | 1.34 | **1.16** | **best yet** |
| Total candidate attempts | 61 | 69 | 67 | 61 | better |
| Grounding rejections (total) | 12 | 16 | 24 | **16** | **much better** |
| Grounding: "another also supported" | 12 | 14 | 24 | **16** | **much better (-33%), still above WP-027's 12** |
| MCQ rejections | 8 | 18 | 9 | 14 | worse than WP-030, much better than WP-028 |
| Quality rejections | 10 | 15 | 3 | 10 | worse than WP-030, matches WP-027 |
| Category rejections | 3 | 6 | 8 | 9 | worse (single-run variance) |
| Textbook rejections | 6 | 2 | 0 | 0 | flat |
| False acceptance: CONFIRMED | 0 | 0 | 0 | **0** | held (4/4 runs now) |
| False acceptance: POSSIBLE | 1 | 2 | 2 | **1** | **best yet, ties WP-027** |
| Diversity | 14/14 | 12/12 | 13/13 | 12/12 | held (all 100%) |

**WP-031 achieved real, measured progress on the WP-030-failed metric** (-33% on "another also supported"), the best-yet first-attempt/average-attempt efficiency, and the cleanest false-acceptance outcome of any run to date (tying WP-027 at 0 confirmed / 1 possible). It has not fully recovered to WP-027's original 12, and category rejections rose modestly - reported honestly rather than minimized.

## 12. Architectural Evaluation (WP-031 section 14 - required)

**Did deterministic competitor discovery improve generation quality? Partially, with real but not fully explained evidence.**

- **What improved, measured directly:** the primary target metric fell from 24 to 16 (-33%); average attempts per accepted question improved to the best level of any run (1.16); the false-acceptance human review found the fewest suspicious cases of any run (1 possible, 0 confirmed).
- **What the investigation could and could not establish:** cross-referencing relationship classification against the 8 planned positions that had at least one "another also supported" grounding rejection found 3 were relationship-classified (`CONTAINS`/`DEVELOPS_INTO`) and 5 were `UNSPECIFIED`. Relative to the overall split (15 classified / 40 targets, 25 unclassified / 40), this is proportionally similar (3/15 = 20% classified-target failure rate vs. 5/25 = 20% unclassified-target failure rate) - **the data does not show classified targets failing less often than unclassified ones within this single run**, which would be the clearest evidence competitor discovery is the direct causal mechanism.
- **Honest conclusion:** the overall run-level metrics improved meaningfully relative to WP-030, but this single run's data cannot cleanly attribute that improvement to competitor discovery specifically, as opposed to ordinary run-to-run variance in which targets the planner happened to select (the same caveat WP-030's own report raised about its own regression). What can be said with more confidence: competitor discovery did **not** make things worse (no metric regressed catastrophically, and the two best-yet results - average attempts and false-acceptance cleanliness - both come from this run), and it did not require abandoning or complicating anything WP-030 established. Given the shared root constraint identified in both this and WP-030's investigation - **relationship-keyword coverage remains the binding limitation** (only 15/40 and 17/40 targets classified in the two most recent runs) - the most defensible interpretation is that competitor discovery's benefit, where it applies, is real but currently gated by the same coverage gap that limited WP-030's own relationship layer, rather than competitor discovery itself being ineffective.

## 13. False-Acceptance Human Review

All 32 accepted questions were individually inspected against their cited grounding evidence.

**Totals: 31 CLEAR_SINGLE_ANSWER, 1 POSSIBLE_SECOND_CORRECT_ANSWER, 0 CONFIRMED_SECOND_CORRECT_ANSWER, 0 INSUFFICIENT_EVIDENCE_TO_JUDGE.**

The one `POSSIBLE` case: question #19 (`גרעיני הבסיס`, "what is the basal ganglia's central role in executing motor movement") designates "regulate movement by activating the thalamus" (`ויסות התנועה על ידי הפעלת התלמוס`) correct against a distractor "activate movement by regulating suppression of the thalamus" (`הפעלת התנועה על ידי ויסות דיכוי התלמוס`) - these two phrasings describe closely related, arguably identical physiological mechanisms (disinhibition) using different word order and emphasis, a wording-closeness concern rather than a clear factual contradiction from the cited evidence. Reported honestly as `POSSIBLE` rather than dismissed, per the review's own instruction not to under-report uncertainty.

Notably, several accepted questions that could have reproduced known risky shapes did not this run: question #12 (Rhinencephalon/limbic system) did not repeat WP-030's "olfactory system" terminology-overlap distractor; question #24 (thalamus as "the central diencephalon structure," among real sibling structures hypothalamus/epithalamus/subthalamus) and question #25 (Bilaminar Disk vs. its own component layers Hypoblast/Epiblast) both correctly avoided the classic enumeration/sibling trap through specific qualifying language, consistent with the pattern established since WP-026/027.

## 14. Per-Category Diversity Review

12 of 20 categories had both planned questions accepted (each of the 8 failed categories lost exactly one position, not both):

| Category | Question 1 | Question 2 | Assessment |
|---|---|---|---|
| התעלה השדרתית ותכולתה | Spinal cord within canal | Rexed layer 9 (motor) | DISTINCT |
| לוקליזציה פונקציונלית | M1 function | Gustatory cortex location | DISTINCT |
| חומר לבן | Association fibers | Stratum Zonale | DISTINCT |
| עצבים קרניאליים | Olfactory nerve | Optic nerve | DISTINCT |
| היסטולוגיה | Molecular layer | Histology (definition/history) | DISTINCT |
| אספקת דם | SCA | Anterior spinal artery | DISTINCT |
| מסילות עצביות | Spinothalamic tract | Medial lemniscus tract | DISTINCT |
| גרעיני הבסיס | Central role (activates thalamus) | Direct pathway (mechanism) | DISTINCT |
| המוח הקטן | Function (coordination) | Structure (gray/white matter) | DISTINCT |
| אמבריולוגיה | Bilaminar disk | Gastrulation | DISTINCT |
| חדרי המוח | Lateral ventricles (C-shape) | 3rd ventricle (interventricular foramen) | DISTINCT |
| תאי מערכת העצבים | Microglia | Ependymal cells | DISTINCT |

**Totals: 12 / 12 DISTINCT (100%), 0 BORDERLINE, 0 DUPLICATE/NEAR-DUPLICATE.**

## 15. Remaining Limitations

- **Relationship-keyword coverage remains the binding constraint**, now confirmed across two consecutive WPs (WP-030: 42.5% classified, WP-031: 37.5% classified) - competitor discovery can only apply where classification already succeeds, so its ceiling is bounded by the same gap WP-030 reported. The specific, concrete, still-unfixed example (per the "no tuning after results" discipline) is the PNS-divisions target's "מחולק ל" verb form.
- **The improvement's causal mechanism is not fully established** (section 12) - this is reported as an honest open question, not resolved by asserting competitor discovery as the cause without stronger evidence.
- Category rejections (9) were the highest of any run measured - a single-run observation not further investigated here, since it was not the WP's primary concern and investigating it would risk tuning based on this run's own results.
- This is a single live acceptance run (n=1) and a small focused-evaluation sample (n=6); the directional signals reported here are real single-run measurements, not statistically powered claims.

## 16. Confirmations

- **No validator was added or modified**: all five validators are byte-for-byte unchanged from WP-027.
- **No diversity/planning change**: `QuestionTargetPlanner` is untouched; no competitor-diversity scoring was introduced (WP-031 section 9).
- **No pipeline/orchestration change**, **no retry/attempt-budget change**, **no additional LLM calls**, **no additional retrieval calls** (confirmed both by design and by `test_discovery_makes_no_llm_or_retrieval_call`).
- **No embeddings/vector database/ontology introduced** (WP-031 section 4's explicit exclusions).
- **No post-run tuning performed**: the prompt/code as they existed when the acceptance run was launched are exactly as they exist now.

---

WP-031 complete.
Tests: 1131 passed
Acceptance run: PARTIAL, 32/40 accepted, 8 failed (grounding "another-also-supported" rejections: 16, down from WP-030's 24 - real partial progress, still above WP-027's 12; best-yet avg attempts 1.16; false acceptance held at 0 confirmed / 1 possible, tying WP-027 as cleanest result)
Completion report:
implementation/WP-031_COMPLETION_REPORT.md

Waiting for architect review.
