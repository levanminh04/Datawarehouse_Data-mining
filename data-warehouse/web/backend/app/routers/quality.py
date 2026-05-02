from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter

from app.db.oracle import get_connection


router = APIRouter(prefix="/api/quality", tags=["quality"])


@router.get("/checks")
def quality_checks() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def to_number(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        text = str(value).strip().replace(",", "")
        return float(text) if text else 0.0

    def run_scalar(cursor: Any, sql: str) -> tuple[float | None, str | None]:
        try:
            cursor.execute(sql)
            row = cursor.fetchone()
            value = to_number(row[0]) if row else 0.0
            return value, None
        except Exception as exc:
            return None, str(exc)

    def run_scalar_candidates(cursor: Any, sql_or_list: str | list[str]) -> tuple[float | None, str | None]:
        sql_list = [sql_or_list] if isinstance(sql_or_list, str) else sql_or_list
        last_error: str | None = None
        for sql in sql_list:
            value, err = run_scalar(cursor, sql)
            if err is None:
                return value, None
            last_error = err
        return None, last_error

    def add_check(
        cursor: Any,
        name: str,
        dw_sql: str,
        src_sql: str | list[str],
        note: str,
    ) -> None:
        dw_value, dw_error = run_scalar(cursor, dw_sql)
        src_value, src_error = run_scalar_candidates(cursor, src_sql)
        error_message = src_error or dw_error
        if dw_value is not None and src_value is not None:
            is_match = abs(dw_value - src_value) < 0.01
        else:
            is_match = None
        checks.append(
            {
                "name": name,
                "dw_value": dw_value,
                "source_value": src_value,
                "match": is_match,
                "note": note,
                "error": error_message,
            }
        )

    with get_connection() as conn:
        with conn.cursor() as cursor:
            add_check(
                cursor,
                "Customer Count",
                "SELECT COUNT(*) FROM DIM_CUSTOMER",
                "SELECT COUNT(*) FROM VANPHONG.KHACHHANG",
                "DIM_CUSTOMER vs VANPHONG.KHACHHANG",
            )
            add_check(
                cursor,
                "Tourist Customers",
                "SELECT COUNT(*) FROM DIM_CUSTOMER WHERE HUONGDANVIEN IS NOT NULL",
                "SELECT COUNT(*) FROM VANPHONG.KH_DULICH",
                "Nguon KH du lich",
            )
            add_check(
                cursor,
                "Postal Customers",
                "SELECT COUNT(*) FROM DIM_CUSTOMER WHERE DIACHIBUUDIEN IS NOT NULL",
                "SELECT COUNT(*) FROM VANPHONG.KH_BUUDIEN",
                "Nguon KH buu dien",
            )
            add_check(
                cursor,
                "Product Count",
                "SELECT COUNT(*) FROM DIM_PRODUCT",
                'SELECT TO_CHAR(COUNT(*)) FROM "MatHang"@sqlserver_banhang',
                "DIM_PRODUCT vs SQL Server MatHang",
            )
            add_check(
                cursor,
                "Order Detail Count",
                "SELECT COUNT(*) FROM FACT_ORDER",
                'SELECT TO_CHAR(COUNT(*)) FROM "MatHang_DuocDat"@sqlserver_banhang',
                "FACT_ORDER vs SQL Server MatHang_DuocDat",
            )
            add_check(
                cursor,
                "Distinct Customer Key",
                "SELECT COUNT(DISTINCT MaKH) FROM DIM_CUSTOMER",
                "SELECT COUNT(*) FROM VANPHONG.KHACHHANG",
                "Distinct MaKH in DIM_CUSTOMER",
            )
            add_check(
                cursor,
                "Distinct Product Key",
                "SELECT COUNT(DISTINCT MaMH) FROM DIM_PRODUCT",
                'SELECT TO_CHAR(COUNT(*)) FROM "MatHang"@sqlserver_banhang',
                "Distinct MaMH in DIM_PRODUCT",
            )
            add_check(
                cursor,
                "Distinct Order Key",
                "SELECT COUNT(DISTINCT MaDon) FROM FACT_ORDER",
                'SELECT TO_CHAR(COUNT(*)) FROM "DonDatHang"@sqlserver_banhang',
                "Distinct MaDon in FACT_ORDER",
            )
            add_check(
                cursor,
                "Total Inventory Qty",
                """
                SELECT TO_CHAR(SUM(f.SoLuongTon))
                FROM FACT_INVENTORY f
                JOIN DIM_LOCATION l ON l.MaCuaHang = f.MaCuaHang
                WHERE l.LoaiCuaHang = 'Vat ly'
                """,
                [
                    'SELECT TO_CHAR(SUM("SoLuongKho")) FROM "MatHang_LuuTru"@sqlserver_banhang',
                    'SELECT TO_CHAR(SUM(SoLuongKho)) FROM "MatHang_LuuTru"@sqlserver_banhang',
                ],
                "Tong ton kho vat ly (khop pham vi nguon SQL Server)",
            )
            add_check(
                cursor,
                "Total Order Amount",
                "SELECT TO_CHAR(ROUND(SUM(TongTien),2)) FROM FACT_ORDER",
                [
                    'SELECT TO_CHAR(ROUND(SUM("SoLuongDat" * "GiaDat"),2)) FROM "MatHang_DuocDat"@sqlserver_banhang',
                    'SELECT TO_CHAR(ROUND(SUM(SoLuongDat * GiaDat),2)) FROM "MatHang_DuocDat"@sqlserver_banhang',
                ],
                "Tong doanh thu don hang",
            )
            add_check(
                cursor,
                "Orphan FACT_ORDER MaKH",
                """
                SELECT COUNT(*)
                FROM FACT_ORDER f
                LEFT JOIN DIM_CUSTOMER d ON f.MaKH = d.MaKH
                WHERE d.MaKH IS NULL
                """,
                "SELECT 0 FROM dual",
                "Ky vong = 0",
            )
            add_check(
                cursor,
                "Orphan FACT_ORDER MaMH",
                """
                SELECT COUNT(*)
                FROM FACT_ORDER f
                LEFT JOIN DIM_PRODUCT d ON f.MaMH = d.MaMH
                WHERE d.MaMH IS NULL
                """,
                "SELECT 0 FROM dual",
                "Ky vong = 0",
            )
            add_check(
                cursor,
                "Orphan FACT_ORDER MaCuaHang",
                """
                SELECT COUNT(*)
                FROM FACT_ORDER f
                LEFT JOIN DIM_LOCATION d ON f.MaCuaHang = d.MaCuaHang
                WHERE d.MaCuaHang IS NULL
                """,
                "SELECT 0 FROM dual",
                "Ky vong = 0",
            )
            add_check(
                cursor,
                "Negative Qty/Price in FACT_ORDER",
                """
                SELECT COUNT(*)
                FROM FACT_ORDER
                WHERE SoLuongDat < 0 OR GiaDat < 0 OR TongTien < 0
                """,
                "SELECT 0 FROM dual",
                "Ky vong = 0",
            )
            add_check(
                cursor,
                "Critical NULLs in FACT_ORDER",
                """
                SELECT COUNT(*)
                FROM FACT_ORDER
                WHERE MaDon IS NULL OR MaKH IS NULL OR MaMH IS NULL OR MaCuaHang IS NULL OR MaThoiGian IS NULL
                """,
                "SELECT 0 FROM dual",
                "Ky vong = 0",
            )

    ok_count = sum(1 for c in checks if c["match"] is True)
    failed_count = sum(1 for c in checks if c["match"] is False)
    unavailable_count = sum(1 for c in checks if c["match"] is None)

    return {
        "summary": {
            "total": len(checks),
            "ok": ok_count,
            "failed": failed_count,
            "unavailable": unavailable_count,
        },
        "checks": checks,
    }
