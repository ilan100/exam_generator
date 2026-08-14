# WP-054 Architecture Review

## Review Status

**ACCEPTED**

WP-054 correctly converts the WP-053 experimental result into a narrow permanent production mechanism.

The implementation follows the approved architectural boundary:

```text
גרעיני הבסיס + Caudate Nucleus
    → IDENTITY_FIRST

גרעיני הבסיס + Nucleus Accumbens
    → IDENTITY_FIRST

everything else
    → DEFAULT
```

The implementation does **not** turn the experiment into a general sparse-evidence strategy, target filter, new validator, retry policy, retrieval mechanism, or schema change.

The completion report states this exact objective and scope. fileciteturn40file0L3-L5

---

# 1. Architectural Assessment

The implementation is structurally sound.

The chosen flow is:

```text
QuestionTarget
    ↓
resolve_strategy_preference(category, topic)
    ↓
GenerationStrategyPreference
    ↓
GenerationPromptContext.strategy_preference
    ↓
format_target_strategy_requirement()
    ↓
target_strategy_requirement
    ↓
existing generation prompt
    ↓
LLM
```

This follows the existing `format_target_*()` pattern rather than introducing a parallel generation mechanism. fileciteturn40file0L15-L30

This is the right level of intervention for the current requirement.

---

# 2. Separation of Concerns

A particularly good decision is that `QuestionTarget` was **not** given a strategy field.

The completion report explicitly states:

```text
QuestionTarget = what the target is

GenerationStrategyPreference = how generation should approach it
```

The strategy enum lives in `models/strategy.py`, while the resolver lives in `generation/strategy.py`. fileciteturn40file0L37-L45

This preserves the architectural distinction we wanted.

I approve this design.

---

# 3. Strategy Resolver

The resolver is:

```text
resolve_strategy_preference(
    category,
    topic
)
```

and uses an explicit in-code mapping:

```text
גרעיני הבסיס
    → {Caudate Nucleus, Nucleus Accumbens}
```

with exact membership rather than fuzzy or substring matching. fileciteturn40file0L43-L55

This is appropriate because the current decision is intentionally narrow and reviewed.

It also avoids a dangerous pattern such as:

```text
if target contains "nucleus":
    identity-first
```

or:

```text
if evidence is sparse:
    identity-first
```

which were explicitly rejected architectural directions.

---

# 4. Canonical Category Handling

The strategy is resolved using:

```text
canonical_category
```

rather than the raw caller-supplied category.

The completion report explicitly states that the lookup occurs after canonical-category resolution. fileciteturn40file0L43-L45

This is important because the strategy policy should operate on the same canonical representation used by the rest of the system.

I approve.

---

# 5. Prompt Integration

The strategy is integrated through the existing prompt-context mechanism:

```text
GenerationPromptContext
        ↓
render_variables()
        ↓
target_strategy_requirement
```

The default case produces an explicit sentinel rather than silently omitting the requirement, matching the project's existing `format_target_*()` convention. fileciteturn40file0L57-L66

This is preferable to mutating prompt templates dynamically.

The completion report also verifies that unrelated prompt text remains byte-identical between `DEFAULT` and `IDENTITY_FIRST` rendering. fileciteturn40file0L64-L66

That is a strong implementation detail.

---

# 6. Prompt Instruction Semantics

The new strategy is correctly implemented as a:

```text
preference
```

rather than an:

```text
exclusive requirement
```

The prompt explicitly states that identity-first does not override:

```text
answer identity
target language
target evidence role
enumeration-member requirements
single-best-answer requirements
grounding
```

fileciteturn40file0L59-L64

This is exactly the right boundary.

The strategy should influence generation, not become a new validity authority.

---

# 7. Production Path

This is important: WP-054 did not merely test a mock implementation.

The verification script uses:

```text
PromptRepository.from_default_location()
QuestionGenerator
QuestionProducer
all five real validators
real OpenAI API
```

and the permanent strategy is resolved automatically by the real `QuestionGenerator`. fileciteturn40file1L3-L17

Therefore the live test genuinely verifies the production path.

---

# 8. Automated Scope Tests

The implementation added deterministic tests for:

```text
Caudate + גרעיני הבסיס
    → IDENTITY_FIRST

Nucleus Accumbens + גרעיני הבסיס
    → IDENTITY_FIRST

Globus Pallidus + גרעיני הבסיס
    → DEFAULT

another target + גרעיני הבסיס
    → DEFAULT

Caudate + another category
    → DEFAULT

Nucleus Accumbens + another category
    → DEFAULT
```

All six passed. fileciteturn40file0L197-L206

This is exactly the regression boundary required by WP-054.

---

# 9. Integration Tests

The integration tests verify that:

```text
IDENTITY_FIRST
```

actually reaches the LLM prompt for the two approved targets.

They also verify that:

```text
Globus Pallidus
other target in basal nuclei
Caudate outside basal nuclei
```

do not receive the identity-first instruction. fileciteturn40file0L74-L80

This is stronger than testing the resolver alone.

The architecture is therefore tested at two levels:

```text
resolver correctness
+
generation integration
```

Good.

---

# 10. Regression Result

The full test suite went from:

```text
1396 passed
```

to:

```text
1426 passed
0 failed
```

with exactly 30 new WP-054 tests. fileciteturn40file0L100-L103

This is a clean result.

No existing tests were removed or weakened.

---

# 11. Retry Boundary

`QuestionProducer` was not modified.

The three-attempt budget remains unchanged.

Strategy resolution occurs inside `QuestionGenerator`, once for each generation call, without changing the retry loop. fileciteturn40file0L108-L110

This is correct.

The purpose of the strategy is to improve what happens **inside** an existing attempt, not to redesign attempt management.

---

# 12. Validator Boundary

No validator was modified.

This is exactly what we wanted.

The architecture remains:

```text
strategy preference
    ↓
generation
    ↓
existing validation
```

rather than:

```text
strategy preference
    ↓
special validation rules
```

The completion report explicitly confirms that no file under `validation/` was modified. fileciteturn40file0L183-L185

---

# 13. Schema Boundary

No product schema was changed.

Neither:

```text
CandidateQuestion
```

nor:

```text
QuestionTarget
```

received a strategy field.

No schema file was touched. fileciteturn40file0L104-L106

This is architecturally correct.

The strategy is internal generation metadata and should not leak into the product JSON.

---

# 14. Historical Data Boundary

The resolver does not read:

```text
historical Excel
```

at runtime.

It uses the reviewed explicit mapping.

A dedicated test also verifies that the resolver contains no historical-repository/OpenPyXL dependency. fileciteturn40file0L43-L45

This is correct.

The historical data justified the architectural decision; it should not become runtime strategy authority.

---

# 15. Source Authority

The implementation does not change source authority.

The completion report confirms:

```text
student summaries
    = factual grounding authority

course_book.pdf
    = secondary consistency check

historical Excel
    = style/structure/terminology reference
```

and the strategy resolver itself performs no source access. fileciteturn40file0L112-L115

Approved.

---

# 16. Language Rule Review

The completion report states that the English-first mechanism from WP-041 remains untouched and that live outputs used the English target names verbatim. fileciteturn40file0L116-L140

The report also records an important nuance:

```text
"...נקרא Caudate Nucleus?"
"...נקרא Nucleus Accumbens?"
```

and concludes that the target name itself is English and therefore compliant with the existing WP-041 rule. fileciteturn40file0L144-L156

However, there is a distinction worth preserving:

```text
English target-name usage
```

is not necessarily equivalent to:

```text
the entire question is English.
```

Based on the completion report alone, I can confirm that the **target-name language requirement** was preserved.

I cannot conclude from this report that the entire generated question must be English, because the report describes the existing WP-041 requirement as applying specifically to the correct answer and references to the target name.

Therefore:

**No WP-054 defect is established here.**

But the broader project language requirement should continue to be treated according to its authoritative project specification rather than inferred from this WP.

---

# 17. Live End-to-End Verification

The real production path was tested once for each of:

```text
Caudate Nucleus
Nucleus Accumbens
Globus Pallidus
```

with no reruns. fileciteturn40file1L19-L21

Results:

```text
Caudate Nucleus
    IDENTITY_FIRST
    accepted on attempt 1

Nucleus Accumbens
    IDENTITY_FIRST
    attempt 1 rejected
    attempt 2 accepted

Globus Pallidus
    DEFAULT
    all 3 attempts rejected
```

fileciteturn40file0L82-L90

This result is important because it confirms the permanent mechanism behaves differently from the experimental WP-053 mechanism only in implementation location—not in intended strategy scope.

---

# 18. Nucleus Accumbens Result

The Nucleus Accumbens live run is especially useful.

Attempt 1:

```text
bare classification-membership shape
```

was rejected by grounding.

Attempt 2:

```text
identity/naming question
```

was accepted.

fileciteturn40file0L86-L90

This validates the architectural decision to treat:

```text
IDENTITY_FIRST
```

as a preference rather than:

```text
IDENTITY_ONLY
```

The existing retry mechanism successfully absorbed the first failure.

No new retry logic was required.

---

# 19. Globus Pallidus Result

Globus Pallidus remained:

```text
DEFAULT
```

through all attempts. fileciteturn40file0L92-L94

All three attempts failed in the previously known classification-ambiguity family.

This is not a WP-054 regression according to the completion evidence.

It is an existing unresolved problem.

This distinction is important:

```text
WP-054 succeeded
≠
Globus Pallidus problem solved
```

The two issues are now cleanly separated.

---

# 20. Coverage

The live verification intentionally constructs targets directly because coverage planning was out of scope. fileciteturn40file1L19-L21

The completion report also confirms that no planning/coverage files were modified. fileciteturn40file0L183-L185

Therefore:

```text
coverage architecture preserved
```

is supported.

We should not claim that WP-054 independently validated coverage behavior.

---

# 21. Code Change Scope

The changed files are appropriately concentrated:

```text
models/strategy.py
generation/strategy.py
generation/generator.py
prompts/formatting.py
prompts/context.py
prompts/generation/question.txt
tests
architecture/status docs
```

while:

```text
production/producer.py
validation
retrieval
historical
planning
schemas
config
```

were untouched. fileciteturn40file0L166-L185

This is an excellent scope boundary.

---

# 22. One Minor Architectural Observation

The resolver mapping is currently:

```text
category string
    →
frozenset of target strings
```

This is acceptable and intentionally simple.

However, we should not allow this dictionary to gradually become a large collection of special cases.

If future work starts adding many target-specific strategies, that is the point at which we should stop and design a more general policy architecture.

For WP-054:

```text
current simple mapping = correct
```

For a future large strategy matrix:

```text
new architecture required
```

This should remain an explicit architectural boundary.

---

# 23. No Need for Another Experiment

WP-054 itself does not need another experiment.

We already have:

```text
WP-052
historical evidence

WP-053
controlled experiment

WP-054
permanent implementation
+
fresh production verification
```

The live result confirms the implementation works.

Do not create WP-055 merely to repeat the same Caudate/Nucleus Accumbens experiment.

---

# 24. What Remains Open

Two distinct future directions remain.

### Direction A — Globus Pallidus

The existing classification-ambiguity problem remains unresolved.

This is now clearly isolated from identity-first.

### Direction B — Expand Identity-First

If we want to apply identity-first to another target/category pair, the correct workflow remains:

```text
candidate target
    ↓
WP-052-style historical analysis
    ↓
WP-053-style controlled experiment
    ↓
architectural decision
    ↓
permanent implementation
```

Do not skip directly from intuition to code.

---

# 25. Recommended WP-055

Based on the completion report, I recommend:

**WP-055 — Investigate Globus Pallidus Classification-Ambiguity Failure**

Reason:

```text
Globus Pallidus
    DEFAULT
    ↓
3/3 attempts rejected
    ↓
known classification-membership ambiguity
    ↓
still unresolved
```

This is now the clearest remaining generation-quality problem exposed by the latest live run.

The alternative—expanding identity-first to more targets—is less urgent because the current approved implementation is already functioning.

---

# 26. Suggested WP-055 Scope

WP-055 should be diagnostic first.

It should investigate:

```text
Why does Globus Pallidus repeatedly produce
classification-membership questions that fail grounding?
```

It should inspect:

```text
retrieved evidence
target factual focus
relationship extraction
competitor discovery
prompt instructions
generated question shape
grounding validator reasoning
historical examples
```

But it should **not** immediately implement a fix.

The goal should be:

```text
understand the failure mechanism
```

before deciding whether the solution is:

```text
prompt change
target strategy
evidence representation
competitor selection
grounding rule
```

---

# 27. Final Architectural Decision

**WP-054 — ACCEPTED.**

The permanent identity-first mechanism is architecturally appropriate and correctly scoped.

Approved permanent mapping:

```text
גרעיני הבסיס + Caudate Nucleus
    → IDENTITY_FIRST

גרעיני הבסיס + Nucleus Accumbens
    → IDENTITY_FIRST

גרעיני הבסיס + Globus Pallidus
    → DEFAULT

all other targets/categories
    → DEFAULT
```

---

# 28. Final State

```text
WP-051
Target filtering
    ↓
CLOSED

WP-052
Historical strategy analysis
    ↓
Identity-first hypothesis

WP-053
Controlled experiment
    ↓
Identity-first supported for two targets

WP-054
Permanent narrow implementation
    ↓
ACCEPTED
```

The main issue that motivated this branch has therefore been meaningfully advanced:

```text
Before:
repeated property-generation failures for certain targets

Now:
explicit identity-first generation preference
for the two experimentally supported targets
```

The implementation remains:

```text
small
deterministic
testable
reviewable
non-invasive
```

and the existing validation/retry/source architecture remains intact.

---

# Final Recommendation

**WP-054: ACCEPTED.**

**Do not modify WP-054 further.**

Proceed to:

```text
WP-055
Globus Pallidus Classification-Ambiguity Investigation
```

with diagnostic investigation first and implementation only after the failure mechanism is understood.

The identity-first expansion path remains available, but any new target/category pair must go through the same evidence → experiment → implementation sequence.
