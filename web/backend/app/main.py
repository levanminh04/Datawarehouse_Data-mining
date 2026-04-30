from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.dashboard import router as dashboard_router
from app.routers.etl import router as etl_router
from app.routers.health import router as health_router
from app.routers.olap import router as olap_router
from app.routers.quality import router as quality_router


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(etl_router)
app.include_router(olap_router)
app.include_router(quality_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "DW Dashboard API is running"}
