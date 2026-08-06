# VER-020 Diagnostic Report — Factual-Source Coverage for `מבוא`

Read-only, offline diagnostic (WP-006 TF-IDF retrieval only, no LLM calls, no code/config/prompt changes). Purpose: determine whether `מבוא` is genuinely a limited-content canonical category compared with the other 19, before any change to retry policy, category policy, or WP-021.

## 1. All-category retrieval comparison (top_k=8, production config, bare category-name query via `retrieve_for_category()`)

| Category | Results | Distinct chunks | Distinct pages | Distinct files | Top score | Min score | Avg score |
|---|---|---|---|---|---|---|---|
| התעלה השדרתית ותכולתה | 8 | 8 | 7 | 2 | 0.303 | 0.135 | 0.200 |
| לוקליזציה פונקציונלית | 8 | 8 | 8 | 3 | 0.339 | 0.114 | 0.165 |
| חומר לבן | 8 | 8 | 8 | 3 | 0.269 | 0.134 | 0.173 |
| עצבים קרניאליים | 8 | 8 | 8 | 3 | 0.368 | 0.219 | 0.281 |
| מיפוי ודימות מוחי | 8 | 8 | 8 | 3 | 0.324 | 0.045 | 0.130 |
| היסטולוגיה | 8 | 8 | 8 | 3 | 0.327 | 0.081 | 0.176 |
| המערכת הלימבית | 8 | 8 | 7 | 3 | 0.442 | 0.148 | 0.209 |
| אספקת דם | 8 | 8 | 8 | 2 | 0.430 | 0.193 | 0.251 |
| קרומים וסינוסים דוראליים | 8 | 8 | 6 | 2 | 0.220 | 0.119 | 0.153 |
| גזע המוח | 8 | 8 | 8 | 3 | 0.485 | 0.131 | 0.248 |
| מסילות עצביות | 8 | 8 | 8 | 3 | 0.377 | 0.154 | 0.250 |
| גרעיני הבסיס | 8 | 8 | 8 | 3 | 0.328 | 0.228 | 0.265 |
| המוח הקטן | 8 | 8 | 8 | 3 | 0.244 | 0.100 | 0.126 |
| מערכת העצבים ההיקפית | 8 | 8 | 8 | 3 | 0.412 | 0.249 | 0.320 |
| דיאנצפלון | 8 | 8 | 7 | 3 | 0.481 | 0.164 | 0.337 |
| אמבריולוגיה | 8 | 8 | 8 | 2 | 0.207 | 0.098 | 0.122 |
| טופוגרפיה של ההמיספרות | 8 | 8 | 8 | 3 | 0.399 | 0.110 | 0.192 |
| חדרי המוח | 8 | 8 | 8 | 3 | 0.136 | 0.095 | 0.112 |
| תאי מערכת העצבים | 8 | 8 | 8 | 3 | 0.374 | 0.272 | 0.330 |
| **מבוא** | 8 | 8 | 6 | 3 | **0.088** | **0.022** | **0.052** |

`מבוא` has the lowest top score, lowest min score, and lowest avg score of all 20 categories — by a wide margin (next-weakest: `חדרי המוח` at 0.136 top score, still ~55% higher).

## 2. `מבוא` evidence in detail

Of the 8 retrieved chunks, only **3 genuinely distinct topic clusters** exist:

| Rank | Score | Chunk | Page/File | Topic |
|---|---|---|---|---|
| 1 | 0.088 | STUDENT_SUMMARY:student_summary_2.pdf:0001:0001 | p.1 / summary_2 | History of anatomy study + anatomical orientation axes (medial/lateral/rostral/caudal/dorsal/ventral/sagittal) |
| 2 | 0.064 | STUDENT_SUMMARY:student_summary_3.pdf:0001:0001 | p.1 / summary_3 | Same topic as rank 1 — near-duplicate from a different student's summary |
| 6 | 0.043 | STUDENT_SUMMARY:student_summary_1.pdf:0001:0001 | p.1 / summary_1 | Same topic as ranks 1/2 again — a third near-duplicate restatement of the identical intro lecture |
| 3 | 0.062 | STUDENT_SUMMARY:student_summary_2.pdf:0002:0001 | p.2 / summary_2 | Evolution of the nervous system (Foramen Magnum, brain volume, *Australopithecus afarensis*/"Lucy") — genuinely distinct |
| 4 | 0.061 | STUDENT_SUMMARY:student_summary_3.pdf:0080:0001 | p.80 / summary_3 | "מבוא למיפוי מוחי" (Introduction to Brain Mapping) — a different lecture's intro section that happens to also be headed "מבוא"; substantively about CT/ultrasound imaging |
| 5 | 0.052 | STUDENT_SUMMARY:student_summary_2.pdf:0041:0001 | p.41 / summary_2 | Same topic as rank 4 — brain-mapping intro again (Phrenology, Broca, CT/ultrasound) |
| 7 | 0.026 | STUDENT_SUMMARY:student_summary_3.pdf:0159:0001 | p.159 / summary_3 | Fear conditioning / amygdala / hippocampus — unrelated, essentially noise |
| 8 | 0.022 | STUDENT_SUMMARY:student_summary_1.pdf:0004:0001 | p.4 / summary_1 | Spinal cord/canal anatomy — unrelated, essentially noise |

## 3. Comparison with other categories

- **Content-rich example** (`עצבים קרניאליים`, top=0.368, min=0.219): all 8 results score above 0.2 — every retrieved chunk is strongly, specifically relevant. `מבוא`'s min score (0.022) is ~10x lower — half its "top-8" is barely-related noise.
- **Median category** (`לוקליזציה פונקציונלית`, top=0.339): a floor nearly 4x higher than `מבוא`'s top score.
- **Next-lowest category** (`חדרי המוח`, top=0.136): still 55% stronger than `מבוא`, and not showing the same duplicate-topic pattern.
- `מבוא` is the only category where 3 of 8 chunks are near-verbatim restatements of the same lecture across different student summaries, and 2 more belong to a topic (brain mapping) that already has its own separate canonical category.

## 4. Why the retrieval score is weak — WP-006's 0.088 finding reproduced exactly

Measured top score: **0.0878** — matches WP-006's previously reported ~0.088 precisely; not a regression, not query-dependent noise, fully reproducible with the current unmodified retrieval implementation.

**Cause: a combination**, but two factors dominate:
- **Short/generic category name**: "מבוא" (= "introduction") is a common Hebrew word functioning as a recurring section-heading prefix across many unrelated lecture topics in the corpus (observed directly: "1. מבוא למבנה מערכת העצבים" and "7. מבוא למיפוי מוחי" — two different chapters both titled "Introduction to..."). Character n-gram TF-IDF gives this word low discriminative weight since it recurs across many different chunks' headers, unlike a specific anatomical term.
- **Evidence present but not lexically distinctive**: the chapter's actual substantive prose (Edwin Smith Papyrus, Galen, Vesalius, Brodmann, anatomical axis terms) doesn't repeat the word "מבוא" itself, so a bare category-name query under-matches content that is topically on-target but lexically dissimilar to the query term.
- Secondary: genuinely narrow distinct content (only 2 real topic clusters, one duplicated 3x) — not "concentration in few pages" (6 distinct pages were still returned) but rather concentration in few concepts.

## 5. Support for 2 distinct questions — Classification

**B. LIMITED BUT SUFFICIENT FOR 2 QUESTIONS.**

There are two genuinely separable concept clusters: (1) history-of-anatomy-study + orientation terminology (well-supported, restated 3x independently by 3 students — high redundancy, but real, extractable, distinct facts within it: historical figures vs. axis-naming conventions), and (2) evolution of the nervous system (thinner, single-chunk support). Two well-grounded, non-duplicate questions look plausible, but the margin is much thinner than a typical category, and a poorly-scoped generation is more likely to either produce near-duplicate "history of anatomy" questions or accidentally drift into the separate `מיפוי ודימות מוחי` category's material (2 of 8 retrieved chunks are literally about brain-mapping intro, not about "מבוא" as this project's canonical topic).

## 6. Reliability statistics, with and without `מבוא`

Recalculated from the already-collected WP-020 20-question reliability sample (no regeneration; existing results only).

| | ALL 20 CATEGORIES | EXCLUDING מבוא (19) | מבוא alone |
|---|---|---|---|
| Accepted | 19 | 18 | 1 |
| Operational failures | 1 | 1 | 0 |
| Exhausted | 0 | 0 | 0 |
| Accepted on attempt 1 | 15 | 15 | 0 |
| Accepted on attempt 2 | 3 | 3 | 0 |
| Accepted on attempt 3 | 1 | 0 | **1** |
| Avg attempts/accepted question | 1.263 | 1.167 | 3.000 |

`מבוא` was the only question in the entire 20-question sample that needed all 3 attempts: attempt 1 was a generation-contract failure (invented evidence ID), attempt 2 was rejected on MCQ + quality simultaneously, attempt 3 was accepted. Small-n caveat: this is one data point, not a trend — but it is the single most attempt-costly result in the sample, and directionally consistent with the retrieval-coverage findings above.

**Note on the unrelated operational failure**: the `InvalidGroundingOutputError` observed in this sample occurred for `התעלה השדרתית ותכולתה`, not `מבוא` — correctly excluded from this analysis. It remains a separate, already-documented system-level reliability issue (WP-018/WP-019/WP-020), not attributable to `מבוא`'s content coverage.

## Policy options the evidence would support (none chosen, none implemented)

- Keep `מבוא` identical to other categories — evidence: not clearly ruled out; only 1 sample data point shows elevated attempt cost, and a valid 2nd distinct question does appear extractable.
- Treat it as a limited-content category (flag for awareness, no behavior change) — evidence: supported by the retrieval-floor gap and topic-redundancy findings.
- Request fewer questions from it (e.g. 1 instead of 2) — evidence: partially supported (only 2 genuinely distinct concept clusters found), but not strongly forced given a 2nd question does appear possible.
- Give it a different (larger) attempt budget — evidence: weakly supported by the single "used all 3 attempts" data point; not statistically established.
- Reconsider whether it should remain an independent canonical category (vs. folding into an existing one, e.g. merging its brain-mapping-adjacent content elsewhere) — evidence: the topic-overlap with `מיפוי ודימות מוחי` is a real, concrete finding worth architect attention, though the "history of anatomy" cluster is genuinely `מבוא`-specific and not naturally absorbed elsewhere.

No source code, prompts, configuration, category mappings, retrieval parameters, chunking, validators, generation policy, or attempt limits were modified in the course of this diagnostic. No commits were made.
