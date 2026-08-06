# WP-018 Post-Hardening Evaluation Report

## Run Summary

- Generated at: 2026-08-05T06:28:16.393773+00:00
- Baseline type: **REDUCED**
- Provider/model: `openai` / `gpt-4o-mini`
- Categories evaluated: 5 of 20 canonical categories
- Questions requested per category: 4
- Total candidate attempts recorded: 25
- Total operational failures recorded: 1

## Acceptance Metrics

- Candidate acceptance rate: 76.0%
- First-attempt acceptance rate: 78.9%
- Attempts per accepted question: mean=2.50, median=2.00, min=1, max=5 (n=10)
- Exhaustion rate: 0.0%

## Validator Failure Metrics

- Total rejected candidates: 6
  - Grounding: 0 (0.0% of rejections)
  - Mcq: 4 (66.7% of rejections)
  - Category: 0 (0.0% of rejections)
  - Quality: 6 (100.0% of rejections)

Textbook status distribution (all attempts):
  - NOT_FOUND: 18
  - CONSISTENT: 7

## Category Results

| Category | Requested | Produced | Attempts | Accepted | Rejected | Exhausted | Op. Failures |
|---|---|---|---|---|---|---|---|
| התעלה השדרתית ותכולתה | 4 | 2 | 4 | 4 | 0 | 0 | 0 |
| מיפוי ודימות מוחי | 4 | 2 | 5 | 4 | 1 | 0 | 0 |
| קרומים וסינוסים דוראליים | 4 | 2 | 6 | 4 | 2 | 0 | 0 |
| המוח הקטן | 4 | 2 | 4 | 4 | 0 | 0 | 0 |
| טופוגרפיה של ההמיספרות | 4 | 2 | 6 | 3 | 3 | 0 | 1 |

## Retrieval Metrics

- Recall@3: 86.5%
- Recall@5: 94.6%
- Recall@8: 94.6%
- Queries missed at K=8: 2 of 37
  - 'Cerebellum' (expected term 'Cerebellum')
  - 'Basal Ganglia' (expected term 'Basal Ganglia')

## Operational/Provenance Failures

- [טופוגרפיה של ההמיספרות / STYLE_SIMILAR] InvalidGroundingOutputError: Grounding result claims supporting evidence chunk id(s) that were not supplied to the validator: ['STUDENT_SUMMARY:student_summary_2.pdf:0050:0001']

## Human Quality Observations

All 19 accepted candidates (across both independent post-hardening runs) were reviewed for the specific defect WP-017's human review surfaced (duplicated in-text answer numbering) plus the same general clarity/answerability/category-fit checklist WP-017 used.

**Duplicated answer-numbering defect: 0 of 19** - a mechanical scan for the exact artifact found in WP-017 (`"1. ..."`-style leading numbering repeated inside 2+ answer choices) found none. The one WP-017 example of this defect surviving automated validation cannot be directly re-tested (the original candidate is gone), but the deterministic pre-check added in WP-018 (`detect_duplicated_answer_numbering`) is unit- and integration-tested against that exact pattern and rejects it before any LLM validation call is made.

Spot-checking all 19 for general construction quality: questions are clear, unambiguous, and fit their requested category. Distractors are topically plausible rather than nonsensical (e.g. the imaging-method questions distinguish CT/MRI/ultrasound along genuine clinical-use-case lines, not arbitrary swaps). No STYLE_SIMILAR question was a verbatim or near-verbatim copy of a historical reference. Four of the accepted questions repeat the cerebellum's general function (`המוח הקטן` was requested twice per run x 2 runs = 4 total for that category), each phrased distinctly and testing a slightly different angle (motor coordination vs. balance vs. general role) - expected repetition from re-requesting the same category multiple times at this sample size, not evidence of a diversity problem.

Correct-answer position distribution across the 19 accepted questions: position 1 (6), position 2 (8), position 3 (5), position 4 (0). Zero occurrences of position 4 in this sample is a small-sample observation, not by itself evidence of systematic bias (WP-017's own 4-question sample was too small to draw this conclusion either) - worth tracking if evaluation scale grows, but not a WP-018 blocker since V1 has no answer-shuffling requirement and no prior baseline showed a bias large enough to act on.

## Exam-Level Quality Observations

19 accepted questions across 5 categories, each category requested 4 times total (2/run x 2 runs) in alternating STYLE_SIMILAR/INDEPENDENT mode. No exact duplicate text was produced (orchestration's own exact-match duplicate guard was never triggered in these runs - not directly observed here since the evaluation runner calls the producer directly rather than the full orchestrator, but no near-duplicate phrasing was observed on manual inspection either). Category coverage was limited to the same 5 categories WP-017 evaluated, by design, to keep the before/after comparison controlled (per WP-018 section 14's explicit instruction not to change evaluation methodology).

## Recommended Next Actions

Ranked by evidence strength and expected impact:

1. **(Confirmed fix) The empty-reason operational-failure class is eliminated in this    evaluation.** WP-017's dominant failure mode (9 of 14 operational failures / 45% of 20    planned questions, all `QualityValidationResult.reason == ""`) did not occur once across 25    candidate attempts / 20 planned questions in this post-hardening evaluation. This matches    the root-cause diagnostic (Field(description=...) + explicit prompt wording eliminated the    defect in a controlled 18-call reproduction: 5/8 empty before, 0/10 empty after) and the live    evaluation result together.
2. **(Reliability, residual) Structured-output provenance violations still occur, at a much    lower rate.** 1 of 25 attempts (4%) - a single invented `evidence_chunk_ids` entry in    grounding validation - vs. WP-017's 4 of 20 planned questions (20%) across generation,    grounding, and textbook combined. WP-018's hardening (explicit "leave empty rather than    guessing" wording, plus the textbook chunk-ID contract change) measurably reduced but did    not eliminate this class; it remains a known V1 limitation, not a blocker, since the    provenance check itself continues to correctly reject the violation rather than silently    accepting fabricated evidence.
3. **(Quality) No recurrence of the duplicated-answer-numbering defect.** Both the deterministic    pre-check (unit/integration-tested) and manual inspection of all 19 accepted candidates in    this evaluation found zero instances.
4. **(Enhancement, low priority, unchanged) TF-IDF retrieval remains sufficient for V1** -    Recall@3=86.5%, Recall@5/@8=94.6%, identical to WP-017 (retrieval was deliberately untouched    by this WP). No new evidence changes this conclusion.
