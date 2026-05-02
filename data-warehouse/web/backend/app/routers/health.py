from __future__ import annotations

from fastapi import APIRouter

from app.db.oracle import fetch_one


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def health_check_db() -> dict[str, str | int]:
    row = fetch_one("SELECT 1 FROM dual")
    value = int(row[0]) if row else 0
    return {"status": "ok", "oracle_ping": value}
