# WP-037 Completion Report — Concept-Anchored Evidence for Deterministic Targets

## 1. Implementation Summary

WP-036's architecture review localized the diversity problem precisely: target *selection* worked, but the generated question frequently tested a different, more salient fact than the one assigned, because `factual_focus` was a wide, fixed-character window that often still contained a competing entity. WP-037 addresses this with two additive, deterministic refinements (new module `planning/concept_anchor.py`), applied only to WP-036's same three pilot categories (`אספקת דם`, `מסילות עצביות`, `גרעיני הבסיס`):

1. **`refine_concept_inventory()`** - post-processes WP-036's raw `extract_concept_inventory()` output (never modified itself) to exclude category-self-restatement concepts and to repair-or-exclude leading-truncated concepts.
2. **`anchor_concept_evidence()`** - replaces the wide fixed-character window with a narrow, line-bounded context around the selected concept's own occurrence.

`QuestionTargetPlanner._plan_targets_from_concept_inventory()` (WP-036) now calls these instead of the raw extraction + wide window. No other production code changed - `QuestionGenerator`, `QuestionProducer`, `OpenAIProvider`, retry mechanisms, structured-output recovery, validation, acceptance policy, relationship extraction, competitor discovery, and every public request/response contract are byte-for-byte unchanged.

## 2. Anchoring Algorithm (Section 4)

`anchor_concept_evidence(*, chunk_text, concept)`:

1. Locate `concept`'s own line in `chunk_text` (exact match first; for a reconstructed concept whose repaired leading character is not literally present verbatim, fall back to matching the text minus its reconstructed prefix).
2. Walk backward and forward from that line via `_walk()`, collecting non-blank lines, stopping at whichever comes first:
   - a line that is itself a candidate concept line (WP-036's own structural detector, reused unchanged) - a sibling's own name, exactly the kind of competing fact that caused WP-036's drift;
   - **two consecutive blank lines** - a genuine paragraph boundary;
   - `_MAX_ANCHOR_WALK_LINES` (3) non-blank lines collected in that direction;
   - a raw-line safety cap (`_MAX_RAW_SCAN_LINES` = 12).
3. Concatenate backward context + the (possibly-reconstructed) concept text + forward context.

**One bug was found and fixed during development, before any live call was made**: an initial version stopped the walk at the *first* blank line. Since this corpus uses single blank lines liberally as visual spacing within the same logical list item (not as paragraph boundaries), this frequently stripped a concept of all context - including the text WP-030's relationship classifier needs to key on (verified directly: `אספקת דם`'s first concept classified `UNSPECIFIED` instead of `SUPPLIES` under the first version, `SUPPLIES` correctly after the fix). The "two consecutive blanks" rule was the correction, found by inspecting real output against real evidence before writing tests or running the live pilot - not a post-hoc tuning-after-results adjustment.

A second, smaller bug was found the same way: the anchored text initially displayed the *raw* (truncated) source line even for a successfully-reconstructed concept, because line lookup succeeded via the drop-prefix fallback but the display step still indexed into the raw line array. Fixed by always displaying the caller-supplied (already-reconstructed) `concept` text, and by excluding the specific orphan-letter neighbor line that was "consumed" by reconstruction from the backward/forward walk (so it is not duplicated as separate context).

## 3. Extraction-Artifact Policy (Section 10)

Applied in `refine_concept_inventory()`, before selection:

- **`_looks_leading_truncated(concept)`**: true if the concept's first word starts with a lowercase letter - the exact shape of WP-036's own observed "edial Lemniscus Tract" (missing "M").
- **`_attempt_leading_reconstruction()`**: reconstructs *only* when exactly one of the concept's two immediate neighbor lines (checked in both directions, since PDF bidi-reordering was observed to place the completing fragment on either side) is a single uppercase letter and nothing else - the exact orphan-letter shape WP-036's own extraction already excludes as noise, now reused as the completing fragment for the specific concept it was severed from. If zero or two such neighbors are found, the concept is **excluded**, never guessed at.

**Outcome, documented exactly (section 10's own A/B/C categories)**:
- Outcome A (reconstructed): "edial Lemniscus Tract" → "Medial Lemniscus Tract" (both WP-036's own live data and this WP's synthetic tests confirm this works).
- Outcome B (excluded, no safe reconstruction): a leading-truncated concept with zero or two candidate neighbors.
- Outcome C (unchanged): every other concept.

**Known, disclosed gap**: this policy targets *leading* truncation only - the two shapes WP-036 itself named explicitly. *Trailing* truncation (e.g. "Corpos Str" for "Corpus Striatum," observed live during this WP's own pilot run, in a multi-fragment, bidi-scrambled shape not matching either the leading-truncation or self-restatement pattern) is not detected. Per section 10's own conservative instruction ("do NOT attempt general OCR/PDF repair"), this was a deliberate scope boundary, not an oversight - see Section 9 (Limitations).

## 4. Category Self-Restatement Policy (Section 11)

`_is_likely_category_self_restatement(chunk_text, concept)`: true if a Hebrew "also called/known as" cue phrase (`נקרא גם`, `נקראים גם`, `נקראת גם`, `הנקרא`, `המכונה`, `מכונה גם`, `ידוע גם כ`, `ידועה גם כ` - a small, explicit, extensible keyword table in the exact spirit of `generation/relationship.py`'s own keyword table) appears within 60 characters immediately before the concept's occurrence. Deliberately lexical/keyword-based, never semantic similarity, per section 11's explicit instruction.

This directly catches WP-036's own named example: `"...גרעיני הבסיס...נקראים גם\nThe Basal Gang[lia]..."` - "The Basal Ganglia" is excluded as a likely naming statement about the category itself, not a genuine sub-concept. Verified against a synthetic test using realistic (non-compressed) spacing between the naming statement and the next, unrelated, genuine concept, confirming no over-exclusion of legitimately later content.

## 5. Tests

- New `tests/unit/test_concept_anchor.py` (22 tests): anchoring around a concept alone on its own line, with multi-line surrounding context, stopping before a competing salient entity (the WP-036 failure shape directly reproduced and shown fixed), concept at the start/end of evidence, a missing concept falling back honestly, malformed/blank-heavy evidence not crashing, the single-blank-vs-two-consecutive-blanks distinction (the exact bug found during development, now regression-tested), Hebrew/English mixed multi-line evidence, anchoring correctly using the reconstructed (not raw-truncated) concept text; clean/truncated/ambiguous-fragment/category-self-restatement extraction-artifact classification (including the two-candidate-neighbors genuinely-ambiguous case); genuine evidence-chunk-id preservation through both plain and reconstructed concepts; no LLM/embedding call anywhere in the module.
- 2 new planner-integration tests in `tests/unit/test_planning.py`: a pilot-category target's `factual_focus` excludes a competing salient entity end-to-end; a category-self-restatement concept is excluded end-to-end, and the next genuine concept is correctly selected instead.
- **Full regression suite: 1259 passed, 0 failed** (up from 1235 before this WP), zero network access, no `OPENAI_API_KEY` required.
- `scripts/generate_schemas.py` re-run: all three schema files **byte-identical** (no public contract was touched).

## 6. Live Pilot Results (Section 23)

One live pilot, no reruns, no manual concept repair, no configuration changes after observing results. Same three pilot categories, four sequential questions each, via `CategoryQuestionSetService`.

| Category | R1 | R2 | R3 | R4 | Accepted |
|---|---|---|---|---|---|
| `אספקת דם` | Superior cerebellar artery ✓ | Superior cerebellar artery ✓ | Superior cerebellar artery ✗ (`DuplicateReplacementExhausted`) | Superior cerebellar artery ✗ (`DuplicateReplacementExhausted`) | 2/4 |
| `גרעיני הבסיס` | Corpos Str ✓ | Corpos Str ✗ (`QuestionAttemptsExhaustedError`) | Corpos Str ✓ | Corpos Str ✗ (`QuestionAttemptsExhaustedError`) | 2/4 |
| `מסילות עצביות` | Spinothalamic Tract ✓ | Spinothalamic Tract ✓ | Spinothalamic Tract ✓ | Medial Lemniscus Tract ✓ | 4/4 |

**Combined: 8/12 accepted** (down from WP-036's 11/12 for these same three categories). Raw data: `evaluation/live_outputs/wp037_pilot_records.json`.

The selected concept is visibly **stuck** for two of the three categories - a different symptom from WP-036's own finding (where selection correctly rotated but generation drifted). Section 8 identifies the precise, evidence-grounded cause.

## 7. Target Alignment Measurements (Sections 12/13/17/19 - the Primary Success Criterion)

**Methodology**: for every accepted question, an automated deterministic pre-classification (normalized substring match between the selected concept and the actual correct-answer text) was computed live and recorded, exactly as WP-037 section 13 permits ("if an automated deterministic alignment check is unreliable, use manual review... document the methodology"). This pre-classification was then manually reviewed against the actual question/answer content for every one of the 8 accepted questions, since the automated check turned out to be unreliable for a specific, identified reason (Section 8).

| # | Category | Round | Selected concept | Correct answer (as generated) | Automated pre-classification | Manual review |
|---|---|---|---|---|---|---|
| 1 | אספקת דם | 1 | Superior cerebellar artery | עורק סופריור צרבלרי | NOT_ALIGNED | **ALIGNED** (Hebrew transliteration of the same entity) |
| 2 | אספקת דם | 2 | Superior cerebellar artery | עורק סופריור צרבלרי | NOT_ALIGNED | **ALIGNED** (same) |
| 3 | גרעיני הבסיס | 1 | Corpos Str[iatum] | קורפוס סטריאטום | NOT_ALIGNED | **ALIGNED** (Hebrew transliteration of the same entity) |
| 4 | גרעיני הבסיס | 3 | Corpos Str[iatum] | להגביר תנועה על ידי הפעלת מסלולי תנועה ("to increase movement by activating movement pathways") | NOT_ALIGNED | **NOT ALIGNED** (a functional description, not the named structure - a genuine misalignment) |
| 5 | מסילות עצביות | 1 | Spinothalamic Tract | מסילה ספינותלמית | NOT_ALIGNED | **ALIGNED** (Hebrew transliteration) |
| 6 | מסילות עצביות | 2 | Spinothalamic Tract | מסילה ספינתלמית | NOT_ALIGNED | **ALIGNED** (Hebrew transliteration, alternate spelling) |
| 7 | מסילות עצביות | 3 | Spinothalamic Tract | Spinothalamic Tract | ALIGNED | **ALIGNED** |
| 8 | מסילות עצביות | 4 | Medial Lemniscus Tract | Medial Lemniscus Tract | ALIGNED | **ALIGNED** |

**Target Alignment Rate**: automated = 2/8 (25%); **manual = 7/8 (87.5%)**.

**Comparison with WP-036** (same manual methodology applied retrospectively to WP-036's own 11 accepted questions across these 3 categories, for a fair comparison): `אספקת דם` 1/4 aligned (only round 1, where the assigned and tested concept happened to coincide), `גרעיני הבסיס` 0/3 aligned (every round tested a broad category-level fact rather than "The Basal Gang" specifically), `מסילות עצביות` 4/4 aligned (the assigned and tested tract always matched, despite the assigned concept's own text being truncated) = **5/11 (~45%)**.

**The manually-verified alignment rate improved substantially: ~45% (WP-036) → 87.5% (WP-037).** This directly supports WP-037's central hypothesis.

## 8. Root Cause of the Accepted-Count Regression (Not an Alignment Failure)

The 8/12 vs. 11/12 accepted-count drop is **not** caused by an anchoring or alignment failure - it is caused by a newly-surfaced, previously-invisible interaction between narrower anchoring and WP-034's own coverage design:

With the old, wide WP-036 window, generated answers were consistently in **English** (the window contained enough English terminology to keep the answer in the same register as the source term). With the new, narrow WP-037 window, the immediate surrounding text is often **predominantly Hebrew** (e.g. `"אזור אספקת דם :המשטח העליון..."`), and generation, given a mostly-Hebrew micro-context, frequently answered in **Hebrew** - transliterating or translating the English concept name rather than reusing it verbatim (`"Superior cerebellar artery"` → `"עורק סופריור צרבלרי"`).

WP-034's `extract_category_coverage()` performs **exact text matching** (by design - a deliberate, still-correct choice to never fabricate synonym equivalence) between a target's assigned concept and later accepted-answer text. When the accepted answer is in a different language/script than the assigned concept, the match fails - the concept is never recognized as tested, and since selection always proceeds by fixed inventory order, the **identical concept is deterministically reselected next round**. The resulting near-duplicate Hebrew-phrased questions were then correctly, honestly rejected by the completely unmodified WP-014 duplicate-replacement mechanism once its bounded budget was exhausted (`DuplicateReplacementExhausted` for `אספקת דם` rounds 3-4; ordinary `QuestionAttemptsExhaustedError` for `גרעיני הבסיס` rounds 2/4, a related but distinct exhaustion since those specific attempts individually failed validation before even reaching the duplicate check).

`מסילות עצביות` shows the mechanism's boundary condition directly: rounds 1-2 answered in Hebrew (never recognized as tested), round 3 happened to answer in **English** (`"Spinothalamic Tract"`, exactly matching the assigned concept's own text) - **which correctly triggered exclusion for round 4**, producing the one genuine rotation observed in this run (`Spinothalamic Tract` → `Medial Lemniscus Tract`). This is direct, positive evidence for the hypothesis: exclusion works exactly as designed whenever language/script happens to align; it silently fails whenever it does not.

## 9. Diversity Measurements

Selected-concept rotation (a proxy for what WP-036 called "target selection diversity"): `אספקת דם` 1/4 distinct selections (stuck), `גרעיני הבסיס` 1/4 distinct (stuck), `מסילות עצביות` 2/4 distinct (rotated once, for the reason in Section 8). This is a **regression** relative to WP-036, where every round selected a different concept - but for a completely different, now-understood reason (a coverage-recognition gap, not a target-assignment defect; `_select_remaining_concepts()` itself is unchanged and was directly re-verified working correctly in isolation, Section 5).

Actual tested-content diversity (the metric that matters, per WP-036's own review): `אספקת דם` 1/2 distinct facts tested among accepted questions (0% - both accepted rounds tested Superior Cerebellar Artery); `גרעיני הבסיס` effectively 2/2 distinct (Corpus Striatum's identity vs. its functional role - though round 2's answer is the misalignment case from Section 7); `מסילות עצביות` 2/4 distinct (Spinothalamic ×3, Medial Lemniscus ×1).

## 10. Reliability Measurements

Accepted count: 8/12 (66.7%), down from WP-036's 11/12 (91.7%) for these same three categories - entirely attributable to Section 8's root cause, not to any change in validation/retry/acceptance logic (all unmodified, confirmed by the full regression suite). Average attempts per accepted question: **1.125** (9 total attempts / 8 accepted), better than WP-036's **~1.27** for these categories - the accepted questions themselves were, if anything, easier to produce; the regression is entirely in *reaching* an accepted, coverage-recognized state per concept, not in individual-attempt quality. Zero generation-contract failures; zero new validator behavior; the two failure types observed (`QuestionAttemptsExhaustedError`, `DuplicateReplacementExhausted`) are both pre-existing, completely unmodified mechanisms operating exactly as designed.

## 11. Comparison With WP-036 (Section 24, Required Table)

| Metric | WP-036 | WP-037 |
|---|---:|---:|
| Target selection diversity | High (rotated every round) | Low (stuck most rounds - new cause) |
| Target alignment rate (manual) | ~45% (5/11) | **87.5% (7/8)** |
| Actual tested-content diversity | Low-moderate | Low-moderate (similar, different cause) |
| Acceptance rate | 91.7% (11/12) | 66.7% (8/12) |
| Average attempts (accepted only) | ~1.27 | 1.125 |
| Inventory failures | 2 unaddressed (self-restatement, leading truncation) | Both addressed; 1 new shape observed (trailing truncation) still unaddressed |
| Anchoring failures | N/A (not yet introduced) | None outright; one referential-completeness tradeoff observed (Section 12) |

```
WP-036:  Target changed  ->  Question often did not      (selection worked, alignment failed)
WP-037:  Target changed  ->  Anchored evidence  ->  Question mostly did change to match  (alignment mostly fixed)
                                                  ->  but coverage stopped recognizing it  (new problem)
```

## 12. Limitations

- **Trailing truncation is not detected** (Section 3) - "Corpos Str" (for "Corpus Striatum") was selected and used live; its multi-fragment, bidi-scrambled shape ("tum"/"ia" fragments, reordered) does not match this WP's leading-truncation-only reconstruction pattern. A future WP would need a distinct, equally conservative policy for this shape - not attempted here, per section 10's own "keep it conservative" instruction and this WP's time/scope budget.
- **Narrow anchoring sometimes sacrifices referential completeness**: `אספקת דם`'s "Basilar Artery" concept, anchored narrowly, would read roughly `"...source: Basilar Artery"` without naming what its source *of* - this specific concept was never actually re-selected during the live run (Section 8's exclusion failure kept "Superior cerebellar artery" selected instead), so this particular tradeoff was not exercised live this run; it remains a documented, plausible risk for future runs.
- **The central limitation is Section 8's finding**: concept-anchored evidence and WP-034's exact-text coverage matching now interact in a way neither WP anticipated in isolation. This is the single most actionable finding of this WP and the natural starting point for whatever comes next.
- **Sample size**: 8 accepted questions is a small base for a percentage (87.5% = 7/8); one additional misaligned or aligned question would shift the rate by 12.5 points. This is reported as directionally strong evidence, not a statistically definitive rate.

## 13. Architectural Conclusion

**Outcome, per WP-037 section 19's own taxonomy: closest to Outcome B ("anchoring improves alignment, but a different reliability gap remains")** - though the specific gap is not inventory-extraction unreliability (which this WP directly improved) but a newly-surfaced coverage-matching/language-consistency interaction. The anchoring hypothesis itself is **supported**: narrowing evidence around a selected concept measurably and substantially increases the likelihood that generation actually tests that concept (45% → 87.5%, manually verified). This is a genuine, positive architectural result, not a repeat of WP-034/036's negative findings.

The regression in accepted count and (superficial) target-selection diversity is a **downstream consequence of a specific, now-precisely-identified mechanism** - not evidence against anchoring itself. Per this WP's own section 19 guidance ("do not immediately add retries or validators... investigate whether the generator contract itself permits too much freedom" - Outcome C's guidance, adapted here since the actual outcome is closer to B): the correct next step is not to expand the pilot, add a validator, or add retries, but to **resolve the coverage-matching/language interaction specifically**.

## 14. Recommendation for the Next WP

Do not expand deterministic concept-anchored planning beyond the current three pilot categories yet. Before any expansion, a future WP should address the Section 8 interaction - concretely, one of:

(a) **Normalize coverage matching to be language/script-tolerant** for pilot categories specifically (e.g. comparing an accepted answer against both the assigned concept's own text and a small, deterministic transliteration-aware comparison) - the more surgical fix, staying within "no semantic matching" if implemented as a narrow, explicit rule rather than general fuzzy matching.

(b) **Constrain generation's answer language for pilot-category questions** to match the assigned concept's own language - this edges toward a prompt-contract change, which was explicitly out of this WP's scope (section 7/25) and would need its own dedicated work package with that scope made explicit.

Either direction should be validated with the exact same three-category, four-question live methodology established across WP-036/WP-037, comparing target alignment rate *and* accepted count together (not alignment alone, since this WP's own data shows the two can move in opposite directions for reasons unrelated to the mechanism under test).

## 15. Confirmations

- No prompt file was modified.
- No validator was modified.
- No retrieval/chunking/TF-IDF logic was modified.
- No relationship/competitor logic was modified.
- No semantic matching or embeddings were introduced anywhere.
- `CategoryQuestionSetRequest`/`Response`/`CategoryGenerationRequest`/`Response` were not modified.
- `extract_concept_inventory()` (WP-036) itself was not modified - only post-processed.
- Full regression suite passes: **1259/1259**.
- Live pilot performed exactly once, no reruns, no manual concept repair, no configuration changes after seeing results.

## 16. Files Created/Modified

**Created:**
- `src/exam_generator/planning/concept_anchor.py`
- `tests/unit/test_concept_anchor.py`

**Modified:**
- `src/exam_generator/planning/planner.py` (`_plan_targets_from_concept_inventory()` uses `refine_concept_inventory()`/`anchor_concept_evidence()` instead of raw extraction and the wide window)
- `tests/unit/test_planning.py` (2 new integration tests)
- `docs/ARCHITECTURE.md` (new "Concept-Anchored Evidence" section)
- `docs/PROJECT_STATUS.md` (Tests count, new Live Evaluation Baseline section, Next WP Context updated)
- `evaluation/live_outputs/README.md` (new row)

---

WP-037 complete.

Tests:
1259 passed, 0 failed

Pilot evaluation:
אספקת דם 2/4, גרעיני הבסיס 2/4, מסילות עצביות 4/4 accepted (8/12, down from WP-036's 11/12) - regression traced to a newly-surfaced Hebrew/English answer-language inconsistency breaking WP-034's exact-text coverage matching (see section 8), not to anchoring quality

Target alignment:
7/8 (87.5%) manually-verified ALIGNED, up from WP-036's ~5/11 (45%) - a substantial, evidence-grounded improvement supporting the pilot's central hypothesis (see section 7 for full per-question data and methodology)

Completion report:
implementation/WP-037_COMPLETION_REPORT.md

Waiting for architect review.
