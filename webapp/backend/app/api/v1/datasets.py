"""Veri seti yönetimi API (plan Bölüm 10, Faz 4b).

Endpoint'ler:
  POST   /datasets          — oluştur (admin)
  GET    /datasets          — liste (tüm roller)
  GET    /datasets/{id}     — detay + vaka sayısı
  DELETE /datasets/{id}     — sil; bağlı vakalar dataset_id=NULL (admin)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_admin
from app.db.models import Case, Dataset, User
from app.schemas.datasets import DatasetCreateRequest, DatasetDto

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _dto(ds: Dataset, case_count: int) -> DatasetDto:
    return DatasetDto(
        id=str(ds.id),
        name=ds.name,
        description=ds.description,
        source=ds.source,
        notes=ds.notes,
        case_count=case_count,
        created_at=ds.created_at.isoformat(),
    )


def _count(db: Session, dataset_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count(Case.id)).where(Case.dataset_id == dataset_id)
    ).scalar() or 0


@router.post("", response_model=DatasetDto, status_code=status.HTTP_201_CREATED)
def create_dataset(
    body: DatasetCreateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> DatasetDto:
    existing = db.execute(select(Dataset).where(Dataset.name == body.name)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"'{body.name}' adında bir veri seti zaten var")
    ds = Dataset(
        name=body.name,
        description=body.description,
        source=body.source or "webapp",
        notes=body.notes,
        created_by=actor.id,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return _dto(ds, 0)


@router.get("", response_model=list[DatasetDto])
def list_datasets(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[DatasetDto]:
    rows = db.execute(select(Dataset).order_by(Dataset.created_at.desc())).scalars().all()
    return [_dto(ds, _count(db, ds.id)) for ds in rows]


@router.get("/{dataset_id}", response_model=DatasetDto)
def get_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> DatasetDto:
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Veri seti bulunamadı")
    return _dto(ds, _count(db, ds.id))


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Veri seti bulunamadı")
    db.delete(ds)
    db.commit()
