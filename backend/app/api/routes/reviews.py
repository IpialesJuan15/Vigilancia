from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AuditLog, LivingReview, User
from app.security import current_user, rate_limit, require_roles
from app.services.documents import IngestionError, normalize_doi, validate_pdf
from app.services.storage import ObjectStore
from app.tasks.ingest import ingest

router = APIRouter(tags=["Revisiones privadas"])
curator = require_roles("curator", "admin")


def owned(review_id: str, user: User, db: Session) -> LivingReview:
    review = db.get(LivingReview, review_id)
    if not review or review.owner_curator_id != user.id:
        raise HTTPException(404, "Revisión no encontrada")
    return review


def summary(review: LivingReview):
    return {
        "id": review.id,
        "original_doi": review.original_doi,
        "original_title": review.original_title,
        "original_authors": review.original_authors,
        "journal": review.journal,
        "year": review.year,
        "status": review.status,
        "progress": review.progress,
        "stage": review.stage,
        "license": review.license,
        "warnings": review.warnings,
        "error_code": review.error_code,
        "error_message": review.error_message,
    }


def queue(db: Session, review: LivingReview):
    try:
        ingest.delay(review.id)
    except Exception:
        review.status = "failed"
        review.error_code, review.error_message = (
            "queue_unavailable",
            "La lectura no pudo iniciarse. Vuelve a intentar",
        )
        db.commit()


@router.get("/reviews")
def listing(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(
        select(LivingReview)
        .where(LivingReview.owner_curator_id == user.id)
        .order_by(LivingReview.created_at.desc())
    ).all()
    return {
        "items": [summary(x) for x in items],
        "total": len(items),
        "ingestion_available": user.role in {"curator", "admin"},
    }


@router.post("/reviews", status_code=202)
async def create(
    request: Request,
    doi: str = Form(...),
    pdf: UploadFile | None = File(None),
    user: User = Depends(curator),
    db: Session = Depends(get_db),
):
    rate_limit(request, "ingest", 10)
    try:
        doi = normalize_doi(doi)
        data = None
        if pdf:
            data = await pdf.read(get_settings().max_pdf_bytes + 1)
            if len(data) > get_settings().max_pdf_bytes:
                raise IngestionError("too_large", "El PDF supera los 20 MB permitidos")
            if pdf.content_type != "application/pdf":
                raise IngestionError("invalid_pdf", "Selecciona un archivo PDF")
            validate_pdf(data)
    except IngestionError as exc:
        raise HTTPException(422, exc.message) from None
    existing = db.scalar(select(LivingReview).where(LivingReview.original_doi == doi))
    if existing:
        if existing.owner_curator_id == user.id:
            return {**summary(existing), "duplicate": True}
        raise HTTPException(409, "Esta revisión ya está registrada por otro curador")
    review = LivingReview(original_doi=doi, owner_curator_id=user.id)
    db.add(review)
    try:
        db.flush()
        if data:
            review.uploaded_key = f"{review.id}/uploaded.pdf"
            ObjectStore().put(review.uploaded_key, data)
        db.add(
            AuditLog(
                actor_id=user.id,
                entity="review",
                entity_id=review.id,
                action="review_created",
                after={"doi": doi},
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "La revisión ya se está registrando. Actualiza la lista") from None
    queue(db, review)
    return summary(review)


@router.get("/reviews/{review_id}")
def detail(review_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    review = owned(review_id, user, db)
    return {**summary(review), "document": review.document}


@router.post("/reviews/{review_id}/retry", status_code=202)
def retry(review_id: str, user: User = Depends(curator), db: Session = Depends(get_db)):
    review = owned(review_id, user, db)
    if review.status != "failed":
        raise HTTPException(409, "La revisión no necesita reintentarse ahora")
    review.status = "queued"
    db.commit()
    queue(db, review)
    return summary(review)


@router.post("/reviews/{review_id}/confirm-license", status_code=202)
def confirm(review_id: str, user: User = Depends(curator), db: Session = Depends(get_db)):
    review = owned(review_id, user, db)
    if review.status != "license_review":
        raise HTTPException(409, "La licencia no está pendiente de confirmación")
    review.license_confirmed, review.status = True, "queued"
    db.add(
        AuditLog(
            actor_id=user.id,
            entity="review",
            entity_id=review.id,
            action="restricted_license_confirmed",
            after={"license": review.license},
        )
    )
    db.commit()
    queue(db, review)
    return summary(review)


@router.get("/reviews/{review_id}/source")
def source(review_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    review = owned(review_id, user, db)
    if not review.source_key:
        raise HTTPException(404, "El archivo todavía no está disponible")
    return Response(
        ObjectStore().get(review.source_key),
        media_type="application/pdf" if review.source_format == "pdf" else "application/xml",
        headers={
            "Content-Disposition": 'attachment; filename="revision.'
            + str(review.source_format)
            + '"'
        },
    )
