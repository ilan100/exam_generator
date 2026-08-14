"""WP-052 prototype-only strategy-classification probe.

NOT production code. Reads real, already-captured pilot records
(evaluation/live_outputs/wp045_pilot_records.json through
wp049_pilot_records.json) and classifies every real generation attempt
for the three primary גרעיני הבסיס targets (Globus Pallidus, Caudate
Nucleus, Nucleus Accumbens) as PROPERTY or IDENTITY, using a small,
deterministic, keyword-based rule over the real generated question text
- never an LLM judgment, never new production logic, never imported by
src/. Produces the baseline/strategy/counterfactual numbers used in
implementation/WP-052_COMPLETION_REPORT.md.

Classification rule (deterministic, explicit, reused nowhere else):
IDENTITY if the question contains a naming-cue phrase ("also known as" /
"called") or a copula ("is/are") immediately followed by (a recognizable
word of) the target's own name, AND does not also contain an explicit
property-predicate marker (function/source/influence/location/
association/enablement/membership) - PROPERTY if such a marker is
present - OTHER/UNCLEAR otherwise (none occurred in the real data).
"""

import json
import re
from pathlib import Path

PILOT_FILES = [
    "wp045_pilot_records.json",
    "wp046_pilot_records.json",
    "wp047_pilot_records.json",
    "wp049_pilot_records.json",
]
CATEGORY = "גרעיני הבסיס"
PRIMARY_TARGETS = {"Caudate Nucleus", "Nucleus Accumbens", "Globus Pallidus"}
LIVE_OUTPUTS_DIR = Path(__file__).resolve().parents[1] / "evaluation" / "live_outputs"

PROPERTY_MARKERS = ["תפקיד", "מקור", "משפיע", "ממוקם", "משויך", "מאפשר", "חלק מ", "המכיל", "נחשב ל"]
NAMING_CUE = ["הנקרא", "הנקראת", "מוכר גם כ", "ידוע גם כ"]


def classify(question: str, target: str) -> str:
    words = [w for w in target.split() if len(w) >= 4]
    for cue in NAMING_CUE:
        idx = question.find(cue)
        if idx != -1:
            window = question[idx : idx + 40]
            if any(w.lower() in window.lower() for w in words):
                return "IDENTITY"
    for copula in ["הוא ", "היא "]:
        for m in re.finditer(re.escape(copula), question):
            window = question[m.end() : m.end() + 30]
            if any(w.lower() in window.lower() for w in words):
                if not any(pm in question for pm in PROPERTY_MARKERS):
                    return "IDENTITY"
    if any(pm in question for pm in PROPERTY_MARKERS):
        return "PROPERTY"
    return "OTHER/UNCLEAR"


def main() -> None:
    rows = []
    for fname in PILOT_FILES:
        wp = fname.split("_")[0]
        data = json.loads((LIVE_OUTPUTS_DIR / fname).read_text())
        for r in data.get(CATEGORY, []):
            if r["target"] not in PRIMARY_TARGETS:
                continue
            for a in r["attempts"]:
                q = a.get("question", "")
                cls = classify(q, r["target"])
                rows.append(
                    {
                        "wp": wp, "round": r["round"], "attempt": a["attempt_number"],
                        "target": r["target"], "accepted": a["accepted"], "strategy": cls,
                        "question": q,
                    }
                )

    for row in rows:
        print(
            f"{row['wp']:>6} r{row['round']} a{row['attempt']} {row['target']:<18} "
            f"accepted={str(row['accepted']):<5} {row['strategy']:<13} | {row['question']}"
        )

    from collections import Counter

    counts = Counter()
    for row in rows:
        group = "GPallidus" if row["target"] == "Globus Pallidus" else "Caudate+NAcc"
        counts[(group, row["strategy"], row["accepted"])] += 1

    print()
    for key in sorted(counts):
        print(key, counts[key])
    print()
    print("total attempts:", len(rows))

    # Within-round "attempts saved if identity had been tried first" -
    # counted only for rounds that actually reached an identity attempt
    # (never a hypothesis about rounds that never tried it).
    rounds: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        rounds.setdefault((row["wp"], row["round"]), []).append(row)

    saved = 0
    for key, attempts in rounds.items():
        attempts_sorted = sorted(attempts, key=lambda a: a["attempt"])
        strategies = [a["strategy"] for a in attempts_sorted]
        if "IDENTITY" in strategies:
            identity_index = strategies.index("IDENTITY")
            saved += identity_index  # number of PROPERTY attempts preceding the first IDENTITY attempt
    print("Directly observed within-round attempts saved (property attempts preceding a successful identity attempt):", saved)


if __name__ == "__main__":
    main()
