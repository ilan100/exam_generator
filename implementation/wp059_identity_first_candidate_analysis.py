"""WP-059 identity-first candidate discovery analysis.

NOT production code. Offline, deterministic, read-only analysis of
already-recorded historical generation-attempt evidence
(``evaluation/live_outputs/wp0{36,37,38,39,40,41,43,44,45,46,47,49}_pilot_records.json``)
across every pilot-category round captured by prior WPs, to rank the
remaining currently-``DEFAULT`` target/category pairs by evidence for a
future controlled identity-first experiment (candidate discovery only -
implements nothing, makes zero LLM/API calls).

Question-shape classification reuses ``wp056_experiment.py``'s own
generalized, already-self-validated ``classify_question_shape()`` -
never a second, incompatible taxonomy (WP-059 section 10/30's explicit
instruction) - imported directly (both files live in ``implementation/``,
neither is part of ``src/``), with its four categories relabeled to
WP-059's own requested vocabulary (``VALID_IDENTITY_SHAPE`` ->
``IDENTITY``, ``MEMBERSHIP_CLASSIFICATION`` -> ``CLASSIFICATION_MEMBERSHIP``,
``PROPERTY`` -> ``PROPERTY``, ``OTHER`` -> ``OTHER_UNKNOWN``).

Data-source schema evolved across WPs (confirmed by direct inspection,
not assumed):
  - WP-036/037/038/040/041/043: round-level only - ``attempts`` is a bare
    integer count, not a per-attempt list. Only the round's own final
    ``question``/``correct_answer_text`` (if accepted) or
    ``failure_type``/``failure_message`` (if exhausted) is available -
    per-attempt shape/validator detail is UNKNOWN for these WPs.
  - WP-039: an extra wrapping dict per category with a ``rounds`` key.
  - WP-044 onward: ``attempts`` is a full per-attempt list (question,
    answers, correct_answer_text, validations, sometimes
    rejection_reasons) - the rich source this analysis relies on most.
  - The round-level target field is named ``selected_concept`` through
    WP-043, ``target`` from WP-044 onward (confirmed by direct
    inspection) - both are read as the same logical field.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp056_experiment import classify_question_shape  # noqa: E402  (reused, not duplicated - see module docstring)

LIVE_OUTPUTS_DIR = Path(__file__).resolve().parents[1] / "evaluation" / "live_outputs"
OUTPUT_JSON_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "wp059_identity_first_candidate_analysis.json"

PILOT_FILES = [
    "wp036_pilot_records.json",
    "wp037_pilot_records.json",
    "wp038_pilot_records.json",
    "wp039_pilot_records.json",
    "wp040_pilot_records.json",
    "wp041_pilot_records.json",
    "wp043_pilot_records.json",
    "wp044_pilot_records.json",
    "wp045_pilot_records.json",
    "wp046_pilot_records.json",
    "wp047_pilot_records.json",
    "wp049_pilot_records.json",
]

PILOT_CATEGORIES = ("גרעיני הבסיס", "אספקת דם", "מסילות עצביות")

ALREADY_IDENTITY_FIRST = {
    ("גרעיני הבסיס", "Caudate Nucleus"),
    ("גרעיני הבסיס", "Nucleus Accumbens"),
    ("גרעיני הבסיס", "Globus Pallidus"),
}

_SHAPE_RELABEL = {
    "VALID_IDENTITY_SHAPE": "IDENTITY",
    "MEMBERSHIP_CLASSIFICATION": "CLASSIFICATION_MEMBERSHIP",
    "PROPERTY": "PROPERTY",
    "OTHER": "OTHER_UNKNOWN",
}


def _relabel(shape: str) -> str:
    return _SHAPE_RELABEL.get(shape, "OTHER_UNKNOWN")


def _rounds_for_category(raw) -> list:
    """Normalize the WP-039 extra-wrapping-dict shape to a plain round list."""
    if isinstance(raw, dict) and "rounds" in raw:
        return raw["rounds"]
    if isinstance(raw, list):
        return raw
    return []


def _round_target(round_record: dict) -> str | None:
    return round_record.get("target") or round_record.get("selected_concept")


def _extract_attempts(source_wp: str, category: str, round_record: dict) -> list[dict]:
    """Return a normalized list of attempt records for one round, each with
    keys: attempt_number, accepted, question, correct_answer_text,
    grounding_passed (bool|None), order (int|None - 1-based position within
    the round, used for retrospective-bias tagging), has_detail (bool).
    """
    target = _round_target(round_record)
    if target is None:
        return []

    raw_attempts = round_record.get("attempts")
    if isinstance(raw_attempts, list) and raw_attempts:
        out = []
        for a in raw_attempts:
            validations = a.get("validations") or {}
            grounding = validations.get("grounding") or {}
            out.append(
                {
                    "source_wp": source_wp,
                    "category": category,
                    "target": target,
                    "attempt_number": a.get("attempt_number"),
                    "accepted": bool(a.get("accepted")),
                    "question": a.get("question"),
                    "correct_answer_text": a.get("correct_answer_text"),
                    "grounding_passed": grounding.get("passed"),
                    "has_detail": True,
                }
            )
        return out

    # Round-level-only schema (WP-036/037/038/040/041/043): at most one
    # usable record per round - the final question if accepted, otherwise
    # nothing usable (a failure_type/failure_message with no question text
    # to classify a shape from). Attempt count itself (an int) is recorded
    # as informational context only, never fabricated into fake per-attempt
    # records.
    if round_record.get("accepted") and round_record.get("question"):
        return [
            {
                "source_wp": source_wp,
                "category": category,
                "target": target,
                "attempt_number": None,
                "accepted": True,
                "question": round_record.get("question"),
                "correct_answer_text": round_record.get("correct_answer_text"),
                "grounding_passed": None,
                "has_detail": False,
            }
        ]
    return []


def load_all_attempts() -> list[dict]:
    attempts: list[dict] = []
    for fname in PILOT_FILES:
        path = LIVE_OUTPUTS_DIR / fname
        if not path.exists():
            continue
        source_wp = fname.split("_")[0].upper()
        data = json.loads(path.read_text())
        for category in PILOT_CATEGORIES:
            raw = data.get(category)
            if raw is None:
                continue
            for round_record in _rounds_for_category(raw):
                if not isinstance(round_record, dict):
                    continue
                attempts.extend(_extract_attempts(source_wp, category, round_record))
    return attempts


def classify_attempts(attempts: list[dict]) -> None:
    """Mutates each attempt dict in place, adding 'shape' (or None if no
    question text is available to classify)."""
    for a in attempts:
        if a["question"]:
            a["shape"] = _relabel(classify_question_shape(a["question"], a["target"]))
        else:
            a["shape"] = None


def tag_retrospective_order(attempts: list[dict]) -> None:
    """For attempts with real attempt_number detail, tag each IDENTITY-
    shaped accepted attempt as FIRST_ATTEMPT (attempt_number == 1) or
    AFTER_PRIOR_FAILURE (attempt_number > 1); round-level-only attempts
    (no attempt_number) are tagged UNKNOWN - never guessed."""
    for a in attempts:
        if a["shape"] != "IDENTITY" or not a["accepted"]:
            a["retrospective_order"] = None
            continue
        if a["attempt_number"] is None:
            a["retrospective_order"] = "UNKNOWN"
        elif a["attempt_number"] == 1:
            a["retrospective_order"] = "FIRST_ATTEMPT"
        else:
            a["retrospective_order"] = "AFTER_PRIOR_FAILURE"


def aggregate_by_target(attempts: list[dict]) -> dict[tuple[str, str], dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for a in attempts:
        grouped[(a["category"], a["target"])].append(a)

    result: dict[tuple[str, str], dict] = {}
    for key, group in grouped.items():
        counts = {"IDENTITY": [0, 0], "PROPERTY": [0, 0], "CLASSIFICATION_MEMBERSHIP": [0, 0], "OTHER_UNKNOWN": [0, 0]}
        first_attempt_identity = 0
        post_failure_identity = 0
        unknown_order_identity = 0
        detailed_count = 0
        for a in group:
            shape = a["shape"] or "OTHER_UNKNOWN"
            counts[shape][0] += 1
            if a["accepted"]:
                counts[shape][1] += 1
            if a["has_detail"]:
                detailed_count += 1
            if a["shape"] == "IDENTITY" and a["accepted"]:
                if a["retrospective_order"] == "FIRST_ATTEMPT":
                    first_attempt_identity += 1
                elif a["retrospective_order"] == "AFTER_PRIOR_FAILURE":
                    post_failure_identity += 1
                else:
                    unknown_order_identity += 1

        total_attempts = len(group)
        total_accepted = sum(1 for a in group if a["accepted"])

        def rate(n, d):
            return round(n / d, 3) if d > 0 else None

        result[key] = {
            "category": key[0],
            "target": key[1],
            "total_attempts": total_attempts,
            "total_accepted": total_accepted,
            "detailed_attempt_count": detailed_count,
            "round_level_only_count": total_attempts - detailed_count,
            "property_attempts": counts["PROPERTY"][0],
            "property_accepted": counts["PROPERTY"][1],
            "identity_attempts": counts["IDENTITY"][0],
            "identity_accepted": counts["IDENTITY"][1],
            "classification_membership_attempts": counts["CLASSIFICATION_MEMBERSHIP"][0],
            "classification_membership_accepted": counts["CLASSIFICATION_MEMBERSHIP"][1],
            "other_unknown_attempts": counts["OTHER_UNKNOWN"][0],
            "other_unknown_accepted": counts["OTHER_UNKNOWN"][1],
            "overall_acceptance_rate": rate(total_accepted, total_attempts),
            "property_acceptance_rate": rate(counts["PROPERTY"][1], counts["PROPERTY"][0]),
            "identity_acceptance_rate": rate(counts["IDENTITY"][1], counts["IDENTITY"][0]),
            "first_attempt_identity_count": first_attempt_identity,
            "post_failure_identity_count": post_failure_identity,
            "unknown_order_identity_count": unknown_order_identity,
            "source_wps": sorted({a["source_wp"] for a in group}),
        }
    return result


# ---------------------------------------------------------------------------
# Deterministic scoring (WP-059 section 17/18: a prioritization heuristic,
# never a probability/statistical-significance claim). Fixed BEFORE
# inspecting real results, applied uniformly, never tuned per-candidate.
# ---------------------------------------------------------------------------


def score_candidate(m: dict) -> tuple[int, str]:
    """Returns (score, rationale). All thresholds are small integers chosen
    for interpretability, not fit to any particular candidate's numbers."""
    score = 0
    reasons = []

    identity_accepted_capped = min(m["identity_accepted"], 3)
    if identity_accepted_capped:
        score += 2 * identity_accepted_capped
        reasons.append(f"+{2 * identity_accepted_capped} for {identity_accepted_capped} (capped) accepted identity attempt(s)")

    property_rejected = m["property_attempts"] - m["property_accepted"]
    property_rejected_capped = min(property_rejected, 4)
    if property_rejected_capped:
        score += property_rejected_capped
        reasons.append(f"+{property_rejected_capped} for {property_rejected_capped} (capped) rejected property attempt(s)")

    ir, pr = m["identity_acceptance_rate"], m["property_acceptance_rate"]
    if ir is not None and pr is not None and (ir - pr) >= 0.4:
        score += 2
        reasons.append(f"+2 strategy contrast (identity rate {ir} - property rate {pr} >= 0.4)")

    if m["total_attempts"] >= 4:
        score += 1
        reasons.append("+1 sample-size support (total_attempts >= 4)")

    if m["first_attempt_identity_count"] >= 1:
        score += 1
        reasons.append("+1 at least one first-attempt (not retrospectively biased) identity success")

    if m["identity_accepted"] == 0:
        score -= 2
        reasons.append("-2 no accepted identity attempt at all (insufficient positive signal)")

    return score, "; ".join(reasons)


def tier_for(m: dict, score: int) -> str:
    if m["total_attempts"] == 0:
        return "INSUFFICIENT_DATA"
    if score >= 6 and m["identity_accepted"] >= 2 and m["total_attempts"] >= 4:
        return "TIER_A_EXPERIMENT_CANDIDATE"
    if score >= 3:
        return "TIER_B_MONITOR"
    return "TIER_C_NOT_SUPPORTED"


def build_analysis() -> dict:
    attempts = load_all_attempts()
    classify_attempts(attempts)
    tag_retrospective_order(attempts)
    aggregated = aggregate_by_target(attempts)

    candidates = []
    for key, m in aggregated.items():
        if key in ALREADY_IDENTITY_FIRST:
            continue
        score, rationale = score_candidate(m)
        tier = tier_for(m, score)
        record = dict(m)
        record["candidate_score"] = score
        record["rationale"] = rationale
        record["status"] = tier
        candidates.append(record)

    candidates.sort(key=lambda r: (-r["candidate_score"], -r["identity_accepted"], r["category"], r["target"]))

    return {
        "analysis_version": "WP-059-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "population_definition": (
            "Every (category, target) pair with at least one recorded generation "
            "attempt across evaluation/live_outputs/wp0{36,37,38,39,40,41,43,44,45,46,47,49}"
            "_pilot_records.json, restricted to the three pilot categories that have "
            "ever used deterministic concept-inventory-based target planning "
            "(גרעיני הבסיס, אספקת דם, מסילות עצביות); no other project category has "
            "any recorded generation-attempt evidence (see the completion report's "
            "category-coverage table)."
        ),
        "excluded_permanent_identity_first_targets": sorted(
            f"{cat} + {target}" for cat, target in ALREADY_IDENTITY_FIRST
        ),
        "ranking_method": (
            "candidate_score = 2*min(identity_accepted,3) + min(property_rejected,4) "
            "+ (2 if identity_rate-property_rate>=0.4 else 0) + (1 if total_attempts>=4 else 0) "
            "+ (1 if first_attempt_identity_count>=1 else 0) - (2 if identity_accepted==0 else 0). "
            "A prioritization heuristic only - never a probability or statistical-significance claim."
        ),
        "tier_definitions": {
            "TIER_A_EXPERIMENT_CANDIDATE": "score>=6 AND identity_accepted>=2 AND total_attempts>=4",
            "TIER_B_MONITOR": "score>=3 (but does not meet Tier A)",
            "TIER_C_NOT_SUPPORTED": "score<3, but at least one recorded attempt exists",
            "INSUFFICIENT_DATA": "zero recorded generation attempts found",
        },
        "candidate_records": candidates,
    }


def main() -> None:
    analysis = build_analysis()
    OUTPUT_JSON_PATH.write_text(json.dumps(analysis, ensure_ascii=False, indent=2))
    print(f"WP-059 ANALYSIS COMPLETE - wrote {len(analysis['candidate_records'])} candidate record(s) to {OUTPUT_JSON_PATH}")
    tier_a = [c for c in analysis["candidate_records"] if c["status"] == "TIER_A_EXPERIMENT_CANDIDATE"]
    print(f"TIER_A candidates: {len(tier_a)}")
    for c in tier_a:
        print(f"  {c['category']} + {c['target']}  score={c['candidate_score']}  {c['rationale']}")


if __name__ == "__main__":
    main()
