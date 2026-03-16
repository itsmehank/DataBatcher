from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .routers import chart_router, minervini_router, options_router

app = FastAPI(title="Minervini LWC API", version="0.1.0")
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


@app.exception_handler(ValueError)
def _value_error_handler(_, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(SQLAlchemyError)
def _sqlalchemy_error_handler(_, exc: SQLAlchemyError):
    logger.exception("Unhandled database error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Database error"})
