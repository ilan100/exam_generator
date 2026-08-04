"""Independent MCQ-construction validation for a WP-009 ``CandidateQuestion``.

Assesses only whether the candidate functions as a proper one-best-answer
multiple-choice question (four answers, a single unambiguously best answer,
plausible distractors, no structural giveaway clues). Factual grounding is
out of scope here - a question can be perfectly well-grounded and still fail
this check (e.g. absurd distractors), or vice versa; see
``exam_generator.validation.grounding`` for the separate grounding concern.
"""

from __future__ import annotations

from exam_generator.config import load_llm_config
from exam_generator.llm import LLMProfile, LLMProvider, build_llm_provider
from exam_generator.models import CandidateQuestion, MCQValidationResult
from exam_generator.prompts import PromptId, PromptRepository, build_prompt_messages, format_candidate_question


class MCQValidator:
    """Application-facing entry point for one independent MCQ-construction
    validation call.

    Every dependency is injected explicitly - never hidden global state - so
    tests can supply fakes/mocks. Use
    ``MCQValidator.from_default_configuration()`` for the normal application
    wiring against real project configuration.
    """

    def __init__(self, *, prompt_repository: PromptRepository, llm_provider: LLMProvider) -> None:
        self._prompt_repository = prompt_repository
        self._llm_provider = llm_provider

    @classmethod
    def from_default_configuration(cls) -> "MCQValidator":
        """Construct the normal application wiring: the real production
        prompt repository and the configured OpenAI provider.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``build_llm_provider`` at this point, not earlier).
        """
        return cls(
            prompt_repository=PromptRepository.from_default_location(),
            llm_provider=build_llm_provider(load_llm_config()),
        )

    def validate(self, candidate: CandidateQuestion) -> MCQValidationResult:
        """Independently determine whether ``candidate`` is a proper
        one-best-answer MCQ.

        Makes exactly one ``LLMProfile.VALIDATION`` call - no retry. A
        negative verdict (``valid=False``) is a normal, successful result;
        a provider/LLM failure raises instead of ever silently becoming a
        fabricated negative verdict. Never mutates ``candidate``.
        """
        messages = build_prompt_messages(
            system_template=self._prompt_repository.get(PromptId.SYSTEM),
            task_template=self._prompt_repository.get(PromptId.MCQ_VALIDATION),
            variables={"candidate_question": format_candidate_question(candidate)},
        )

        return self._llm_provider.generate_structured(
            messages=messages,
            response_model=MCQValidationResult,
            profile=LLMProfile.VALIDATION,
        )
