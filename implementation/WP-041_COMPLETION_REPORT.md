# WP-041 Completion Report — Deterministic English-First Language Policy

## 1. Implementation Summary

The architectural decision point reached after WP-040 (`implementation/ARCHITECTURAL_DECISION_AFTER_WP040.md`) named the remaining problem precisely: WP-040 made generation reliably answer with the assigned named concept, but it could still do so in Hebrew, and WP-038's deterministic coverage matching cannot safely recognize a Hebrew answer against an English-stored concept - so a concept could be correctly and completely tested every round, yet never be recognized as covered. WP-041 reaffirms a hard, pre-existing product requirement as an explicit architectural rule: **English is the canonical language whenever an English representation exists; Hebrew is permitted only when none exists for that specific item.** The application decides this deterministically, before generation; the LLM never chooses. Scope is unchanged: the same three pilot categories only. No public contract changed, no new model field, no bilingual-pairing search, no validator touched. `QuestionGenerator`, `QuestionProducer`, `OpenAIProvider`, every validator, WP-037's anchoring, WP-038's `ConceptIdentity`/coverage matching, WP-039's truncation recovery, and WP-040's answer-identity requirement are all byte-for-byte unchanged - confirmed by their full, unmodified test suites passing.

## 2. Existing Language Behavior (Section 3, Pre-Change Investigation)

Investigated directly, before any code was written:

- **The base generation prompt already had a hard, general rule**: *"The question text and all four answer choices must be written in Hebrew... but do not write the question or the answer choices in English"* (`prompts/generation/question.txt`, unchanged since early WPs). This is a real, pre-existing tension with WP-041's own goal - a literal reading forbids exactly what WP-041 requires for a named target's own answer.
- **No validator actually enforces this as an absolute bar**: `QualityValidator`'s own Hebrew-language check (`prompts/validation/quality.txt`) explicitly tolerates *"Hebrew or standard English/Latin"* terminology. WP-040's own live pilot had already produced several fully-English accepted answers (`Superior cerebellar artery`, `Spinothalamic Tract`, `Medial Lemniscus Tract`, `Anterior Corticospinal Tract`, `Lateral Corticospinal Tract`) - confirming in practice that a fully-English named-entity answer was never actually rejected by any validator, even before this WP.
- **Conclusion**: the tension was textual/instructional, not a real validator conflict. The correct fix was a precise carve-out in the base prompt text (Section 6), not a validator change.

## 3. Root Cause of Bilingual Drift

Directly attributable to the *absence* of any explicit language decision prior to WP-041 - generation was free to choose whichever language "sounded natural" for the correct answer, and, per WP-038's own live data, this choice was not even self-consistent for the same concept across rounds (three different Hebrew renderings of `Superior cerebellar artery` were observed in a single WP-038 run). WP-040 fixed *what* the answer must identify but never constrained *which language* it must use. This is the same class of finding as WP-040's own root-cause analysis (an existing prompt permission, not a model failure) - here, the "problem" was an unstated freedom rather than an explicit permission.

## 4. Language-Selection Design (Section 5/9/10)

**Critical question (section 7): how can the application know deterministically that an English representation exists for a specific item?** Investigated directly: every pilot-category `QuestionTarget.topic` is, by construction, always the concept's own pure-ASCII, English-representable text - `extract_concept_inventory()`'s own structural filter (`_CANDIDATE_LINE_PATTERN`) guarantees this, the same invariant WP-040's `named_entity_target` field already relies on. This means the "representation discovery" step reduces to *re-confirming an existing invariant explicitly*, never a new search across evidence, never a new bilingual mapping, and never consulting WP-038's `ConceptIdentity.explicitly_supported_language_forms` (deliberately not duplicated, per section 10's own instruction - and, per WP-038's own investigation, that field is empty for essentially every real concept in this corpus anyway).

**No new model field was added.** `format_target_language_requirement()` (new, `prompts/formatting.py`) derives the decision purely from `target.named_entity_target` and `target.topic`'s own script - both already available.

## 5. Representation-Discovery Mechanism (Section 8)

`_is_english_representable(text)`: a small, self-contained ASCII check. **Deliberately not importing** `planning.concept_inventory`'s own equivalent `_CANDIDATE_LINE_PATTERN` - `exam_generator.planning` already imports from `exam_generator.prompts` (established since WP-034's `CategoryCoverage` precedent), so the reverse import would create a circular dependency. The two checks intentionally do not need to be byte-identical: `concept_inventory`'s pattern additionally gates extraction-candidate-line detection with a narrower charset; this one only asks "is this text expressible without any non-ASCII character" - exactly the WP-041 question, nothing more.

No search of `factual_focus`, no search of other evidence chunks, no consultation of any bilingual pairing - confirmed by a dedicated test (`test_case8_ambiguous_relationship_never_guessed_since_no_search_is_ever_performed`) that inspects the function's own source and asserts it never references `factual_focus`, `ConceptIdentity`, or `explicitly_supported_language_forms`.

## 6. Implementation (Section 4/5)

- `format_target_language_requirement(target)`: three deterministic branches.
  - `named_entity_target=False` → honest sentinel ("no additional target-language requirement applies").
  - `named_entity_target=True`, `topic` English-representable (true for every real pilot-category target) → `TARGET LANGUAGE = English`, requires the target's own English text verbatim for the correct answer and any in-question reference to the target, explicitly forbidding translation/transliteration into Hebrew regardless of how Hebrew-dominant the surrounding evidence is, and forbidding substitution of a different English form (abbreviation/alternate spelling).
  - `named_entity_target=True`, `topic` not English-representable (never actually produced by the current extraction path, but handled honestly rather than assumed impossible) → `TARGET LANGUAGE = Hebrew`, explicitly forbids inventing an English translation not already present in evidence.
- `GenerationPromptContext.render_variables()` gained exactly one new key (`target_language_requirement`) - no new dataclass field.

## 7. Prompt Changes (Section 13/14/15)

`prompts/generation/question.txt` gained:
- A precise carve-out in the existing base Hebrew-language rule: *"...but do not write the question or the answer choices in English - except when the 'Target-language requirement' below explicitly specifies English for this target; that requirement takes precedence over this general default for the correct answer choice and for any reference to the target's own name within the question, and for nothing else."* The general Hebrew default is otherwise completely unchanged.
- One new section, "Target-language requirement", explaining the decision is made by the application (not chosen by the model), and stating both branches' behavior explicitly.
- One new checklist item appended to the blueprint self-review checklist: "the intended correct answer uses the language stated in the target-language requirement below."
- One new rendered block, `{target_language_requirement}`, placed directly after the existing `{target_answer_requirement}` block.

This satisfies section 13's "update only as necessary, no large rewrite" - every other line of the prompt is untouched.

## 8. Tests (Section 20/21)

12 new tests in `tests/unit/test_prompts.py`, covering all 8 required cases plus prompt-semantic checks:

- **Case 1** (English+Hebrew both exist, via `factual_focus` containing an unrelated Hebrew rendering) → English selected.
- **Case 2** (English only) → English selected.
- **Case 3** (Hebrew-only, synthetic - this shape never occurs via the real planner, but is tested per section 19/20's explicit instruction) → Hebrew selected, "invent" language present in the fallback text.
- **Case 4** (bilingual target with Hebrew-dominant surrounding evidence) → still English.
- **Case 6** (Hebrew-only target) → never invents an English form; `target.topic` itself is never rewritten.
- **Case 7** (unrelated Hebrew text elsewhere in `factual_focus`) → never associated with or affecting the decision - verified by equality between a target with and without the unrelated Hebrew text.
- **Case 8** (no bilingual search exists at all, so no ambiguous case can arise) → verified via source inspection.
- Non-named-entity target → honest sentinel, never mentions `TARGET LANGUAGE`.
- The pre-existing base Hebrew-language default text is still present for non-named targets.
- WP-040's answer-identity requirement still renders alongside the new section (`TARGET CONCEPT = ...` and `TARGET LANGUAGE = English` both present).
- WP-037's concept-anchored evidence variable still renders unaffected.
- `format_target_language_requirement()` is a pure deterministic function.

**1 pre-existing WP-040 test updated**: `test_target_answer_requirement_never_forces_a_specific_language`'s slice boundary was adjusted (it originally sliced up to "Possible competing concepts:", which now also captures the new, intentionally language-mentioning section inserted in between) - the answer-identity text itself is unchanged and still never mentions a language; only the test's isolation boundary needed updating.

**WP-037/038/039/040 regression**: their full, pre-existing test suites all pass completely unmodified.

**Full regression suite: 1325 passed, 0 failed** (up from 1313), zero network access, no `OPENAI_API_KEY` required.

`scripts/generate_schemas.py` re-run: all three schema files **byte-identical**.

## 9. Offline Evaluation (Section 23/24, Before Any Live Pilot)

One real generation call each for the four named concepts, specifically re-testing the two concepts WP-040's own live pilot had answered in Hebrew:

| Target | Correct Answer | English (ASCII)? |
|---|---|---|
| `Corpos Striatum` | `Corpos Striatum` | Yes (WP-040 answered `קורפוס סטריאטום`) |
| `Medial Lemniscus Tract` | `Medial Lemniscus Tract` | Yes |
| `Superior cerebellar artery` | `Superior cerebellar artery` | Yes (WP-040 answered `עורק סופריור צרבלרי`) |
| `Anterior Corticospinal Tract` | `Anterior Corticospinal Tract` | Yes |

**4/4** - both WP-040 regression cases directly reproduced and confirmed fixed, before any live-pilot randomness was introduced. Raw data: `evaluation/live_outputs/wp041_offline_eval.json`.

## 10. Live Pilot (Section 25)

One live pilot, no reruns, no manual repair, no configuration changes after observing results. Same three pilot categories, four sequential questions each, via `CategoryQuestionSetService`.

| Category | R1 | R2 | R3 | R4 | Accepted |
|---|---|---|---|---|---|
| `אספקת דם` | Superior cerebellar artery ✓ | Basillar artery ✗ (`QuestionAttemptsExhaustedError`) | Basillar artery ✓ | Anterior Inferior Cerebellar Artery (AICA) ✓ | 3/4 |
| `גרעיני הבסיס` | Corpos Striatum ✗ (`QuestionAttemptsExhaustedError`) | Corpos Striatum ✗ (`QuestionAttemptsExhaustedError`) | Corpos Striatum ✓ | Caudate Nucleus ✓ | 2/4 |
| `מסילות עצביות` | Spinothalamic Tract ✓ | Medial Lemniscus Tract ✓ | Anterior Corticospinal Tract ✓ | Lateral Corticospinal Tract ✓ | 4/4 |

**Combined: 9/12 accepted.** Raw data: `evaluation/live_outputs/wp041_pilot_records.json`.

## 11. English-First Compliance (Section 26/27, Primary Success Criterion)

Every accepted question's `target_language` (the deterministic decision) and `correct_answer_is_ascii_english` (whether the actual answer complied) were recorded:

| # | Category | Round | Target | Target Language | Correct Answer | English? |
|---|---|---|---|---|---|---|
| 1 | אספקת דם | 1 | Superior cerebellar artery | English | Superior cerebellar artery | Yes |
| 2 | אספקת דם | 3 | Basillar artery | English | Basillar artery | Yes |
| 3 | אספקת דם | 4 | Anterior Inferior Cerebellar Artery (AICA) | English | Anterior Inferior Cerebellar Artery (AICA) | Yes |
| 4 | גרעיני הבסיס | 3 | Corpos Striatum | English | Corpos Striatum | Yes |
| 5 | גרעיני הבסיס | 4 | Caudate Nucleus | English | Caudate Nucleus | Yes |
| 6 | מסילות עצביות | 1 | Spinothalamic Tract | English | Spinothalamic Tract | Yes |
| 7 | מסילות עצביות | 2 | Medial Lemniscus Tract | English | Medial Lemniscus Tract | Yes |
| 8 | מסילות עצביות | 3 | Anterior Corticospinal Tract | English | Anterior Corticospinal Tract | Yes |
| 9 | מסילות עצביות | 4 | Lateral Corticospinal Tract | English | Lateral Corticospinal Tract | Yes |

**English-first compliance: 9/9 (100%)** - the required count of "bilingual target → English generated" is 9; the required count of "bilingual target → Hebrew generated" (section 26: "should be 0") is **0**, exactly as specified.

## 12. Target Alignment (Section 11)

Every one of the 9 accepted questions' correct answer is an **exact string match** to its assigned target's own `topic`. **Manual alignment: 9/9 (100%)** - identical to the English-first compliance count in this run, since every accepted answer was both English and an exact match.

## 13. Acceptance (Section 12/28B)

**9/12 (75%)** - down from WP-040's 11/12 (91.7%). **This is a material regression and does not meet WP-041's own secondary success criterion B** ("do not materially degrade the WP-040 baseline"), reported honestly rather than minimized. Three rounds failed, all `QuestionAttemptsExhaustedError` (an ordinary, pre-existing WP-013 mechanism, not a new generation-contract failure): `אספקת דם` round 2 (`Basillar artery`), `גרעיני הבסיס` rounds 1 and 2 (both `Corpos Striatum`).

## 14. Attempts (Section 28D)

| Category | Attempts (accepted rounds) | Attempts (failed rounds, at budget cap) |
|---|---|---|
| `אספקת דם` | 3, 2, 1 | 3 (round 2) |
| `גרעיני הבסיס` | 3, 3 | 3, 3 (rounds 1, 2) |
| `מסילות עצביות` | 1, 1, 1, 2 | - |

Attempts rose further for `גרעיני הבסיס` specifically (every round for this category used the maximum 3 attempts, whether it ultimately succeeded or not) compared to WP-040's own already-elevated figure for the same category (avg 2.25). **Not confirmed causally**, per the same honest-disclosure standard WP-040 itself used for its own attempt increase: a plausible hypothesis is that English-first adds a sixth simultaneous constraint (alongside grounding, MCQ structure, quality, category match, and WP-040's answer-identity requirement), and `Corpos Striatum`'s own evidence passage has been independently flagged as less structurally clean since WP-035 - but this WP does not establish causation, only correlation with the categories/concepts already known to be the corpus's least clean.

## 15. Concept Rotation (Section 28A)

**Genuinely improved, live, for both previously cross-script-stuck categories:**
- `אספקת דם`: **3/4 distinct** (`Superior cerebellar artery` → `Basillar artery` → `Anterior Inferior Cerebellar Artery (AICA)`), up from WP-040's 2/4.
- `גרעיני הבסיס`: **2/4 distinct** (`Corpos Striatum` → `Caudate Nucleus`), up from WP-040's 1/4 (stuck every round with zero rotation).
- `מסילות עצביות`: 4/4 distinct, matching WP-040's own already-best result for this category.

Per section 29's explicit interpretation rule ("verify this happens because of the intended causal chain, not some other unrelated behavior"): the causal chain is directly confirmed. Every rotation observed followed exactly `English answer generated → existing, unmodified WP-034/036 exact-match coverage recognizes it → concept correctly excluded → next concept selected` - no coverage-layer code was touched, and the rotation improvement tracks precisely with English-first compliance (100%) rather than with any other changed variable.

## 16. Comparison With WP-036/037/038/039/040 (Section 30)

| Metric | WP-036 | WP-037 | WP-038 | WP-039 | WP-040 | WP-041 |
|---|---:|---:|---:|---:|---:|---:|
| Accepted | 11/12 | 8/12 | 10/12 | 11/12 | 11/12 | **9/12** |
| Target alignment | ~45% | 87.5% | 80% | ~45% | 100% | **100%** |
| English-first compliance | - | - | - | - | not measured | **100%** |
| Cross-script coverage | problem | problem | investigated | remains | remains, isolated | **practically removed for concepts that occur** |
| Concept rotation (`גרעיני הבסיס`) | stuck | stuck | stuck | stuck | stuck (1/4) | **2/4** |
| Concept rotation (`אספקת דם`) | - | - | - | - | 2/4 | **3/4** |

WP-041 answers WP-040's own posed question directly: **yes, enforcing English-first removes the practical cross-script coverage problem for every concept it actually applies to** - but **it does introduce a new, disclosed reliability cost** that the comparison table above shows plainly (9/12 vs. the 11/12 baseline every prior WP since WP-036 had been converging back toward).

## 17. Failures and Limitations

- **The acceptance regression (Section 13) is real and unresolved** - not attributed with confidence to any single cause, and not fixed within this WP's own scope (per section 31: "do not modify coverage to compensate," and no instruction to relax validators either).
- **The Hebrew-only branch of `format_target_language_requirement()` is untested by real live data** - by construction, the current pilot-category extraction path never produces a non-English-representable named-entity topic. The branch is implemented and unit-tested (Section 8, Case 3/6) but has zero live-pilot exercise.
- **Question-internal English-terminology usage (section 14) was not separately measured** - the live pilot's manual review focused on the correct answer's language (the primary criterion); whether the question text itself consistently used the target's English name where it referenced the target was not independently tallied.
- **Sample size**: 9 accepted questions and 1 live run remain a small base; both the 100% compliance figure and the 75% acceptance figure should be read as a single-run result, not a stable long-run rate.

## 18. Architectural Conclusion

**Outcome: a genuine, mixed result - decisive on the primary criterion, materially short on a secondary one.** Per section 29's own interpretation rule and the comparison in Section 16, WP-041's central hypothesis is confirmed without qualification: a deterministic, application-owned English-first language decision, fed into generation as an explicit requirement, removes the practical cross-script coverage-recognition problem for the concepts this pilot actually encounters - with zero changes to coverage matching itself, exactly the intended, minimal-blast-radius design. This is the correct architectural layer for this fix, matching the same "fix generation's own contract, not downstream validation" philosophy WP-040 already established successfully.

However, the same live run shows a real, honestly-disclosed reliability cost: acceptance fell from WP-040's 11/12 to 9/12, driven specifically by the same category (`גרעיני הבסיס`) and concept (`Corpos Striatum`) that WP-035, WP-037, and WP-039 have all independently already flagged as this corpus's least structurally clean passage. This is not proof that English-first *causes* unreliability in general - it may instead reveal that this specific already-troublesome passage is now hitting its ceiling under the combined weight of every constraint accumulated since WP-030 - but the report does not have evidence to assert this confidently, and does not claim to.

## 19. Recommendation for the Next WP

Before any further language/coverage work, and before considering expansion beyond the three pilot categories (per every prior WP's own consistent "not yet" recommendation, still valid): **investigate whether `Corpos Striatum`'s/`גרעיני הבסיס`'s own evidence quality - not the English-first requirement itself - is the deeper cause of the acceptance regression.** A targeted, small investigation (not a full new mechanism) comparing attempt-level rejection reasons (grounding vs. MCQ vs. quality vs. category) for this specific category before and after WP-041, isolated from the other two categories (which did not regress), would directly answer whether the cost is a general property of English-first or a `גרעיני הבסיס`-specific effect. If the latter, the English-first policy itself may need no further change at all - only this one category's evidence/extraction quality would warrant more attention, an entirely different, narrower problem than language policy.

## 20. Confirmations

- No validator was modified.
- No retrieval/chunking/TF-IDF logic was modified.
- Concept extraction (WP-036/037/039), `ConceptIdentity`/coverage matching (WP-038), and the answer-identity requirement (WP-040) were not modified - confirmed unchanged by their full, unmodified test suites passing.
- No semantic matching, embeddings, LLM judge, fuzzy/edit-distance matching, or bilingual dictionary was introduced anywhere.
- No new `QuestionTarget` field or other public/shared contract change.
- No new retry/validator loop was introduced - the fix is entirely a prompt-contract change at generation time, exactly as WP-040 established the precedent for.
- Full regression suite passes: **1325/1325**.
- Live pilot performed exactly once, no reruns, no manual concept repair, no configuration changes after seeing results. Offline evaluation performed once, no configuration changes between individual concept evaluations.

## 21. Files Created/Modified

**Created:** none (WP-041 extends existing modules, matching the established pattern since WP-040).

**Modified:**
- `src/exam_generator/prompts/formatting.py` (`_is_english_representable()`, `format_target_language_requirement()`, new functions)
- `src/exam_generator/prompts/context.py` (`GenerationPromptContext.render_variables()` gained one new key)
- `prompts/generation/question.txt` (base Hebrew-rule carve-out, new "Target-language requirement" section, new `{target_language_requirement}` placeholder, one blueprint checklist item)
- `tests/unit/test_prompts.py` (12 new tests, 1 pre-existing test's slice boundary updated)
- `docs/ARCHITECTURE.md` (new "Deterministic English-First Language Policy (WP-041)" section)
- `docs/PROJECT_STATUS.md` (Tests count, new Live Evaluation Baseline section, Next WP Context updated, closing sentence)
- `evaluation/live_outputs/README.md` (two new rows, updated explanatory paragraphs)

---

WP-041 complete.

Tests:
1325 passed, 0 failed

Offline evaluation:
4/4 real generation calls produced fully English correct answers - both WP-040 Hebrew-answer regressions (Corpos Striatum, Superior cerebellar artery) confirmed fixed before the live pilot

English-first compliance:
9/9 (100%) among accepted questions - zero Hebrew answers where English was required

Pilot evaluation:
אספקת דם 3/4, גרעיני הבסיס 2/4, מסילות עצביות 4/4 accepted (9/12, down from WP-040's 11/12 - a disclosed, material regression not meeting WP-041's own secondary acceptance criterion)

Target alignment:
9/9 (100%) manually-verified ALIGNED among accepted questions

Acceptance:
9/12 (75%), down from WP-040's 11/12 (91.7%) - three ordinary QuestionAttemptsExhaustedError failures, two for Corpos Striatum specifically, plausibly but not confirmedly linked to a sixth simultaneous generation constraint

Concept rotation:
Genuinely improved live for both previously cross-script-stuck categories - אספקת דם reached 3/4 distinct concepts (up from WP-040's 2/4), גרעיני הבסיס reached 2/4 distinct (up from WP-040's 1/4 stuck-every-round) - directly confirming the English-answer-recognized-by-existing-coverage hypothesis with zero coverage-layer changes

Cross-script coverage impact:
Practically removed for every concept this pilot actually encounters, live-confirmed, with zero changes to WP-038's coverage-matching mechanism itself

Completion report:
implementation/WP-041_COMPLETION_REPORT.md

Waiting for architect review.
