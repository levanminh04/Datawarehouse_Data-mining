from __future__ import annotations

from fastapi import APIRouter

from app.db.oracle import fetch_all, fetch_one


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


TABLES = [
    "DIM_TIME",
    "DIM_LOCATION",
    "DIM_PRODUCT",
    "DIM_CUSTOMER",
    "FACT_INVENTORY",
    "FACT_ORDER",
    "ETL_LOG",
]

LAST_RUN_ALL_SQL = """
SELECT LogID, TenJob, TrangThai, SoBanGhi, GhiChu, ThoiGianKT
FROM ETL_LOG
WHERE TenJob = 'RUN_ALL'
ORDER BY LogID DESC
FETCH FIRST 1 ROWS ONLY
"""

LAST_LOAD_JOBS_SQL = """
SELECT LogID, TenJob, TrangThai, SoBanGhi, GhiChu, ThoiGianKT
FROM (
    SELECT
        LogID,
        TenJob,
        TrangThai,
        SoBanGhi,
        GhiChu,
        ThoiGianKT,
        ROW_NUMBER() OVER (PARTITION BY TenJob ORDER BY LogID DESC) AS rn
    FROM ETL_LOG
    WHERE TenJob LIKE 'LOAD_%'
)
WHERE rn = 1
ORDER BY TenJob
"""

ETL_ERROR_24H_SQL = """
SELECT COUNT(*)
FROM ETL_LOG
WHERE TrangThai = 'LOI'
  AND ThoiGianKT >= SYSTIMESTAMP - INTERVAL '1' DAY
"""


@router.get("/summary")
def dashboard_summary() -> dict[str, object]:
    counts: dict[str, int] = {}
    for table_name in TABLES:
        row = fetch_one(f"SELECT COUNT(*) FROM {table_name}")
        counts[table_name] = int(row[0]) if row else 0

    last = fetch_one(LAST_RUN_ALL_SQL)
    last_run_all = None
    if last:
        last_run_all = {
            "log_id": int(last[0]),
            "job_name": last[1],
            "status": last[2],
            "row_count": int(last[3] or 0),
            "note": last[4],
            "finished_at": str(last[5]) if last[5] is not None else None,
        }

    load_rows = fetch_all(LAST_LOAD_JOBS_SQL)
    last_load_jobs = [
        {
            "log_id": int(row[0]),
            "job_name": row[1],
            "status": row[2],
            "row_count": int(row[3] or 0),
            "note": row[4],
            "finished_at": str(row[5]) if row[5] is not None else None,
        }
        for row in load_rows
    ]

    error_row = fetch_one(ETL_ERROR_24H_SQL)
    errors_24h = int(error_row[0]) if error_row else 0

    return {
        "table_counts": counts,
        "last_run_all": last_run_all,
        "last_load_jobs": last_load_jobs,
        "etl_error_24h": errors_24h,
    }
