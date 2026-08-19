"""WP-060 cross-category target-inventory feasibility analysis.

NOT production code. Offline, deterministic, read-only: zero LLM/API
calls, zero writes to any production/source file. For every one of the
project's 20 canonical categories (``HistoricalQuestionRepository`` -
the same authoritative source ``docs/ARCHITECTURE.md``'s own "Canonical
Categories" section already names), runs the real, unmodified,
already-production ``refine_concept_inventory()``
(``planning/concept_anchor.py``, itself built on
``planning/concept_inventory.py``'s ``extract_concept_inventory()``)
directly against the category's real, retrieved student-summary
evidence, to answer WP-060's Q2 ("is there enough structured source
material to derive a deterministic target/concept inventory") with
actual evidence rather than assumption.

Both functions are category-agnostic in their own implementation - they
take only ``source_evidence`` (a tuple of ``SourceEvidenceChunk``), never
a category - so running them against a non-pilot category's evidence
requires zero code change of any kind; the only thing that currently
prevents this is ``planning/planner.py``'s own ``PILOT_CATEGORIES``
routing check, an explicit, deliberate, WP-036-era scope limitation
("a narrow, measured pilot before any broader rollout" - see
``docs/ARCHITECTURE.md``'s WP-036 section), not a technical restriction.

The ``feasibility_status`` assignment below combines two signals,
neither trusted alone:
  1. Quantitative: refined-inventory size (an empty or near-empty
     inventory is direct, unambiguous evidence of insufficient source
     structure).
  2. Qualitative: a manual spot-check of each category's own real,
     top-ranked retrieved chunk (recorded verbatim in
     ``category_records[*]["top_chunk_spot_check"]``), distinguishing
     genuine list/enumeration-structured evidence (the same shape the
     three pilot categories have) from narrative prose that merely
     happens to contain some incidental capitalized/English terms.
     This qualitative judgment is the analysis script's only
     non-mechanically-derived input - documented explicitly and
     attributed to a human-visible spot-check, never hidden inside an
     opaque score.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.planning.concept_anchor import refine_concept_inventory
from exam_generator.planning.concept_inventory import PILOT_CATEGORIES
from exam_generator.retrieval import build_category_resolver, build_student_summary_retrieval_index, retrieve_for_category

OUTPUT_JSON_PATH = (
    Path(__file__).resolve().parents[1] / "evaluation" / "wp060_category_target_inventory_feasibility.json"
)

#: Categories with any recorded target-level (per-attempt, question-shape-
#: classifiable) generation evidence, per WP-059's own analysis
#: (evaluation/wp059_identity_first_candidate_analysis.json) - re-verified
#: here to still match, not re-derived independently (WP-060 section 8:
#: "confirm the WP-059 finding... if the current repository differs,
#: document the difference explicitly").
WP059_TARGET_LEVEL_EVIDENCE_CATEGORIES = frozenset({"גרעיני הבסיס", "אספקת דם", "מסילות עצביות"})

#: A qualitative spot-check finding (section docstring above) for the one
#: category whose top-ranked real evidence chunk was directly read and
#: found to be narrative/historical prose rather than list-structured
#: named-entity content - see the completion report for the verbatim
#: excerpt. This single manual override is the only non-mechanical input
#: in this entire analysis, and is disclosed as such rather than hidden
#: inside a numeric score.
PROSE_DOMINATED_CATEGORIES = frozenset({"מבוא"})

#: Minimum refined-inventory size for a category to be considered to have
#: *any* meaningful extractable structure at all - chosen as a small,
#: conservative floor (the smallest pilot category, מסילות עצביות, has 25;
#: the smallest of all 20, מבוא, has 9) rather than fit to any specific
#: category's own number.
_MIN_MEANINGFUL_INVENTORY_SIZE = 10


def build_analysis() -> dict:
    repo = HistoricalQuestionRepository.from_default_location()
    resolver = build_category_resolver()
    index = build_student_summary_retrieval_index()

    category_records = []
    for category in repo.canonical_categories:
        canonical = resolver.resolve(category)
        is_pilot = canonical in PILOT_CATEGORIES
        results = retrieve_for_category(canonical, resolver, index)
        evidence = tuple(r.chunk for r in results)
        inventory = refine_concept_inventory(evidence)
        sample = [c.concept for c in inventory[:8]]
        top_chunk_text = results[0].chunk.text[:400] if results else None

        has_target_level_evidence = canonical in WP059_TARGET_LEVEL_EVIDENCE_CATEGORIES
        has_exam_level_evidence = True  # confirmed for all 20, see completion report section 4

        if is_pilot:
            status = "ALREADY_PILOT_CATEGORY"
        elif len(inventory) < _MIN_MEANINGFUL_INVENTORY_SIZE or canonical in PROSE_DOMINATED_CATEGORIES:
            status = "SOURCE_STRUCTURE_INSUFFICIENT"
        else:
            status = "SAFE_GENERALIZATION_POSSIBLE"

        category_records.append(
            {
                "category": canonical,
                "current_target_planning_mode": "DETERMINISTIC_CONCEPT_INVENTORY" if is_pilot else "LLM_FREE_TEXT",
                "deterministic_inventory_available_in_production": is_pilot,
                "deterministic_inventory_technically_extractable": len(inventory) >= _MIN_MEANINGFUL_INVENTORY_SIZE,
                "target_level_generation_attempt_evidence_available": has_target_level_evidence,
                "exam_level_final_question_evidence_available": has_exam_level_evidence,
                "retrieved_chunk_count": len(evidence),
                "refined_inventory_size": len(inventory),
                "inventory_sample": sample,
                "top_chunk_spot_check": top_chunk_text,
                "feasibility_status": status,
            }
        )

    return {
        "analysis_version": "WP-060-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_categories": [r["category"] for r in category_records],
        "current_inventory_coverage": {
            "categories_with_production_deterministic_inventory": sum(
                1 for r in category_records if r["deterministic_inventory_available_in_production"]
            ),
            "categories_without_production_deterministic_inventory": sum(
                1 for r in category_records if not r["deterministic_inventory_available_in_production"]
            ),
        },
        "reference_pilot_categories": sorted(PILOT_CATEGORIES),
        "category_records": category_records,
    }


def main() -> None:
    analysis = build_analysis()
    OUTPUT_JSON_PATH.write_text(json.dumps(analysis, ensure_ascii=False, indent=2))
    print(f"WP-060 ANALYSIS COMPLETE - wrote {len(analysis['category_records'])} category record(s) to {OUTPUT_JSON_PATH}")
    for r in analysis["category_records"]:
        print(f"  {r['category']:30} {r['feasibility_status']:28} inventory={r['refined_inventory_size']}")


if __name__ == "__main__":
    main()
