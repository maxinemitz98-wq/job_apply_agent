"""
CV parser utility — runs before the agent session, NOT called as an agent tool.
Parses PDF or DOCX files and returns structured text.
"""
import io
from pathlib import Path


async def parse_cv(file_path: str) -> dict:
    """
    Parse a PDF or DOCX CV file and return structured text.

    Returns:
        {"raw_text": str, "file_type": str}
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return await _parse_pdf(path)
    elif suffix in (".docx", ".doc"):
        return await _parse_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Upload a PDF or DOCX file.")


async def _parse_pdf(path: Path) -> dict:
    import pdfplumber

    text_parts = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    raw_text = "\n\n".join(text_parts)
    if not raw_text.strip():
        raise ValueError("Could not extract text from PDF. The file may be scanned/image-based.")

    return {"raw_text": raw_text, "file_type": "pdf"}


async def _parse_docx(path: Path) -> dict:
    from docx import Document

    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    raw_text = "\n".join(paragraphs)

    if not raw_text.strip():
        raise ValueError("Could not extract text from DOCX. The file may be empty.")

    return {"raw_text": raw_text, "file_type": "docx"}
