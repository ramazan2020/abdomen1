import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin, require_doctor_or_admin
from app.db.models import (
    Annotation, AnnotationAuditLog, AnnotationGroup,
    Case, CaseSlice, ClassificationPrediction, Dataset,
    DataAccessLog, InferenceBatch, InferenceRun, User,
)
from app.db.session import get_db
from app.schemas.cases import CaseListItem, CaseResponse, ReviewStatusUpdateRequest
from app.schemas.datasets import DatasetAssignRequest
from app.services.dicom_ingest import ingest_case
from app.services.job_queue import get_queue
from app.services.png_cache_service import get_or_generate_png_bytes
from app.services.storage_service import get_storage_backend

router = APIRouter(prefix="/cases", tags=["cases"])

_REVIEW_STATUSES = ("unreviewed", "in_review", "reviewed", "approved_for_training", "excluded")
_DOCTOR_ALLOWED_TRANSITIONS = {"unreviewed", "in_review", "reviewed"}


@router.post("/upload", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def upload_case(
    file: UploadFile = File(...),
    case_label: str | None = Form(default=None),
    dataset_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_doctor_or_admin),
) -> Case:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=422, detail="Sadece .zip yükleme desteklenir")

    ds_id: uuid.UUID | None = None
    if dataset_id:
        ds_id = uuid.UUID(dataset_id)
        if db.get(Dataset, ds_id) is None:
            raise HTTPException(status_code=404, detail="Veri seti bulunamadı")

    case = Case(case_label=case_label, uploaded_by=user.id, storage_key="", status="uploaded", dataset_id=ds_id)
    db.add(case)
    db.commit()
    db.refresh(case)

    # Gerçek depolama önekini case.id bilindikten sonra ayarla (DB hiçbir zaman ham
    # dosya yolu tutmaz — sadece bu key, StorageBackend üzerinden çözümlenir).
    case.storage_key = f"cases/{case.id}/dicom"
    db.add(case)

    storage = get_storage_backend()
    data = await file.read()
    storage.save(f"uploads/{case.id}.zip", data)
    db.commit()
    db.refresh(case)

    # Arka planda ingest job'ı (plan Bölüm 1/4: RQ üzerinden, lazy PNG cache ile)
    get_queue().enqueue(ingest_case, str(case.id))

    return case


@router.get("", response_model=list[CaseListItem])
def list_cases(
    review_status: str | None = Query(default=None),
    dataset_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Case]:
    stmt = select(Case).order_by(Case.created_at.desc())
    if review_status:
        if review_status not in _REVIEW_STATUSES:
            raise HTTPException(status_code=422, detail="Geçersiz review_status")
        stmt = stmt.where(Case.review_status == review_status)
    if dataset_id:
        stmt = stmt.where(Case.dataset_id == uuid.UUID(dataset_id))
    return list(db.execute(stmt).scalars().all())


def _get_case_or_404(db: Session, case_id: uuid.UUID) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case bulunamadı")
    return case


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Case:
    case = _get_case_or_404(db, case_id)
    db.add(DataAccessLog(user_id=user.id, case_id=case.id, patient_id=case.patient_id, action="view"))
    db.commit()
    return case


@router.patch("/{case_id}/review-status", response_model=CaseResponse)
def update_review_status(
    case_id: uuid.UUID,
    payload: ReviewStatusUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_doctor_or_admin),
) -> Case:
    if payload.review_status not in _REVIEW_STATUSES:
        raise HTTPException(status_code=422, detail="Geçersiz review_status")

    # Plan Bölüm 2: approved_for_training/excluded kararı admin-only (QA kontrol noktası)
    if payload.review_status in ("approved_for_training", "excluded") and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="'approved_for_training'/'excluded' sadece admin tarafından ayarlanabilir",
        )

    case = _get_case_or_404(db, case_id)
    case.review_status = payload.review_status
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("/{case_id}/slices")
def list_slices(case_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[dict]:
    _get_case_or_404(db, case_id)
    stmt = select(CaseSlice).where(CaseSlice.case_id == case_id).order_by(CaseSlice.z_index)
    rows = db.execute(stmt).scalars().all()
    return [{"image_id": r.image_id, "z_index": r.z_index, "png_ready": r.png_storage_key is not None} for r in rows]


@router.get("/{case_id}/slices/{image_id}/png")
def get_slice_png(
    case_id: uuid.UUID, image_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> Response:
    case_slice = (
        db.execute(
            select(CaseSlice).where(CaseSlice.case_id == case_id, CaseSlice.image_id == image_id)
        )
        .scalars()
        .first()
    )
    if case_slice is None:
        raise HTTPException(status_code=404, detail="Dilim bulunamadı")
    png_bytes = get_or_generate_png_bytes(db, case_slice)
    return Response(content=png_bytes, media_type="image/png")


@router.patch("/{case_id}/dataset", response_model=CaseResponse)
def assign_dataset(
    case_id: uuid.UUID,
    payload: DatasetAssignRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_doctor_or_admin),
) -> Case:
    case = _get_case_or_404(db, case_id)
    if payload.dataset_id:
        ds_id = uuid.UUID(payload.dataset_id)
        if db.get(Dataset, ds_id) is None:
            raise HTTPException(status_code=404, detail="Veri seti bulunamadı")
        case.dataset_id = ds_id
    else:
        case.dataset_id = None
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(require_doctor_or_admin)) -> None:
    """KVKK Bölüm 3: kalıcı silme — doktor ve admin yetkilidir.
    Storage + tüm ilişkili DB satırları (annotations, audit log, inference, erişim log)
    doğru FK sırasıyla temizlenir."""
    case = _get_case_or_404(db, case_id)
    storage = get_storage_backend()

    # 1. Storage dosyalarını temizle (case_slices üzerinden)
    for cs in db.execute(select(CaseSlice).where(CaseSlice.case_id == case_id)).scalars().all():
        for key in (cs.dicom_storage_key, cs.png_storage_key):
            if key:
                try:
                    storage.delete(key)
                except Exception:
                    pass  # Storage'da yoksa sessizce geç

    # 2. FK sırasına göre ilişkili tablolar
    # 2a. Annotation audit log (annotations'a FK)
    ann_ids = db.execute(
        select(Annotation.id).where(Annotation.case_id == case_id)
    ).scalars().all()
    if ann_ids:
        db.execute(delete(AnnotationAuditLog).where(AnnotationAuditLog.annotation_id.in_(ann_ids)))

    # 2b. Annotations ve annotation_groups
    db.execute(delete(Annotation).where(Annotation.case_id == case_id))
    db.execute(delete(AnnotationGroup).where(AnnotationGroup.case_id == case_id))
    db.execute(delete(ClassificationPrediction).where(ClassificationPrediction.case_id == case_id))

    # 2c. Inference runs -> batches
    batch_ids = db.execute(
        select(InferenceBatch.id).where(InferenceBatch.case_id == case_id)
    ).scalars().all()
    if batch_ids:
        db.execute(delete(InferenceRun).where(InferenceRun.batch_id.in_(batch_ids)))
    db.execute(delete(InferenceBatch).where(InferenceBatch.case_id == case_id))

    # 2d. CaseSlices ve erişim logu
    db.execute(delete(CaseSlice).where(CaseSlice.case_id == case_id))
    db.execute(delete(DataAccessLog).where(DataAccessLog.case_id == case_id))

    # 3. Case kendisi
    db.delete(case)
    db.commit()
