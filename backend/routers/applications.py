"""
Application routes:
  POST /apply                - Trigger the full agent pipeline
  GET  /apply/{session_id}  - Poll pipeline status
  GET  /applications        - List all applications
  GET  /applications/{id}   - Get application detail
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models.application import Application
from backend.models.candidate import Candidate
from backend.agents.orchestrator import run_pipeline
from backend.routers.stream import emit_event, close_session

router = APIRouter()


class ApplyRequest(BaseModel):
    jd_text: str
    company_name: str
    role_title: str
    cv_file_id: str
    user_notes: str | None = None


@router.post("/apply")
async def apply(
    body: ApplyRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Load CV
    candidate = await db.get(Candidate, body.cv_file_id)
    if candidate is None:
        raise HTTPException(404, "CV file not found. Upload a CV first.")

    session_id = str(uuid.uuid4())
    app_id = str(uuid.uuid4())

    application = Application(
        id=app_id,
        session_id=session_id,
        status="running",
        jd_text=body.jd_text,
        company_name=body.company_name,
        role_title=body.role_title,
        cv_file_id=body.cv_file_id,
        user_notes=body.user_notes,
    )
    db.add(application)
    await db.commit()

    background_tasks.add_task(
        _run_pipeline_bg,
        app_id=app_id,
        session_id=session_id,
        jd_text=body.jd_text,
        company_name=body.company_name,
        role_title=body.role_title,
        cv_text=candidate.parsed_text,
    )

    return {
        "session_id": session_id,
        "application_id": app_id,
        "status": "running",
        "stream_url": f"/api/stream/{session_id}",
    }


async def _run_pipeline_bg(
    app_id: str,
    session_id: str,
    jd_text: str,
    company_name: str,
    role_title: str,
    cv_text: str,
):
    """Background task: runs the pipeline and updates the DB when done."""
    from backend.db import AsyncSessionLocal

    async def emit(event: str, data: dict):
        await emit_event(session_id, event, data)

    try:
        outputs = await run_pipeline(
            jd_text=jd_text,
            company_name=company_name,
            role_title=role_title,
            cv_text=cv_text,
            session_id=session_id,
            emit=emit,
        )

        async with AsyncSessionLocal() as db:
            app = await db.get(Application, app_id)
            app.status = "ready"
            app.outputs = outputs
            app.completed_at = datetime.utcnow()
            await db.commit()

        await emit_event(session_id, "pipeline_complete", {"status": "ready"})

    except Exception as exc:
        async with AsyncSessionLocal() as db:
            app = await db.get(Application, app_id)
            app.status = "failed"
            app.error = str(exc)
            app.completed_at = datetime.utcnow()
            await db.commit()

        await emit_event(session_id, "pipeline_error", {"error": str(exc)})

    finally:
        await close_session(session_id)


@router.get("/apply/{session_id}")
async def get_apply_status(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Application).where(Application.session_id == session_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(404, "Session not found.")

    return {
        "application_id": app.id,
        "session_id": app.session_id,
        "status": app.status,
        "company_name": app.company_name,
        "role_title": app.role_title,
        "outputs": app.outputs if app.status == "ready" else None,
        "error": app.error,
        "created_at": app.created_at.isoformat(),
        "completed_at": app.completed_at.isoformat() if app.completed_at else None,
    }


@router.get("/applications")
async def list_applications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Application).order_by(Application.created_at.desc())
    )
    apps = result.scalars().all()
    return [
        {
            "id": a.id,
            "session_id": a.session_id,
            "status": a.status,
            "company_name": a.company_name,
            "role_title": a.role_title,
            "created_at": a.created_at.isoformat(),
        }
        for a in apps
    ]


@router.get("/applications/{app_id}")
async def get_application(app_id: str, db: AsyncSession = Depends(get_db)):
    app = await db.get(Application, app_id)
    if app is None:
        raise HTTPException(404, "Application not found.")

    return {
        "id": app.id,
        "session_id": app.session_id,
        "status": app.status,
        "company_name": app.company_name,
        "role_title": app.role_title,
        "jd_text": app.jd_text,
        "user_notes": app.user_notes,
        "outputs": app.outputs,
        "error": app.error,
        "created_at": app.created_at.isoformat(),
        "completed_at": app.completed_at.isoformat() if app.completed_at else None,
    }
