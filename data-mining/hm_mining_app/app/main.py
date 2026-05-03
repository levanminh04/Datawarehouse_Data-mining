"""
H&M Mining App — entry point.

Chạy:
    uvicorn app.main:app --reload --port 8000

Các trang:
    /              — Dashboard
    /docs          — OpenAPI Swagger
    /redoc
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import ingest, predict, retrain, metrics
from app.scheduler import start_scheduler, shutdown_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="H&M Mining App",
    description="3 lớp khai phá (KMeans + Apriori + RandomForest) — có học liên tục.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(ingest.router)
app.include_router(predict.router)
app.include_router(retrain.router)
app.include_router(metrics.router)


# Phục vụ frontend tĩnh
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
