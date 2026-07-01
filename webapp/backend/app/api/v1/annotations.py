import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_doctor_or_admin
from app.db.models import Annotation, Case, User
from app.db.session import get_db
from app.schemas.annotations import (
    AnnotationCreateRequest,
    AnnotationResponse,
    AnnotationUpdateRequest,
    AnnotationZipImportResponse,
)
from app.services.annotation_import_service import AnnotationZipError, import_annotation_zip
from app.services.annotation_service import (
    accept_prediction,
    correct_annotation,
    create_manual_annotation,
    soft_delete_annotation,
)

router = APIRouter(tags=["annotations"])

_GEOMETRY_TYPES = ("bbox", "polygon")
_CLASS_TYPES = ("lesion", "organ")


def _get_case_or_404(db: Session, case_id: uuid.UUID) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case bulunamadı")
    return case


def _get_annotation_or_404(db: Session, annotation_id: uuid.UUID) -> Annotation:
    ann = db.get(Annotation, annotation_id)
    if ann is None:
        raise HTTPException(status_code=404, detail="Annotasyon bulunamadı")
    return ann


@router.post("/annotations/import-zip", response_model=AnnotationZipImportResponse)
async def import_annotations_zip(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_doctor_or_admin),
) -> dict:
    """`make_annotation_zip.py` ile üretilen bir annotation ZIP'ini içe aktarır
    (plan Bölüm 6: dışa/içe aktarma kaçış yolu — CLI script'iyle aynı mantık).
    ZIP'teki her case, mevcut vakaların `case_label` alanında aranarak eşleştirilir."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=422, detail="Sadece .zip yükleme desteklenir")
    data = await file.read()
    try:
        return import_annotation_zip(db, zip_bytes=data, actor=user)
    except AnnotationZipError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/cases/{case_id}/annotations", response_model=list[AnnotationResponse])
def list_annotations(
    case_id: uuid.UUID,
    image_id: int | None = Query(default=None),
    source: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Annotation]:
    _get_case_or_404(db, case_id)
    stmt = select(Annotation).where(Annotation.case_id == case_id, Annotation.status != "deleted")
    if image_id is not None:
        stmt = stmt.where(Annotation.image_id == image_id)
    if source is not None:
        stmt = stmt.where(Annotation.source == source)
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/cases/{case_id}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_annotation(
    case_id: uuid.UUID,
    payload: AnnotationCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_doctor_or_admin),
) -> Annotation:
    _get_case_or_404(db, case_id)
    if payload.geometry_type not in _GEOMETRY_TYPES:
        raise HTTPException(status_code=422, detail="geometry_type 'bbox' veya 'polygon' olmalı")
    if payload.class_type not in _CLASS_TYPES:
        raise HTTPException(status_code=422, detail="class_type 'lesion' veya 'organ' olmalı")
    return create_manual_annotation(
        db,
        case_id=case_id,
        actor=user,
        image_id=payload.image_id,
        class_type=payload.class_type,
        class_id=payload.class_id,
        geometry_type=payload.geometry_type,
        geometry=payload.geometry,
    )


@router.put("/annotations/{annotation_id}", response_model=AnnotationResponse)
def update_annotation(
    annotation_id: uuid.UUID,
    payload: AnnotationUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_doctor_or_admin),
) -> Annotation:
    original = _get_annotation_or_404(db, annotation_id)
    if original.status != "active":
        raise HTTPException(status_code=409, detail="Bu annotasyon artık aktif değil (silinmiş/superseded)")

    if original.source == "manual":
        # Doktorun kendi çizdiği bir annotasyonu düzenlemesi yeni bir zincir
        # başlatmaz — doğrudan günceller (henüz bir model tahmini değil).
        if payload.class_id is not None:
            original.class_id = payload.class_id
        if payload.geometry is not None:
            original.geometry = payload.geometry
        db.add(original)
        db.commit()
        db.refresh(original)
        return original

    return correct_annotation(
        db, original=original, actor=user, class_id=payload.class_id, geometry=payload.geometry
    )


@router.post("/annotations/{annotation_id}/accept", response_model=AnnotationResponse)
def accept(
    annotation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_doctor_or_admin)
) -> Annotation:
    ann = _get_annotation_or_404(db, annotation_id)
    if ann.source != "prediction":
        raise HTTPException(status_code=422, detail="Sadece source='prediction' kabul edilebilir")
    return accept_prediction(db, prediction=ann, actor=user)


@router.delete("/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_annotation(
    annotation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_doctor_or_admin)
) -> None:
    ann = _get_annotation_or_404(db, annotation_id)
    soft_delete_annotation(db, annotation=ann, actor=user)
