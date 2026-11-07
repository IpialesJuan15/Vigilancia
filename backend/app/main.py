import logging
import time

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.auth import router as auth_router
from app.api.routes.reviews import router as reviews_router
from app.config import get_settings
from app.db import engine, get_db
from app.middleware import BodyLimitMiddleware
from app.models import User
from app.schemas import RoleInput, UserOut
from app.security import csrf_guard, current_user, rate_limit, require_roles
from app.services.auth import audit

app = FastAPI(
    title="LiveSRL", version="0.1.0", root_path="/api", dependencies=[Depends(csrf_guard)]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().app_base_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.add_middleware(BodyLimitMiddleware, max_bytes=get_settings().max_pdf_bytes + 1024 * 1024)
app.include_router(auth_router)
app.include_router(reviews_router)
logger = logging.getLogger("livesrl")


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"code": f"http_{exc.status_code}", "message": str(exc.detail), "details": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": "invalid_input",
            "message": "Revisa los campos del formulario",
            "details": [
                {"field": ".".join(map(str, e["loc"])), "type": e["type"]} for e in exc.errors()
            ],
        },
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error("request_failed", extra={"error_type": type(exc).__name__})
    return JSONResponse(
        status_code=500,
        content={
            "code": "internal_error",
            "message": "No pudimos completar la solicitud. Inténtalo de nuevo",
            "details": None,
        },
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    logger.info(
        "request",
        extra={
            "method": request.method,
            "status": response.status_code,
            "duration_ms": round((time.monotonic() - start) * 1000),
        },
    )
    return response


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        Redis.from_url(get_settings().redis_url).ping()
    except Exception:
        raise HTTPException(503, "Un servicio necesario no está disponible") from None
    return {"status": "ok", "phase": "F0"}


@app.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/public/reviews")
def public_reviews(request: Request):
    rate_limit(request, "public", 120, 60)
    return {"items": [], "total": 0, "page": 1}


@app.get("/admin/users", response_model=list[UserOut])
def users(admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.created_at).limit(100)).all()


@app.patch("/admin/users/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: str,
    data: RoleInput,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Cuenta no encontrada")
    if admin.id == user.id and data.role != "admin":
        raise HTTPException(409, "No puedes retirar tu propio acceso de administración")
    audit(
        db,
        admin,
        "role_changed",
        {"user_id": user.id, "role": user.role},
        {"user_id": user.id, "role": data.role},
    )
    user.role = data.role
    user.session_version += 1
    db.commit()
    return user
