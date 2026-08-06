Perform a read-only architecture/contract diagnostic of the current evidence-provenance mechanism.

This is NOT an implementation WP.

Do not modify:
- source code;
- prompts;
- schemas;
- configuration;
- tests;
- retrieval;
- validators;
- audit/output models.

Do not make any OpenAI/LLM/API calls.
Do not commit anything.

The purpose is to answer one architectural question:

Can we replace LLM-facing full canonical chunk IDs with short, call-local
evidence references such as E1, E2, E3 while preserving the existing canonical
SourceEvidenceChunk.chunk_id internally and in audit/output, without broad
architectural changes or weakening strict provenance?

Context:

The current grounding validator asks the LLM to return identifiers such as:

    STUDENT_SUMMARY:student_summary_2.pdf:0071:0001

WP-021 added one bounded retry when the LLM returns an invented evidence ID.

In the latest 40-question acceptance run, the exam reached question 27/40 and
then failed because both grounding-validation calls returned invented evidence
IDs.

We do NOT want to solve this by adding more retries unless necessary.

The proposed alternative is approximately:

    application has canonical chunks:

        STUDENT_SUMMARY:...:0001
        STUDENT_SUMMARY:...:0002
        STUDENT_SUMMARY:...:0003

    for one LLM call, application assigns:

        E1 -> canonical chunk 1
        E2 -> canonical chunk 2
        E3 -> canonical chunk 3

    prompt contains evidence labeled E1/E2/E3

    LLM returns:

        evidence_refs: ["E1", "E3"]

    application validates that E1/E3 were actually supplied and then
    deterministically maps them back to the canonical chunk IDs.

If the LLM returns E9 when only E1-E3 exist, it must still fail closed.

The application must NEVER guess, fuzzy-match, repair, or substitute an
invalid reference.

## 1. Trace the current grounding provenance path

Trace the complete current path from retrieval to audit.

Identify:

1. where SourceEvidenceChunk.chunk_id originates;
2. where retrieved chunks are formatted for the grounding prompt;
3. exactly how the chunk ID appears in the prompt;
4. the GroundingValidationResult response field(s) carrying provenance;
5. where OpenAI structured-output schema for those fields is derived;
6. where returned IDs are verified;
7. where InvalidGroundingOutputError is raised;
8. where grounding provenance is stored in QuestionAttempt / audit models;
9. where grounding evidence IDs are serialized;
10. every downstream consumer that depends on those IDs being canonical
    SourceEvidenceChunk.chunk_id values.

Give file names, classes/functions, and important field names.

Do not change anything.

## 2. Determine whether full canonical IDs are actually required from the LLM

For every downstream consumer identified above, determine whether it requires:

A. the LLM itself to return the canonical chunk ID;

or merely:

B. the application to ultimately possess the canonical chunk ID.

This distinction is central.

Identify any place where replacing:

    LLM returns canonical chunk_id

with:

    LLM returns local evidence reference
        ↓
    application deterministically resolves reference
        ↓
    application stores canonical chunk_id

would break an existing contract.

Be specific.

## 3. Analyze call-local reference feasibility

Evaluate a design where each grounding validation call creates a deterministic,
call-local mapping such as:

    E1 -> <SourceEvidenceChunk 1>
    E2 -> <SourceEvidenceChunk 2>
    ...
    En -> <SourceEvidenceChunk n>

The mapping must correspond exactly to the evidence sequence supplied to that
LLM call.

Determine:

- where the mapping should be created;
- whether numbering by evidence order is deterministic;
- whether E1/E2/etc. is sufficient;
- whether references should be strings or another simple representation;
- how prompt formatting would change;
- how the response model would change;
- where validation of returned local references should occur;
- where conversion back to canonical chunk IDs should occur;
- whether the existing GroundingValidationResult should continue exposing
  canonical chunk IDs to the rest of the application.

Prefer keeping the local-reference mechanism entirely inside the
prompt/validator boundary if possible.

## 4. Strict provenance invariant

Determine whether this design can preserve the invariant:

    every canonical evidence_chunk_id recorded by the application
    must correspond to a SourceEvidenceChunk that was actually supplied
    to that exact validation call

For example:

    supplied: E1, E2, E3

    model returns: E1, E3
        -> valid
        -> deterministic canonical mapping

    model returns: E4
        -> invalid
        -> fail closed

    model returns:
    STUDENT_SUMMARY:some-other-chunk
        -> invalid local reference
        -> fail closed

There must be no:

- fuzzy matching;
- nearest-ID matching;
- prefix completion;
- index guessing;
- silent dropping;
- substitution;
- repair.

Explain whether the proposed mechanism is equally strict, stricter, or weaker
than the current mechanism.

## 5. WP-021 retry interaction

Determine what should happen to WP-021 if local evidence references are adopted.

Specifically analyze:

    call #1 returns invalid local reference E9
        ↓
    provenance violation
        ↓
    WP-021 retry same validation once

Would the retry use the exact same:

    E1 -> chunk A
    E2 -> chunk B
    E3 -> chunk C

mapping?

It should not renumber/retrieve/reorder evidence merely because a retry occurs.

Determine whether the existing WP-021 loop naturally supports this.

Do not remove or change WP-021 during this diagnostic.

## 6. WP-020 interaction

Confirm that malformed structured JSON remains completely separate:

    malformed JSON
        -> WP-020

    valid JSON + nonexistent local evidence ref
        -> validator provenance check / WP-021

Determine whether any changes would be required to WP-020.

Expected answer is likely none, but verify from the actual code.

## 7. Audit compatibility

This is especially important.

Determine whether we can keep the external/internal audit contract using
canonical IDs such as:

    STUDENT_SUMMARY:student_summary_2.pdf:0071:0001

even though the LLM only returned:

    E2

Desired flow:

    LLM: E2
        ↓
    validator verifies E2 exists
        ↓
    application resolves E2
        ↓
    GroundingValidationResult exposed downstream contains canonical chunk_id
        ↓
    audit continues storing canonical chunk_id

Determine whether this is possible without broad refactoring.

Identify exactly which model boundary would perform this conversion.

## 8. Response-model design

Inspect the existing GroundingValidationResult.

Determine whether the cleanest design would require:

A. changing GroundingValidationResult itself to contain local refs;

B. introducing a small LLM-facing response model such as:

    GroundingValidationResponse

and then converting it deterministically into the existing:

    GroundingValidationResult

with canonical chunk IDs;

or:

C. another smaller approach consistent with the current architecture.

Prefer not leaking temporary E1/E2 identifiers beyond the LLM/validator
boundary.

Do not implement anything.

State which option best preserves existing domain contracts and minimizes
refactoring.

## 9. Textbook provenance

Perform the same analysis for TextbookValidator.

Trace:

- course-book evidence formatting;
- TextbookCheckResult;
- evidence_chunk_ids;
- source_page;
- reference_text;
- _validate_textbook_provenance();
- audit/output usage.

Determine whether textbook validation should also use call-local references.

Pay special attention to whether:

    source_page
    reference_text

are still necessary provenance fields if canonical chunk IDs are
deterministically recovered from local references.

Do NOT decide to remove them yet.

Just report:

- their current purpose;
- whether downstream code depends on them;
- whether they are redundant once a canonical chunk is known;
- whether they have historically caused provenance failures.

## 10. Generation provenance

Inspect QuestionGenerator separately.

It also currently has generation-time provenance reporting.

Determine whether the same local-reference concept could technically apply
there.

However, do NOT assume WP-022 should change generation.

Report separately:

    Grounding validator feasibility
    Textbook validator feasibility
    Question generator feasibility

We may deliberately scope a future WP only to validators.

## 11. Historical-reference IDs

Check whether historical_reference_id has the same problem.

Determine:

- how it is supplied;
- how it is returned;
- how it is validated;
- whether it is already a short/simple ID;
- whether there is any evidence from previous runs that it causes failures.

Do not generalize the solution unnecessarily if this field is already reliable.

## 12. Required changes inventory

If local references are feasible, provide a minimal change inventory.

For each likely change identify:

- file;
- class/function/model;
- conceptual change.

Group into:

MUST CHANGE

SHOULD CHANGE

DOES NOT NEED TO CHANGE

In particular identify expected impact on:

- prompt formatting;
- grounding prompt;
- textbook prompt;
- response models;
- GroundingValidator;
- TextbookValidator;
- QuestionGenerator;
- WP-021 retry;
- WP-020 retry;
- QuestionAttempt;
- audit models;
- output serialization;
- JSON schemas;
- CLI;
- retrieval.

## 13. Testing implications

Describe the minimum tests a future WP would need.

At minimum consider:

- E1/E2 valid mapping;
- unknown E9 rejected;
- canonical ID returned instead of E1 rejected;
- mapping deterministic by evidence order;
- WP-021 retry reuses identical mapping;
- canonical chunk IDs preserved downstream;
- audit contains canonical IDs, never E1/E2;
- Hebrew evidence unaffected;
- textbook equivalent behavior;
- no regression to WP-020;
- no regression to generation-contract handling.

Do not write the tests now.

## 14. Final assessment

Finish with one of:

A. FEASIBLE — SMALL, LOCALIZED CHANGE

B. FEASIBLE — BUT REQUIRES BROAD REFACTORING

C. NOT FEASIBLE WITHOUT WEAKENING PROVENANCE

Support the classification from the actual code.

Then answer explicitly:

1. Can the LLM stop reproducing full canonical chunk IDs?
2. Can strict fail-closed provenance be preserved?
3. Can downstream code/audit continue seeing canonical chunk IDs?
4. Can E1/E2 references remain entirely internal to the LLM-facing boundary?
5. Would WP-021 still work?
6. Would WP-020 require changes?
7. Should textbook use the same mechanism?
8. Could generation use it later if desired?
9. Are source_page/reference_text still needed for textbook validation?
10. What is the smallest likely implementation scope for a future WP-022?

Do not implement WP-022.
Do not make API calls.
Do not modify files.
Do not commit anything.

Return the diagnostic report and wait for architect/user review.
