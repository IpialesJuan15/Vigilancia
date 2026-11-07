import hashlib
import logging
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import AuditLog, LivingReview
from app.services.documents import (
    IngestionError,
    enrich_pdf,
    jats_license,
    license_policy,
    parse_jats,
    parse_pdf,
)
from app.services.storage import ObjectStore
from app.sources.ingestion import fetch, resolve
from app.tasks import celery

logger = logging.getLogger(__name__)


def ingest_review(review_id: str):
    with SessionLocal() as db:
        review = db.get(LivingReview, review_id)
        if not review or review.status not in {"queued", "failed"}:
            return
        try:
            review.status, review.stage, review.progress = (
                "resolving",
                "Verificando acceso abierto y licencia",
                15,
            )
            review.error_code = review.error_message = None
            db.commit()
            metadata = resolve(review.original_doi)
            review.original_title = metadata["title"]
            review.normalized_title = re.sub(r"\W+", " ", review.original_title.casefold()).strip()
            duplicate = db.scalar(
                select(LivingReview).where(
                    LivingReview.normalized_title == review.normalized_title,
                    LivingReview.id != review.id,
                )
            )
            if duplicate:
                raise IngestionError("duplicate_title", "Ya existe una revisión con este título")
            review.original_authors = metadata["authors"]
            review.journal, review.year = metadata["journal"], metadata["year"]
            review.oa_url = metadata["url"]
            review.stage, review.progress = "Descargando el texto completo", 35
            db.commit()
            store = ObjectStore()
            data = store.get(review.uploaded_key) if review.uploaded_key else fetch(metadata["url"])
            fmt = "pdf" if review.uploaded_key else metadata["format"]
            license_value = metadata.get("license")
            if metadata["format"] == "xml":
                xml_data = data if fmt == "xml" else fetch(metadata["url"])
                license_value = jats_license(xml_data) or license_value
            license_name, restricted = license_policy(license_value)
            review.license = license_name
            if restricted and not review.license_confirmed:
                review.status, review.stage = (
                    "license_review",
                    "Confirma las condiciones de la licencia",
                )
                review.progress = 35
                review.warnings = [
                    "Esta licencia limita el uso o las obras derivadas. "
                    "Se requiere confirmar la reextracción de datos con atribución."
                ]
                db.commit()
                return
            review.source_key = f"{review.id}/source.{fmt}"
            review.source_sha256 = hashlib.sha256(data).hexdigest()
            review.source_format = fmt
            store.put(review.source_key, data)
            review.status, review.stage, review.progress = (
                "parsing",
                "Leyendo secciones, referencias y tablas",
                65,
            )
            db.commit()
            if review.uploaded_key:
                import pymupdf

                with pymupdf.open(stream=data, filetype="pdf") as pdf:
                    uploaded_text = "".join(pdf[i].get_text() for i in range(min(5, len(pdf))))
                if review.original_doi not in re.sub(r"\s+", "", uploaded_text.lower()):
                    raise IngestionError(
                        "pdf_doi_mismatch",
                        "El DOI no aparece en las primeras páginas "
                        "del PDF. Comprueba que subiste el artículo correcto",
                    )
            document = parse_jats(data) if fmt == "xml" else enrich_pdf(data, parse_pdf(data))
            document["provenance"] = {
                "doi": review.original_doi,
                "url": None if review.uploaded_key else metadata["url"],
                "verification_url": metadata["url"],
                "origin": "uploaded_pdf" if review.uploaded_key else "download",
                "format": fmt,
                "license": license_name,
                "sha256": review.source_sha256,
                "provider": metadata["provider"],
            }
            if restricted:
                document["warnings"].append(
                    "Licencia con restricciones: conservar atribución y confirmación del curador"
                )
            review.document = document
            review.warnings = document["warnings"]
            if not re.search(
                r"systematic|sistem[aá]tica|meta.analysis", review.original_title, re.I
            ):
                review.warnings = [
                    *review.warnings,
                    "Confirma que el artículo es una revisión sistemática. "
                    "La clasificación con evidencia estará disponible en la siguiente etapa.",
                ]
            review.status, review.stage, review.progress = (
                "parsed",
                "Documento leído; pendiente de confirmar el método",
                100,
            )
            db.add(
                AuditLog(
                    actor_id=review.owner_curator_id,
                    action="review_parsed",
                    entity="review",
                    entity_id=review.id,
                    after={"doi": review.original_doi, "license": license_name},
                )
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            review.normalized_title = None
            review.status, review.error_code = "failed", "duplicate_title"
            review.error_message = "Ya existe una revisión con este título"
            review.stage = "La revisión ya está registrada"
            db.commit()
        except IngestionError as exc:
            db.rollback()
            review.status, review.error_code, review.error_message = "failed", exc.code, exc.message
            review.stage = "La lectura necesita atención"
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error("ingestion_failed", extra={"error_type": type(exc).__name__})
            review.status, review.error_code = "failed", "source_unavailable"
            review.error_message = (
                "No pudimos leer la fuente. Comprueba su disponibilidad y vuelve a intentar"
            )
            review.stage = "No se pudo completar la lectura"
            db.commit()


@celery.task(soft_time_limit=240, time_limit=300)
def ingest(review_id: str):
    ingest_review(review_id)
