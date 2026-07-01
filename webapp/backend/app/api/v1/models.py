import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import require_admin
from app.db.models import ModelOutput, ModelVersion, User
from app.db.session import get_db
from app.schemas.models import ModelOutputCreateRequest, ModelVersionResponse
from app.services.storage_service import get_storage_backend

router = APIRouter(prefix="/models", tags=["models"])

_ARCHITECTURES = (
    "yolo_det", "yolo_seg", "rfdetr", "dfine", "nnunet", "mednext",
    "organ_bag_transformer", "cls_timm",
)
_OUTPUT_TYPES = ("bbox", "mask", "classification")


def _get_model_or_404(db: Session, model_id: uuid.UUID) -> ModelVersion:
    stmt = (
        select(ModelVersion)
        .options(selectinload(ModelVersion.outputs))
        .where(ModelVersion.id == model_id)
    )
    model = db.execute(stmt).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Model bulunamadı")
    return model


@router.get("", response_model=list[ModelVersionResponse])
def list_models(
    status_filter: str | None = None,
    architecture: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
) -> list[ModelVersion]:
    stmt = select(ModelVersion).options(selectinload(ModelVersion.outputs)).order_by(ModelVersion.created_at.desc())
    if status_filter:
        stmt = stmt.where(ModelVersion.status == status_filter)
    if architecture:
        stmt = stmt.where(ModelVersion.architecture == architecture)
    return list(db.execute(stmt).scalars().all())


@router.get("/active", response_model=list[ModelVersionResponse])
def list_active_models(db: Session = Depends(get_db)) -> list[ModelVersion]:
    """Doktorun model seçici dropdown'u için — RBAC'sız, sadece aktif modeller
    (plan Bölüm 4: `status='active'` olan model_versions doktor tarafına açık)."""
    stmt = (
        select(ModelVersion)
        .options(selectinload(ModelVersion.outputs))
        .where(ModelVersion.status == "active")
        .order_by(ModelVersion.run_mode, ModelVersion.name)
    )
    return list(db.execute(stmt).scalars().all())


@router.get("/{model_id}", response_model=ModelVersionResponse)
def get_model(model_id: uuid.UUID, db: Session = Depends(get_db), _admin: User = Depends(require_admin)) -> ModelVersion:
    return _get_model_or_404(db, model_id)


@router.post("/register", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    file: UploadFile = File(...),
    name: str = Form(...),
    architecture: str = Form(...),
    run_mode: str = Form(default="comparison"),
    base_weights: str | None = Form(default=None),
    outputs_json: str = Form(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ModelVersion:
    """Kaggle/Colab'da eğitilmiş ağırlıkları manuel kaydetme (plan Bölüm 4 —
    eğitim job sistemi tam devreye girene kadar geçiş yolu, Faz 3+'ta da kalıcı
    kullanılacak bir yol). `outputs_json`, ModelOutputCreateRequest listesinin
    JSON serileştirmesidir (örn. OrganBagTransformer için 2 eleman: bbox +
    classification)."""
    if architecture not in _ARCHITECTURES:
        raise HTTPException(status_code=422, detail=f"architecture şunlardan biri olmalı: {_ARCHITECTURES}")
    if run_mode not in ("default", "comparison"):
        raise HTTPException(status_code=422, detail="run_mode 'default' veya 'comparison' olmalı")

    try:
        outputs_raw = json.loads(outputs_json)
        outputs = [ModelOutputCreateRequest(**o) for o in outputs_raw]
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"outputs_json geçersiz: {exc}") from exc
    if not outputs:
        raise HTTPException(status_code=422, detail="En az bir model_output tanımlanmalı")
    for o in outputs:
        if o.output_type not in _OUTPUT_TYPES:
            raise HTTPException(status_code=422, detail=f"output_type şunlardan biri olmalı: {_OUTPUT_TYPES}")

    model = ModelVersion(
        name=name, architecture=architecture, run_mode=run_mode,
        base_weights=base_weights, status="inactive",
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    storage = get_storage_backend()
    data = await file.read()
    weights_key = f"models/{model.id}/{file.filename or 'weights.pt'}"
    storage.save(weights_key, data)
    model.weights_storage_key = weights_key

    for o in outputs:
        db.add(ModelOutput(
            model_version_id=model.id, output_type=o.output_type,
            class_set=o.class_set, postprocess_config=o.postprocess_config,
        ))

    db.add(model)
    db.commit()
    return _get_model_or_404(db, model.id)


@router.post("/{model_id}/activate", response_model=ModelVersionResponse)
def activate_model(model_id: uuid.UUID, db: Session = Depends(get_db), _admin: User = Depends(require_admin)) -> ModelVersion:
    model = _get_model_or_404(db, model_id)
    model.status = "active"
    db.add(model)
    db.commit()
    return _get_model_or_404(db, model_id)


@router.post("/{model_id}/deactivate", response_model=ModelVersionResponse)
def deactivate_model(model_id: uuid.UUID, db: Session = Depends(get_db), _admin: User = Depends(require_admin)) -> ModelVersion:
    model = _get_model_or_404(db, model_id)
    model.status = "inactive"
    db.add(model)
    db.commit()
    return _get_model_or_404(db, model_id)
