"""WP-050 prototype-only architecture probe.

NOT production code. Runs the REAL, existing deterministic pipeline
(retrieval -> refine_concept_inventory -> anchor_concept_evidence ->
extract_relationship -> discover_competitors -> GenerationPromptContext)
against the real category evidence for גרעיני הבסיס, and prints exactly
what the current architecture computes and would render into the
generation prompt for the three primary WP-050 targets. Zero LLM calls,
zero new production logic - pure inspection of existing code.
"""

from exam_generator.generation.competitors import discover_competitors
from exam_generator.generation.relationship import extract_relationship
from exam_generator.models import GenerationMode
from exam_generator.planning.concept_anchor import anchor_concept_evidence, refine_concept_inventory
from exam_generator.prompts.context import GenerationPromptContext
from exam_generator.prompts.formatting import format_competitors, format_question_target
from exam_generator.retrieval import build_category_resolver, build_student_summary_retrieval_index, retrieve_for_category

CATEGORY = "גרעיני הבסיס"
PRIMARY_TARGETS = {"Caudate Nucleus", "Nucleus Accumbens", "Globus Pallidus"}

resolver = build_category_resolver()
index = build_student_summary_retrieval_index()
canonical = resolver.resolve(CATEGORY)
print(f"canonical category: {canonical!r}")

results = retrieve_for_category(canonical, resolver, index)
source_evidence = tuple(r.chunk for r in results)
print(f"retrieved {len(source_evidence)} chunk(s)")
for chunk in source_evidence:
    print(f"  chunk_id={chunk.chunk_id} source_file={chunk.source_file} page={chunk.page} len={len(chunk.text)}")

print("\n=== FULL RAW CHUNK TEXT (every retrieved chunk) ===")
for chunk in source_evidence:
    print(f"\n--- chunk {chunk.chunk_id} ---")
    print(chunk.text)

inventory = refine_concept_inventory(source_evidence)
print(f"\n=== refined concept inventory: {len(inventory)} concept(s) ===")
for c in inventory:
    print(f"  concept={c.concept!r} chunk={c.evidence_chunk_id} lines={c.source_line_indices}")

chunk_text_by_id = {c.chunk_id: c.text for c in source_evidence}

for concept_item in inventory:
    if concept_item.concept not in PRIMARY_TARGETS:
        continue
    print(f"\n\n########## TARGET: {concept_item.concept} ##########")
    chunk_text = chunk_text_by_id[concept_item.evidence_chunk_id]
    factual_focus = anchor_concept_evidence(
        chunk_text=chunk_text,
        concept=concept_item.concept,
        source_line_indices=concept_item.source_line_indices,
    )
    print(f"--- narrow factual_focus ---\n{factual_focus}")

    broad_focus = anchor_concept_evidence(
        chunk_text=chunk_text,
        concept=concept_item.concept,
        source_line_indices=concept_item.source_line_indices,
        broad=True,
    )
    print(f"\n--- broad factual_focus ---\n{broad_focus}")

    from exam_generator.models import QuestionTarget

    target = QuestionTarget(
        target_id=1,
        category=canonical,
        topic=concept_item.concept,
        factual_focus=factual_focus,
        supporting_evidence_chunk_ids=(concept_item.evidence_chunk_id,),
        named_entity_target=True,
    )
    relationship = extract_relationship(target)
    print(f"\n--- extract_relationship ---\nrelationship_type={relationship.relationship_type!r}")

    competitors = discover_competitors(target=target, relationship=relationship, source_evidence=source_evidence)
    print(f"\n--- discover_competitors: {len(competitors)} found ---")
    for comp in competitors:
        print(f"  concept={comp.concept!r}")
        print(f"    reason={comp.similarity_reason}")

    print(f"\n--- format_question_target (actual prompt text) ---\n{format_question_target(target)}")
    print(f"\n--- format_competitors (actual prompt text) ---\n{format_competitors(competitors)}")
