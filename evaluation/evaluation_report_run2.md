# WP-017 Evaluation Report

## Run Summary

- Generated at: 2026-08-04T18:48:06.518040+00:00
- Baseline type: **REDUCED**
- Provider/model: `openai` / `gpt-4o-mini`
- Categories evaluated: 5 of 20 canonical categories
- Questions requested per category: 2
- Total candidate attempts recorded: 4
- Total operational failures recorded: 6

## Acceptance Metrics

- Candidate acceptance rate: 100.0%
- First-attempt acceptance rate: 100.0%
- Attempts per accepted question: mean=1.00, median=1.00, min=1, max=1 (n=4)
- Exhaustion rate: 0.0%

## Validator Failure Metrics

- Total rejected candidates: 0
  - Grounding: 0 (0.0% of rejections)
  - Mcq: 0 (0.0% of rejections)
  - Category: 0 (0.0% of rejections)
  - Quality: 0 (0.0% of rejections)

Textbook status distribution (all attempts):
  - NOT_FOUND: 4

## Category Results

| Category | Requested | Produced | Attempts | Accepted | Rejected | Exhausted | Op. Failures |
|---|---|---|---|---|---|---|---|
| התעלה השדרתית ותכולתה | 2 | 1 | 1 | 1 | 0 | 0 | 1 |
| מיפוי ודימות מוחי | 2 | 1 | 1 | 1 | 0 | 0 | 1 |
| קרומים וסינוסים דוראליים | 2 | 1 | 1 | 1 | 0 | 0 | 1 |
| המוח הקטן | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| טופוגרפיה של ההמיספרות | 2 | 1 | 1 | 1 | 0 | 0 | 1 |

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

_Not recorded._

## Exam-Level Quality Observations

_Not recorded._

## Recommended Next Actions

_Not recorded._
