from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import csv
from io import StringIO
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.db.oracle import fetch_all_with_columns, fetch_one


router = APIRouter(prefix="/api/olap", tags=["olap"])


def _limited(sql: str) -> str:
    return f"SELECT * FROM ({sql}) WHERE ROWNUM <= :limit"

def _apply_limit(sql: str, limit: int | None) -> str:
    if limit is None:
        return sql
    return _limited(sql)


def _to_json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _query_table(sql: str, params: dict[str, Any]) -> dict[str, Any]:
    cols, rows = fetch_all_with_columns(sql, params)
    items: list[dict[str, Any]] = []
    for row in rows:
        items.append({c: _to_json_value(v) for c, v in zip(cols, row)})
    return {"columns": cols, "rows": items, "count": len(items)}


@router.get("/1")
def olap_q1(limit: int | None = Query(default=None, ge=1, le=100000)) -> dict[str, Any]:
    sql = _apply_limit(
        """
        SELECT l.MaCuaHang, l.TenCuaHang, l.TenThanhPho, l.Bang, l.SoDienThoai,
               p.MaMH, p.MoTa, p.KichCo, p.TrongLuong, p.Gia AS DonGia, fi.SoLuongTon
        FROM FACT_INVENTORY fi
        JOIN DIM_LOCATION l ON fi.MaCuaHang = l.MaCuaHang
        JOIN DIM_PRODUCT p  ON fi.MaMH = p.MaMH
        ORDER BY l.MaCuaHang, p.MaMH
        """
        ,
        limit
    )
    params: dict[str, Any] = {"limit": limit} if limit is not None else {}
    return _query_table(sql, params)


@router.get("/2")
def olap_q2(limit: int | None = Query(default=None, ge=1, le=100000)) -> dict[str, Any]:
    sql = _apply_limit(
        """
        SELECT fo.MaDon, c.TenKH,
               t.Ngay || '/' || t.Thang || '/' || t.Nam AS NgayDatHang,
               t.ThuTrongTuan, fo.KenhBanHang, SUM(fo.TongTien) AS TongTienDon
        FROM FACT_ORDER fo
        JOIN DIM_CUSTOMER c ON fo.MaKH = c.MaKH
        JOIN DIM_TIME t     ON fo.MaThoiGian = t.MaThoiGian
        GROUP BY fo.MaDon, c.TenKH, t.Ngay, t.Thang, t.Nam, t.ThuTrongTuan, fo.KenhBanHang
        ORDER BY t.Nam, t.Thang, t.Ngay
        """,
        limit
    )
    params: dict[str, Any] = {"limit": limit} if limit is not None else {}
    return _query_table(sql, params)


@router.get("/3")
def olap_q3(
    ma_kh: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100000),
) -> dict[str, Any]:
    if not ma_kh:
        picked = fetch_one("SELECT MIN(MaKH) FROM FACT_ORDER")
        ma_kh = str(picked[0]) if picked and picked[0] is not None else ""

    sql = _apply_limit(
        """
        SELECT DISTINCT l.MaCuaHang, l.TenCuaHang, l.TenThanhPho, l.SoDienThoai
        FROM FACT_ORDER fo
        JOIN DIM_LOCATION l ON fo.MaCuaHang = l.MaCuaHang
        WHERE fo.MaKH = :ma_kh
        ORDER BY l.MaCuaHang
        """,
        limit
    )
    params: dict[str, Any] = {"ma_kh": ma_kh}
    if limit is not None:
        params["limit"] = limit
    data = _query_table(sql, params)
    data["params"] = {"ma_kh": ma_kh}
    return data


@router.get("/4")
def olap_q4(
    ma_mh: str | None = Query(default=None),
    min_so_luong_ton: int = Query(default=100, ge=0),
    limit: int | None = Query(default=None, ge=1, le=100000),
) -> dict[str, Any]:
    if not ma_mh:
        picked = fetch_one(
            "SELECT MIN(MaMH) FROM FACT_INVENTORY WHERE SoLuongTon > :n",
            {"n": min_so_luong_ton},
        )
        ma_mh = str(picked[0]) if picked and picked[0] is not None else ""

    sql = _apply_limit(
        """
        SELECT DISTINCT l.MaCuaHang, l.TenCuaHang, l.DiaChiVP, l.TenThanhPho, l.Bang, fi.SoLuongTon
        FROM FACT_INVENTORY fi
        JOIN DIM_LOCATION l ON fi.MaCuaHang = l.MaCuaHang
        WHERE fi.MaMH = :ma_mh
          AND fi.SoLuongTon > :min_sl
        ORDER BY l.Bang, l.TenThanhPho
        """,
        limit
    )
    params: dict[str, Any] = {"ma_mh": ma_mh, "min_sl": min_so_luong_ton}
    if limit is not None:
        params["limit"] = limit
    data = _query_table(sql, params)
    data["params"] = {"ma_mh": ma_mh, "min_so_luong_ton": min_so_luong_ton}
    return data


@router.get("/5")
def olap_q5(limit: int | None = Query(default=None, ge=1, le=100000)) -> dict[str, Any]:
    sql = _apply_limit(
        """
        SELECT fo.MaDon, c.TenKH, p.MaMH, p.MoTa, fo.MaCuaHang, l.TenCuaHang, l.TenThanhPho,
               fo.SoLuongDat, fo.GiaDat, fo.TongTien
        FROM FACT_ORDER fo
        JOIN DIM_CUSTOMER c ON fo.MaKH = c.MaKH
        JOIN DIM_PRODUCT p  ON fo.MaMH = p.MaMH
        JOIN DIM_LOCATION l ON fo.MaCuaHang = l.MaCuaHang
        ORDER BY fo.MaDon, p.MaMH
        """,
        limit
    )
    params: dict[str, Any] = {"limit": limit} if limit is not None else {}
    return _query_table(sql, params)


@router.get("/6")
def olap_q6(
    ma_kh: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100000),
) -> dict[str, Any]:
    if not ma_kh:
        picked = fetch_one("SELECT MIN(MaKH) FROM DIM_CUSTOMER")
        ma_kh = str(picked[0]) if picked and picked[0] is not None else ""

    sql = _apply_limit(
        """
        SELECT MaKH, TenKH, MaThanhPho, TenThanhPho, Bang
        FROM DIM_CUSTOMER
        WHERE MaKH = :ma_kh
        """,
        limit
    )
    params: dict[str, Any] = {"ma_kh": ma_kh}
    if limit is not None:
        params["limit"] = limit
    data = _query_table(sql, params)
    data["params"] = {"ma_kh": ma_kh}
    return data


@router.get("/7")
def olap_q7(
    ma_mh: str | None = Query(default=None),
    ma_thanh_pho: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100000),
) -> dict[str, Any]:
    if not ma_mh or not ma_thanh_pho:
        picked = fetch_one(
            """
            SELECT x.MaMH, x.MaThanhPho
            FROM (
                SELECT fi.MaMH, l.MaThanhPho
                FROM FACT_INVENTORY fi
                JOIN DIM_LOCATION l ON fi.MaCuaHang = l.MaCuaHang
                ORDER BY fi.MaMH, l.MaThanhPho
            ) x
            WHERE ROWNUM = 1
            """
        )
        if picked:
            ma_mh = ma_mh or str(picked[0])
            ma_thanh_pho = ma_thanh_pho or str(picked[1])

    sql = _apply_limit(
        """
        SELECT l.MaCuaHang, l.TenCuaHang, l.LoaiCuaHang, p.MaMH, p.MoTa, fi.SoLuongTon
        FROM FACT_INVENTORY fi
        JOIN DIM_LOCATION l ON fi.MaCuaHang = l.MaCuaHang
        JOIN DIM_PRODUCT p  ON fi.MaMH = p.MaMH
        WHERE fi.MaMH = :ma_mh
          AND l.MaThanhPho = :ma_tp
        ORDER BY l.MaCuaHang
        """,
        limit
    )
    params: dict[str, Any] = {"ma_mh": ma_mh, "ma_tp": ma_thanh_pho}
    if limit is not None:
        params["limit"] = limit
    data = _query_table(sql, params)
    data["params"] = {"ma_mh": ma_mh, "ma_thanh_pho": ma_thanh_pho}
    return data


@router.get("/8")
def olap_q8(
    ma_don: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100000),
) -> dict[str, Any]:
    if not ma_don:
        picked = fetch_one("SELECT MIN(MaDon) FROM FACT_ORDER")
        ma_don = str(picked[0]) if picked and picked[0] is not None else ""

    sql = _apply_limit(
        """
        SELECT fo.MaDon, p.MaMH, p.MoTa, fo.SoLuongDat, fo.GiaDat, fo.TongTien,
               c.MaKH, c.TenKH, l.MaCuaHang, l.TenCuaHang, l.TenThanhPho
        FROM FACT_ORDER fo
        JOIN DIM_PRODUCT p  ON fo.MaMH = p.MaMH
        JOIN DIM_CUSTOMER c ON fo.MaKH = c.MaKH
        JOIN DIM_LOCATION l ON fo.MaCuaHang = l.MaCuaHang
        WHERE fo.MaDon = :ma_don
        ORDER BY p.MaMH
        """,
        limit
    )
    params: dict[str, Any] = {"ma_don": ma_don}
    if limit is not None:
        params["limit"] = limit
    data = _query_table(sql, params)
    data["params"] = {"ma_don": ma_don}
    return data


@router.get("/9")
def olap_q9(limit: int | None = Query(default=None, ge=1, le=100000)) -> dict[str, Any]:
    def _run(sql: str) -> dict[str, Any]:
        q = _apply_limit(sql, limit)
        params: dict[str, Any] = {"limit": limit} if limit is not None else {}
        return _query_table(q, params)

    q9a = _run(
            """
            SELECT MaKH, TenKH, HuongDanVien
            FROM DIM_CUSTOMER
            WHERE LoaiKH = 'Du lich'
            ORDER BY MaKH
            """
    )
    q9b = _run(
            """
            SELECT MaKH, TenKH, DiaChiBuuDien
            FROM DIM_CUSTOMER
            WHERE LoaiKH = 'Buu dien'
            ORDER BY MaKH
            """
    )
    q9c = _run(
            """
            SELECT MaKH, TenKH, HuongDanVien, DiaChiBuuDien
            FROM DIM_CUSTOMER
            WHERE LoaiKH = 'Ca hai'
            ORDER BY MaKH
            """
    )
    q9d = _run(
            """
            SELECT LoaiKH, COUNT(*) AS SoLuong
            FROM DIM_CUSTOMER
            WHERE LoaiKH IS NOT NULL
            GROUP BY LoaiKH
            ORDER BY SoLuong DESC
            """
    )

    return {"du_lich": q9a, "buu_dien": q9b, "ca_hai": q9c, "thong_ke": q9d}


def _table_to_csv(table: dict[str, Any]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    columns = table.get("columns", [])
    rows = table.get("rows", [])
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(col, "") for col in columns])
    return output.getvalue()


@router.get("/export")
def export_olap_csv(
    question: int = Query(ge=1, le=9),
    section: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100000),
    ma_kh: str | None = Query(default=None),
    ma_mh: str | None = Query(default=None),
    ma_thanh_pho: str | None = Query(default=None),
    ma_don: str | None = Query(default=None),
    min_so_luong_ton: int = Query(default=100, ge=0),
) -> StreamingResponse:
    if question == 1:
        data = olap_q1(limit=limit)
    elif question == 2:
        data = olap_q2(limit=limit)
    elif question == 3:
        data = olap_q3(ma_kh=ma_kh, limit=limit)
    elif question == 4:
        data = olap_q4(ma_mh=ma_mh, min_so_luong_ton=min_so_luong_ton, limit=limit)
    elif question == 5:
        data = olap_q5(limit=limit)
    elif question == 6:
        data = olap_q6(ma_kh=ma_kh, limit=limit)
    elif question == 7:
        data = olap_q7(ma_mh=ma_mh, ma_thanh_pho=ma_thanh_pho, limit=limit)
    elif question == 8:
        data = olap_q8(ma_don=ma_don, limit=limit)
    else:
        all_sections = olap_q9(limit=limit)
        selected = section or "thong_ke"
        data = all_sections.get(selected, all_sections["thong_ke"])

    csv_content = _table_to_csv(data)
    filename = f"olap_q{question}.csv" if question != 9 else f"olap_q9_{section or 'thong_ke'}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(iter([csv_content]), media_type="text/csv", headers=headers)
