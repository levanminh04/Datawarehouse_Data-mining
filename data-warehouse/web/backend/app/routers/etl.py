from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from time import perf_counter
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.oracle import execute_sql, fetch_all_with_columns, fetch_one


router = APIRouter(prefix="/api/etl", tags=["etl"])


def _to_json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


@router.post("/run")
def run_etl() -> dict[str, Any]:
    started = perf_counter()
    try:
        execute_sql("BEGIN PKG_ETL_DW.RUN_ALL; END;")
    except Exception as exc:  # pragma: no cover - runtime DB errors
        raise HTTPException(status_code=500, detail=f"ETL execution failed: {exc}") from exc

    elapsed_seconds = round(perf_counter() - started, 3)

    last_run = fetch_one(
        """
        SELECT LogID, TenJob, TrangThai, SoBanGhi, GhiChu, ThoiGianKT
        FROM ETL_LOG
        WHERE TenJob = 'RUN_ALL'
        ORDER BY LogID DESC
        FETCH FIRST 1 ROWS ONLY
        """
    )

    result: dict[str, Any] = {"status": "ok", "elapsed_seconds": elapsed_seconds}
    if last_run:
        result["last_run"] = {
            "log_id": int(last_run[0]),
            "job_name": last_run[1],
            "status": last_run[2],
            "row_count": int(last_run[3] or 0),
            "note": last_run[4],
            "finished_at": _to_json_value(last_run[5]),
        }
    return result


@router.get("/logs")
def get_etl_logs(
    limit: int = Query(default=50, ge=1, le=500),
    status: str | None = Query(default=None),
    job_name: str | None = Query(default=None),
    from_time: str | None = Query(default=None),
    to_time: str | None = Query(default=None),
) -> dict[str, Any]:
    where_parts: list[str] = []
    params: dict[str, Any] = {"limit": limit}

    if status:
        where_parts.append("TrangThai = :status")
        params["status"] = status
    if job_name:
        where_parts.append("TenJob = :job_name")
        params["job_name"] = job_name
    if from_time:
        where_parts.append("ThoiGianBD >= TO_TIMESTAMP(:from_time, 'YYYY-MM-DD\"T\"HH24:MI:SS')")
        params["from_time"] = from_time
    if to_time:
        where_parts.append("ThoiGianBD <= TO_TIMESTAMP(:to_time, 'YYYY-MM-DD\"T\"HH24:MI:SS')")
        params["to_time"] = to_time

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    sql = f"""
    SELECT LogID, TenJob, ThoiGianBD, ThoiGianKT, TrangThai, SoBanGhi, GhiChu
    FROM ETL_LOG
    {where_sql}
    ORDER BY LogID DESC
    FETCH FIRST :limit ROWS ONLY
    """

    cols, rows = fetch_all_with_columns(sql, params)
    items: list[dict[str, Any]] = []
    for row in rows:
        items.append({c: _to_json_value(v) for c, v in zip(cols, row)})

    return {"count": len(items), "rows": items}
