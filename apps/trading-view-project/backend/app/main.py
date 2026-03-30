from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .admin_init import ensure_admin_user_exists
from .config import settings
from .db import verify_db_connection
from .routers import auth_router, chart_router, minervini_router, options_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.startup_db_check:
        verify_db_connection()
        try:
            ensure_admin_user_exists()
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Admin bootstrap skipped due to startup error: %s", exc
            )
    if settings.cookie_secure and any("localhost" in o or "127.0.0.1" in o for o in settings.allowed_origins):
        logging.getLogger(__name__).warning(
            "COOKIE_SECURE=true but ALLOWED_ORIGINS contains localhost. "
            "Set ALLOWED_ORIGINS to your production domain."
        )
    yield

app = FastAPI(title="Minervini LWC API", version="0.1.0", lifespan=lifespan)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(options_router)
app.include_router(minervini_router)
app.include_router(chart_router)
app.include_router(auth_router)


@app.exception_handler(ValueError)
def _value_error_handler(_, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(SQLAlchemyError)
def _sqlalchemy_error_handler(_, exc: SQLAlchemyError):
    logger.exception("Unhandled database error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Database error"})
