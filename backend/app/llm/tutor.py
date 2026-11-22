"""Tutor: re-explains a graded problem in plain language.

The model only ever *rephrases* the deterministic solution it's given. It never computes or
grades. Answers come from tested code (SPEC principle 5).
"""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings

SYSTEM = """You are a patient poker-math coach for a beginner studying No-Limit Hold'em.

You are given a practice problem, the student's answer, the correct answer, and a worked
solution produced by tested code. Re-explain *why* the correct answer is right, in a
different way from the worked solution: an analogy, a smaller step-by-step, or the mental
shortcut a strong player would use at the table.

Rules:
- Every number you state must come from the problem or the worked solution. Never compute
  new figures and never contradict the worked solution.
- If the student was wrong, name the likely mistake in one sentence, without scolding.
- Plain Markdown, at most 150 words. No preamble, no sign-off."""

HUMAN = """Problem: {prompt}
{scene}
Student answered: {student_answer}
Correct answer: {correct_answer} ({verdict})

Worked solution:
{explanation}

{question}"""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", HUMAN)])


@lru_cache
def _anthropic_model() -> BaseChatModel | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.tutor_model,
        api_key=settings.anthropic_api_key,
        max_tokens=600,
        temperature=0.3,
        timeout=30,
    )


def get_tutor_model() -> BaseChatModel | None:
    """FastAPI dependency; tests override it with a fake model."""
    return _anthropic_model()


async def explain(
    model: BaseChatModel,
    *,
    prompt: str,
    scene: str,
    student_answer: str,
    correct_answer: str,
    verdict: str,
    explanation: str,
    question: str | None,
) -> str:
    chain = PROMPT | model | StrOutputParser()
    return await chain.ainvoke(
        {
            "prompt": prompt,
            "scene": scene,
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "verdict": verdict,
            "explanation": explanation,
            "question": f"The student asks: {question}" if question else "Explain it differently.",
        }
    )


def render_messages(**kw: str) -> list[BaseMessage]:
    """For tests / debugging: the exact messages sent to the model."""
    return PROMPT.format_messages(**kw)
