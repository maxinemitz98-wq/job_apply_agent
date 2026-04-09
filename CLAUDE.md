# Job Agent — Project Memory

## Stack
- Frontend: React 18 + Vite 5 + Tailwind CSS 3 (in /frontend)
- Backend: FastAPI async (in /backend)
- Agent runtime: Anthropic Claude Managed Agents API (`managed-agents-2026-04-01`)
- Python SDK: `anthropic` (standard SDK — NOT claude-agent-sdk which does not exist)

## Key conventions
- All agent definitions live in /backend/agents/
- All custom tools live in /backend/tools/
- FastAPI routers are thin — no business logic inside routers
- Use async/await everywhere in backend
- SSE is used for streaming agent progress to frontend via sse-starlette
- SQLite in dev, Postgres in prod (set via DATABASE_URL env var)

## Agent tool design rules
- NEVER use "read", "write", "edit" as tool names — those are Claude Code CLI tools, NOT Anthropic API tools
- CV text is always passed as message context, not fetched via a tool
- Custom tools must define a JSON schema and a corresponding async Python executor function
- Built-in Anthropic tools: web_search, web_fetch (available in researcher agent)
- Custom tools: cv_parser (utility fn only, not agent-called in Phase 1), document_export

## Environment variables needed
- ANTHROPIC_API_KEY
- DATABASE_URL (default: sqlite+aiosqlite:///./job_agent.db)
- STORAGE_PATH (local folder for CV uploads and outputs, default: ./storage)

## Test commands
- Backend: `cd backend && pytest`
- Frontend: `cd frontend && npm test`

## Phase notes
- Phase 1a: flat single-agent pipeline (sequential, standard anthropic SDK)
- Phase 1b: multi-agent via Managed Agents API (parallel sub-agent threads)
- Phase 2: application submission with human-in-the-loop approval flow
- Phase 3: profile_store persistence, analytics, email integration

## Do not touch
- /backend/agents/orchestrator.py without reviewing sub-agent coordination order
- /backend/tools/*.py schemas must match what is registered in agent definitions
