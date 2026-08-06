# WP-017 Evaluation Report

## Run Summary

- Generated at: 2026-08-05T06:28:16.393773+00:00
- Baseline type: **REDUCED**
- Provider/model: `openai` / `gpt-4o-mini`
- Categories evaluated: 5 of 20 canonical categories
- Questions requested per category: 2
- Total candidate attempts recorded: 13
- Total operational failures recorded: 0

## Acceptance Metrics

- Candidate acceptance rate: 76.9%
- First-attempt acceptance rate: 80.0%
- Attempts per accepted question: mean=1.30, median=1.00, min=1, max=3 (n=10)
- Exhaustion rate: 0.0%

## Validator Failure Metrics

- Total rejected candidates: 3
  - Grounding: 0 (0.0% of rejections)
  - Mcq: 2 (66.7% of rejections)
  - Category: 0 (0.0% of rejections)
  - Quality: 3 (100.0% of rejections)

Textbook status distribution (all attempts):
  - NOT_FOUND: 9
  - CONSISTENT: 4

## Category Results

| Category | Requested | Produced | Attempts | Accepted | Rejected | Exhausted | Op. Failures |
|---|---|---|---|---|---|---|---|
| התעלה השדרתית ותכולתה | 2 | 2 | 2 | 2 | 0 | 0 | 0 |
| מיפוי ודימות מוחי | 2 | 2 | 2 | 2 | 0 | 0 | 0 |
| קרומים וסינוסים דוראליים | 2 | 2 | 4 | 2 | 2 | 0 | 0 |
| המוח הקטן | 2 | 2 | 2 | 2 | 0 | 0 | 0 |
| טופוגרפיה של ההמיספרות | 2 | 2 | 3 | 2 | 1 | 0 | 0 |

## Retrieval Metrics

- Recall@3: 86.5%
- Recall@5: 94.6%
- Recall@8: 94.6%
- Queries missed at K=8: 2 of 37
  - 'Cerebellum' (expected term 'Cerebellum')
  - 'Basal Ganglia' (expected term 'Basal Ganglia')

## Operational/Provenance Failures

- None recorded.

## Human Quality Observations

_Not recorded._

## Exam-Level Quality Observations

_Not recorded._

## Recommended Next Actions

_Not recorded._
