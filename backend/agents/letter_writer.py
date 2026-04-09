"""
Letter Writer sub-agent.
Receives tailored CV + JD + research brief as message context.
Tool: document_export (custom) — exports the finished letter to DOCX.
"""
from pathlib import Path
import anthropic

from backend.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from backend.tools import document_export

SYSTEM_PROMPT = """
You are a professional career writer specialising in motivation and cover letters.
You receive a tailored CV and a job description.
Your job is to:
- Write a concise, compelling motivation letter (max 4 paragraphs, max 350 words)
- Connect the candidate's background explicitly to the role's needs
- Open with a strong hook, not a cliché
- Close with a confident, specific call to action
- Tone: professional but human. Never generic.
- Once you are satisfied with the letter, call document_export with doc_type="letter"

Return ONLY the final motivation letter in markdown. Do not add commentary.
"""

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def run(tailored_cv_md: str, jd_text: str, research_brief_md: str, session_dir: Path) -> dict:
    """
    Run the Letter Writer sub-agent.

    Returns:
        {"letter_md": str, "letter_path": str}
    """
    tools = [document_export.TOOL_SCHEMA]

    messages = [
        {
            "role": "user",
            "content": (
                f"Here is the tailored CV:\n\n{tailored_cv_md}\n\n"
                f"Here is the job description:\n\n{jd_text}\n\n"
                f"Here is the company research brief:\n\n{research_brief_md}\n\n"
                "Write the motivation letter and export it to DOCX."
            ),
        }
    ]

    letter_md = None
    letter_path = None

    while True:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        for block in response.content:
            if block.type == "text" and letter_md is None:
                letter_md = block.text

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "document_export":
                    inp = block.input
                    letter_path = document_export.execute(
                        content=inp["content"],
                        doc_type=inp["doc_type"],
                        filename=inp["filename"],
                        session_dir=session_dir,
                    )
                    letter_md = inp["content"]
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": letter_path,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return {
        "letter_md": letter_md or "",
        "letter_path": letter_path,
    }
