"""
CV Tailor sub-agent.
Receives CV text + JD text as message context.
Tool: document_export (custom) — exports the finished CV to DOCX.
"""
import json
from pathlib import Path
import anthropic

from backend.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from backend.tools import document_export

SYSTEM_PROMPT = """
You are an expert CV editor. You receive a candidate's existing CV and a job description.
Your job is to:
- Rewrite and tailor the CV to maximise alignment with the JD
- Keep the candidate's authentic experience — never invent facts
- Prioritise skills, achievements, and language from the JD
- Output a clean structured CV in markdown
- Focus on: skill keywords, seniority alignment, sector framing, measurable achievements
- Once you are happy with the CV markdown, call document_export with doc_type="cv"

Return ONLY the final tailored CV in markdown. Do not add commentary before or after.
"""

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def run(cv_text: str, jd_text: str, session_dir: Path) -> dict:
    """
    Run the CV Tailor agent.

    Returns:
        {"tailored_cv_md": str, "tailored_cv_path": str}
    """
    tools = [document_export.TOOL_SCHEMA]

    messages = [
        {
            "role": "user",
            "content": (
                f"Here is the candidate's current CV:\n\n{cv_text}\n\n"
                f"Here is the job description:\n\n{jd_text}\n\n"
                "Please tailor the CV for this role and export it to DOCX."
            ),
        }
    ]

    tailored_md = None
    docx_path = None

    while True:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # Collect text from this response turn
        for block in response.content:
            if block.type == "text" and tailored_md is None:
                tailored_md = block.text

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "document_export":
                    inp = block.input
                    docx_path = document_export.execute(
                        content=inp["content"],
                        doc_type=inp["doc_type"],
                        filename=inp["filename"],
                        session_dir=session_dir,
                    )
                    # If the agent exported the content, use that as authoritative markdown
                    tailored_md = inp["content"]
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": docx_path,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            # stop_reason == "end_turn" or similar
            break

    return {
        "tailored_cv_md": tailored_md or "",
        "tailored_cv_path": docx_path,
    }
