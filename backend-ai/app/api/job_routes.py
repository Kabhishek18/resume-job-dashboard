from fastapi import APIRouter

from app.services.job_import import ImportPreviewApiV1, ImportPreviewRequest, fetch_import_preview

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/import-preview", response_model=ImportPreviewApiV1)
def import_preview(body: ImportPreviewRequest) -> ImportPreviewApiV1:
    return fetch_import_preview(str(body.url))
