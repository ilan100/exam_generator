# WP-017 Evaluation Report

> This is a **combined** dataset merging two independent live runs
> (`evaluation_report_run1.{json,md}`, `evaluation_report_run2.{json,md}`)
> made with the identical configuration (same 5 categories, 2 requested
> questions/category/run) - run 2 followed a narrow instrumentation fix
> (recording `pydantic.ValidationError` as an operational failure instead
> of crashing the run, and capturing accepted-candidate text for human
> review). "Questions requested per category" below (4) reflects
> 2 requested/run x 2 runs. Retrieval-evaluation results are
> run-independent (deterministic, offline) and appear once.

## Run Summary

- Generated at: 2026-08-04T18:54:25.167940+00:00
- Baseline type: **REDUCED**
- Provider/model: `openai` / `gpt-4o-mini`
- Categories evaluated: 5 of 20 canonical categories
- Questions requested per category: 4
- Total candidate attempts recorded: 7
- Total operational failures recorded: 14

## Acceptance Metrics

- Candidate acceptance rate: 85.7%
- First-attempt acceptance rate: 83.3%
- Attempts per accepted question: mean=1.17, median=1.00, min=1, max=2 (n=6)
- Exhaustion rate: 0.0%

## Validator Failure Metrics

- Total rejected candidates: 1
  - Grounding: 0 (0.0% of rejections)
  - Mcq: 0 (0.0% of rejections)
  - Category: 0 (0.0% of rejections)
  - Quality: 1 (100.0% of rejections)

Textbook status distribution (all attempts):
  - NOT_FOUND: 7

## Category Results

| Category | Requested | Produced | Attempts | Accepted | Rejected | Exhausted | Op. Failures |
|---|---|---|---|---|---|---|---|
| התעלה השדרתית ותכולתה | 4 | 1 | 1 | 1 | 0 | 0 | 3 |
| מיפוי ודימות מוחי | 4 | 2 | 3 | 2 | 1 | 0 | 2 |
| קרומים וסינוסים דוראליים | 4 | 1 | 1 | 1 | 0 | 0 | 3 |
| המוח הקטן | 4 | 1 | 1 | 1 | 0 | 0 | 3 |
| טופוגרפיה של ההמיספרות | 4 | 1 | 1 | 1 | 0 | 0 | 3 |

## Retrieval Metrics

- Recall@3: 86.5%
- Recall@5: 94.6%
- Recall@8: 94.6%
- Queries missed at K=8: 2 of 37
  - 'Cerebellum' (expected term 'Cerebellum')
  - 'Basal Ganglia' (expected term 'Basal Ganglia')

## Operational/Provenance Failures

- [התעלה השדרתית ותכולתה / STYLE_SIMILAR] ValidationError: 1 validation error for QualityValidationResult
reason
  Value error, value must not be empty or whitespace-only [type=value_error, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/value_error
- [התעלה השדרתית ותכולתה / INDEPENDENT] ValidationError: 1 validation error for QualityValidationResult
reason
  Value error, value must not be empty or whitespace-only [type=value_error, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/value_error
- [מיפוי ודימות מוחי / INDEPENDENT] ValidationError: 1 validation error for QualityValidationResult
reason
  Value error, value must not be empty or whitespace-only [type=value_error, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/value_error
- [קרומים וסינוסים דוראליים / STYLE_SIMILAR] ValidationError: 1 validation error for QualityValidationResult
reason
  Value error, value must not be empty or whitespace-only [type=value_error, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/value_error
- [קרומים וסינוסים דוראליים / INDEPENDENT] ValidationError: 1 validation error for GroundingValidationResult
  Invalid JSON: EOF while parsing a string at line 1 column 3536 [type=json_invalid, input_value='{"grounded":true,"correc...\n\\n\\n\\n\\n\\n\\n\\n', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/json_invalid
- [המוח הקטן / INDEPENDENT] ValidationError: 1 validation error for QualityValidationResult
reason
  Value error, value must not be empty or whitespace-only [type=value_error, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/value_error
- [טופוגרפיה של ההמיספרות / STYLE_SIMILAR] ValidationError: 1 validation error for QualityValidationResult
reason
  Value error, value must not be empty or whitespace-only [type=value_error, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/value_error
- [טופוגרפיה של ההמיספרות / INDEPENDENT] InvalidTextbookOutputError: Textbook check result cites reference_text that does not appear in any course-book chunk actually supplied to the validator
- [התעלה השדרתית ותכולתה / STYLE_SIMILAR] ValidationError: 1 validation error for QualityValidationResult
reason
  Value error, value must not be empty or whitespace-only [type=value_error, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/value_error
- [מיפוי ודימות מוחי / INDEPENDENT] InvalidTextbookOutputError: Textbook check result cites reference_text that does not appear in any course-book chunk actually supplied to the validator
- [קרומים וסינוסים דוראליים / STYLE_SIMILAR] ValidationError: 1 validation error for QualityValidationResult
reason
  Value error, value must not be empty or whitespace-only [type=value_error, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/value_error
- [המוח הקטן / STYLE_SIMILAR] InvalidGeneratedOutputError: Generated response claims evidence chunk id(s) that were not supplied: ['STUDENT_SUMMARY:student_summary_2.pdf:0168:0001']
- [המוח הקטן / INDEPENDENT] InvalidGeneratedOutputError: Generated response claims evidence chunk id(s) that were not supplied: ['STUDENT_SUMMARY:student_summary_2.pdf:0168:0001']
- [טופוגרפיה של ההמיספרות / INDEPENDENT] ValidationError: 1 validation error for QualityValidationResult
reason
  Value error, value must not be empty or whitespace-only [type=value_error, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/value_error

## Human Quality Observations

4 of the 6 accepted candidates (from the schema-fixed second run) were reviewed in full (the 2 accepted candidates from the first run predate the question-text capture fix and have no persisted text to review):

1. **"מהו המבנה שאחראי להעברת מידע סנסורי ומוטורי ממוח השדרה אל שאר הגוף?"** (spinal canal category)    - Clear, well-formed. Correct answer (spinal nerve) and distractors (dorsal root / ventral    root / vertebra) test a genuine, precise anatomical distinction rather than an arbitrary    pick. No ambiguity observed. Good category fit.
2. **"מהו היתרון העיקרי של שיטת ה-CT בהדמיה מוחית?"** (brain imaging category) - Clear factual    question; distractors correctly describe MRI's advantages rather than CT's, so the    question meaningfully tests the CT-vs-MRI distinction rather than an obvious pick. Good    category fit, natural Hebrew.
3. **"מהו הסינוס הדוראלי העליון?"** (dural sinuses category) - Clear and topically correct;    distractor 3 plausibly confuses the dural sinus with the CSF-containing subarachnoid    space, a reasonable test of precise understanding. Good category fit.
4. **"באיזה מבנה במשטח התחתון של ההמיספרה ממוקם ה-Olfactory Bulb?"** (hemisphere topography    category) - **A real quality defect the automated QualityValidator did not catch**: each    answer choice is redundantly numbered *inside its own text* ("1. לטרלית ל-...", "2. מדיאלית    ל-...", etc.) in addition to the exam format's own answer1..answer4 numbering, so a real    exam-taker would see visibly duplicated numbering per choice. The question wording itself    ("in which structure is X located") is also a slightly awkward fit for an answer that is    really a *relative position* ("medial to the olfactory tract"), not a containing structure.    `quality_valid` was `True` for this candidate - a concrete, reproducible example of    automated validators missing something a human reviewer catches immediately, exactly the    gap WP-017 section 19 asks this review to surface.

Overall: 3 of 4 reviewed questions were genuinely solid, exam-ready material with meaningful distractors: the fourth had one clear, missable construction defect (duplicated in-text numbering) that survived MCQ/Quality validation. This is a small sample (4 questions) - not a systematic quality measurement, but concrete evidence that automated validation, while generally effective, is not perfectly reliable at catching every construction artifact.

## Exam-Level Quality Observations

Sample too small (4 reviewed / 6 total accepted, across 5 distinct categories) to meaningfully assess repeated patterns, near-duplicates, or answer-position concentration - every accepted question came from a different category and covered clearly distinct subtopics, so no repetition was observed, but this is expected at this sample size rather than evidence of genuine diversity at scale. Correct-answer positions across the 4 reviewed questions were [2, 1, 1, 2] - roughly balanced, but far too small a sample to draw a conclusion about systematic answer-position bias. No STYLE_SIMILAR question was close enough to its historical reference to raise a style-copying concern in this sample. No corrective diversity logic was implemented, per WP-017 section 20.

## Recommended Next Actions

Ranked by evidence strength and expected impact:

1. **(Reliability, highest priority) Investigate and reduce the empty-string-required-field    failure rate.** This was the dominant failure mode across both live runs (9 of 14    operational failures / 45% of all 20 planned questions), exclusively on    `QualityValidationResult.reason` specifically, at `validation_temperature=0.0` (should be    the most deterministic setting available) - a much higher rate than the occasional,    scattered instances noted in WP-013/WP-014. Candidate hypotheses worth investigating    (not confirmed by this baseline): something about `quality.txt`'s specific prompt/response    shape, or a session/sequence-position effect (quality is the 4th of 5 validator calls)    rather than causal quality-content. This blocks far more candidate production today than    any actual quality/MCQ/category rejection does - when the pipeline *did* complete    operationally, 6 of 7 attempts (85.7%) were accepted immediately.
2. **(Reliability) Continue hardening structured-output provenance.** 5 of 14 operational    failures were already-known issue classes: 2x invented `evidence_chunk_ids` (WP-010's    class), 2x non-verbatim textbook `reference_text` (WP-012/013's class, one per run), 1x    malformed/truncated JSON from the provider (`GroundingValidationResult`). None of these are    new; this baseline is further evidence they remain non-negligible in aggregate, not    evidence any single one dominates.
3. **(Enhancement, low priority) TF-IDF retrieval appears sufficient for V1 as currently    configured** - Recall@3=86.5%, Recall@5/@8=94.6% across 37 corpus-grounded queries spanning    all 20 canonical categories, with only 2 misses (Cerebellum, Basal Ganglia - both still    present in top results just outside the measured K). No evidence in this baseline supports    prioritizing embeddings/hybrid retrieval over the reliability issues above.
4. **(Quality, minor) MCQ/Quality validators occasionally miss real construction defects**    (see human review finding #4 above - duplicated in-answer numbering). Not evidence of a    systemic quality problem (candidate quality was otherwise good in this sample), but a    concrete data point that automated validation is not a substitute for occasional human    spot-checks.

**Proposed WP-018 scope**: primarily a **reliability-hardening WP** targeting finding #1 above (the empty-required-field failure), not a new feature WP. Given the small sample size here, WP-018 should very plausibly *start* by widening this same evaluation (more categories/questions, still using the runner introduced in WP-017) specifically to confirm whether the 50% empty-reason-field rate holds at larger scale before committing to a specific fix - this baseline is suggestive, not yet decisive, given only 20 planned questions were evaluated live.
