# WP-026 False-Acceptance Diagnostic

**Status: read-only diagnostic. Not a Work Package. No code, prompt, test, configuration, schema, or architecture file was modified in the course of this investigation.**

## 1. Executive Summary

Question #23 (`מערכת העצבים ההיקפית`, "Which of the following systems is part of the peripheral nervous system?") is a **confirmed invalid MCQ**: its own supplied evidence explicitly states that the peripheral nervous system divides into *both* the autonomic and somatic nervous systems, yet the accepted candidate marks the somatic system correct and the autonomic system incorrect. All four validators (grounding, MCQ, category, quality) approved it.

Root cause is **not a single missing check** - it is a gap that exists identically in both of the two validators positioned to catch it, for different reasons:

- **`GroundingValidator`'s contract already asks the right question** (`other_answers_not_equally_correct`) and, in this specific case, **was given the evidence sentence that answers it** - but the LLM's own reasoning simply failed to apply that sentence to the "autonomic" distractor, asserting instead (incorrectly) that only the central nervous system was excluded. This is a **reasoning/implementation gap**, not a contract gap, in this specific instance - though the prompt does not force the model to evaluate each distractor individually, which is a related, compounding weakness.
- **`MCQValidator` structurally cannot catch this at all** - it receives zero factual evidence, only the candidate's own question/answer text (`format_candidate_question()`), and its prompt explicitly declares factual grounding out of scope. Its approval was fully consistent with its documented contract; it judged plausibility from general knowledge, and its own (flawed) reasoning happened to independently assert the same wrong claim ("the other options... do not belong to the peripheral system").
- **`QualityValidator`'s approval was also fully expected** - its contract is explicitly wording/clarity/style only, never factual correctness, and question #23 is genuinely well-worded.
- **Generation's WP-026 distractor rule does not cover this shape.** WP-026 forbids *recombining* enumerated members ("A and B" vs. "B and C"); question #23 instead used a *single genuine sibling member* of a 2-item target as a false single distractor - a related but textually uncovered case.

Reviewing all 35 accepted questions for the same failure class (a distractor that is also evidence-supported as correct) found **3 additional suspicious cases** beyond #23 - two with the same "genuine sibling member misused as a distractor" shape are absent, but three others show a distractor directly, verbatim supported by the same evidence text shown to the validators as a true statement, structurally identical to #23's problem even though the target itself wasn't the exact enumeration shape. This indicates the weakness is systemic to how grounding/MCQ validation currently work, not an isolated fluke tied only to enumeration-shaped targets.

**Recommended direction (see Part 11 for full reasoning): C - strengthen `GroundingValidator`**, by making its existing `other_answers_not_equally_correct` determination require explicit, structured, per-distractor reasoning rather than a single holistic boolean, reusing the same evidence retrieval and the same LLM call (zero additional calls). This is the smallest change that closes the gap the current architecture already assigns this responsibility to, without collapsing validator independence or asking `MCQValidator` to do something outside its documented, evidence-free scope.

## 2. Exact Reconstruction of Question #23

From `evaluation/live_outputs/wp026_acceptance_audit.json` (`number: 23`, `planned_position: 27`) and `wp026_acceptance_targets.json`:

**QuestionTarget** (category `מערכת העצבים ההיקפית`, `target_id: 1`):
- `topic`: "מערכת העצבים ההיקפית - חלוקות"
- `factual_focus`: "מערכת העצבים ההיקפית כוללת את מערכת העצבים האוטונומית ומערכת העצבים הסומטית." ("The peripheral nervous system includes the autonomic nervous system and the somatic nervous system.")
- `supporting_evidence_chunk_ids`: `["STUDENT_SUMMARY:student_summary_2.pdf:0145:0001"]`

**Generation**: `STYLE_SIMILAR`, accepted on **attempt 3** (attempts 1 and 2 were correctly rejected - attempt 1 by `MCQValidator` for a different ambiguity between somatic and "sensory nervous system"; attempt 2 by both `MCQValidator` and `CategoryValidator` for mixing in the central nervous system - so the bounded-retry mechanism was actively filtering bad candidates before this one slipped through).

**Accepted candidate (attempt 3)**:

> **Q**: איזו מהמערכות הבאות היא חלק ממערכת העצבים ההיקפית? ("Which of the following systems is part of the peripheral nervous system?")
> 1. מערכת העצבים הסומטית (somatic) — **marked correct**
> 2. מערכת העצבים המרכזית (central)
> 3. מערכת העצבים האוטונומית (autonomic)
> 4. מערכת העצבים הפרא-סימפתטית (parasympathetic)

**Exact evidence text supplied to and cited by the accepted attempt's `GroundingValidator` call** (`evidence_chunk_ids: ["STUDENT_SUMMARY:student_summary_3.pdf:0005:0001", "STUDENT_SUMMARY:student_summary_3.pdf:0160:0001", "STUDENT_SUMMARY:student_summary_2.pdf:0145:0001"]`):

> "מערכת העצבים שלנו מתחלקת באופן גס ל מערכת עצבים מרכזית (CNS) central nervous system ול מערכת עצבים היקפית (PNS) peripheral nervous system. מערכת העצבים ההיקפית כוללת את היציאות והכניסות מהמערכת המרכזית, עצבים שיוצאים מהמערכת המרכזית קרניאליים, **מערכת העצבים ההיקפית נחלקת למערכת אוטונומית ולמערכת סומטית**."

("Our nervous system divides roughly into the central nervous system (CNS) and the peripheral nervous system (PNS)... **the peripheral nervous system divides into the autonomic system and the somatic system**.")

## 3. Is the "Autonomic Nervous System" Distractor Also Correct?

**Yes, unambiguously, per the exact evidence shown above.** The last clause of the cited evidence text states, in one sentence, that PNS divides into *both* the autonomic and somatic systems - the identical evidence chunk actually supplied to (and cited by) the validators that approved this question. The question asks "which of the following systems is part of the peripheral nervous system" - a plain membership question - and the autonomic nervous system satisfies that exactly as much as the somatic nervous system does, per this evidence. There is no wording in the question that narrows it to "the two of these which is NOT paired with X" or any other framing that would make only one of the two true; it is a bare membership question against a target that names two members, and both members are offered as answer choices, with only one marked correct.

This is not a case of insufficient evidence reaching the validator - the exact sentence needed was present in the supplied evidence and was even quoted back in `grounding.evidence_text`. The validator had the fact and still reasoned past it (see Part 4).

## 4. GroundingValidator Responsibility Analysis

**Current documented responsibility** (`src/exam_generator/validation/grounding.py` docstring, `prompts/validation/grounding.txt`): independently determine (1) the question's factual premise is supported, (2) the stated correct answer is supported, and (3) **"no other answer choice is equally well supported"** (`other_answers_not_equally_correct`) - explicitly a per-response boolean field that already exists precisely to catch "another answer is also correct." (4) no unsupported factual claim exists in the question/answer.

**The response model already has the structure to express the relevant determination** - `other_answers_not_equally_correct: StrictBool` is exactly what should have been `false` here. This is not a response-model/contract gap (classification B does not apply) - the field exists and is asked for.

**What went wrong**: `GroundingValidator`'s actual reasoning for this attempt (`grounding.reason`):

> "The evidence clearly states that the PNS includes both the somatic nervous system and the autonomic nervous system. The correct answer, 'מערכת העצבים הסומטית', is supported by the evidence... **Other options, such as the central nervous system, are not part of the PNS, making the somatic nervous system the only correct answer supported by the evidence.**"

This reasoning **states the correct fact in its first sentence** (PNS includes both) and then **contradicts it two sentences later**, addressing only the central-nervous-system distractor explicitly and asserting "the only correct answer" without ever engaging with why the autonomic-system option (which its own first sentence just confirmed is a genuine PNS member) is excluded. This is an internally inconsistent LLM output that a stricter validation policy could plausibly catch, but nothing in the current architecture checks the internal consistency of `reason` against the boolean fields it is meant to justify.

**Classification: C, implementation/reasoning gap, with a contributing A (prompt) weakness.** The contract already asks the right question (not B); the LLM's own answer to that question was simply wrong despite having the necessary evidence (a genuine C, since this is best understood as an LLM-execution failure under the current prompt and response shape, not a missing structural capability). The prompt (`prompts/validation/grounding.txt`) states the requirement as a single holistic instruction ("whether no other answer choice is equally well supported") rather than requiring the model to evaluate every one of the three distractors individually and explicitly - this is a real, secondary prompt weakness (A) that plausibly makes the C-type reasoning failure more likely, since a holistic judgment is easier to get wrong than an enumerated per-option one. This is **not** D (expected/someone-else's-responsibility) - the architecture, as currently documented and contracted, already assigns this exact responsibility to `GroundingValidator`.

## 5. MCQValidator Responsibility Analysis

Inspected `src/exam_generator/validation/mcq.py`, `prompts/validation/mcq.txt`, `MCQValidationResult` (`src/exam_generator/models/validation.py`), `format_candidate_question()` (`src/exam_generator/prompts/formatting.py`).

Direct answers to the diagnostic's specific questions:

1. **Does `MCQValidator` receive factual evidence? No.** `validate(self, candidate: CandidateQuestion)` takes only the candidate; `format_candidate_question()` renders only `question`, the four `answers`, `correct_answer` position, `category`, and `generation_mode` - no evidence of any kind, ever.
2. **What information does it use?** Only the candidate's own text plus the LLM's own general/world knowledge from training - there is no mechanism for it to verify anything against this project's specific source material.
3. **Does its prompt require evaluating every option?** Partially - it asks "Whether more than one answer choice could reasonably be defended as correct" (a holistic question), not an explicit per-option enumeration.
4. **Does it explicitly ask "could any distractor also correctly answer the question"?** Only implicitly, via the "more than one answer choice... defended as correct" wording above - not as an explicit per-distractor instruction.
5. **Does it have factual evidence sufficient to determine that?** No - see (1). Any correct judgment it makes on this axis is incidental (general knowledge happening to align), not something the architecture guarantees.
6. **Response model**: `MCQValidationResult` provides only `valid` + `exactly_four_answers` + `single_best_answer` + `reason` - a single holistic boolean per axis, no structured per-option analysis.
7. **Why did it approve this question?** Its own reasoning: "The other options are plausible distractors related to the nervous system but do not belong to the peripheral system, making them reasonable incorrect choices." This is factually wrong even under general neuroanatomy knowledge (the autonomic nervous system is a real PNS division), so this was an independent reasoning failure, made without evidence and without correction from any other signal.

**Distinguishing structural MCQ validity from factual one-best-answer validity**: `MCQValidator` as currently built and prompted implements only **structural MCQ validity** - four choices, plausible distinct-looking distractors, no giveaway clues, internal coherence of the question/answer text. It does **not**, and by its documented contract ("This is not a factual grounding check... out of scope here") is not intended to, implement **factual one-best-answer validity** - verifying against authoritative evidence that exactly one answer is true. Question #23 is exactly the case the diagnostic anticipated: it looks like a clean four-option MCQ (which is why `MCQValidator` approved it) while having two factually correct answers (which `MCQValidator` has no means to detect).

## 6. QualityValidator Responsibility Analysis

Inspected `prompts/validation/quality.txt` and `src/exam_generator/validation/quality.py`. `QualityValidator`'s contract is explicitly and exclusively: clarity, answerability (given the question as written, without missing context), exam style/natural phrasing, Hebrew language correctness, and absence of *unintentional wording* ambiguity. It states outright "This is not a factual grounding check... out of scope here," and like `MCQValidator` it receives no evidence (same `format_candidate_question()` input).

Question #23 **is** clearly worded, natural, and grammatically sound - there is nothing about its *wording* that is ambiguous; the ambiguity is entirely in its *factual content* (two of its answer choices are both true). `QualityValidator`'s approval was **fully expected and correct under its own documented contract** - it was never positioned to catch this, and extending it to do so would blur it into `GroundingValidator`'s or `MCQValidator`'s territory rather than fixing a gap in its own.

## 7. WP-026 Generation-Prompt Gap Analysis

`prompts/generation/question.txt`'s distractor-construction rule (added by WP-026) reads:

> "Do not build distractors by rearranging or partially recombining the target's own listed members (for example 'A and B' vs 'B and C' as two different answer choices)... Once you have narrowed to one specific property, distractors should be clearly, unambiguously incorrect for that exact property."

This rule's literal subject is **recombination of members into new pair/group answer choices** - e.g., presenting "autonomic + somatic" as one option and "somatic + parasympathetic" as another. Question #23 did not do this: each of its four options is a single, distinct system name, not a recombination. Instead, it used **a single genuine sibling member of the same 2-item target as a standalone false distractor** - a different, more literal failure shape the rule's wording does not name.

However, the same section's earlier "strong framing" guidance does implicitly warn against exactly this question's *shape*: it explicitly discourages "which of the following lists the types of X" (full-enumeration recall) in favor of testing "ONE evidence-supported member through ONE distinguishing property." Question #23's actual framing - "which of the following IS a member of X" - is a bare-membership test, not a genuine distinguishing-property test; when a target names exactly two members and both appear among the four options, bare membership is not a valid "distinguishing property" at all, since it is equally true of both. The prompt does not say this explicitly.

**Classification: C, both.** (A) The general "test one member via one distinguishing property, not the raw fact of membership itself" spirit already argues against this question's shape, so the model's choice was in some tension with the prompt's own intent - a partial "the model already violated the spirit of the existing guidance" case. But (B) there is also a genuine, specific wording gap: nothing explicitly states "do not test bare classification membership as the property when the target names more than one genuine member, and never place a genuine sibling member among the distractors when doing so" - the closest existing rule (recombination) does not cover this literal case, so a reasonable generation pass following the letter of the current rules would not obviously be blocked from producing question #23's shape.

## 8. Review of All Accepted WP-026 Questions for the Same Failure Class

All 35 accepted questions (`evaluation/live_outputs/wp026_acceptance_exam.json` cross-referenced with `wp026_acceptance_audit.json`'s `grounding.evidence_text`/`grounding.reason` and `wp026_acceptance_targets.json`) were inspected offline, from the persisted evidence text already captured in the audit - no new LLM calls were made for this review, per the diagnostic's cost-consciousness instruction.

| # | Category | Classification | Note |
|---|---|---|---|
| 1–7, 9–13, 15–22, 24–29, 31, 33–35 (30 questions) | various | **CLEAR_SINGLE_ANSWER** | Distractors are either genuinely non-members of the tested classification, or are siblings whose own real properties are clearly false when attributed to the tested member (e.g. #5, Stratum Zonale - a well-designed case that avoids this failure class despite testing one member of a 3-item enumeration, because the distractors are the *other members' own true descriptions*, which are false statements *about the tested member*, not membership claims). |
| **8** | מיפוי ודימות מוחי | **CONFIRMED_SECOND_CORRECT_ANSWER** | Q asks CT's main advantage over ultrasound; marks "provides accurate 3D imaging" correct (not present verbatim in the cited evidence text) while the *cited evidence text itself verbatim states* "CT מאפשרת זיהוי גידולים ומומים בקלות רבה יותר" ("CT allows easier identification of tumors and malformations") as a real fact, yet that statement is answer option 3, marked **incorrect**. The evidence directly supports a distractor as true and does not verbatim support the marked-correct option's specific "3D imaging" claim at all. |
| 14 | אספקת דם | **POSSIBLE_SECOND_CORRECT_ANSWER** | Q asks which artery "branches from the Basilar Artery and supplies posterior brain regions"; the target's own `factual_focus` states Basilar "splits into PCA and two others," and the cited evidence explicitly says the Superior Cerebellar Artery (option 4, marked incorrect) also branches from Basilar and supplies the cerebellum's superior surface - a posterior-fossa structure. Genuinely arguable whether "posterior regions of the brain" as intended excludes the cerebellum; not as clear-cut as #8 or #23, hence POSSIBLE rather than CONFIRMED. |
| **23** | מערכת העצבים ההיקפית | **CONFIRMED_SECOND_CORRECT_ANSWER** | The case under primary investigation (Parts 2-7 above). |
| 30 | חדרי המוח | INSUFFICIENT_EVIDENCE_TO_JUDGE (tangential) | Not a second-correct-answer case (no distractor is evidenced as also-correct), but the cited evidence text does not itself specify "stage 3" for when lateral ventricles become C-shaped - the marked-correct answer's own specific numeric framing is not clearly traceable to the shown evidence. Flagged separately since it is a different defect shape (a possibly-unsupported correct answer, not a supported-but-rejected distractor) and is not counted in the "additional suspicious" total below. |
| 32 | תאי מערכת העצבים | **POSSIBLE_SECOND_CORRECT_ANSWER** | Q asks microglia's central CNS role; the cited evidence states microglia have "a role of phagocytosis (macrophages in the immune system)" (option 1, marked incorrect) **and** "can also be involved in... targeted destruction of... irrelevant synapses" (the marked-correct option). Both are directly evidenced as real microglia functions in the same sentence; the evidence's own wording ("also... can be involved") is genuinely ambiguous about which is "central" versus secondary. |

**Totals: 30 CLEAR_SINGLE_ANSWER, 2 CONFIRMED_SECOND_CORRECT_ANSWER (#8, #23), 2 POSSIBLE_SECOND_CORRECT_ANSWER (#14, #32), 1 tangential INSUFFICIENT_EVIDENCE_TO_JUDGE (#30, different defect shape).**

**Additional suspicious accepted questions beyond #23: 3** (#8, #14, #32).

This is an important finding in its own right: **only one of the three additional cases (none, in fact - #8, #14, #32 are all outside any enumeration-shaped `QuestionTarget`)** shares WP-026's originally-diagnosed "enumeration target" structural shape. #8's target is about a two-way comparison (CT vs. ultrasound advantages/disadvantages), #14's is about arterial branching, and #32's is about a cell type's functions - none of the three failing `factual_focus` values read as "X consists of/divides into A, B, C" the way WP-025A's original four cases and #23 did. **This shows the false-acceptance weakness is broader than the specific enumeration pattern WP-026 targeted** - it is a general property of how `GroundingValidator`/`MCQValidator` currently reason about "is any other option also correct," triggered whenever the supplied evidence happens to state two true facts close enough together that a distractor ends up directly supported, independent of whether the underlying target was itself enumeration-shaped.

## 9. Architectural Alternatives

**Option A - generation prompt only.** Strengthening generation to never place an evidence-supported sibling fact as a distractor would reduce the *rate* of this shape occurring, and is a reasonable complementary step (see Part 7's identified wording gap). But it is **not sufficient as a correctness guarantee** on its own: #8, #14, and #32 show the same failure class arising from ordinary comparative/functional facts, not just enumerated classification targets - a purely generation-side fix could not plausibly anticipate and forbid every way two true facts might end up adjacent in supplied evidence. Generation-only leaves no independent backstop; WP-026 itself already relied on generation-only for the *narrower* enumeration case and that still left #23.

**Option B - strengthen MCQValidator.** Would require **giving it evidence it currently never receives** - a genuine architectural change to its call, since today it is deliberately evidence-free ("not a factual grounding check... out of scope"). This blurs its documented boundary with `GroundingValidator` unless carefully scoped (e.g. it could receive evidence purely to answer "is any distractor also correct," without taking on grounding's other responsibilities). Feasible, but duplicates work `GroundingValidator` is already positioned and contracted to do, and would require the same evidence-retrieval machinery `GroundingValidator` already has, effectively wired a second time.

**Option C - strengthen GroundingValidator.** The contract already claims this responsibility (`other_answers_not_equally_correct`) and already receives the evidence needed - in question #23's case, the evidence was present and cited but the reasoning was wrong. Expanding the *response structure* to force explicit per-distractor reasoning (e.g. a structured `distractor_analysis: list[{option, supported_as_correct: bool, reason}]` alongside the existing boolean, or at minimum prompt wording that requires evaluating each of the three distractors by name before concluding) directly targets the actual observed failure mode (holistic judgment skipping over one option) using the exact call/evidence that already exists. This is conceptually squarely grounding's responsibility per the architecture as documented - "no other answer choice is equally well supported" is a factual-support question, which is what grounding already exists to answer.

**Option D - deterministic check.** Not realistic as the primary mechanism: "is this distractor also a factually correct answer to this specific question" is a semantic-equivalence judgment (e.g. recognizing "autonomic nervous system" and "somatic nervous system" as siblings under an evidence-stated classification) that a regex/keyword check cannot reliably make. A narrow deterministic guard is conceivable only for exact-string overlap between an answer choice and the correct answer's own evidence sentence - too narrow to catch most real cases (including #23, where the issue is semantic membership, not string overlap) and not recommended as more than a supplementary sanity check.

**Option E - generation improvement + independent validation.** This is effectively "A + C" together: reduce occurrence probability at generation time (closing the Part 7 wording gap) while relying on a strengthened `GroundingValidator` as the actual backstop against false acceptance. This is architecturally the most robust combination, since it does not rely on generation alone (Option A's weakness) nor invert `MCQValidator`'s documented evidence-free scope (Option B's cost).

**Option F - other.** Not identified; the existing five-validator architecture already assigns this responsibility most naturally to grounding (Option C), and the cleanest available combination is E.

## 10. Cost/Call-Count Implications

- **Option A (generation prompt)**: zero additional LLM calls - a prompt-text change to the existing generation call only.
- **Option B (MCQValidator + evidence)**: requires richer context in an existing call (MCQValidator's own prompt/context would need to carry evidence, a new dependency: retrieval index + evidence assembly it currently lacks entirely) - not a new call, but a materially larger context and a new wiring dependency (MCQValidator would need a student-summary retrieval index injected, mirroring GroundingValidator's own constructor).
- **Option C (strengthen GroundingValidator)**: **zero additional LLM calls** - reuses the exact existing `validate_grounding()` call, existing retrieval, existing response model shell (extended with more structured fields, not a new call). This is the cheapest viable option that still meaningfully targets the actual gap.
- **Option D (deterministic check)**: zero additional LLM calls, but as discussed not reliable enough to serve as the actual guarantee.
- **Option E (A + C)**: same call-count profile as C (zero additional calls) plus a prompt-only generation change (also zero additional calls) - **no cost increase at all** over the current architecture, since it strengthens two calls that already happen rather than adding a sixth validator.

**Recommendation on cost**: prefer C or E - both achieve the correctness goal without any additional LLM call, retrieval, or retry-behavior change, and without the new evidence-dependency wiring Option B would require.

## 11. Validator-Independence Implications

The existing architecture deliberately separates grounding / MCQ structure / category / quality / textbook as five independent concerns (`docs/ARCHITECTURE.md`, "Candidate Question Validation"). Strengthening `GroundingValidator` (Option C) **preserves this boundary cleanly** - "is every answer choice's correctness evaluated against the authoritative evidence" is already squarely within grounding's documented job description; making that determination more rigorous does not absorb any responsibility currently belonging to `MCQValidator` (structural/plausibility judgment, evidence-free), `CategoryValidator`, `QualityValidator` (wording/style), or `TextbookValidator` (secondary course-book cross-check).

Giving `MCQValidator` evidence (Option B) would be the one alternative that risks blurring boundaries: if `MCQValidator` starts reasoning about factual correctness using evidence, its distinction from `GroundingValidator` ("MCQ structure is out of scope for factual grounding" / "factual grounding is out of scope for MCQ") would need to be redrawn - e.g. explicitly scoping it to "using the supplied evidence, could any distractor also be defended as a correct answer" while still never assessing the *premise's own* grounding (which remains `GroundingValidator`'s job). This is feasible but requires deliberately narrowing what "evidence-aware MCQ validation" means so it does not simply duplicate grounding.

**Base the recommendation on the existing architecture, not preference**: since `GroundingValidator`'s contract already explicitly claims "no other answer choice is equally well supported" as one of its four determinations, and its response model already has a boolean field dedicated to exactly that determination, the architecture itself already says this is grounding's job. The fix belongs there.

## 12. Correct Failure Semantics

Traced against `CandidateValidationResults.accepted` (`src/exam_generator/production/models.py`): acceptance already requires `grounding.passed` (itself `grounded AND correct_answer_supported AND other_answers_not_equally_correct`) to be `True`, alongside `mcq.valid`, `category.valid`, `quality.valid`, and textbook not being `POTENTIAL_CONFLICT`.

**This means a strengthened `GroundingValidator` that correctly sets `other_answers_not_equally_correct = False` for a case like #23 requires zero new failure-semantics wiring.** It already flows through the existing `.accepted` property into the existing `QuestionProducer.produce_question()` bounded-retry loop (`src/exam_generator/production/producer.py`): a `False` verdict here is recorded as a normal rejected `QuestionAttempt` (not an exception, not an operational failure) and the loop simply proceeds to the next of the `max_generation_attempts` attempts, retrying generation against the *same* `QuestionTarget` exactly as any other grounding/MCQ/quality rejection already does today. This is exactly the "candidate-quality rejection, not operational failure" semantics the diagnostic anticipated, and it requires no new exception type, no new `_QUESTION_LOCAL_ERROR_TYPES`/`_SYSTEM_LEVEL_ERROR_TYPES` entry, and no change to WP-013's attempt-budget policy - the existing mechanism already does the right thing the moment the underlying determination is made correctly.

The same is true if Option B (evidence-aware `MCQValidator`) were chosen instead: `mcq.valid = False` already gates acceptance identically.

## 13. Recommended WP-027 Direction

**Recommended primary direction: E - generation improvement + independent (grounding) validation strengthening.**

Direct answers to the diagnostic's required questions:

1. **Where should factual distractor correctness be checked?** In `GroundingValidator` - it already claims this responsibility contractually and already has the evidence access needed; this is the existing architectural home for "is this claim supported by the authoritative evidence," and a distractor's correctness is exactly that kind of claim.
2. **Should every answer option be evaluated independently?** Yes - the observed failure mode is a holistic "no other answer is equally correct" judgment silently skipping one option. A structured, explicit per-option determination (four judgments, one per answer choice, in the response model) closes this specific gap.
3. **What evidence should the validator receive?** The same evidence `GroundingValidator` already retrieves and receives today - no change to retrieval is indicated by this diagnostic. (A future WP should separately consider whether the existing validation-retrieval query - built from category + question + *correct answer only*, deliberately excluding distractor text, per `_build_validation_query()` - should also incorporate distractor text so retrieval itself is more likely to surface evidence directly relevant to each distractor; in question #23 this was not the proximate cause, since the needed evidence was retrieved and cited anyway, but it is a plausible contributing risk factor for other cases and worth flagging for that future WP to evaluate, not decide here.)
4. **Can existing retrieval/evidence be reused without violating validator independence?** Yes - Option C/E requires no new retrieval mechanism and no cross-validator coupling.
5. **Does the solution require another LLM call?** No - zero additional calls (Part 10).
6. **What should the result contract look like?** `GroundingValidationResult`/`GroundingValidationResponse` would need an extension (illustrative shape, not a proposal to implement here - this diagnostic does not design WP-027) that forces explicit reasoning about each non-designated answer choice, rather than a single holistic `other_answers_not_equally_correct` boolean - the existing evidence-reference mechanism (`evidence_refs`) generalizes naturally to "per-option evidence references," but the exact shape is a WP-027 design decision.
7. **How should a detected second-correct-answer interact with WP-013's existing 3-attempt budget?** No change needed - it already becomes a normal rejected attempt within the existing bounded-retry loop, retried against the same `QuestionTarget` (Part 12).
8. **Does the WP-026 generation prompt also need the narrow sibling-distractor rule strengthened?** Yes, as a complementary (not sufficient-alone) measure - Part 7 identified a genuine wording gap (a sibling member of a small enumerated target used as a bare-membership distractor is not explicitly forbidden the way member-recombination is). Since #8/#14/#32 show the underlying weakness is broader than enumeration targets, this generation-side tightening should be paired with the grounding-side fix (Option E), not substituted for it.

## 14. Explicit Confirmation: Nothing Was Modified

No file under `src/exam_generator/`, no file under `prompts/`, no file under `tests/`, no YAML/configuration file, no schema file, and no `docs/ARCHITECTURE.md`/`docs/PROJECT_STATUS.md` content was changed in the course of this diagnostic. The full exam was not rerun. Question #23 was not regenerated. No findings were used to tune any existing artifact. This report and its parent directory (`evaluation/`) are the only files written.

---

WP-026 false-acceptance diagnostic complete.
Question #23 confirmed invalid: yes
Additional suspicious accepted questions: 3
Recommended WP-027 direction: E
Report: evaluation/wp026_false_acceptance_diagnostic.md

Wait for architect/user review.
