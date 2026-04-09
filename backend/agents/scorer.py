"""
Scorer sub-agent.
Receives CV text + JD text as message context. No tools needed.
Returns structured JSON with dimension scores and overall assessment.
"""
import json
import anthropic

from backend.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

SYSTEM_PROMPT = """
You are a hiring process analyst. You assess how well a candidate profile matches a job description.

Evaluate on these dimensions (score each 1-5):
1. Skills & technical match (keywords, tools, certifications)
2. Seniority & experience match (years, scope, complexity)
3. Sector / domain fit (industry, asset class, client type)
4. Language & communication fit
5. Credential match (degree, licenses)
6. Location & logistics fit

Output ONLY valid JSON in this exact schema:
{
  "dimensions": [
    {"name": "Skills & technical match", "score": 4, "reason": "..."},
    {"name": "Seniority & experience match", "score": 3, "reason": "..."},
    {"name": "Sector / domain fit", "score": 5, "reason": "..."},
    {"name": "Language & communication fit", "score": 4, "reason": "..."},
    {"name": "Credential match", "score": 3, "reason": "..."},
    {"name": "Location & logistics fit", "score": 5, "reason": "..."}
  ],
  "overall_score": 8.2,
  "strengths": ["...", "...", "..."],
  "gaps": ["...", "...", "..."],
  "interview_likelihood": "HIGH"
}

interview_likelihood must be one of: LOW, MEDIUM, HIGH, STRONG
overall_score is out of 10, computed as weighted average of dimension scores.
Base scoring on explicit evidence in the CV and JD only. Do not fabricate.
Output ONLY the JSON object, no other text.
"""

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def run(cv_text: str, jd_text: str) -> dict:
    """
    Run the Scorer sub-agent.

    Returns:
        The parsed score dict with keys: dimensions, overall_score, strengths, gaps, interview_likelihood
    """
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Here is the candidate's CV:\n\n{cv_text}\n\n"
                    f"Here is the job description:\n\n{jd_text}\n\n"
                    "Evaluate the fit and return the JSON score."
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "dimensions": [],
            "overall_score": 0,
            "strengths": [],
            "gaps": ["Score parsing failed — raw response stored"],
            "interview_likelihood": "MEDIUM",
            "raw": raw,
        }
