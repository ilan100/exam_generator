# WP-052 Completion Report — Property-vs-Identity Strategy Selection Study

## 1. Objective

WP-051 closed target-selection filtering: `Caudate Nucleus`/`Nucleus Accumbens` lack a known distinguishing property, but still reliably produce accepted questions via the bare-identity/naming shape, so the target must remain eligible. WP-052's narrower objective: can the existing authoritative evidence safely tell us, **before generation**, whether to attempt a PROPERTY question or go directly to an IDENTITY question for a given target — investigation only, no prompt change, no new validator, no target filtering, no production implementation unless the historical data clearly justifies it.

## 2. WP-051 Findings (Recap, OBSERVED)

Six of seven candidate sufficiency signals had zero discriminating power; one new signal (distinct-chunk mention count: `Globus Pallidus`=5, `Caudate Nucleus`/`Nucleus Accumbens`=2) correctly separated the three targets, but using it as a target-*skip* mechanism would have discarded 8 of 11 real accepted `Caudate Nucleus`/`Nucleus Accumbens` questions — all via the bare-identity shape. Decision: Option C, no target filtering. The architecture review recommended reframing the question from "should we generate for this target" to "what question strategy should we attempt."

## 3. Method (OBSERVED, this WP)

No new live pilot was run (per section 47's precedent, reused here). Every real attempt (not just round-level outcomes) across all 15 real `גרעיני הבסיס` rounds for the three primary targets (WP-045/046/047/049, 31 total generation attempts) was individually reconstructed and classified as `PROPERTY` or `IDENTITY` by a small, deterministic, keyword-based classifier operating on the real generated question text — `implementation/wp052_strategy_probe.py` (committed alongside this report, never imported by `src/`, zero LLM calls). The classification rule: `IDENTITY` if the question uses a naming/"also known as" construction or a direct "X is/are TARGET_NAME" copula referencing the target, and does not also contain a property-predicate marker (function/source/influence/location/association/enablement/membership); `PROPERTY` if a property-predicate marker is present. Every one of the 31 real attempts classified cleanly (zero `OTHER/UNCLEAR`).

## 4. Current Generation Strategy Behavior (Section 3, OBSERVED)

There is no explicit strategy selection anywhere in the current architecture — `QuestionGenerator`/`QuestionProducer` make one LLM call per attempt with the same prompt regardless of prior attempts within the same round (aside from ordinary retry context), and the LLM implicitly chooses what kind of predicate to test each time. WP-049's own prompt guidance nudges toward "find a specific property," which is exactly what the real data shows generation attempting first, most of the time, for these three targets, before sometimes falling back to a bare-identity question within the same round's remaining attempts.

## 5. Identity Strategy Definition (Section 4, per the real data)

A question whose correct-answer choice is uniquely determined by the target's own name/identity (e.g. `"which of the following IS Caudate Nucleus"`, `"...also known as Nucleus Accumbens"`) rather than by any distinguishing factual property. Uses the existing output contract unchanged — no new schema, no new field; classified here only for analysis.

## 6. Property Strategy Definition (Section 5, per the real data)

A question whose correct-answer choice depends on a specific evidence-supported fact about the target (membership/classification, function, location, source/origin, association) that the LLM intends to be true of the target and false of the distractors.

## 7. Historical Strategy Reconstruction / Baseline Metrics (Sections 6-7, 45, exact real counts via `wp052_strategy_probe.py`)

| Target | Rounds | Accepted rounds | Attempts | PROPERTY attempts | PROPERTY accepted | IDENTITY attempts | IDENTITY accepted | Avg attempts/accepted round | Observed identity failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `Globus Pallidus` | 4 | 4 (100%) | 8 | 4 | 1 (25.0%) | 4 | 3 (75.0%) | 2.00 | 1 (WP-046 r3 a1) |
| `Caudate Nucleus` | 5 | 3 (60%) | 12 | 8 | **0 (0.0%)** | 4 | 4 (100%) | — | 0 |
| `Nucleus Accumbens` | 6 | 5 (83.3%) | 11 | 8 | 1 (12.5%) | 3 | 3 (100%) | — | 0 |
| `Caudate Nucleus` + `Nucleus Accumbens` (combined) | 11 | 8 (72.7%) | 23 | 16 | 1 (6.25%) | 7 | 7 (100%) | 1.75 | 0 |

`Caudate Nucleus`'s own property-attempt success rate is **exactly 0/8** — the strongest, cleanest signal in this whole investigation, and it independently corroborates WP-050's own separate finding ("no property-based success found in 16 real historical rounds" — this WP's more granular per-attempt count refines that to 0/8 property *attempts*, not just 0 successful rounds). `Nucleus Accumbens`'s one property success (1/8) is the same WP-046 "center of the reward system" round WP-050 already flagged as validator-fidelity-uncertain (§9/§16 below) — not independent confirmation that property questions work for this target.

## 8. Property Availability Analysis (Section 8/17, required table, Section 46)

| Target | Known distinguishing property? | Evidence supporting decision | Property evidence location | Confidence | Recommended strategy |
|---|---|---|---|---|---|
| `Globus Pallidus` | **YES** | Thalamus suppression via GPi in the direct pathway (WP-050 §13, corroborated across 3 independent chunks) | Full cross-chunk evidence — **not** inside its own narrow/broad `factual_focus` (WP-050/051) | Medium-High (one clear, corroborated fact; still only 25% empirical property-attempt success, likely a generation-reliability gap on top of evidence availability) | `PROPERTY` when reachable, `IDENTITY` as reliable fallback — do **not** force identity-only here, it would discard the one genuinely informative question type this target supports |
| `Caudate Nucleus` | **NO** (0/8 real property attempts ever succeeded; WP-050's exhaustive read of all 8 retrieved chunks found no individually-attributed fact) | Absence confirmed by both an exhaustive manual evidence read (WP-050) and, independently, by every real generation attempt (this WP) | N/A | High confidence in the *negative* finding, for this corpus | `IDENTITY` — property attempts are empirically futile here |
| `Nucleus Accumbens` | **UNKNOWN/uncertain** — one accepted property question exists (WP-046 r2, "center of the reward system"), but WP-050 already flagged it as not actually attributable to this target in the *supplied* evidence (the corpus's own reward-system statement is category-level) | Same flagged case; not independently re-resolved by this WP | Ambiguous — possibly relies on knowledge beyond supplied evidence | Low confidence either direction | `IDENTITY` preferred (1/8 empirical property success, and that one success is itself of uncertain evidentiary grounding) |

## 9. Full-Evidence Analysis (Section 9, recap of WP-050/051, OBSERVED)

Re-confirmed, not re-derived: `Globus Pallidus`'s real distinguishing fact is reachable only through the full, cross-chunk evidence text, never through its own narrow or broad `factual_focus` anchor. Any strategy signal built only from `factual_focus` would misclassify `Globus Pallidus` identically to `Caudate Nucleus`/`Nucleus Accumbens` — the same trap WP-051 already identified and avoided. This is why this WP's strategy-signal analysis (§10) treats `factual_focus`-only signals as unsafe by construction, not merely unproven.

## 10. Strategy-Signal Analysis (Section 10, required table, Section 48)

| Signal | Property availability accuracy | Identity recommendation accuracy | Deterministic | Evidence-grounded | False-positive risk | False-negative risk | Safe? |
|---|---|---|---|---|---|---|---|
| Distinct chunk count (WP-051) | Correctly ranks all 3 targets (5 vs 2 vs 2), consistent with §7's success-rate data | Correctly would not force identity-only on `Globus Pallidus` | Yes | Yes | Untested at scale beyond this one category/3 targets (WP-051 §22) | None observed in this data | **Partially** — real, promising, but unvalidated generally |
| Existing relationship (`extract_relationship() != UNSPECIFIED`) | No — identical (`UNSPECIFIED`) for all 3 targets (WP-050/051, confirmed again) | No discriminating power | Yes | Yes | N/A (never varies) | N/A (never varies) | Not useful as-is |
| Non-enumerative evidence (`is_enumeration_evidence_insufficient()`) | No — identical (`False`) for all 3 targets (WP-051) | No discriminating power | Yes | Yes | N/A | N/A | Not useful as-is |
| Full-evidence target-specific evidence (WP-050's hand-built `TRUE`/`FALSE`/`UNKNOWN` matrix) | **Yes** — the actual ground truth this WP's real success-rate data (§7) independently corroborates | Yes | No — requires the same manual/exhaustive evidence read WP-050 performed; not automatable without either new semantic extraction (forbidden) or per-target hard-coding (forbidden) | Yes | None found | None found | Accurate but **not currently computable deterministically at scale** — the actual limiting factor |
| This WP's own strategy classifier, applied *retrospectively* to real generation attempts | N/A — this classifies *output*, not *input*; cannot run before generation exists | N/A | Yes (as an offline analysis tool) | Yes | N/A | N/A | Not a pre-generation signal by construction — analysis-only |

The central, honest finding: the one signal that is **accurate** (WP-050's manual evidence read) is not **automatable** without violating an explicit prohibition (semantic extraction or per-target rules), and the one signal that is **automatable and deterministic** (chunk count) is accurate on this exact 3-target sample but **unvalidated at scale** (WP-051's own already-disclosed limitation, unchanged by this WP).

## 11. Historical Counterfactual Replay (Sections 11, 36-38, required table, Section 56)

For every round that reached an `IDENTITY` attempt, the number of `PROPERTY` attempts that preceded it within that same round is a directly observed, non-hypothetical saving. For rounds that never reached `IDENTITY` (fully exhausted on `PROPERTY` alone), any claim that `IDENTITY` would have succeeded is an explicit **HYPOTHESIS**, not a fact — per section 38's own requirement.

| Round | Actual attempt sequence (strategy) | Actual result | Hypothetical first strategy | Directly observed attempts saved | Would accepted output change? |
|---|---|---|---|---:|---|
| WP-045 r1 (Caudate) | PROPERTY, PROPERTY, IDENTITY | Accepted (a3) | IDENTITY | 2 (OBSERVED) | No — already accepted |
| WP-045 r2 (NAcc) | IDENTITY | Accepted (a1) | IDENTITY | 0 | No |
| WP-046 r1 (Caudate) | PROPERTY, IDENTITY | Accepted (a2) | IDENTITY | 1 (OBSERVED) | No |
| WP-046 r2 (NAcc) | PROPERTY (accepted) | Accepted (a1) | uncertain — see §8 | 0 | No, but strategy is itself uncertain-grounded |
| WP-047 r1 (Caudate) | PROPERTY, PROPERTY, IDENTITY | Accepted (a3) | IDENTITY | 2 (OBSERVED) | No |
| WP-047 r2 (NAcc) | PROPERTY, PROPERTY, PROPERTY | **Rejected (exhausted)** | IDENTITY (HYPOTHESIS only) | up to 2-3 (HYPOTHESIS) | **Possibly** — this round could have become accepted, not proven |
| WP-047 r3 (NAcc) | PROPERTY, PROPERTY, PROPERTY | **Rejected (exhausted)** | IDENTITY (HYPOTHESIS only) | up to 2-3 (HYPOTHESIS) | **Possibly** |
| WP-047 r4 (NAcc) | PROPERTY, IDENTITY | Accepted (a2) | IDENTITY | 1 (OBSERVED) | No |
| WP-049 r1 (Caudate) | PROPERTY, PROPERTY, PROPERTY | **Rejected (exhausted)** | IDENTITY (HYPOTHESIS only) | up to 2-3 (HYPOTHESIS) | **Possibly** |
| WP-049 r2 (Caudate) | IDENTITY | Accepted (a1) | IDENTITY | 0 | No |
| WP-049 r3 (NAcc) | IDENTITY | Accepted (a1) | IDENTITY | 0 | No |
| WP-045 r3 (GPallidus) | PROPERTY, PROPERTY (accepted) | Accepted (a2) | uncertain — property genuinely viable here | 0 | No |
| WP-045 r4 (GPallidus) | PROPERTY, PROPERTY, IDENTITY | Accepted (a3) | uncertain | 2 (OBSERVED) | No |
| WP-046 r3 (GPallidus) | IDENTITY, IDENTITY | Accepted (a2) | IDENTITY | 0 | No |
| WP-049 r4 (GPallidus) | IDENTITY | Accepted (a1) | IDENTITY | 0 | No |

## 12. Potential Attempts Saved (Section 12/37, exact counts)

**Directly observed** (only counting rounds that actually reached an `IDENTITY` attempt, per `wp052_strategy_probe.py`): **8 attempts total** across all 15 rounds — 6 from `Caudate Nucleus`/`Nucleus Accumbens` rounds, 2 from `Globus Pallidus` rounds. This is a real, non-hypothetical number: had generation gone straight to `IDENTITY` in exactly these rounds, these 8 wasted `PROPERTY` attempts would not have occurred, with no change to the accepted outcome.

**HYPOTHESIS only** (the 3 fully-exhausted `Caudate Nucleus`/`Nucleus Accumbens` rounds, 9 attempts, currently rejected): if `IDENTITY` had been attempted in these rounds and succeeded (consistent with, but not proven by, its 100% observed success rate elsewhere in this exact sample), up to 9 further attempts could have been saved **and** these 3 rounds could have become accepted output (11/11 = 100% hypothetical acceptance for `Caudate Nucleus`/`Nucleus Accumbens`, up from the real 8/11 = 72.7%). This is the single largest potential upside identified, and it is explicitly unproven — per section 38, the sample of `IDENTITY` attempts that actually ran is not a random sample of all rounds; it is disproportionately drawn from rounds where `PROPERTY` had already failed at least once, so its 100% success rate could be inflated by rounds that happened to be "easy" in some unmeasured way.

## 13. Accepted-Output Impact (Section 13)

No accepted round would have been *lost* under a hypothetical "try identity first for Caudate Nucleus/Nucleus Accumbens" policy — every round that already succeeds does so via `IDENTITY` as its final strategy in 7 of 8 cases (§7), and the one exception (WP-046 r2, `PROPERTY`) is itself evidentially uncertain (§8). The only plausible impact is a **gain** (§12's hypothesis), never a loss, for these two targets specifically. For `Globus Pallidus`, forcing identity-only would remove the one real, evidence-grounded property success (25% of property attempts) — this must not be done (§16 below).

## 14. Question-Diversity Impact (Section 14/39)

If `Caudate Nucleus`/`Nucleus Accumbens` were steered toward `IDENTITY` questions specifically, real historical diversity of *question shape* for these two targets would narrow (currently a mix of attempted-but-failing property predicates and eventually-successful identity questions; a steered version would mostly show identity questions). This is a real, measurable tradeoff — cleaner/faster generation at the cost of predicate variety for exactly these two targets. `Globus Pallidus` diversity would be preserved (its property attempts are not futile, so nothing about this data justifies discouraging them there).

## 15. Coverage Impact (Section 15)

None — the target itself is never skipped under any strategy considered here (unlike WP-051's rejected target-filtering approach). Category coverage/`tested_concepts` behavior is entirely unaffected; only the *shape* of the question attempted for an already-selected target would change, if anything were implemented.

## 16. Counterexamples (Section 16/49, required)

The mandatory `Globus Pallidus` counterexample was tested directly (§7-§10): it is **not** misclassified as "no property" by the real success-rate data (25% property success, non-trivial), and any signal that would treat it identically to `Caudate Nucleus`/`Nucleus Accumbens` (e.g. a `factual_focus`-only check) is explicitly rejected as unsafe (§9). No counterexample was found in the other direction (a target with "apparently weak" evidence that nonetheless produced a strong property question) beyond the already-flagged, uncertain `Nucleus Accumbens` reward-system case (§8) — which is exactly the kind of case this section asks to be analyzed explicitly, and it already was, in WP-050.

## 17. Safety Analysis (Section 17/43)

- Could a signal treat `UNKNOWN` as `FALSE`? The one deterministic, automatable signal (chunk count) does not reason in `TRUE`/`FALSE`/`UNKNOWN` terms at all — it is a coarse aggregate count, not a property-truth-value system, so this specific failure mode does not apply to it directly; but it also means it cannot express uncertainty, which is itself a limitation, not a safety guarantee.
- Could category-level evidence be treated as target-specific? Already the central risk this whole investigation chain (WP-048→WP-052) keeps re-confirming (the `Nucleus Accumbens` reward-system case) — not solved by anything in this WP.
- Could it reject a valid target or admit an unsuitable one? Not applicable — no target filtering is proposed here (WP-051 already closed that).
- Could it reduce coverage or cause repeated target reuse? No (§15).

## 18. Candidate Strategy-Selection Architecture (Section 18, required table, Section 57)

| Architecture | Target retained? | Property strategy | Identity fallback | Deterministic? | Risk | Recommendation |
|---|---|---|---|---|---|---|
| Current behavior (no strategy selection) | YES | default/current (implicit LLM choice) | YES (via retry) | N/A | Wastes 8 observed + up to 9 hypothesized attempts across the real dataset | Baseline |
| Target filtering (WP-051) | NO | — | — | Yes | Discards 8/11 real accepted questions | **Already REJECTED (WP-051)** |
| Strategy selection (this WP's subject) | YES | conditional, based on a per-target signal | YES | Only the chunk-count signal is deterministic and automatable; the accurate signal (manual evidence read) is not | Unvalidated generalization risk (§10); would need a controlled generation experiment to confirm it changes real LLM behavior as hypothesized | **Recommend an experimental follow-up, not direct production implementation** |
| Always identity | YES | NO | YES | Trivial | Removes `Globus Pallidus`'s one real property success; reduces diversity project-wide with no justification for targets where property works | **Not recommended** |

## 19. Implementation Criteria Checklist (Section 19/51)

1. Deterministic/safely bounded? — **Partial.** The accurate signal (manual read) is not automatable; the automatable signal (chunk count) is deterministic but unvalidated beyond n=3 targets/1 category.
2. Uses authoritative evidence? — Yes.
3. Never treats `UNKNOWN` as `FALSE`? — Satisfied by construction (chunk count is not a property-truth system); but this also means it cannot express calibrated uncertainty.
4. Correctly preserves the `Globus Pallidus` property case? — Yes (§16).
5. Correctly identifies `Caudate Nucleus`/`Nucleus Accumbens` as difficult in the current corpus? — Yes, strongly (§7: 0/8 and 1/8 property success respectively).
6. Does not reduce accepted output? — **Unproven, only a strong hypothesis** (§12/§13) — no accepted round would be lost in the observed data, but whether a real prompt change would reproduce the same 100% identity success rate under a genuinely different instruction (rather than the retry-driven fallback observed here) is untested.
7. Measurable reduction in wasted attempts? — Yes, at minimum 8 directly observed, plausibly more (§12).
8. Does not destroy useful diversity? — **Requires care** (§14) — full identity-forcing would narrow diversity for two targets; a real implementation would need to preserve some property attempts, not eliminate them.
9. Does not alter coverage semantics? — Confirmed unaffected (§15).
10. Existing validators unchanged? — Yes, nothing here touches them.

**Overall: 6 of 10 criteria clearly satisfied, 2 satisfied with caveats, 2 unproven pending an actual controlled experiment.** Per section 52, this does not meet the bar for direct production implementation.

## 20. Recommended Decision (Section 20/50)

```text
B — A conservative strategy signal exists but needs a controlled generation
experiment before implementation; recommend experimental WP-053.
```

Not **A**, because criteria 6 and 8 (§19) are not yet proven — the historical data is retrospective (identity attempts observed here were themselves triggered by an unmanaged LLM choice, often after property attempts already failed), not a genuine test of what would happen if a prompt explicitly instructed generation to prefer identity for these targets from attempt 1. Not **C**, because the evidence is too strong and too consistent (0/8, 1/8 vs. 100%/100%/75% identity success, corroborated independently by two separate WPs' worth of analysis) to say no signal exists at all. Not **D** — the evidence is decisive enough to define the next experiment precisely, not merely "inconclusive."

## 21. Prototype Results (Section 21)

One prototype-only, read-only script this WP: `implementation/wp052_strategy_probe.py` (committed alongside this report, never imported by `src/`, zero LLM calls) — classifies all 31 real historical attempts and computes every metric in this report by direct execution against real, already-captured pilot data.

## 22. Regression (Section 22/53)

**NOT APPLICABLE.** No production code was changed. `git status --porcelain src/ tests/` confirms no modifications to either directory.

## 23. Unresolved Issues (Section 23)

- Whether a real, controlled prompt experiment (mirroring WP-049's own one-shot, no-reruns discipline) that explicitly instructs generation to attempt identity-first for targets flagged as "no known property" would reproduce the retrospective 100%/100% identity success rate, or whether that rate is partly an artifact of identity only having been tried after property already failed (a different generation context than "identity first"), is untested and is exactly what a WP-053 experiment should measure.
- The `Nucleus Accumbens` reward-system validator-fidelity question (WP-050 §12/16, re-confirmed here as the one property success for that target) remains open and unresolved by this WP.
- `Basillar artery`'s own separate WP-048 thread remains untouched (out of scope, §3).
- The chunk-count signal (WP-051, re-used here as the only automatable proxy) remains unvalidated beyond this one category and 3 targets.

## 24. Recommendation for WP-053 (Section 24)

**Recommend an experimental WP-053**, narrowly scoped: a single, controlled, prototype-only prompt variant (never production, per this WP's own section 30 restriction) that instructs generation, for `Caudate Nucleus`/`Nucleus Accumbens` specifically, to attempt an identity-shaped question on its *first* attempt rather than a property-shaped one, run as one fresh live pilot (no reruns, matching WP-049's own precedent), measuring: (1) does first-attempt acceptance rate rise toward the retrospective 100% observed here, (2) is any accepted output lost, (3) is `Globus Pallidus` behavior unaffected (it must not be included in the identity-first instruction, since its property strategy is genuinely viable). If the experiment confirms the hypothesis, only then recommend a real, permanent prompt implementation as a further WP; if it does not, document the negative result honestly, exactly as WP-049 already modeled.

## Required Final Strategy Table (Section 55)

| Target | Property strategy justified? | Identity strategy justified? | Current behavior | Hypothetical preferred strategy | Evidence |
|---|---|---|---|---|---|
| `Globus Pallidus` | Yes (25% real success, one genuine evidence-grounded property) | Yes (75% real success) | Unmanaged, implicit LLM choice | Keep both available — do not force either | §7, §8, §16 |
| `Caudate Nucleus` | **No** (0/8 real successes) | Yes (4/4 real successes) | Unmanaged — wastes attempts on property first, most rounds | `IDENTITY`-preferred (pending WP-053's own controlled confirmation) | §7, §8 |
| `Nucleus Accumbens` | Uncertain (1/8, evidentially flagged) | Yes (3/3 real successes) | Unmanaged | `IDENTITY`-preferred (pending WP-053), do not treat the one property success as reliable | §7, §8 |

---

## Required Terminal Summary

```text
WP-052 complete.

Objective:
Determine whether the existing authoritative evidence can safely tell us,
before generation, whether to attempt a distinguishing-property question
or go directly to a bare-identity question, for Globus Pallidus / Caudate
Nucleus / Nucleus Accumbens.

Primary targets:
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens

Current generation strategy:
No explicit strategy selection exists anywhere - the LLM implicitly
chooses a predicate shape each attempt, nudged by WP-049's existing
"find a specific property" prompt guidance.

Historical baseline:
31 real attempts across 15 real rounds, classified deterministically by
question text as PROPERTY or IDENTITY. Globus Pallidus: 4/4 rounds
accepted (property 25% success, identity 75%). Caudate Nucleus: 3/5
rounds accepted (property 0/8 = 0% success, identity 4/4 = 100%).
Nucleus Accumbens: 5/6 rounds accepted (property 1/8 = 12.5%, identity
3/3 = 100%).

Property strategy:
Justified only for Globus Pallidus (one real, evidence-grounded unique
property, corroborated by WP-050). Empirically futile for Caudate
Nucleus (0/8) and unreliable/uncertain for Nucleus Accumbens (1/8, and
that one success is itself evidentially flagged).

Identity strategy:
100% observed success for Caudate Nucleus (4/4) and Nucleus Accumbens
(3/3), 75% for Globus Pallidus (3/4). Zero observed identity failures
for the two harder targets.

Known distinguishing properties:
One: Globus Pallidus / thalamus suppression (not Caudate Nucleus or
Nucleus Accumbens - re-confirmed, not just recalled from WP-050).

Strategy signals investigated:
The one accurate signal (WP-050's manual evidence read) is not
automatable without forbidden semantic extraction or per-target
hard-coding. The one automatable, deterministic signal (WP-051's
distinct-chunk count) is accurate on this sample but unvalidated at
scale. Relationship classification and enumeration-insufficiency
signals have zero discriminating power (identical for all 3 targets).

Historical counterfactual:
8 attempts directly saved (observed, non-hypothetical) across rounds
that already reached an identity attempt. Up to 9 more attempts
(hypothesis only) and 3 additional accepted rounds possible if identity
had been tried first in the 3 fully-exhausted Caudate/Nucleus Accumbens
rounds - not proven, flagged as the key open question for WP-053.

Potential attempts saved:
8 observed, up to 17 total if the unproven hypothesis holds.

Accepted-output impact:
No accepted round would have been lost under a hypothetical
identity-first policy for Caudate Nucleus/Nucleus Accumbens; only
possible gains identified, never losses.

Question-diversity impact:
Would narrow real predicate variety for Caudate Nucleus/Nucleus
Accumbens specifically if implemented; Globus Pallidus diversity
preserved since forcing identity-only there is explicitly not
recommended.

Coverage impact:
None - target selection itself is unaffected; only question shape for
an already-selected target would change if anything were implemented.

Safe deterministic strategy selector:
PARTIAL

Recommended architecture:
No direct production change. A conservative signal (0/8 and 1/8 vs.
100%/100% identity success) is real and strong, but the historical data
is retrospective, not a genuine test of an identity-first instruction -
recommend a narrow, controlled, prototype-only experiment (WP-053)
before any permanent implementation.

Production implementation:
NONE

Regression:
NOT APPLICABLE - no production code changed.

Unresolved issues:
Whether a real identity-first prompt experiment reproduces the
retrospective 100% success rate is untested. The Nucleus Accumbens
reward-system validator-fidelity question (WP-050) remains open.
Basillar artery thread (WP-048) remains untouched.

Recommended WP-053:
A single, controlled, prototype-only prompt experiment (never
production) instructing generation to attempt identity-first for
Caudate Nucleus/Nucleus Accumbens specifically (never Globus Pallidus),
run as one fresh live pilot with no reruns, measuring first-attempt
acceptance rate and confirming no accepted output is lost - only then
recommend a permanent implementation WP.

Completion report:
implementation/WP-052_COMPLETION_REPORT.md

Waiting for architect review.
```
