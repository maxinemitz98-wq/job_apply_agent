"""
Researcher sub-agent.
Uses Anthropic built-in web_search tool (server-side execution via beta header).
The SDK handles tool execution transparently when using the search beta.
"""
import anthropic

from backend.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

SYSTEM_PROMPT = """
You are a company and market research specialist.
You receive a company name and job title.
Your job is to:
- Research the company: strategy, recent news, culture, key people, competitive position
- Research the role: what the hiring manager cares about, what success looks like
- Produce a structured 1-page brief the candidate can use for interview prep
- Use web_search for fresh data. Prioritise sources from the past 6 months.

Output format — markdown with these exact sections:
## Company Overview
## Recent News
## Role Context
## Key People
## Prep Tips

Be specific and factual. Do not pad with generic statements.
"""

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def run(company_name: str, role_title: str) -> dict:
    """
    Run the Researcher sub-agent.
    Uses the Anthropic web_search tool (beta) for live company research.

    Returns:
        {"research_brief_md": str}
    """
    # web_search is a built-in server-side tool; Anthropic executes searches automatically
    tools = [{"type": "web_search_20250305", "name": "web_search"}]

    messages = [
        {
            "role": "user",
            "content": (
                f"Research the company '{company_name}' and the role '{role_title}'. "
                "Produce the structured research brief as specified."
            ),
        }
    ]

    research_md = None

    # Agentic loop — web_search tool calls are handled by the Anthropic platform.
    # The model may emit multiple tool_use blocks before producing the final text.
    while True:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
            betas=["web-search-2025-03-05"],
        )

        if response.stop_reason == "tool_use":
            # Add assistant turn + placeholder tool results so the loop can continue.
            # For web_search (server-side), the platform injects results; we echo back
            # the tool_use blocks and the API resolves them on the next call.
            messages.append({"role": "assistant", "content": response.content})
            tool_results = [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "",  # server fills this in for built-in tools
                }
                for block in response.content
                if hasattr(block, "type") and block.type == "tool_use"
            ]
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
        else:
            for block in response.content:
                if block.type == "text":
                    research_md = block.text
                    break
            break

    return {"research_brief_md": research_md or ""}
