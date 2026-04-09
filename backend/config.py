import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./job_agent.db")
STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "./storage"))
STORAGE_PATH.mkdir(parents=True, exist_ok=True)

ANTHROPIC_MODEL = "claude-sonnet-4-6"
MANAGED_AGENTS_VERSION = "managed-agents-2026-04-01"
