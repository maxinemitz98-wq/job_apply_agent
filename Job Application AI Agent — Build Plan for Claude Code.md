# Job Application AI Agent — Build Plan for Claude Code

> **Purpose of this document:** A structured build specification to feed directly into Claude Code. It defines the product, architecture, frontend, backend, agent design, data flows, and phased implementation plan for an AI-powered job application assistant built on Claude Managed Agents.

***

## 1. Product Overview

### What we are building

A personal job application assistant that takes a job description (JD) and an existing CV as inputs, and outputs:

1. A tailored, updated CV aligned to the JD
2. A company research brief
3. A personalised motivation letter
4. An interview likelihood / fit score with reasoning
5. (Phase 2) A drafted or submitted application

The app has a clean React frontend and a Python FastAPI backend. The backend delegates all AI work to a multi-agent pipeline built on **Anthropic Claude Managed Agents** (`managed-agents-2026-04-01`).

### Who it is for

A single user (personal tool) or a small team. Not a multi-tenant SaaS at first. Authentication is simple (single API key or basic login).

***

## 2. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend | React + Vite + Tailwind CSS | Fast to scaffold in Claude Code; clean component structure |
| Backend | Python FastAPI | Async-native, pairs well with the Python Claude Agent SDK[^1] |
| Agent runtime | Anthropic Claude Managed Agents API + `claude_agent_sdk` | Built-in sessions, harness, tools, sandboxed execution |
| File storage | Local filesystem (Phase 1), S3-compatible (Phase 2) | CV and output documents need persistence across sessions |
| Database | SQLite (Phase 1), Postgres (Phase 2) | Track applications, sessions, scores |
| PDF/DOCX parsing | `pdfplumber`, `python-docx` | Extract structured text from uploaded CVs |

***

## 3. Repository Structure

Claude Code should scaffold the following directory layout:

```
job-agent/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadPanel.jsx         # CV + JD upload
│   │   │   ├── OutputPanel.jsx         # Tailored CV, letter, research
│   │   │   ├── FitScore.jsx            # Interview likelihood display
│   │   │   ├── ApplicationTracker.jsx  # Track all applications
│   │   │   └── StatusStream.jsx        # Live SSE stream of agent steps
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   └── ApplicationDetail.jsx
│   │   ├── api/
│   │   │   └── client.js               # Axios wrapper to FastAPI
│   │   └── App.jsx
│   ├── index.html
│   └── vite.config.js
│
├── backend/
│   ├── main.py                         # FastAPI entry point
│   ├── routers/
│   │   ├── applications.py             # POST /apply, GET /applications
│   │   ├── documents.py                # Upload CV, parse JD
│   │   └── stream.py                   # SSE stream endpoint
│   ├── agents/
│   │   ├── orchestrator.py             # Master agent: routes tasks
│   │   ├── cv_tailor.py                # Sub-agent: CV rewrite
│   │   ├── researcher.py               # Sub-agent: company research
│   │   ├── letter_writer.py            # Sub-agent: motivation letter
│   │   ├── scorer.py                   # Sub-agent: fit scoring
│   │   └── apply_agent.py              # Sub-agent: application submission (Phase 2)
│   ├── tools/
│   │   ├── cv_parser.py                # Custom tool: parse uploaded PDF/DOCX
│   │   ├── profile_store.py            # Custom tool: read/write candidate profile
│   │   ├── document_export.py          # Custom tool: export DOCX/PDF output
│   │   └── apply_submit.py             # Custom tool: submit via API or browser (Phase 2)
│   ├── models/
│   │   ├── application.py              # SQLAlchemy models
│   │   └── candidate.py
│   ├── db.py
│   └── config.py                       # API keys, model names, env vars
│
├── CLAUDE.md                           # Project memory file for Claude Code sessions
├── plan.md                             # This document (living spec)
└── .env.example
```

***

## 4. CLAUDE.md File (Project Memory)

Claude Code uses `CLAUDE.md` to keep project conventions persistent across sessions. Create this file in the root immediately.[^2][^3]

```markdown
# Job Agent — Project Memory

## Stack
- Frontend: React + Vite + Tailwind (in /frontend)
- Backend: FastAPI async (in /backend)
- Agent runtime: Anthropic Claude Managed Agents API (`managed-agents-2026-04-01`)
- Python SDK: `claude_agent_sdk`

## Key conventions
- All agent definitions live in /backend/agents/
- All custom tools live in /backend/tools/
- FastAPI routers are thin — no business logic inside routers
- Use async/await everywhere in backend
- SSE is used for streaming agent progress to frontend
- SQLite in dev, Postgres in prod (set via DATABASE_URL env var)

## Environment variables needed
- ANTHROPIC_API_KEY
- DATABASE_URL
- STORAGE_PATH (local folder for CV uploads and outputs)

## Test commands
- Backend: `cd backend && pytest`
- Frontend: `cd frontend && npm test`

## Do not touch
- /backend/agents/orchestrator.py without updating callable_agents list
- /backend/tools/*.py must follow the custom tool contract (see agents/README.md)
```

***

## 5. Agent Architecture

### Design: Orchestrator + 4 Specialist Sub-agents

The Managed Agents API supports multi-agent orchestration where one coordinator agent delegates to specialist sub-agents, each running in their own isolated context thread. Each sub-agent has its own system prompt, tool access, and context — they do not share state directly.[^4]

```
                        ┌─────────────────────────────────────┐
                        │         ORCHESTRATOR AGENT           │
                        │  - Parses inputs                     │
                        │  - Routes to sub-agents              │
                        │  - Collects + assembles outputs      │
                        └──────┬──────┬──────┬──────┬──────────┘
                               │      │      │      │
               ┌───────────────┘      │      │      └───────────────┐
               ▼                      ▼      ▼                       ▼
    ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  CV TAILOR AGENT │  │  RESEARCHER  │  │LETTER WRITER │  │    SCORER    │
    │                  │  │    AGENT     │  │    AGENT     │  │    AGENT     │
    │ - Read old CV    │  │              │  │              │  │              │
    │ - Read JD        │  │ - web_search │  │ - Read JD    │  │ - Read JD    │
    │ - Edit & rewrite │  │ - web_fetch  │  │ - Read CV    │  │ - Read CV    │
    │ - Export DOCX    │  │ - Write brief│  │ - Write draft│  │ - Rubric eval│
    └──────────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

This pattern is recommended by Anthropic for parallelisable specialised tasks. The researcher and CV tailor can run in parallel; the letter writer and scorer depend on CV tailor output and should run after.[^5][^4]

### Agent Definitions (pseudo-code — Claude Code will implement)

#### Orchestrator

```python
# backend/agents/orchestrator.py
ORCHESTRATOR_SYSTEM = """
You are a job application coordinator. You receive a job description and a candidate CV.
Your job is to:
1. Delegate CV tailoring to the cv_tailor agent
2. Delegate company + role research to the researcher agent (run in parallel with CV tailoring)
3. Once CV is ready, delegate motivation letter writing to the letter_writer agent
4. Delegate fit scoring to the scorer agent (can run in parallel with letter writing)
5. Collect all outputs and return a structured JSON summary

Always confirm before submitting any application. Never submit without explicit user approval.
"""
```

#### CV Tailor Sub-agent

```python
# backend/agents/cv_tailor.py
CV_TAILOR_SYSTEM = """
You are an expert CV editor. You receive a candidate's existing CV and a job description.
Your job is to:
- Rewrite and tailor the CV to maximise alignment with the JD
- Keep the candidate's authentic experience — never invent facts
- Prioritise skills, achievements, and language from the JD
- Output a clean structured CV in markdown, then export to DOCX using the document_export tool
- Focus on: skill keywords, seniority alignment, sector framing, measurable achievements
"""

CV_TAILOR_TOOLS = ["read", "write", "edit", "document_export"]  # document_export is a custom tool
```

#### Researcher Sub-agent

```python
# backend/agents/researcher.py
RESEARCHER_SYSTEM = """
You are a company and market research specialist.
You receive a company name and job title.
Your job is to:
- Research the company: strategy, recent news, culture, key people, competitive position
- Research the role: what the hiring manager cares about, what success looks like
- Produce a structured 1-page brief the candidate can use for interview prep
- Use web_search and web_fetch for fresh data. Prioritise sources from the past 6 months.
Output format: markdown with sections: Company Overview, Recent News, Role Context, Key People, Prep Tips
"""

RESEARCHER_TOOLS = ["web_search", "web_fetch", "write"]
```

#### Letter Writer Sub-agent

```python
# backend/agents/letter_writer.py
LETTER_WRITER_SYSTEM = """
You are a professional career writer specialising in motivation and cover letters.
You receive a tailored CV and a job description.
Your job is to:
- Write a concise, compelling motivation letter (max 4 paragraphs, max 350 words)
- Connect the candidate's background explicitly to the role's needs
- Open with a strong hook, not a cliché
- Close with a confident, specific call to action
- Tone: professional but human. Never generic.
- Export the final letter using the document_export tool
"""

LETTER_WRITER_TOOLS = ["read", "write", "edit", "document_export"]
```

#### Scorer Sub-agent

```python
# backend/agents/scorer.py
SCORER_SYSTEM = """
You are a hiring process analyst. You assess how well a candidate profile matches a job description.
Evaluate on these dimensions (score each 1-5):
1. Skills & technical match (keywords, tools, certifications)
2. Seniority & experience match (years, scope, complexity)
3. Sector / domain fit (industry, asset class, client type)
4. Language & communication fit
5. Credential match (degree, licenses)
6. Location & logistics fit

Output:
- Dimension scores with brief explanation
- Overall weighted score (out of 10)
- Top 3 strengths for this application
- Top 3 gaps to address in the cover letter or interview
- Interview likelihood label: LOW / MEDIUM / HIGH / STRONG

Do not fabricate statistical probabilities. Base scoring on explicit evidence in the CV and JD only.
"""

SCORER_TOOLS = ["read"]  # read-only; scorer does not write files
```

***

## 6. Custom Tool Contracts

Custom tools extend Claude beyond built-in capabilities. Your application executes the tool; Claude emits a structured call and waits for the result. Define these tools clearly in the agent configuration and implement the execution logic in `/backend/tools/`.

### `cv_parser` — Parse uploaded CV

```json
{
  "type": "custom",
  "name": "cv_parser",
  "description": "Parses a PDF or DOCX CV file uploaded by the user and returns structured text including work history, education, skills, and languages. Use this at the start of every session to extract the candidate's profile. Input: file_path to the uploaded CV.",
  "input_schema": {
    "type": "object",
    "properties": {
      "file_path": { "type": "string", "description": "Absolute path to the uploaded CV file (PDF or DOCX)" }
    },
    "required": ["file_path"]
  }
}
```

**Backend implementation:** uses `pdfplumber` (PDF) or `python-docx` (DOCX) to extract text, then returns structured JSON.

### `document_export` — Export CV or letter to DOCX

```json
{
  "type": "custom",
  "name": "document_export",
  "description": "Exports a markdown document to a formatted DOCX or PDF file. Use this after writing the tailored CV or motivation letter. Returns the file path of the exported file.",
  "input_schema": {
    "type": "object",
    "properties": {
      "content": { "type": "string", "description": "Markdown content to export" },
      "doc_type": { "type": "string", "enum": ["cv", "letter", "research_brief"], "description": "Document type — affects formatting template used" },
      "filename": { "type": "string", "description": "Output filename without extension" }
    },
    "required": ["content", "doc_type", "filename"]
  }
}
```

**Backend implementation:** uses `python-docx` with a branded template. Outputs to `STORAGE_PATH/{session_id}/`.

### `profile_store` — Read/write candidate profile

```json
{
  "type": "custom",
  "name": "profile_store",
  "description": "Reads or writes the candidate's normalised profile (structured JSON). Use read at the start of each agent run to load existing profile context. Use write to update profile after CV parsing. This persists the candidate's master profile across sessions.",
  "input_schema": {
    "type": "object",
    "properties": {
      "action": { "type": "string", "enum": ["read", "write"] },
      "profile": { "type": "object", "description": "Profile JSON — required when action is write" }
    },
    "required": ["action"]
  }
}
```

***

## 7. API Endpoints (FastAPI Backend)

```
POST   /api/upload/cv              Upload CV file → returns file_path
POST   /api/apply                  Trigger full agent pipeline → returns session_id
GET    /api/apply/{session_id}     Poll status and collect outputs
GET    /api/stream/{session_id}    SSE stream of agent progress events
GET    /api/applications           List all past applications
GET    /api/applications/{id}      Get application detail (CV, letter, score, brief)
POST   /api/applications/{id}/submit   Approve and submit application (Phase 2)
```

### `/api/apply` Request Body

```json
{
  "jd_text": "Full text of the job description...",
  "company_name": "Julius Baer",
  "role_title": "Relationship Manager",
  "cv_file_id": "abc123",
  "user_notes": "Optional notes — e.g. emphasise German language skills"
}
```

### `/api/apply` Response

```json
{
  "session_id": "sess_xyz789",
  "status": "running",
  "stream_url": "/api/stream/sess_xyz789"
}
```

***

## 8. Frontend Pages and Components

### Dashboard (`/`)

- Left panel: Upload CV (drag-and-drop), paste JD text, optional notes field
- Right panel: Past applications list with status chips (PROCESSING / READY / SUBMITTED)
- "Run Agent" button → POSTs to `/api/apply`, then opens Application Detail

### Application Detail (`/application/:id`)

Four output tabs:

| Tab | Content |
|---|---|
| **Tailored CV** | Markdown preview + DOCX download button |
| **Company Brief** | Markdown research brief |
| **Motivation Letter** | Editable text + DOCX download button |
| **Fit Score** | Dimension scores (radar or bar chart), overall score, strengths, gaps, likelihood label |

- Status stream bar at top: shows live agent steps as SSE events arrive[^6]
- "Approve & Submit" button (Phase 2): triggers `/api/applications/{id}/submit` after confirmation modal

### StatusStream Component

Connects to `/api/stream/{session_id}` via EventSource. Displays:
- Which sub-agent is currently running (CV Tailor / Researcher / etc.)
- Tool calls being made (web_search query, document_export call)
- Completion status per sub-agent
- Total estimated cost (from Managed Agents session billing)

***

## 9. Data Flow — Full Request Lifecycle

```
User uploads CV + pastes JD
        │
        ▼
FastAPI POST /api/apply
        │
        ├── cv_parser tool runs → structured profile JSON
        │
        ▼
Orchestrator Agent session created (Managed Agents API)
        │
        ├── [parallel] CV Tailor thread starts
        │       ├── reads CV text
        │       ├── reads JD
        │       ├── rewrites CV
        │       └── calls document_export → cv_tailored.docx
        │
        ├── [parallel] Researcher thread starts
        │       ├── web_search: company name + news
        │       ├── web_fetch: company website, LinkedIn, news
        │       └── writes research_brief.md
        │
        ├── [sequential, waits for CV Tailor] Letter Writer thread
        │       ├── reads tailored CV
        │       ├── reads JD + research brief
        │       ├── writes motivation letter
        │       └── calls document_export → motivation_letter.docx
        │
        └── [sequential, waits for CV Tailor] Scorer thread
                ├── reads tailored CV
                ├── reads JD
                └── outputs fit_score.json

Orchestrator collects all outputs
        │
        ▼
FastAPI stores results in DB + filesystem
        │
        ▼
SSE stream notifies frontend → outputs render in tabs
```

***

## 10. Permissions and Safety Design

Following Anthropic's guidance on agentic permissions:

| Action | Permission mode | Rationale |
|---|---|---|
| Read files | Auto-allow | Necessary for agent reasoning |
| Write/edit files within session folder | Auto-allow | CV and letter outputs are expected |
| Web search / web fetch | Auto-allow | Core to researcher functionality |
| Bash commands | Restricted (disabled in sub-agents) | Only enabled in specific tools via custom tool contract |
| Application submission | `always_ask` — requires explicit user approval | High-stakes irreversible action |
| Login to external services | Not used in Phase 1 | Phase 2 only, with sandboxed browser |

The `always_ask` mode on submission means the agent will pause and surface a confirmation event to the frontend before proceeding. The frontend shows a modal; the user approves; the backend sends `user.tool_confirmation` back to the session stream.[^4]

***

## 11. Build Phases

### Phase 1 — Core pipeline (build this first)

- [ ] Scaffold repo, install deps, set up CLAUDE.md
- [ ] FastAPI app with upload, apply, stream endpoints
- [ ] CV parser custom tool (PDF + DOCX)
- [ ] Orchestrator agent definition (no sub-agents yet — flat single agent)
- [ ] CV Tailor sub-agent + document_export custom tool
- [ ] Researcher sub-agent (web search + web fetch)
- [ ] Letter Writer sub-agent
- [ ] Scorer sub-agent + fit score JSON schema
- [ ] React frontend: upload panel, status stream, 4-tab output view
- [ ] SQLite persistence for applications

### Phase 2 — Application submission (build after Phase 1 is stable)

- [ ] `apply_submit` custom tool: integrate with Greenhouse API / Lever API for direct API-based submission
- [ ] Browser automation fallback for portals without API (sandboxed Playwright instance)
- [ ] `always_ask` confirmation flow in frontend (approval modal)
- [ ] Application status tracking (submitted / response / interview / rejected)

### Phase 3 — Quality and scale

- [ ] Candidate profile store (persist structured profile across sessions, avoid re-parsing every time)
- [ ] Application history analytics (response rate, score calibration)
- [ ] CV version history per application
- [ ] Email integration: parse JD from email, trigger pipeline automatically

***

## 12. Key Dependencies

```toml
# backend/pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.111"
uvicorn = "^0.29"
claude-agent-sdk = "*"          # Anthropic Claude Agent SDK
anthropic = "*"                  # Anthropic Messages API (for non-agent calls)
pdfplumber = "^0.11"
python-docx = "^1.1"
sqlalchemy = "^2.0"
aiosqlite = "^0.20"
sse-starlette = "^2.1"          # SSE streaming
python-multipart = "^0.0.9"     # File uploads
```

```json
// frontend/package.json dependencies
{
  "react": "^18",
  "vite": "^5",
  "tailwindcss": "^3",
  "@headlessui/react": "^2",
  "axios": "^1.6",
  "react-markdown": "^9",
  "recharts": "^2"
}
```

***

## 13. First Prompt to Give Claude Code

Once this file is saved as `plan.md` in the project root, start Claude Code with:

```
Read plan.md fully before writing any code.
Do not start implementing yet.
Give me your understanding of the architecture, flag any gaps or questions, then wait for my go-ahead.
Start with Phase 1 only.
First task: scaffold the repository structure exactly as defined in Section 3,
create the CLAUDE.md file from Section 4, and set up the FastAPI app skeleton in backend/main.py with all routers registered but no logic yet.
```

This follows the recommended "plan → verify → implement" workflow for Claude Code to avoid rework.[^3][^7][^2]

***

## 14. Costs to Expect

| Component | Pricing |
|---|---|
| Claude Managed Agents token usage | Standard Claude Platform token rates |
| Active session runtime | $0.08 per session-hour |
| Per-application estimate (Phase 1) | ~$0.10–0.30 per full pipeline run (4 sub-agents, web research) |
| Web search tool calls | Included in token pricing |

Multi-agent coordination (research preview) requires separate access request from Anthropic. Single-agent flat mode works without it and is recommended for Phase 1.[^4]

---

## References

1. [Work with sessions - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/sessions) - This guide covers how to pick the right approach for your app, the SDK interfaces that track session...

2. [Claude Code Best Practices: Planning, Context Transfer, TDD](https://www.datacamp.com/tutorial/claude-code-best-practices) - Learn Claude Code best practices from production teams. Use plan mode, CLAUDE.md files, and test-dri...

3. [7 Claude Code best practices for 2026 (from real projects) - eesel AI](https://www.eesel.ai/blog/claude-code-best-practices) - 1. Master the CLAUDE.md file for project memory · 2. Get into a 'plan, then execute' workflow · 3. G...

4. [Multiagent sessions - Claude API Docs](https://platform.claude.com/docs/en/managed-agents/multi-agent) - Multi-agent orchestration lets one agent coordinate with others ... Session threads are where you dr...

5. [[PDF] Building Effective AI Agents: Architecture Patterns and ... - Anthropic](https://resources.anthropic.com/hubfs/Building%20Effective%20AI%20Agents-%20Architecture%20Patterns%20and%20Implementation%20Frameworks.pdf) - Claude Sonnet's gains come from "consistency over large tasks and documents and accurately following...

6. [Built open source platform for running multiple Claude Agents in ...](https://www.reddit.com/r/AI_Agents/comments/1oj7n1w/built_open_source_platform_for_running_multiple/) - Session isolation: Each conversation gets its own Docker container that stays alive for the entire s...

7. [Plan Mode & Thinking Strategies - Elegant Software Solutions](https://www.elegantsoftwaresolutions.com/blog/claude-code-mastery-plan-mode-thinking) - Master Claude Code's thinking modes and the explore-plan-code-commit workflow. Learn context managem...

