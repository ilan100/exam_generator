# WP-017 Evaluation Report

## Run Summary

- Generated at: 2026-08-04T18:41:19.037956+00:00
- Baseline type: **REDUCED**
- Provider/model: `openai` / `gpt-4o-mini`
- Categories evaluated: 5 of 20 canonical categories
- Questions requested per category: 2
- Total candidate attempts recorded: 3
- Total operational failures recorded: 8

## Acceptance Metrics

- Candidate acceptance rate: 66.7%
- First-attempt acceptance rate: 50.0%
- Attempts per accepted question: mean=1.50, median=1.50, min=1, max=2 (n=2)
- Exhaustion rate: 0.0%

## Validator Failure Metrics

- Total rejected candidates: 1
  - Grounding: 0 (0.0% of rejections)
  - Mcq: 0 (0.0% of rejections)
  - Category: 0 (0.0% of rejections)
  - Quality: 1 (100.0% of rejections)

Textbook status distribution (all attempts):
  - NOT_FOUND: 3

## Category Results

| Category | Requested | Produced | Attempts | Accepted | Rejected | Exhausted | Op. Failures |
|---|---|---|---|---|---|---|---|
| התעלה השדרתית ותכולתה | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| מיפוי ודימות מוחי | 2 | 1 | 2 | 1 | 1 | 0 | 1 |
| קרומים וסינוסים דוראליים | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| המוח הקטן | 2 | 1 | 1 | 1 | 0 | 0 | 1 |
| טופוגרפיה של ההמיספרות | 2 | 0 | 0 | 0 | 0 | 0 | 2 |

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

## Human Quality Observations

_Not recorded._

## Exam-Level Quality Observations

_Not recorded._

## Recommended Next Actions

_Not recorded._
