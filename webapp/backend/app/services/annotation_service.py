"""Annotasyon CRUD + denetim izi mantığı (plan Bölüm 2/4/6).

Kritik kural: bir `prediction` annotasyonu asla yerinde değiştirilmez.
Düzenleme her zaman yeni bir `corrected` satırı oluşturur, orijinal
`superseded` durumuna geçer — böylece tahmin geçmişi, model karşılaştırması
ve denetim için korunur.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Annotation, AnnotationAuditLog, User


def create_manual_annotation(
    db: Session,
    *,
    case_id: uuid.UUID,
    actor: User,
    image_id: int,
    class_type: str,
    class_id: int,
    geometry_type: str,
    geometry: dict[str, Any],
) -> Annotation:
    ann = Annotation(
        case_id=case_id,
        image_id=image_id,
        class_type=class_type,
        class_id=class_id,
        geometry_type=geometry_type,
        geometry=geometry,
        source="manual",
        included_in_training_pool=True,
        created_by=actor.id,
    )
    db.add(ann)
    db.flush()
    _audit(db, ann, action="create", actor=actor, before=None, after=geometry)
    db.commit()
    db.refresh(ann)
    return ann


def correct_annotation(
    db: Session,
    *,
    original: Annotation,
    actor: User,
    class_id: int | None,
    geometry: dict[str, Any] | None,
) -> Annotation:
    """`original` bir tahmin veya daha önceki bir düzeltme olabilir; her durumda
    yeni bir `corrected` satır oluşturulur, `original` `superseded` yapılır."""
    new_geometry = geometry if geometry is not None else original.geometry
    new_class_id = class_id if class_id is not None else original.class_id

    corrected = Annotation(
        case_id=original.case_id,
        image_id=original.image_id,
        class_type=original.class_type,
        class_id=new_class_id,
        geometry_type=original.geometry_type,
        geometry=new_geometry,
        source="corrected",
        derived_from_annotation_id=original.id,
        model_output_id=original.model_output_id,
        group_id=original.group_id,
        included_in_training_pool=True,
        created_by=actor.id,
    )
    original.status = "superseded"
    db.add(original)
    db.add(corrected)
    db.flush()

    action = "class_change" if class_id is not None and class_id != original.class_id else "edit"
    _audit(db, corrected, action=action, actor=actor, before=original.geometry, after=new_geometry)
    db.commit()
    db.refresh(corrected)
    return corrected


def accept_prediction(db: Session, *, prediction: Annotation, actor: User) -> Annotation:
    """Doktor 'bu tahmin doğru' der — tahmin değişmeden havuza dahil edilir."""
    prediction.included_in_training_pool = True
    prediction.reviewed_by = actor.id
    db.add(prediction)
    _audit(db, prediction, action="accept_prediction", actor=actor, before=None, after=None)
    db.commit()
    db.refresh(prediction)
    return prediction


def soft_delete_annotation(db: Session, *, annotation: Annotation, actor: User) -> Annotation:
    annotation.status = "deleted"
    db.add(annotation)
    _audit(db, annotation, action="delete", actor=actor, before=annotation.geometry, after=None)
    db.commit()
    db.refresh(annotation)
    return annotation


def _audit(
    db: Session,
    annotation: Annotation,
    *,
    action: str,
    actor: User,
    before: dict | None,
    after: dict | None,
) -> None:
    db.add(
        AnnotationAuditLog(
            annotation_id=annotation.id,
            action=action,
            actor_id=actor.id,
            before_geometry=before,
            after_geometry=after,
        )
    )
