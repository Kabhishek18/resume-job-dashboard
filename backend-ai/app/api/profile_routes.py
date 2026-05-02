from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.profile import ProfileApiV1, UpdateResumeBody
from app.schemas.resume_extract import ExtractResumeFileApiV1
from app.services import resume_file_extract

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileApiV1)
def get_profile(current: User = Depends(get_current_user)) -> ProfileApiV1:
    return ProfileApiV1(
        id=current.id,
        email=current.email,  # type: ignore[arg-type]
        name=current.name,
        resume_text=current.resume_text,
        resume_updated_at=current.resume_updated_at,
    )


@router.post("/resume-upload", response_model=ExtractResumeFileApiV1)
async def resume_upload_extract(
    file: UploadFile = File(...),
    _current: User = Depends(get_current_user),
) -> ExtractResumeFileApiV1:
    """Multipart extract for PDF/DOCX/TXT; returns plain text for the editor only (does not persist)."""
    blob = await file.read()
    name = file.filename or "upload.bin"
    text, warns = resume_file_extract.extract_resume_plain_text(blob, name)
    return ExtractResumeFileApiV1(plain_text=text, warnings=warns)


@router.put("/resume", response_model=ProfileApiV1)
def update_saved_resume(
    body: UpdateResumeBody,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileApiV1:
    current.resume_text = body.resume_text.strip()
    current.resume_updated_at = datetime.now(timezone.utc)
    db.add(current)
    db.commit()
    db.refresh(current)
    return ProfileApiV1(
        id=current.id,
        email=current.email,  # type: ignore[arg-type]
        name=current.name,
        resume_text=current.resume_text,
        resume_updated_at=current.resume_updated_at,
    )
