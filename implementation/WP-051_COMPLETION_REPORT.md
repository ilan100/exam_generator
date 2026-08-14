# WP-051 Completion Report — Target Evidence Sufficiency / Questionability Study

## 1. Objective

WP-050 found that `Caudate Nucleus`/`Nucleus Accumbens` have no evidence-supported unique property in the retrieved corpus at all, while `Globus Pallidus` has one. WP-051's objective: determine whether the *existing* authoritative evidence can tell us, **before generation**, whether a selected target has enough target-specific information to make attempting generation worthwhile — investigation only, scoped to `גרעיני הבסיס` and the same three targets, no prompt changes, no new validator, no LLM judge, no production target-selection change unless clearly justified.

## 2. WP-050 Findings (Recap, OBSERVED)

Direct execution of the real pipeline found zero deterministic distinguishing signal in today's actual generation prompt payload for all three targets (empty-ish `factual_focus`, `UNSPECIFIED` relationship, zero competitors). A hand-built `TRUE`/`FALSE`/`UNKNOWN` matrix, from exhaustively reading all 8 retrieved chunks, found `Globus Pallidus` has a genuine unique property (thalamus suppression via GPi) while `Caudate Nucleus`/`Nucleus Accumbens` have none anywhere in the corpus. Decision: Option C, no candidate-uniqueness mechanism implemented. WP-050's own architecture review recommended this WP as the next productive direction: evidence-*sufficiency* (worth attempting at all) rather than evidence-*uniqueness* (a specific property beats every sibling).

## 3. Method (OBSERVED, this WP)

No new live pilot was run (per section 47). All evidence is either (a) real, already-captured pilot data (`wp045`–`wp049`, 16 real `גרעיני הבסיס` rounds), or (b) two prototype-only, read-only inspection scripts reusing real, unmodified production functions: `implementation/wp050_architecture_probe.py` (from WP-050, reused) and `implementation/wp051_signal_probe.py` (new this WP, committed alongside this report) — zero LLM calls, zero new production logic, never imported by `src/`.

## 4. Current Target-Selection Flow (Section 37, OBSERVED)

```text
category
   ↓
retrieve_for_category()                    (retrieval/, TF-IDF, deterministic)
   ↓
refine_concept_inventory()                 (planning/concept_anchor.py — full inventory, ~53 concepts for גרעיני הבסיס)
   ↓
_select_remaining_concepts()               (planning/planner.py — excludes coverage.tested_concepts, keeps inventory order)
   ↓
per remaining concept, in order, until `count` targets built:
   anchor_concept_evidence() narrow → is_factual_focus_sufficient()?
       insufficient → anchor_concept_evidence(broad=True) → still insufficient? → SKIP concept entirely
   is_enumeration_evidence_insufficient()? → SKIP concept entirely
   detect_source_evidence_role() / extract_source_relationship_entity()
   detect_enumeration_member_shape()
   ↓
QuestionTarget (topic, factual_focus, named_entity_target=True, ...)
   ↓
generation (QuestionProducer, 3-attempt budget, 5 validators)
```

The exact insertion point for a future evidence-*sufficiency* decision (section 17) is **inside the same per-concept loop in `_plan_targets_from_concept_inventory()` (`planning/planner.py`, lines ~414–456)**, immediately alongside the two existing skip checks (`is_factual_focus_sufficient`/broad-fallback, and `is_enumeration_evidence_insufficient`) — both already implement exactly this "skip a concept before building a target for it" pattern; a sufficiency check would be a third, structurally identical skip condition in the same loop, not a new architectural layer.

## 5. Current Evidence Flow (Section 38, OBSERVED)

At target-selection time, the following is already available, per concept: `concept.evidence_chunk_id` (one canonical chunk id — the concept's *first-occurrence* chunk only, not every chunk it appears in), `concept.factual_focus` (a wide fixed-window snippet from `extract_concept_inventory()`, not yet the narrow anchor), `concept.source_line_indices`. The **full retrieved `source_evidence` tuple (all 8 chunks) is already in scope** at this point (it is the input to `refine_concept_inventory()` itself) — so a cross-chunk sufficiency signal (§9 below) requires no new retrieval call, only reusing data already in hand. `existing questions`/`coverage` are also already available (`CategoryCoverage`, passed into this same method). Not yet available at this point: any structured property/relationship representation (confirmed absent by WP-050) and any per-concept *count of distinct supporting chunks* (computed today only implicitly, one chunk id per concept, never aggregated).

## 6. Definition of Evidence Sufficiency Used (Section 5/7)

Operationalized, per WP-051 section 8's own required distinction:

```text
OBSERVED: "evidence sufficiency" (this WP) = enough source information
exists to justify attempting generation at all.

OBSERVED: "generation success" (already measured by WP-045-049) = the LLM
actually produced a valid, accepted question.

A target can have sufficient evidence and still fail generation (ordinary
validator rejection). A target can have thin evidence and still succeed
(the bare-identity fallback question shape - see section 11).
```

This WP tests candidate signals against the first definition, then separately checks (section 11/13) whether flagging a target "insufficient" would have discarded real, valid accepted questions of the second kind — the exact distinction section 8 requires be kept separate.

## 7. Target Evidence Reconstruction (Section 6/10, OBSERVED, via `wp050_architecture_probe.py` + `wp051_signal_probe.py`)

| Target | Own concept inventory chunk | Narrow `factual_focus` | Broad `factual_focus` | Distinct chunks mentioning the concept's own full name, among the 8 retrieved |
|---|---|---|---|---|
| `Caudate Nucleus` | `...0036...` | `"o\nCaudate Nucleus\no"` | identical (no wider content reachable) | **2** (`...0036...`, `...0063...`) |
| `Nucleus Accumbens` | `...0036...` | `"o\nNucleus Accumbens\no\nutamen\nP"` | `"...\no"` (one more bullet marker, no real content) | **2** (`...0036...`, `...0063...`) |
| `Globus Pallidus` | `...0036...` | `"utamen\nP\no\nGlobus Pallidus"` | `"o\nutamen\nP\no\nGlobus Pallidus"` | **5** (`...0036...`, `...0039...`, `...0063...`, `...0114...`, `...0141...`) |
| `Putamen` (sibling, not a primary target, for contrast) | `...0036...` | — | — | 2 (`...0036...`, `...0063...`) |

## 8. Enumeration vs. Target-Specific Analysis (Section 11)

`is_enumeration_evidence_insufficient()`/`detect_enumeration_member_shape()` (WP-044 Part A, already-existing production code) return **identically `False` for all three primary targets** — confirmed by direct execution. Not because their evidence is genuinely rich, but because the real enumeration-introduction cue phrase ("מכילים מספר תתי מבנים") sits several sibling-lines *before* any of these three concepts' own lines, outside the bounded backward-walk window `anchor_concept_evidence()` uses (it correctly stops at each intervening sibling concept line). **This existing check has zero discriminating power for these three targets** — it was built for a different real shape (`Corpos Striatum`, WP-043/044) and does not fire here, in either direction.

## 9. Category-Level Evidence Analysis (Section 14, OBSERVED, reusing WP-050's §13 matrix)

The one category-level statement found in the corpus ("additional functions: decision-making, participates in the reward system") is attributed to `גרעיני הבסיס` collectively (chunk `0036`'s closing line), never to any one member by name — confirmed again this WP by re-reading the same source text. This is the same finding WP-050 already established; re-confirmed here as the reason Signal G ("non-category-level statement", §11) below cannot be computed as a simple presence/absence check — the category-level statement mentions no target name at all, so a naive "target name appears near this sentence" check would never even find it as a false positive; the real risk (as WP-050 already showed) is the *opposite* direction — an LLM, not this deterministic layer, wrongly attributing a category-level fact to one member.

## 10. Candidate Sufficiency Signals Evaluated (Section 9/17-18, via `wp051_signal_probe.py`, direct execution)

| Signal | Globus Pallidus | Caudate Nucleus | Nucleus Accumbens | Deterministic? | Evidence-grounded? | Safe? |
|---|---|---|---|---|---|---|
| A — non-enumerative evidence (`not is_enumeration_evidence_insufficient()`) | `True` (trivially — never fires) | `True` (trivially — never fires) | `True` (trivially — never fires) | Yes | Yes | **No discriminating power** — identical for all 3 |
| E — non-empty `factual_focus` (`is_factual_focus_sufficient()`, narrow or broad) | `True` | `True` | `True` | Yes | Yes | **No discriminating power** — identical for all 3; "sufficient" per this check even though narrow focus is pure bullet noise |
| F — relationship `!= UNSPECIFIED` (`extract_relationship()`, narrow or broad `factual_focus`) | `False` (`UNSPECIFIED`) | `False` (`UNSPECIFIED`) | `False` (`UNSPECIFIED`) | Yes | Yes | **No discriminating power** — identical for all 3 |
| B/C — explicit target-property / target-specific relationship, computed from `factual_focus` alone | Same as F — `UNSPECIFIED` | Same as F | Same as F | Yes | Yes | **No discriminating power** — the real Globus Pallidus distinguishing fact (§13, WP-050) is never inside its own `factual_focus`, narrow or broad |
| Full-evidence keyword-proximity (new, this WP: reuses the existing 10-entry `_RELATIONSHIP_KEYWORDS` vocabulary, scanned across *all* retrieved chunk text, not just the target's own anchor) | 5 hits, all `CONTAINS`/`LOCATED_IN`/`DEVELOPS_INTO` from the *shared enumeration passage*, not target-specific | 9 hits, same shared passage | 9 hits, same shared passage | Yes | Yes | **Confounded, not useful** — every hit comes from the enumeration sentence itself ("Striatum contains: caudate, accumbens, putamen..."), which trivially mentions every sibling near the word "contains"; does not surface Globus Pallidus's real distinguishing fact either, since "suppress/inhibit" (Hebrew "מדכא") is not in the existing keyword vocabulary at all |
| D (new) — distinct-chunk mention count (concept's own full name found in how many of the 8 retrieved chunks, substring match, no new retrieval) | **5** | **2** | **2** | Yes (pure counting over already-retrieved chunks) | Yes | **Correctly separates this exact case** (§11) — but see §12/§13: coarse, count-only, content-unverified; a plausible false-positive/false-negative shape exists (§14/§15) |

## 11. Historical-Question Analysis / "Would We Have Skipped It?" (Section 12/20/40, exact real counts)

All 16 real historical `גרעיני הבסיס` rounds across WP-045/046/047/049, split by whether Signal D (distinct-chunk count) with a threshold of "count ≤ 2 → NOT_CONFIRMED sufficient" would have skipped the target *before* generation:

| Target group | Real rounds | Real accepted | Real rejected (exhausted) | Signal-D verdict | Would-skip |
|---|---|---|---|---|---|
| `Globus Pallidus` (count=5) | 4 | **4 (100%)** | 0 | sufficient | No — correctly never skipped |
| `Caudate Nucleus` + `Nucleus Accumbens` (count=2 each) | 11 | **8 (72.7%)** | 3 | NOT_CONFIRMED | Yes, every round, if the rule skipped generation outright |

Exact per-round detail (`Caudate Nucleus`/`Nucleus Accumbens`, all 11 real rounds):

```text
WP-045 r1 Caudate:  ACCEPTED (3 attempts)   WP-045 r2 NAcc: ACCEPTED (1 attempt)
WP-046 r1 Caudate:  ACCEPTED (2 attempts)   WP-046 r2 NAcc: ACCEPTED (1 attempt)
WP-047 r1 Caudate:  ACCEPTED (3 attempts)   WP-047 r2 NAcc: REJECTED (3, exhausted)
WP-047 r3 NAcc:     REJECTED (3, exhausted) WP-047 r4 NAcc: ACCEPTED (2 attempts)
WP-049 r1 Caudate:  REJECTED (3, exhausted) WP-049 r2 Caudate: ACCEPTED (1 attempt)
WP-049 r3 NAcc:     ACCEPTED (1 attempt)
```

## 12. False-Positive Analysis (Section 13/41)

A false positive here means: the signal says `INSUFFICIENT`, but a valid target-specific question was actually possible. **None found for these three targets** — every real `Caudate Nucleus`/`Nucleus Accumbens` accepted question (8/11) used the bare-identity/naming shape (WP-050 §12), never a genuinely target-specific property; this is consistent with, not contradicted by, Signal D's `NOT_CONFIRMED` verdict for these two. The critical counterexample the spec requires (§41 — "the Globus Pallidus example is the most important test") is checked directly: Signal D correctly rates `Globus Pallidus` sufficient (count=5), so it is **not** a false positive for the one case that would be dangerous to get wrong.

## 13. False-Negative Analysis (Section 14/42) — The Decisive Finding

A false negative here means: the signal says `SUFFICIENT`, but the evidence does not safely support a unique question. Not directly observed for these 3 targets (Signal D never says `SUFFICIENT` for `Caudate Nucleus`/`Nucleus Accumbens`). **The actual decisive problem is different and more important**: applying Signal D as a **pre-generation skip** (the architecture WP-051's own section 1 diagram proposes) would have **discarded 8 of the 11 real, legitimately accepted `Caudate Nucleus`/`Nucleus Accumbens` questions** (§11 table) — every one of them succeeded via the bare-identity/naming shape, which requires no target-specific distinguishing property at all, only the target's own name (already always available, by construction, for every named-entity target). Skipping generation entirely for these targets would have traded **9 wasted attempts** (the 3 rejected rounds × 3 attempts each) for the loss of **8 valid, accepted exam questions** — a clearly unfavorable trade for the product. This is the exact trap WP-050's own architecture review (§27) anticipated and WP-051 section 51 explicitly warns against: "the unacceptable result is a heuristic that appears to improve acceptance by silently discarding difficult targets."

## 14. Coverage Impact (Section 15/44)

If Signal D were used as a hard skip for `Caudate Nucleus`/`Nucleus Accumbens`, category coverage would lose these two concepts as eligible targets entirely — for `גרעיני הבסיס` specifically this is a **minor** pool-size impact (2 of ~53 inventory concepts), but as just shown (§13) it is a **severe quality/completeness impact**: real, valid, accepted questions for these exact targets would never be generated again.

## 15. Empty-Eligible-Set Scenario (Section 16/45)

Not triggered for `גרעיני הבסיס` (53-concept inventory, only 2 of which would be excluded by Signal D) — plenty of other eligible targets remain even under a hypothetical skip rule. This scenario would only become material for a category with a much smaller inventory or where coverage has already exhausted most other concepts; documented as a required consideration for any future WP, not resolved here (no rule is being implemented).

## 16. Architecture Insertion Point (Section 17)

Confirmed at §4 above: the same per-concept loop in `_plan_targets_from_concept_inventory()` already contains two structurally identical skip conditions (evidence-sufficiency-of-anchor, enumeration-insufficiency). A third, evidence-*count* condition would fit the same place mechanically — but §13's finding means it must **not** be added as a hard skip given current generation behavior (bare-identity fallback already succeeds without any such check).

## 17. Candidate Architectural Outcomes Considered (Section 18)

- **Outcome A** (safe general sufficiency signal, recommend implementation): rejected — no signal tested proves sufficiency; Signal D only weakly correlates, is count-only/content-unverified, and using it as a skip would regress real accepted output (§13).
- **Outcome B** (conservative partial signal, safely rejects obviously-insufficient targets): the closest fit for Signal D *in isolation*, but §13 shows that "insufficient for a distinguishing property" is not the same as "insufficient to generate at all" in this architecture — the two would need to be different mechanisms, and only the first is even weakly supported.
- **Outcome C** (no safe signal exists; do not implement target filtering): **the correct conclusion for production purposes**, for the reason in §13 — not because no signal was found, but because the one signal found targets the wrong question (property-uniqueness) for what generation actually needs (any valid question, and the bare-identity fallback already reliably provides one).
- **Outcome D** (inconclusive): not applicable — the evidence is decisive (§11/§13), not ambiguous.

## 18. Recommended Architecture (Section 19)

**No change to target selection.** The existing architecture already handles the real underlying situation adequately without a new eligibility layer: generation attempts a property-based question first (per WP-049's own prompt guidance), and the existing 3-attempt budget already allows it to fall back to the bare-identity shape, which reliably succeeds for these targets (8/11 = 72.7% real historical acceptance, with only 9 total wasted attempts across the whole real dataset). A pre-generation skip would remove exactly this working fallback path.

## 19. Whether Implementation Is Justified (Section 20)

**No.** Per section 51's own explicit warning, implementing a target-skip mechanism here would be exactly "a heuristic that appears to improve [attempt efficiency] by silently discarding difficult targets" — and it would do so while destroying real product value (8 real accepted questions in the historical record alone).

## 20. Prototype Results (Section 21)

Two prototype-only, read-only scripts (never imported by `src/`, zero LLM calls, zero new production logic): `implementation/wp050_architecture_probe.py` (reused from WP-050) and `implementation/wp051_signal_probe.py` (new, committed alongside this report) — together produced every table in this report via direct execution against real retrieved evidence and real pilot data.

## 21. Regression (Section 22/48)

**NOT APPLICABLE.** No production code was changed. `git status --porcelain src/ tests/` confirms no modifications to either directory.

## 22. Unresolved Issues (Section 23)

- Signal D (distinct-chunk mention count) is a real, interesting, deterministic correlate of "has a target-specific distinguishing property" in this one category — but was validated against only 3 primary targets (plus one contrast sibling, `Putamen`) in one category. It has not been tested at scale and a plausible false-positive shape exists (a concept repeated verbatim across multiple independently-authored student summaries, inflating its count without adding real distinguishing content) that this investigation's data cannot rule out. Worth recording as a research finding, not worth acting on.
- The deeper, still-open question this WP surfaces: generation's own choice between attempting a "property" question versus a "bare-identity" question is entirely implicit (an LLM judgment call, not a deterministic strategy) — WP-049's prompt guidance nudges toward "specific property," which is precisely what fails for `Caudate Nucleus`/`Nucleus Accumbens` before the bare-identity fallback eventually succeeds. Whether generation could be told, deterministically and safely, "no distinguishing property is known to exist for this target, so do not spend attempts trying to invent one, go straight to identity" is a materially different, narrower, and more promising question than either WP-050's uniqueness study or this WP's skip-the-target question — flagged for a future WP, not investigated here (would touch the generation prompt, explicitly out of this WP's own scope, §29).
- `Basillar artery`'s own separate WP-048 thread remains untouched, per this WP's explicit scope exclusion (§4).

## 23. Recommendation for WP-052 (Section 24)

**Do not implement target-selection filtering for evidence sufficiency** — this thread is closed for production purposes (Outcome C). If a future WP wants to act on the one real finding here, the promising, narrower direction is: **can generation be told, deterministically, when a target is known (from the same evidence used here) to lack a distinguishing property, so it skips straight to a bare-identity question shape instead of spending 1-2 attempts on a doomed property-based one?** This would need its own investigation (does this save attempts without regressing acceptance, does it risk generation always defaulting to the "easy" identity shape even when a real property exists, is it even representable without a new prompt mechanism) before any implementation — explicitly not authorized by this report, only suggested as a research direction.

## 24. Required Architectural Decision (Section 53)

```text
C — No safe deterministic sufficiency signal exists; do not implement target filtering.
```

One real, deterministic, evidence-grounded signal (distinct-chunk mention count) was found and correctly separates the three primary targets exactly as WP-050's hand-built ground truth does — but it answers a narrower question (does a distinguishing *property* likely exist) than the one target-selection actually needs answered (is *any* valid question likely, including the bare-identity fallback this architecture already relies on and which already succeeds 72.7% of the time for these exact targets). Implementing it as a skip mechanism would regress real, measured product output. No implementation is recommended.

---

## Required Terminal Summary

```text
WP-051 complete.

Objective:
Determine whether the existing authoritative evidence can tell us, before
generation, whether a selected target has enough target-specific
information to make attempting generation worthwhile, for Globus Pallidus
/ Caudate Nucleus / Nucleus Accumbens.

Primary targets:
Globus Pallidus
Caudate Nucleus
Nucleus Accumbens

Current target-selection flow:
Concept inventory -> coverage exclusion -> per-concept loop (existing
evidence-sufficiency and enumeration-insufficiency skip checks) ->
QuestionTarget -> generation. A sufficiency signal would fit the same
loop mechanically, alongside the two checks already there.

Current evidence flow:
Full retrieved source_evidence (8 chunks) is already in scope at target-
selection time; only one canonical chunk id and a fixed-window snippet
are currently retained per concept - no per-concept multi-chunk count is
currently computed or retained anywhere.

Definition of evidence sufficiency:
Enough source information to justify attempting generation - explicitly
distinct from generation success (LLM actually producing a valid,
accepted question). Kept separate throughout this investigation.

Target evidence:
Caudate Nucleus and Nucleus Accumbens: mentioned in only 2 of 8 retrieved
chunks each (the shared enumeration passage plus one repeat). Globus
Pallidus: mentioned in 5 of 8 chunks, including the ones that actually
carry its real, unique distinguishing fact (WP-050).

Candidate sufficiency signals:
6 of 7 signals from the WP-051 spec (non-enumerative evidence, explicit
target property, target-specific relationship, non-empty factual_focus,
relationship != UNSPECIFIED, plus a new full-evidence keyword-proximity
scan) have ZERO discriminating power - identical result for all 3 targets
when computed with existing primitives. One new signal (distinct-chunk
mention count) correctly separates Globus Pallidus (5) from Caudate
Nucleus/Nucleus Accumbens (2 each).

Signal matrix:
See report section 10 - full table, 7 signals x 3 targets, safety notes.

Historical comparison:
Globus Pallidus: 4/4 real rounds accepted (100%). Caudate Nucleus +
Nucleus Accumbens: 8/11 real rounds accepted (72.7%), all 8 via the
bare-identity question shape, never a distinguishing property.

False positives:
None found - the one signal with discriminating power (chunk count)
correctly rates Globus Pallidus sufficient, the critical test case.

False negatives:
Not in the signal itself, but in its INTENDED USE: a pre-generation skip
based on this signal would have discarded 8 of 11 real, legitimately
accepted Caudate Nucleus/Nucleus Accumbens questions, to save only 9
wasted attempts across 3 rejected rounds - a clearly unfavorable trade.

Coverage impact:
Minor pool-size impact (2 of ~53 inventory concepts) but severe quality
impact if implemented - 8 real accepted questions would be lost.

Empty eligible set:
Not triggered for גרעיני הבסיס (53-concept inventory); would need separate
analysis for a smaller category, not resolved here since no rule is
being implemented.

Safe deterministic signal:
PARTIAL

Recommended architecture:
No change to target selection. The existing 3-attempt retry budget
already lets generation fall back to the bare-identity question shape,
which already reliably succeeds for these targets without any new
eligibility layer.

Production implementation:
NONE

Regression:
NOT APPLICABLE - no production code changed.

Unresolved issues:
Distinct-chunk mention count is a real but unvalidated-at-scale research
finding. Whether generation could be told, deterministically, to skip
straight to a bare-identity question for targets known to lack a
distinguishing property (rather than skip the target entirely) is a
narrower, more promising, unexplored direction - explicitly out of this
WP's scope (would touch the generation prompt). Basillar artery thread
(WP-048) remains untouched.

Recommended WP-052:
None for target-selection filtering - closed for production purposes.
Optional future research direction only: investigate whether generation
itself can be told, deterministically and safely, when to skip straight
to a bare-identity question shape rather than attempt a property-based
one first, for targets with no known distinguishing property.

Completion report:
implementation/WP-051_COMPLETION_REPORT.md

Waiting for architect review.
```
