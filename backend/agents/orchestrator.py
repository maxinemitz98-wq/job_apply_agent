"""
Orchestrator — coordinates the full pipeline.

Phase 1a: Sequential execution (flat single-agent pattern).
Phase 1b: Upgrade to parallel via asyncio.gather() or Managed Agents API threads.

The orchestrator is Python code, not an LLM. It coordinates async calls to each
specialist sub-agent function and publishes progress events to the SSE queue.
"""
import asyncio
import uuid
from pathlib import Path
from typing import Callable, Awaitable

from backend.config import STORAGE_PATH
from backend.agents import cv_tailor, researcher, letter_writer, scorer


async def run_pipeline(
    jd_text: str,
    company_name: str,
    role_title: str,
    cv_text: str,
    session_id: str,
    emit: Callable[[str, dict], Awaitable[None]] | None = None,
) -> dict:
    """
    Run the full job application pipeline.

    Args:
        jd_text: Full job description text
        company_name: Company name for research
        role_title: Role title for research
        cv_text: Parsed CV text (pre-processed, not fetched by agent)
        session_id: Unique session identifier
        emit: Optional async callback for SSE progress events — emit(event_name, data)

    Returns:
        {
            "tailored_cv_md": str,
            "tailored_cv_path": str | None,
            "research_brief_md": str,
            "letter_md": str,
            "letter_path": str | None,
            "score": dict,
        }
    """
    session_dir = STORAGE_PATH / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    async def _emit(event: str, data: dict):
        if emit:
            await emit(event, data)

    # ── Phase 1a: Sequential ─────────────────────────────────────────────────
    # Step 1: CV Tailor + Researcher in parallel (asyncio.gather for Phase 1a)
    await _emit("agent_started", {"agent": "cv_tailor"})
    await _emit("agent_started", {"agent": "researcher"})

    cv_result, research_result = await asyncio.gather(
        cv_tailor.run(cv_text=cv_text, jd_text=jd_text, session_dir=session_dir),
        researcher.run(company_name=company_name, role_title=role_title),
    )

    await _emit("agent_completed", {"agent": "cv_tailor"})
    await _emit("agent_completed", {"agent": "researcher"})

    # Step 2: Letter Writer + Scorer in parallel (both depend on CV result)
    await _emit("agent_started", {"agent": "letter_writer"})
    await _emit("agent_started", {"agent": "scorer"})

    letter_result, score_result = await asyncio.gather(
        letter_writer.run(
            tailored_cv_md=cv_result["tailored_cv_md"],
            jd_text=jd_text,
            research_brief_md=research_result["research_brief_md"],
            session_dir=session_dir,
        ),
        scorer.run(cv_text=cv_text, jd_text=jd_text),
    )

    await _emit("agent_completed", {"agent": "letter_writer"})
    await _emit("agent_completed", {"agent": "scorer"})

    return {
        "tailored_cv_md": cv_result["tailored_cv_md"],
        "tailored_cv_path": cv_result.get("tailored_cv_path"),
        "research_brief_md": research_result["research_brief_md"],
        "letter_md": letter_result["letter_md"],
        "letter_path": letter_result.get("letter_path"),
        "score": score_result,
    }
