import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import STORAGE_PATH
from backend.db import get_db
from backend.models.candidate import Candidate
from backend.tools.cv_parser import parse_cv

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload/cv")
async def upload_cv(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{suffix}'. Upload PDF or DOCX.")

    file_id = str(uuid.uuid4())
    dest_dir = STORAGE_PATH / file_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file.filename

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large. Maximum size is 10 MB.")

    dest_path.write_bytes(content)

    try:
        parsed = await parse_cv(str(dest_path))
    except ValueError as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(422, str(e))

    candidate = Candidate(
        id=file_id,
        original_filename=file.filename,
        storage_path=str(dest_path),
        parsed_text=parsed["raw_text"],
    )
    db.add(candidate)
    await db.commit()

    return {"cv_file_id": file_id, "filename": file.filename}
