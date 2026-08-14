import pytest

from exam_generator.generation import resolve_strategy_preference
from exam_generator.models import GenerationStrategyPreference

BASAL_NUCLEI_CATEGORY = "גרעיני הבסיס"
OTHER_CATEGORY = "אספקת דם"


# ---------------------------------------------------------------------------
# WP-054/WP-057 required scope tests (pair-specific, not target-global or
# category-global) - three approved (category, topic) pairs since WP-057
# added Globus Pallidus alongside the original WP-054 pair.
# ---------------------------------------------------------------------------


def test_case_1_caudate_nucleus_in_basal_nuclei_is_identity_first():
    preference = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="Caudate Nucleus")
    assert preference == GenerationStrategyPreference.IDENTITY_FIRST


def test_case_2_nucleus_accumbens_in_basal_nuclei_is_identity_first():
    preference = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="Nucleus Accumbens")
    assert preference == GenerationStrategyPreference.IDENTITY_FIRST


def test_case_3_globus_pallidus_in_basal_nuclei_is_identity_first():
    # WP-057: promoted from DEFAULT to IDENTITY_FIRST, per the WP-055
    # diagnostic investigation, the WP-056 controlled experiment (0/7
    # CONTROL vs. 3/4 EXPERIMENT primary-success attempts), and the WP-056
    # architecture review's explicit approval.
    preference = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="Globus Pallidus")
    assert preference == GenerationStrategyPreference.IDENTITY_FIRST


def test_case_4_another_target_in_basal_nuclei_is_default():
    # WP-054 section 37 / WP-057 section 21: prevents the rule from
    # becoming category-global - an unmapped target in the same category
    # must remain DEFAULT even though three of its siblings are now mapped.
    preference = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="Putamen")
    assert preference == GenerationStrategyPreference.DEFAULT


def test_case_5_caudate_nucleus_in_another_category_is_default():
    # WP-054 section 36: prevents the rule from becoming target-global.
    preference = resolve_strategy_preference(category=OTHER_CATEGORY, topic="Caudate Nucleus")
    assert preference == GenerationStrategyPreference.DEFAULT


def test_case_6_nucleus_accumbens_in_another_category_is_default():
    preference = resolve_strategy_preference(category=OTHER_CATEGORY, topic="Nucleus Accumbens")
    assert preference == GenerationStrategyPreference.DEFAULT


def test_case_7_globus_pallidus_in_another_category_is_default():
    # WP-057 section 22 (category isolation): the strategy decision is
    # category + target, never target alone - Globus Pallidus must not
    # inherit IDENTITY_FIRST outside גרעיני הבסיס.
    preference = resolve_strategy_preference(category=OTHER_CATEGORY, topic="Globus Pallidus")
    assert preference == GenerationStrategyPreference.DEFAULT


def test_unknown_category_is_default():
    preference = resolve_strategy_preference(category="קטגוריה שלא קיימת", topic="Caudate Nucleus")
    assert preference == GenerationStrategyPreference.DEFAULT


# ---------------------------------------------------------------------------
# Exact matching only - no fuzzy/case-insensitive/substring matching
# ---------------------------------------------------------------------------


def test_case_sensitive_topic_match_is_not_identity_first():
    preference = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="caudate nucleus")
    assert preference == GenerationStrategyPreference.DEFAULT


def test_partial_topic_match_is_not_identity_first():
    preference = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="Caudate")
    assert preference == GenerationStrategyPreference.DEFAULT


def test_globus_pallidus_externus_is_not_identity_first():
    # WP-057 section 23 (exact target matching): a related target whose
    # name merely contains "Globus Pallidus" as a substring must not
    # accidentally inherit the strategy - no substring/fuzzy matching.
    preference = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="Globus Pallidus Externus")
    assert preference == GenerationStrategyPreference.DEFAULT


def test_gpe_abbreviation_is_not_identity_first():
    preference = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="(GPe)")
    assert preference == GenerationStrategyPreference.DEFAULT


def test_blank_topic_is_default():
    preference = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="")
    assert preference == GenerationStrategyPreference.DEFAULT


# ---------------------------------------------------------------------------
# Determinism / purity
# ---------------------------------------------------------------------------


def test_resolve_strategy_preference_is_deterministic():
    first = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="Caudate Nucleus")
    second = resolve_strategy_preference(category=BASAL_NUCLEI_CATEGORY, topic="Caudate Nucleus")
    assert first == second


def test_resolve_strategy_preference_makes_no_llm_or_network_call():
    # Purely a signature/behavior check: resolve_strategy_preference takes
    # only two strings - structurally nowhere for a provider or prompt
    # repository to be injected.
    import inspect

    params = inspect.signature(resolve_strategy_preference).parameters
    assert set(params) == {"category", "topic"}


def test_resolve_strategy_preference_never_reads_the_historical_workbook():
    # WP-054 section 25: the mapping must be a fixed, reviewed policy, not
    # runtime-computed from the historical Excel workbook.
    import inspect

    from exam_generator.generation import strategy as strategy_module

    source = inspect.getsource(strategy_module)
    assert "HistoricalQuestionRepository" not in source
    assert ".xlsx" not in source
    assert "openpyxl" not in source


# ---------------------------------------------------------------------------
# GenerationStrategyPreference model
# ---------------------------------------------------------------------------


def test_generation_strategy_preference_has_exactly_two_values():
    assert {member.value for member in GenerationStrategyPreference} == {"DEFAULT", "IDENTITY_FIRST"}


@pytest.mark.parametrize("value", ["DEFAULT", "IDENTITY_FIRST"])
def test_generation_strategy_preference_values_are_constructible(value):
    assert GenerationStrategyPreference(value).value == value
