"""Gyan Sathi — FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import Base, engine

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level, "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("gyansathi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure every model is registered, then create tables table-by-table so a
    # single unsupported type (e.g. pgvector on SQLite dev) doesn't block the rest.
    import app.models  # noqa: F401

    try:
        from sqlalchemy import text

        if settings.database_url.startswith("postgresql"):
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(bind=engine)
        logger.info("Database ready (all tables ensured)")
    except Exception:
        created = 0
        for table in Base.metadata.sorted_tables:
            try:
                table.create(bind=engine, checkfirst=True)
                created += 1
            except Exception:
                pass
        logger.warning("Partial table creation: %d/%d tables", created,
                       len(Base.metadata.sorted_tables))
    yield


app = FastAPI(
    title="Gyan Sathi API",
    description="ગુજરાતી વિદ્યાર્થીઓનો AI અભ્યાસ સાથી — Gujarat Board Std 9–10 AI tutor",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self), camera=()"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "કંઈક સમસ્યા આવી છે. કૃપા કરીને થોડીવાર પછી ફરી પ્રયાસ કરો."},
    )


# ---- Routers
from app.api import admin, auth, chat, progress, quizzes, subjects, subscriptions, uploads  # noqa: E402

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(subjects.router)
app.include_router(uploads.router)
app.include_router(quizzes.router)
app.include_router(progress.router)
app.include_router(subscriptions.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Gyan Sathi", "tagline": "તમારો અભ્યાસ, અમારો સાથી"}
