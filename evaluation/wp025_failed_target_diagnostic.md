# WP-025A — Failed-Target Diagnostic: WP-025 Acceptance Run's Four Exhaustions

Read-only diagnostic. No code, prompt, configuration, test, retrieval, attempt-limit, or architecture change was made at any point during this task. The full exam was not rerun. WP-026 was not implemented.

## 1. Executive Summary

The WP-025 acceptance run exhausted 4 of 40 planned questions (positions 5, 11, 26, 27), all with `QuestionAttemptsExhaustedError` after 3 candidate-generation attempts each. All 12 failed attempts were well-grounded (zero grounding rejections) and zero were generation-contract failures (zero invented evidence references) — every failure was an MCQ-construction problem: the generated question had more than one defensible correct answer.

**All four assigned targets shared the same structural property**: each target's `factual_focus` was phrased as a *classification/enumeration* ("X is divided into N types/parts: A, B, C...") rather than a single, specific relationship or property. Cross-referencing with the categories' successful sibling questions (and a broader sample of first-attempt-accepted WP-025 questions) shows a consistent pattern: questions that ask the model to identify **one specific item via a distinguishing property** succeed cleanly; questions that ask the model to **recall the full enumerated set** are prone to MCQ ambiguity, because natural distractors are subsets, near-subsets, or hierarchically-adjacent classifications that a rigorous MCQ validator cannot cleanly rule "wrong."

A small control run (Part 9) reusing the exact four failed targets in fresh, independent `QuestionProducer` calls found **3 of 4 targets succeeded easily** (2 on the first attempt, 1 on the third) — showing the original exhaustion for those three was substantially stochastic bad luck, not a deterministic property of the target. The fourth target (`מערכת העצבים ההיקפית`, PNS divided into autonomic/somatic) **exhausted again**, with the identical structural failure recurring in all 6 attempts across both runs: "sympathetic + parasympathetic" (a real, evidence-supported classification *one hierarchical level down*) keeps appearing as a distractor that validators correctly flag as also defensible. This is the strongest, most reproducible signal in the diagnostic.

**Regression assessment**: **B — target-planning quality issue**, narrowly scoped. The planner successfully optimizes for evidence-groundedness and topical diversity but does not currently consider MCQ suitability, specifically for classification/enumeration-shaped facts. This is a genuine WP-025-attributable mechanism, not merely "ordinary stochastic variance" restated: WP-025's explicit instruction that generation must not silently switch away from its assigned target removes the freedom pre-WP-025 unconstrained generation had to simply avoid MCQ-hard facts.

**Recommendation for WP-026**: **C — improve target-constrained generation** as the primary fix (evidenced by 3 of 4 cases resolving cleanly once generation picked a "single distinguishing property" framing instead of a "recall the enumeration" framing, from the *same* target and *same* evidence, no re-planning needed), with a narrow, secondary consideration under **B** specifically for targets whose evidence contains a hierarchically-adjacent alternative classification (the position-27 pattern), which reframing alone did not resolve in 6 attempts.

## 2. Reconstruction Table — All 12 Failed Attempts

**Important limitation, stated up front**: the persisted audit (`QuestionAttemptAudit`, per WP-015's original design) stores every validator's full result and reasoning for a rejected attempt, but does **not** persist the candidate's own generated question/answer text for a rejected attempt (only the final *accepted* candidate's text ever reaches `exam.json`). This is a genuine architectural gap for diagnostics of this kind, not something this task is authorized to fix. The table below reconstructs the substance of what each generated candidate was from the validators' own detailed reasoning (which frequently quotes or closely paraphrases specific answer content) — this is not a verbatim transcript of the original Hebrew question text.

| Pos | Attempt | Grounding | MCQ | Category | Quality | Textbook | Primary rejection reason(s) |
|---|---|---|---|---|---|---|---|
| 5 | 1 | PASS | **FAIL** | PASS | PASS | NOT_FOUND | MCQ: "no unambiguous single best answer... overlap in terminology and the nature of the classifications of white matter fibers" |
| 5 | 2 | PASS | **FAIL** | PASS | **FAIL** | NOT_FOUND | MCQ: "plausible combinations of terms... distractors similar in structure and terminology"; Quality: "lacks clarity and specificity... terms may overlap in meaning" |
| 5 | 3 | PASS | **FAIL** | PASS | **FAIL** | NOT_FOUND | MCQ: "multiple options contain plausible combinations of white matter types... distractors are not clearly incorrect"; Quality: "asks for types... without providing context or a clear framework" |
| 11 | 1 | PASS | **FAIL** | PASS | **FAIL** | NOT_FOUND | MCQ: "Answers 1 and 4 both state there are six layers, but they differ in their descriptions"; Quality: "not clearly formatted... asks for a specific number of layers and their characteristics without providing a clear structure" |
| 11 | 2 | PASS | PASS | PASS | **FAIL** | NOT_FOUND | Quality only: "lacks clarity and specificity... does not define what aspects should be considered... answer choices contain misleading information" |
| 11 | 3 | PASS | PASS | PASS | **FAIL** | NOT_FOUND | Quality only: "combines two distinct inquiries: the number of layers... and the unique characteristics of each layer" |
| 26 | 1 | PASS | **FAIL** | PASS | **FAIL** | CONSISTENT | MCQ: "presence of multiple structures in each answer choice complicates the determination of a single best answer"; Quality: "uses the term 'גרעינים' (nuclei) without specifying" |
| 26 | 2 | PASS | **FAIL** | PASS | **FAIL** | CONSISTENT | MCQ: "Answer 4 is nonsensical... repeats 'Cortex' and includes 'Ganglion'"; Quality: "inaccuracies and inconsistencies in anatomical terminology" |
| 26 | 3 | PASS | **FAIL** | PASS | **FAIL** | CONSISTENT | MCQ: "other options... also plausible in a broader context of brain structures, leading to ambiguity"; Quality: "terms not consistently in Hebrew... non-standard terms" |
| 27 | 1 | PASS | **FAIL** | PASS | PASS | NOT_FOUND | MCQ only: "more than one answer choice that could reasonably be defended as correct. Specifically, Answer 1 is correct, but Answer 3 also includes components of the peripheral nervous system" |
| 27 | 2 | PASS | **FAIL** | PASS | **FAIL** | NOT_FOUND | MCQ: "Both Answer 2... and Answer 3... are plausible combinations"; Quality: "answer choices include options that reference the central nervous system" |
| 27 | 3 | PASS | **FAIL** | PASS | **FAIL** | NOT_FOUND | MCQ: "Answer 2 is intended as the correct answer, but both Answer 3 and Answer 4 could also be defended as correct"; Quality: "factual inaccuracy... Answer 1 incorrectly includes 'מערכת העצבים המרכזית'" |

**Totals across 12 attempts**: grounding 12/12 PASS, MCQ 11/12 FAIL, category 12/12 PASS, quality 8/12 FAIL, textbook never blocking (NOT_FOUND ×9, CONSISTENT ×3, zero POTENTIAL_CONFLICT). MCQ rejection was present in every single failing attempt except one (position 11, attempts 2-3, which failed on quality alone) — but even those two quality-only rejections describe the identical underlying ambiguity ("combines two distinct inquiries," "lacks clarity... does not define what aspects should be considered") that MCQ rejected explicitly in attempt 1 for the same target.

## 3. Detailed Analysis of Each of the 4 Targets

### Position 5 — `חומר לבן` (STYLE_SIMILAR) — Target 1

- **Topic**: "סוגי חומר לבן" (types of white matter)
- **Factual focus**: "White matter in the brain is divided into different types, including projection fibers, commissural fibers, and association fibers."
- **Supporting evidence**: 2 chunks, directly listing and defining the three fiber types.

### Position 11 — `היסטולוגיה` (STYLE_SIMILAR) — Target 1

- **Topic**: "שכבות הנאוקורטקס" (neocortex layers)
- **Factual focus**: "The neocortex is divided into six different layers, each with unique characteristics."
- **Supporting evidence**: 1 chunk, listing the six layers by cell type and axonal target.

### Position 26 — `המוח הקטן` (INDEPENDENT) — Target 2

- **Topic**: "מבנה המוח הקטן" (cerebellum structure)
- **Factual focus**: "The structure of the cerebellum includes nuclei such as the Fastigial, Interposed, and Dentate Nucleus."
- **Supporting evidence**: 1 chunk, naming the three nuclei (with Interposed further split into Globose/Emboliform).

### Position 27 — `מערכת העצבים ההיקפית` (STYLE_SIMILAR) — Target 1

- **Topic**: "מערכת העצבים ההיקפית - חלוקות" (PNS divisions)
- **Factual focus**: "The basic division of the peripheral nervous system into two main systems: the autonomic nervous system and the somatic nervous system."
- **Supporting evidence**: 1 chunk, stating the PNS divides into autonomic and somatic systems - the same chunk region also contains the autonomic system's own sympathetic/parasympathetic sub-division, immediately adjacent in the source material.

## 4. Target/Evidence Suitability Assessment

| Question | Pos 5 | Pos 11 | Pos 26 | Pos 27 |
|---|---|---|---|---|
| A. Factually supported? | Yes | Yes | Yes | Yes |
| B. Sufficiently specific? | Borderline - names 3 categories but no single fact singled out | **No** - "6 layers, each with characteristics" names no specific layer/characteristic | Borderline - names 3 nuclei but no distinguishing single fact | Yes - only 2 named systems, the most specific of the four |
| C. Too broad? | Somewhat | **Yes, clearly** - invites covering "how many + what characterizes each" simultaneously | Somewhat | Mild |
| D. Too narrow? | No | No | No | No |
| E. Lends itself to a 4-option, 1-best-answer MCQ? | **Poor as phrased** (enumeration) | **Poor as phrased** (enumeration) | **Poor as phrased** (enumeration) | **Poor as phrased** - a real, evidence-adjacent classification one level down creates a plausible alternative |
| F. Evidence supports plausible distractors while leaving one clearly correct answer? | Only when generation narrows to one specific item's property (proven in the control run); not when asking for the full set | Only when generation asks about the *principle* of characterization, not the layers/characteristics themselves | Only when generation asks about one nucleus's specific identifying property | **No** - the natural "one level down" alternative was never avoidable across 6 total attempts |
| G. Describes a relationship/fact difficult to MCQ-ify without ambiguity? | Yes, as an enumeration | Yes, as an enumeration | Yes, as an enumeration | Yes, as a classification with a nested-hierarchy neighbor |
| H. Diverse but pedagogically awkward? | Yes | Yes | Yes | Yes |

**Good factual target vs. good MCQ target**: all four targets are unambiguously *good factual targets* - each is concise, evidence-grounded, and (per the WP-025 diversity review already completed) genuinely distinct from its category sibling. None of the four is a *good MCQ target as literally phrased* - each states a classification/enumeration rather than a single fact with one natural correct answer and clean distractors. This is exactly the distinction WP-025A section 2 anticipated.

## 5. Per-Attempt Root-Cause Classification

| Pos | Attempt | Classification | Evidence |
|---|---|---|---|
| 5 | 1, 2, 3 | **TARGET_PROBLEM** | Every attempt's MCQ rejection cites "overlap in terminology"/"plausible combinations" of the enumerated fiber types - the same structural issue recurs verbatim in different words across all three attempts, never converging. |
| 11 | 1 | **MIXED** (target + generation) | Attempt 1 tried to ask about "the number of layers AND their characteristics" simultaneously - a target-broadness problem generation could have narrowed but did not. |
| 11 | 2, 3 | **GENERATION_PROBLEM**, secondarily target-caused | Grounding and (attempt 2) MCQ passed; only quality failed, citing lack of a clear single framing ("does not define what aspects should be considered," "combines two distinct inquiries") - generation was drifting toward a broad, multi-part question rather than narrowing to one layer's one property, which the category's own sibling target proved achievable from a similarly enumerative starting point. |
| 26 | 1, 2, 3 | **TARGET_PROBLEM** | Every attempt's MCQ rejection cites the same structural issue: multiple real cerebellar/brain-region structures appearing across answer choices makes no option cleanly, uniquely correct. Attempt 2's quality rejection ("Answer 4 is nonsensical") and attempt 3's ("terms not consistently in Hebrew") show generation also struggling with distractor construction once forced to enumerate 3 named structures across 4 answer slots - a downstream symptom of the same root target framing, not an independent defect. |
| 27 | 1, 2, 3 | **TARGET_PROBLEM** | Identical, highly specific failure mode in all three attempts (confirmed a 4th, 5th, 6th time in the Part 9 control run): the evidence-adjacent, one-level-deeper classification (sympathetic/parasympathetic) keeps surfacing as a distractor that a rigorous validator cannot rule strictly wrong, since it genuinely is a valid PNS-related classification, just at the wrong hierarchical level for the question being asked. |

No attempt across all 12 showed evidence of `VALIDATOR_FALSE_NEGATIVE` (the validators' stated reasoning is specific, textually grounded, and - on inspection of the actual overlapping/ambiguous answer choices described - correct to reject), `EVIDENCE_LIMITATION` (evidence was never thin; if anything it was rich enough to make multiple classification levels available, which is *part* of the problem for position 27), or `HISTORICAL_STYLE_INTERFERENCE` (no rejection reason ever references style, form, or the historical reference at all - three of the four cases are STYLE_SIMILAR and one is INDEPENDENT, with no discernible difference in failure pattern between the two modes).

## 6. Cross-Case Pattern Analysis

Checking each pattern named in WP-025A Part 4 against the 12 attempts:

- **Ambiguous distractors**: present in all 12 attempts (universal).
- **Multiple technically correct answers**: the dominant, explicit MCQ-rejection reason in 11 of 12 attempts.
- **Distractors unsupported by evidence**: not observed - grounding passed 12/12; distractors were evidence-adjacent, not fabricated.
- **Overly broad factual_focus**: clearly present for position 11 (explicitly "6 layers, each with characteristics" with no single characteristic named); present to a lesser degree in all four.
- **Overly narrow factual_focus**: not observed in any case.
- **Definition-style targets**: not the pattern here - these are classification/enumeration targets, a related but distinct shape.
- **Structure/function targets**: 3 of 4 targets describe *structure* (white matter types, neocortex layers, cerebellar nuclei); 1 (PNS divisions) describes a *classification*. All four are still enumerative in shape regardless of structure-vs-function framing.
- **Targets that contain several facts at once**: yes, all four - each names 2-3 (position 27) or 3 (positions 5, 26) or 6 (position 11) distinct items as a single target.
- **Targets where the correct answer becomes obvious**: not observed - if anything the opposite (too many defensible answers).
- **Questions requiring information beyond supplied evidence**: not observed - grounding passed every time.
- **Hebrew wording ambiguity**: not a distinct pattern - quality validators repeatedly praised the Hebrew as "natural and grammatically sound"; the ambiguity described is always conceptual (multiple defensible answers), never linguistic.
- **Generation drifting away from the assigned target**: not observed - grounding validators confirmed every attempt's question matched its assigned target's evidence; generation stayed on-target throughout, it simply could not cleanly single-answer the enumeration.
- **STYLE_SIMILAR interference**: no evidence found (see above).
- **Repeated validator disagreement**: not observed between validators within a single attempt (grounding/MCQ/quality/category never contradicted each other about the same fact; MCQ and quality frequently *co-failed* for the same underlying reason, which is agreement, not disagreement).
- **Same rejection recurring all three times for one target**: **yes, for all four targets** - this is the single strongest, most consistent finding. Quantified: position 5 - "ambiguous/overlapping classification" in 3/3; position 11 - "broad/multi-part framing" in 3/3; position 26 - "multiple defensible structures" in 3/3; position 27 - "adjacent-hierarchy classification" in 3/3 (and again 3/3 in the independent control run - 6/6 total).

**Quantified summary**: 4/4 failed targets share the enumeration/classification structural pattern; 0/4 show evidence of a validator, evidence, or generation-drift problem as the *primary* cause; 1/4 (position 27) shows the pattern reproducing deterministically across two fully independent runs.

## 7. Comparison with Successful WP-025 Targets

### Same-category siblings (all four succeeded on the first attempt)

| Category | Failed target (enumeration-shaped) | Successful sibling (single-property-shaped) |
|---|---|---|
| חומר לבן | "types of white matter: projection/commissural/association fibers" | "Which white-matter **structure is found within the thalamus**?" → picks one item (External Medullary Lamina) via a specific locational property |
| היסטולוגיה | "neocortex has 6 layers, each with characteristics" | "**Which tissue type** makes up the CNS?" → picks one item (nervous tissue) from an enumerated set of 4, using the *other three* as automatically-wrong-category distractors |
| המוח הקטן | "cerebellum structure includes nuclei: Fastigial/Interposed/Dentate" | "What **role** is associated with the cerebellum in **learning** systems?" → picks one function (motor coordination) from a broader functional description |
| מערכת העצבים ההיקפית | "PNS divided into 2 systems: autonomic + somatic" | "**Which subsystem** is responsible for activity in **stress/fear** situations?" → picks one subsystem (sympathetic) via a specific functional property, at the correct hierarchical level for the question asked |

The pattern is completely consistent: every successful sibling asks the model to identify **one specific item via a distinguishing property** (location, specific function, specific alternate name), while every failed target's original attempts asked the model to **recall the enumerated set itself** (what are the types / how many layers / which nuclei / which two systems).

### Broader sample (10 additional first-attempt-accepted targets, other categories)

Every one of the 10 additionally sampled successful targets (`לוקליזציה פונקציונלית` ×2, `עצבים קרניאליים`, `מיפוי ודימות מוחי`, `אספקת דם` ×2, plus the four above) is phrased as a single location, a single primary function, or a single named entity's single property - never as "X is divided into / composed of N parts." This confirms the structural difference is not particular to the four failed categories; it is a general property distinguishing easy from hard WP-025 targets across the whole run.

## 8. Assessment of Whether WP-025 Caused a Reliability Regression

**Conclusion: B — target-planning quality issue**, precisely scoped.

Reasoning, weighing the possible conclusions against the evidence:

- **Not (A) "no evidence of regression"**: the four failures are not randomly distributed across target shapes - they are 4/4 concentrated on the one identifiable structural pattern (classification/enumeration targets), while 0 of the ~16 single-property-shaped targets observed in this run failed. A purely random/stochastic explanation would not produce this concentration. Additionally, the control run's reproducible re-exhaustion of the position-27 target (6/6 attempts across two independent runs, always the identical failure mode) is inconsistent with pure chance.
- **(B) target-planning quality issue - supported**: the planner (by design, per WP-025's own specification) optimizes for evidence-groundedness and inter-target diversity, but has no explicit notion of "MCQ suitability." All four failed targets are individually excellent *factual* targets (accurate, evidence-grounded, genuinely distinct from their siblings) and would very likely be flagged as good targets by the current planning prompt - yet three of the four categories' *other* target (chosen by the same planning call) happened to be single-property-shaped and succeeded immediately. The planner has no mechanism today to prefer the MCQ-friendlier framing when both are available and both are genuinely diverse.
- **Not primarily (C) generation prompt issue**: generation did not drift from its target, and the *same* generation prompt/model successfully converted three of the four exact same targets into accepted questions on retry (2 of them immediately) once it happened to land on a single-property framing - the generation prompt is capable of producing a good MCQ from an enumerative target, it is just not reliably instructed to prefer that framing.
- **Not (D) validator issue**: inspecting the actual described ambiguities (not merely trusting the rejection), the MCQ validator's objections are consistently well-founded - "sympathetic + parasympathetic" genuinely is a defensible answer to "what are the PNS's two main divisions" if the question does not make the hierarchy level unambiguous, and the repeated multi-structure distractor confusion for the cerebellum-nuclei target is a real ambiguity, not an overly strict misreading.
- **Architectural point specific to WP-025**: before WP-025, unconstrained generation had complete freedom to simply avoid asking about facts shaped like these four - it could silently choose any other fact from the category's evidence. WP-025 deliberately removed that freedom (`generation.txt`: "do not silently switch to another easier, or more familiar fact... do not broaden the target merely to make the question easier to write") in order to guarantee the diversity gains measured in the WP-025 completion report (16/16 distinct pairs). That same removal of freedom is the mechanism by which an occasional MCQ-hard-but-diverse target now reaches generation instead of being silently avoided. This is a genuine, identifiable trade-off introduced by WP-025's design, not a restatement of pre-existing stochastic variance.

The regression is real but **narrow and bounded**: 4 of 40 planned questions (10%), zero grounding or generation-contract failures, and (per the control run) at least 3 of the 4 specific cases are not deterministically unrecoverable.

## 9. Optional Control-Run Results (Part 7)

Performed - `OPENAI_API_KEY` was available. Exactly one fresh `QuestionProducer.produce_question()` call per failed target, reusing the exact same `QuestionTarget` object reconstructed from the persisted audit/plan-history artifacts (same `target_id`, `category`, `topic`, `factual_focus`, `supporting_evidence_chunk_ids`), normal production configuration, `max_generation_attempts=3` unchanged, no re-planning, no case repeated.

| Pos | Category | Result | Attempt | Notes |
|---|---|---|---|---|
| 5 | חומר לבן | **Accepted** | 1 | New framing: "which white-matter type connects same-hemisphere cortical areas?" - single distinguishing property, not the full enumeration. |
| 11 | היסטולוגיה | **Accepted** | 1 | New framing: "in what way are the neocortex layers characterized?" → "by cell type" - the organizing *principle*, not per-layer specifics. |
| 26 | המוח הקטן | **Accepted** | 3 | New framing: "which nucleus is also known as Globose/Emboliform?" - a single distinguishing alternate-name property. Needed all 3 attempts even so - elevated but not deterministic difficulty. |
| 27 | מערכת העצבים ההיקפית | **Exhausted again** | - (3/3 failed) | All three fresh attempts independently reproduced the identical "sympathetic+parasympathetic is also defensible" ambiguity found in the original run - 6/6 attempts across both runs share the same root cause. |

This distinguishes deterministic target difficulty from stochastic generation variance cleanly: three targets were merely unlucky in the original run (two trivially so - accepted on the very first fresh attempt); one target (`מערכת העצבים ההיקפית`, PNS divisions) shows a reproducible, structural difficulty that is the strongest single finding of this diagnostic.

## 10. Recommended Direction for WP-026

**Primary: C — improve target-constrained generation.**

Evidenced by: 3 of 4 failed targets converted successfully to an accepted MCQ from the *exact same* target and evidence, with no re-planning, purely by generation landing on a "identify one specific item via a distinguishing property" framing instead of a "recall the full enumerated classification" framing. The generation prompt could be strengthened (a smallest-possible addition, not implemented here) to explicitly instruct: when the assigned target's factual focus itself names multiple items/parts, the question should ask about one specific, uniquely-identifying property of one item (a location, a distinguishing name, a specific function) rather than asking the model to recall the complete set - mirroring exactly the framing every successful attempt in this diagnostic (both same-category siblings and the control-run recoveries) already used spontaneously.

**Secondary, narrower consideration under B**: for the position-27 pattern specifically (a target whose evidence contains a hierarchically-adjacent alternative classification, e.g. autonomic/somatic vs. the nested sympathetic/parasympathetic), generation-side reframing alone did not resolve it in 6 independent attempts. If this pattern recurs at larger scale, target planning could additionally be given a smallest-possible instruction to prefer the most MCQ-stable hierarchical level available in the evidence, or to note the presence of a nested alternative classification. This is offered as a secondary, not primary, recommendation - the evidence for it rests on a single case (n=1 target, albeit 2/2 independent reproductions), versus the generation-framing pattern which is supported by 3 independent successful recoveries plus the entire successful-target comparison sample.

No implementation was performed for either direction. This is measurement only.

## 11. Explicit Statement

No code, prompt, configuration, test, retrieval, attempt-limit, or architecture change was made at any point during this diagnostic. The full 40-question exam was not rerun. The four targets used in the Part 9 control run were reused exactly as persisted, never re-planned, never modified. WP-026 was not started or implemented.
