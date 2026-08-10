# WP-038 Completion Report — Deterministic Concept Identity and Coverage Matching

## 1. Implementation Summary

WP-037's architecture review localized the accepted-count regression it found precisely: coverage exclusion (`extract_category_coverage()`, WP-034) compares an assigned concept's own text against a later accepted answer's text with plain exact matching, and WP-037's narrower, more precisely-anchored evidence caused generation to answer in Hebrew far more often than the old wide window did - breaking that exact-text comparison silently. WP-038 introduces a deterministic concept-identity mechanism (new module, `planning/concept_identity.py`) so coverage can recognize the same concept across safe, explicitly-supported representations, without introducing semantic similarity, embeddings, an LLM judge, or fuzzy/edit-distance matching. Scope is unchanged from WP-036/037: the same three pilot categories only (`אספקת דם`, `מסילות עצביות`, `גרעיני הבסיס`). No public contract changed. `QuestionGenerator`, `QuestionProducer`, `OpenAIProvider`, every validator, and WP-037's own anchoring algorithm (`refine_concept_inventory()`/`anchor_concept_evidence()`) are byte-for-byte unchanged.

## 2. Investigation Before Implementation (Section 4)

Before any code was written, the actual retrieved evidence behind all three of WP-037's live-pilot concepts was inspected directly via production retrieval wiring (`retrieve_for_category()`), not guessed at:

- **`אספקת דם` / "Superior cerebellar artery"**: zero Hebrew rendering found anywhere in the category's 8 retrieved chunks.
- **`מסילות עצביות` / "Spinothalamic Tract"**: a Hebrew rendering ("ספינותלמית") exists in the retrieved evidence, but only in a *different* chunk than the concept's own, in ordinary unrelated prose - not adjacent to the concept.
- **`גרעיני הבסיס` / "Corpos Str" (Corpus Striatum)**: a Hebrew rendering ("קורפוס סטריאטום") appears later in the concept's *own* chunk, but only as independent prose reuse ("ניתן לחלק את הקורפוס סטריאטום לתתי מבנים...") - never as an explicit paired/parenthetical statement next to the English concept.

**Conclusion reached before writing any code**: "explicit bilingual forms already present in the same evidence" (section 7's first suggested approach) is not available for any of the three concepts that were actually live-piloted. This directly shaped the design - see Section 3.

## 3. Concept Identity Model (Section 5)

`ConceptIdentity` (new, `planning/concept_identity.py`, internal-only - never part of any public request/response contract, mirroring `InventoryConcept`/`CategoryCoverage`'s existing precedent):

```
ConceptIdentity
    canonical_form: str                                  # the concept's own extracted text, verbatim
    normalized_forms: tuple[str, ...]                     # deterministic, always-safe transforms
    explicitly_supported_language_forms: tuple[str, ...]  # evidence-derived alternate forms, () by default
```

`build_concept_identity(concept, *, chunk_text)` constructs one from an `InventoryConcept` and its own source chunk text.

## 4. Deterministic Normalization (Section 6)

`_deterministic_normalized_forms()` applies exactly three transforms, each independently derivable from `canonical_form` alone: `normalize_concept_text()` (WP-036, whitespace-collapse + casefold), Unicode NFKC normalization (`unicodedata.normalize("NFKC", ...)` - collapses compatibility-equivalent character sequences, e.g. ligature presentation forms), and a small, fixed punctuation-stripped variant (`()`, `,`, `.` removed - never a general "strip everything non-alphanumeric" rule, to avoid merging genuinely distinct short forms like "GPe" vs "GPi"). **Explicitly not implemented**: edit distance, fuzzy matching, or approximate-spelling inference (section 24's explicit prohibitions) - these transforms only ever produce a *lossless-intent* rewrite of the same text, never a guess at a different one.

## 5. Cross-Language / Cross-Script Strategy (Section 7/8)

**`_extract_paired_language_form()`**: the one narrow, structural pattern judged safe to trust - the concept's own text immediately adjacent (same line, or the single preceding/following non-blank line) to a parenthetical run of Hebrew characters. This is the same explicit-pairing convention this corpus already uses for English abbreviations (e.g. "Anterior Inferior Cerebellar Artery (AICA)"), applied to a Hebrew payload instead of an English one. Genuinely implemented and unit-tested working correctly against synthetic evidence containing this pattern (both parenthetical orders, and the pattern on an adjacent line) - see Section 8.

**Deliberately not implemented, and why (Section 2's proven-not-guessed requirement, Section 24's explicit prohibitions)**:
- **General transliteration matching**: the live WP-037 data already showed the LLM's own Hebrew transliteration is not self-consistent (the same concept produced two different Hebrew spellings across consecutive rounds: "ספינותלמית" vs "ספינתלמית"). WP-038's own live pilot (Section 9) reinforced this further - "Superior cerebellar artery" was rendered **three different ways** across four rounds in a single run: "עורק סופריאורי צרבלרי" (×2), "עורק צרבלרי עליון" (a *translation*, not a transliteration - ×1), and "עורק סופריור צרבלרי" (×1). Building a phonetic transliteration matcher to bridge this would itself be a fuzzy-matching mechanism by construction (section 24: "Do NOT use edit distance as a general equivalence mechanism", "Do NOT implement broad fuzzy matching"), and would still not reliably track output this inconsistent even if it were permitted.
- **Broader proximity/co-occurrence matching** (e.g. "any Hebrew text within N lines of the concept"): rejected specifically because `גרעיני הבסיס`'s own chunk contains many concepts and much unrelated Hebrew prose in close proximity; without either phonetic verification (prohibited) or explicit structural adjacency, there is no safe way to know which Hebrew span belongs to which concept - exactly the false-positive risk section 10 warns is "more dangerous than false negative coverage."
- **A large bilingual dictionary or manually-authored concept mapping** (section 24, explicitly prohibited) - never considered.

## 6. Coverage Matching (Section 9)

`concept_identity_matches_text(identity, candidate_text)`: exact match only, after normalization, against every form the identity recognizes as itself (`canonical_form`, every `normalized_forms` entry, every `explicitly_supported_language_forms` entry). Deliberately never substring or fuzzy matching. `planning/planner.py`'s `_select_remaining_concepts()` now builds each remaining concept's `ConceptIdentity` (via `concept_identities_for_inventory()`) and excludes it only when this matches an already-tested answer, replacing WP-034/036's plain `normalize_concept_text()` comparison. Same-script/same-normalization behavior (whitespace, case, punctuation tolerance) is fully preserved - confirmed by 5 pre-existing WP-036 tests in `test_concept_inventory.py` continuing to pass unmodified (only their call signature changed, to supply the new required `chunk_text_by_id` parameter).

## 7. Safety Analysis (Section 10)

The matching mechanism is conservative by construction: `explicitly_supported_language_forms` is populated *only* by a narrow structural check (Section 5), never by proximity, never by phonetic similarity, never by category/anatomical-system relatedness. A dedicated "Safety" test section (`test_concept_identity.py`) explicitly confirms structure/function, source/destination-area, and pathway/general-system pairs never collapse merely because they are related - and a further test confirms a naming-cue phrase elsewhere in the same chunk (WP-037's own self-restatement signal) does not cause an unrelated later concept's Hebrew description to be misattributed. **Zero false-positive identity matches were observed in the live pilot** (Section 9) - every `identity_recognized=True` case was a genuine same-concept English exact match.

## 8. Tests (Section 15/16)

- New `tests/unit/test_concept_identity.py` (24 tests): **Normalization** (whitespace, case, punctuation, Unicode NFKC, deduplication, unsupported orthographic variants correctly not matching). **Identity** (identical concept, explicitly-paired bilingual forms in both parenthetical orders and on an adjacent line, unrelated concepts staying separate, related-but-non-identical concepts staying separate, ambiguous/absent forms never guessed at - including the real `גרעיני הבסיס` corpus shape reproduced synthetically, and a parenthetical containing English content correctly not treated as a language form). **Coverage** (same-language recognized, supported-alternate-language recognized, unsupported alternate representation remains unmatched - the exact live WP-037 regression reproduced deterministically, semantically-related-but-different concepts remain unmatched, batch `concept_identities_for_inventory()` construction). **Safety** (structure/function, source/destination-area, pathway/general-system never collapsing; a naming-cue-adjacent but unrelated concept never misattributed). Plus an internal-only-model confirmation test.
- 3 new planner-integration tests in `tests/unit/test_planning.py`: a concept with a genuine evidence-derived Hebrew form is excluded end-to-end once that form appears in coverage; the real live-observed regression (no pairing available) is reproduced and confirmed to honestly remain unmatched end-to-end; case/whitespace-tolerant exclusion still works end-to-end (baseline behavior preserved).
- 5 pre-existing `tests/unit/test_concept_inventory.py` tests updated only for `_select_remaining_concepts()`'s new required `chunk_text_by_id` keyword parameter - assertions and behavior unchanged.
- **WP-037 regression tests**: `tests/unit/test_concept_anchor.py` (22 tests) and the existing WP-037 planner-integration tests all pass unmodified - anchoring, leading-truncation handling, category self-restatement filtering, canonical evidence IDs, and "no LLM calls in concept planning" are all preserved exactly.
- **Full regression suite: 1286 passed, 0 failed** (up from 1259), zero network access, no `OPENAI_API_KEY` required for the offline suite.
- `scripts/generate_schemas.py` re-run: all three schema files **byte-identical** (`ConceptIdentity` is never schema-exported).

## 9. Live Pilot (Section 17/18)

One live pilot, no reruns, no manual concept repair, no configuration changes after observing results. Same three pilot categories, four sequential questions each, via `CategoryQuestionSetService`.

| Category | R1 | R2 | R3 | R4 | Accepted |
|---|---|---|---|---|---|
| `אספקת דם` | Superior cerebellar artery ✓ | Superior cerebellar artery ✓ | Superior cerebellar artery ✓ | Superior cerebellar artery ✓ | 4/4 |
| `גרעיני הבסיס` | Corpos Str ✓ | Corpos Str ✓ | Corpos Str ✗ (`QuestionAttemptsExhaustedError`) | Corpos Str ✗ (`QuestionAttemptsExhaustedError`) | 2/4 |
| `מסילות עצביות` | Spinothalamic Tract ✓ | Medial Lemniscus Tract ✓ | Anterior Corticospinal T ✓ | Anterior Corticospinal T ✓ | 4/4 |

**Combined: 10/12 accepted** - between WP-036's 11/12 and WP-037's 8/12 for these same three categories. Raw per-round data, including each round's `ConceptIdentity` (`concept_normalized_forms`/`concept_explicitly_supported_language_forms`) and whether that identity recognized the generated answer (`identity_recognized_generated_answer`): `evaluation/live_outputs/wp038_pilot_records.json`.

**A caveat on interpreting the accepted-count change, stated honestly**: `אספקת דם`'s improvement from 2/4 (WP-037) to 4/4 (this run) is **not** attributable to WP-038's own mechanism - `identity_recognized_generated_answer` was `false` for all four of its rounds (Section 10), meaning coverage exclusion never fired differently than it would have under WP-037's own plain-text matching. The concept remained selected all four rounds in both runs; the difference is that this run's four independently-generated Hebrew phrasings happened not to collide with WP-014's unmodified duplicate-detection mechanism, where WP-037's run's phrasings did. This is inherent run-to-run generation stochasticity, not a WP-038 improvement, and should not be reported as one.

## 10. Target Alignment (Section 18/20D)

The 10 accepted questions were manually reviewed for whether the actual correct answer semantically matches the assigned concept (the same methodology WP-037 established):

| # | Category | Round | Selected concept | Correct answer | Manual alignment |
|---|---|---|---|---|---|
| 1 | אספקת דם | 1 | Superior cerebellar artery | עורק סופריאורי צרבלרי | ALIGNED |
| 2 | אספקת דם | 2 | Superior cerebellar artery | עורק צרבלרי עליון | ALIGNED |
| 3 | אספקת דם | 3 | Superior cerebellar artery | עורק סופריור צרבלרי | ALIGNED |
| 4 | אספקת דם | 4 | Superior cerebellar artery | עורק סופריאורי צרבלרי | ALIGNED |
| 5 | גרעיני הבסיס | 1 | Corpos Str | מאפשר הפעלת תנועה על ידי הפסקת דיכוי התלמוס (a functional description) | **NOT ALIGNED** |
| 6 | גרעיני הבסיס | 2 | Corpos Str | Caudate Nucleus (a different, sibling sub-structure) | **NOT ALIGNED** |
| 7 | מסילות עצביות | 1 | Spinothalamic Tract | Spinothalamic Tract | ALIGNED |
| 8 | מסילות עצביות | 2 | Medial Lemniscus Tract | Medial Lemniscus Tract | ALIGNED |
| 9 | מסילות עצביות | 3 | Anterior Corticospinal T[ract] | Anterior Corticospinal Tract | ALIGNED |
| 10 | מסילות עצביות | 4 | Anterior Corticospinal T[ract] | Anterior Corticospinal Tract | ALIGNED |

**Manual alignment: 8/10 (80%)** - in the same high range as WP-037's 87.5% (7/8), confirming WP-037's anchoring improvement was preserved (anchoring itself was never touched by this WP). Both misalignments are in `גרעיני הבסיס`, the same category where WP-037 also found its one misalignment.

Note that `אספקת דם`'s four rounds used **three distinct Hebrew renderings** of the same concept ("עורק סופריאורי צרבלרי" ×2, "עורק צרבלרי עליון" ×1, "עורק סופריור צרבלרי" ×1) - all four still manually ALIGNED (correctly identifying the same underlying entity despite the spelling/phrasing variation), which is exactly the kind of variation a transliteration-matching mechanism would need to handle reliably, and exactly the kind of variation this pilot's own live data shows is not reliably predictable (see Section 5).

## 11. Diversity and Rotation (Section 20A/B)

- `אספקת דם`: 1/4 distinct selections (stuck) - unchanged from WP-037.
- `גרעיני הבסיס`: 1/4 distinct selections (stuck) - unchanged from WP-037, but this run's round 2 answer ("Caudate Nucleus") diverged from the assigned concept entirely, a WP-036-style drift not observed in WP-037's own run of this category.
- `מסילות עצביות`: **3/4 distinct selections** - the best rotation result across WP-036/037/038 for this category. Both successful rotations (R1→R2, R2→R3) occurred specifically in rounds where generation answered in English, exact-matching the assigned concept's own text - the pre-existing WP-034/036 normalized-match capability, correctly preserved and functioning, not new WP-038 capability (Section 9's `identity_recognized_generated_answer=true` cases both fall in this category, both from `normalized_forms`, never from `explicitly_supported_language_forms`, which was empty throughout the entire run).

## 12. A Second, Newly-Surfaced Coverage-Recognition Failure Mode

Round 3 of `מסילות עצביות` selected "Anterior Corticospinal T" - truncated by the exact same *already-disclosed, still-unaddressed* WP-037 limitation ("trailing truncation is not detected," WP-037 section 7.1/completion report section 12), the same shape as `גרעיני הבסיס`'s own persistent "Corpos Str." Generation correctly and completely answered "Anterior Corticospinal Tract" - a well-aligned, correct answer (Section 10, row 9) - but because the *assigned* concept's own stored text is itself incomplete, `concept_identity_matches_text()` correctly (by its own conservative design) did not recognize "Anterior Corticospinal Tract" as identical to "Anterior Corticospinal T," and the identical truncated concept was reselected for round 4.

This is a **distinct root cause** from the cross-script problem WP-038 was built to address (a same-script completeness mismatch, not a language mismatch) but produces the **identical downstream symptom** - repeated reselection of a concept that was, in fact, correctly and completely tested. It is not a WP-038 regression; it is a direct second-order consequence of a gap WP-037 already flagged as unaddressed and out of scope to fix at the time, now shown to also affect coverage recognition, not only anchoring quality.

## 13. Comparison With WP-036 and WP-037 (Section 21)

| Metric | WP-036 | WP-037 | WP-038 |
|---|---:|---:|---:|
| Accepted count | 11/12 | 8/12 | **10/12** |
| Manual target alignment | ~45% (5/11) | 87.5% (7/8) | 80% (8/10) |
| Target selection rotation | High (every round) | Low (stuck most rounds) | Mixed (2/3 categories stuck; 1/3 rotated well) |
| Evidence-derived cross-script identity matches found | N/A (not yet introduced) | N/A (not yet introduced) | **0 of 12 rounds** |
| False-positive identity matches | N/A | N/A | **0** |
| New failure modes surfaced | Context-window ambiguity, inventory-quality issues | Hebrew/English coverage-matching mismatch | Same-script trailing-truncation coverage-matching mismatch |

The desired composite outcome WP-038 section 21 named explicitly - "WP-036 selection behavior + WP-037 alignment improvement + without WP-037's coverage regression" - was **not fully achieved**: alignment was preserved, but the coverage regression for 2 of 3 categories was not resolved, because (per Section 2's investigation) the evidence those two categories' selected concepts actually rest on does not contain the structural pattern needed to resolve it safely.

## 14. Limitations

- **The evidence-derived identity mechanism never fired in this live run** - it is real, tested, and functional, but the current pilot corpus's concepts (as actually selected across 12 rounds) do not contain the explicit adjacent-parenthetical pairing it requires. This is not a defect in the mechanism; it is an honestly-documented property of the available evidence for these specific concepts.
- **Transliteration/translation variation remains completely unaddressed by design** (Section 5) - and this run's own data (three distinct Hebrew renderings of one concept) reinforces that this was the correct call, not merely a cautious one.
- **The newly-surfaced trailing-truncation/coverage interaction (Section 12) is not fixed by this WP** - it is a second-order consequence of an already-disclosed WP-037 gap, out of this WP's own scope (section 12 of the WP-038 spec: "do not redesign the WP-037 concept anchoring algorithm... if tests reveal a direct incompatibility... document it separately" - which this section does).
- **Sample size**: 10 accepted questions and 12 pilot rounds remain a small base for percentages; one additional round could shift alignment/rotation figures noticeably. Reported as directionally consistent with WP-037's findings, not as a statistically definitive rate.
- **`אספקת דם`'s accepted-count recovery is not attributable to this WP's mechanism** (Section 9's caveat) - stated explicitly to avoid overclaiming a result driven by generation stochasticity.

## 15. Architectural Conclusion

**Outcome, per WP-038 section 23's own taxonomy: Outcome C - "Safe deterministic cross-language identity is not feasible" for the concepts this pilot actually encounters.** This is not a failure of implementation: the mechanism was built exactly as the spec's "Preferred Principle: Evidence-Derived Identity" (section 8) describes, is genuinely functional and thoroughly unit-tested, and was investigated against real data *before* any code was written (Section 2) rather than assumed. The honest, evidence-grounded finding is that the specific evidence pattern required to make it fire safely (explicit adjacent bilingual pairing) does not exist in this corpus for the concepts actually selected by the pilot - confirmed identically by both the pre-implementation static check and the live pilot at scale.

Per section 23's own required response to Outcome C: **do not guess** (upheld throughout - `explicitly_supported_language_forms` stayed empty rather than being populated by any looser heuristic); **preserve exact matching** (same-script/normalized matching is fully preserved, unchanged in behavior from WP-034/036); **document the architectural limitation** (this report, plus `docs/ARCHITECTURE.md`'s new WP-038 section); **reconsider whether generation language should instead be constrained** - this becomes the explicit recommendation below.

## 16. Recommendation for the Next WP

Do not attempt further coverage-matching cleverness for the cross-script problem (broader proximity heuristics, transliteration tables, or fuzzy matching) - this WP's own live data (three distinct Hebrew renderings of one concept in one run) is itself evidence that such an approach would be unreliable even if it were architecturally permitted. Two concrete directions remain, both already anticipated by WP-037's own architecture review:

(a) **Constrain generation's answer language for pilot-category questions** to match the assigned concept's own language (e.g. requiring an English-named concept's answer to be expressed in English) - this directly addresses the root cause rather than working around it downstream, but is a prompt-contract change, explicitly out of scope for both WP-037 and WP-038, and would need its own dedicated work package with that scope made explicit.

(b) **Address the newly-surfaced trailing-truncation extraction gap** (Section 12) as a narrower, independently-scoped fix to `refine_concept_inventory()` - unlike the cross-script problem, this has a clear, bounded, structurally-detectable shape (a concept whose reconstruction requires recovering a *trailing* fragment rather than a leading one), and fixing it would likely also improve `גרעיני הבסיס`'s persistent "Corpos Str" stuck-selection pattern, independent of any language-matching work.

Either direction should be validated with the exact same three-category, four-question live methodology established across WP-036/037/038, measuring accepted count, manual alignment, and rotation together (not any one metric alone), per this WP's own Section 13 comparison table.

## 17. Confirmations

- No prompt file was modified.
- No validator was modified.
- No retrieval/chunking/TF-IDF logic was modified.
- WP-037's `refine_concept_inventory()`/`anchor_concept_evidence()` were not modified - confirmed unchanged by the full, unmodified WP-037 test suite passing.
- No semantic matching, embeddings, LLM judge, or fuzzy/edit-distance matching was introduced anywhere.
- `CategoryQuestionSetRequest`/`Response`/`ExamQuestion`/`CategoryCoverage` public/shared contracts were not modified.
- `ConceptIdentity` is internal-only, never schema-exported - confirmed by `scripts/generate_schemas.py` producing byte-identical output.
- Full regression suite passes: **1286/1286**.
- Live pilot performed exactly once, no reruns, no manual concept repair, no configuration changes after seeing results.
- Zero false-positive identity matches observed, live or in dedicated safety tests.

## 18. Files Created/Modified

**Created:**
- `src/exam_generator/planning/concept_identity.py`
- `tests/unit/test_concept_identity.py`

**Modified:**
- `src/exam_generator/planning/planner.py` (`_select_remaining_concepts()` now builds and matches on `ConceptIdentity`; `_plan_targets_from_concept_inventory()` threads `chunk_text_by_id` through earlier)
- `tests/unit/test_planning.py` (3 new integration tests)
- `tests/unit/test_concept_inventory.py` (5 pre-existing tests updated for the new `chunk_text_by_id` parameter, behavior unchanged)
- `docs/ARCHITECTURE.md` (new "Deterministic Concept Identity and Coverage Matching (WP-038)" section)
- `docs/PROJECT_STATUS.md` (Tests count, new Live Evaluation Baseline section, Next WP Context updated, closing sentence)
- `evaluation/live_outputs/README.md` (new row, updated explanatory paragraphs)

---

WP-038 complete.

Tests:
1286 passed, 0 failed

Pilot evaluation:
אספקת דם 4/4, גרעיני הבסיס 2/4, מסילות עצביות 4/4 accepted (10/12, between WP-036's 11/12 and WP-037's 8/12) - the אספקת דם recovery is generation stochasticity, not attributable to this WP's mechanism (see section 9)

Target alignment:
8/10 (80%) manually-verified ALIGNED, preserving WP-037's 87.5% improvement (anchoring itself untouched)

Coverage recognition:
Outcome C - 0/12 rounds found a safe evidence-derived cross-script identity match (confirmed both by pre-implementation investigation and live at scale); same-script normalized matching fully preserved; a second, distinct same-script "trailing truncation" coverage-recognition failure mode was newly surfaced (see section 12)

Completion report:
implementation/WP-038_COMPLETION_REPORT.md

Waiting for architect review.
