"""
Trích xuất đặc trưng — KHÔNG load toàn bộ vào RAM.

Mọi câu lệnh JOIN/AGG đều push xuống PostgreSQL (theo đúng tinh thần
mục 3.3 trong báo cáo: chống OOM khi >1 triệu khách hàng).
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from app.db import engine


SQL_FILE = Path(__file__).parent.parent / "sql" / "feature_queries.sql"


def _read_section(marker: str) -> str:
    """Bóc tách một block SQL theo marker --- Q1/Q2/Q3."""
    raw = SQL_FILE.read_text(encoding="utf-8")
    sections = raw.split("-- ----- ")
    for sec in sections:
        if sec.startswith(marker):
            # Bỏ dòng tiêu đề + comment, giữ phần SQL có thật
            lines = sec.splitlines()[1:]
            sql_lines = [ln for ln in lines if not ln.strip().startswith("--")]
            return "\n".join(sql_lines).strip().rstrip(";")
    raise KeyError(f"Không tìm thấy section {marker!r} trong feature_queries.sql")


def latest_cutoff_date() -> date:
    """Lấy ngày giao dịch lớn nhất trong DB → mốc cắt động (báo cáo mục 4.3.1)."""
    with engine.connect() as c:
        d = c.execute(text("SELECT MAX(t_dat) FROM transactions")).scalar()
    if d is None:
        raise RuntimeError("Bảng transactions trống — không có dữ liệu để huấn luyện.")
    return d


def extract_customer_features(
    cutoff_date: date,
    sample_size: int | None = None,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Trả về DataFrame một dòng / khách hàng với các cột:
      customer_id, age, total_items, frequency, monetary, avg_price,
      pct_online, pct_ladieswear, pct_divided, pct_menswear, pct_baby,
      pct_sport, recency_days
    """
    sql = _read_section("Q1:")
    df = pd.read_sql(text(sql), engine, params={"cutoff_date": cutoff_date})

    # Null-fill: khách có trong customers nhưng chưa giao dịch nào trước cutoff
    pct_cols = [c for c in df.columns if c.startswith("pct_")]
    df[pct_cols] = df[pct_cols].fillna(0.0)
    df["avg_price"] = df["avg_price"].fillna(0.0)
    df["recency_days"] = df["recency_days"].fillna(9999).astype(int)
    df["age"] = df["age"].fillna(df["age"].median()).astype(int)

    if sample_size and len(df) > sample_size:
        df = df.sample(sample_size, random_state=random_state).reset_index(drop=True)
    return df


def extract_baskets(cluster_id: int) -> list[list[str]]:
    """Trả về danh sách giỏ hàng (mỗi giỏ là list product_group_name)."""
    sql = _read_section("Q2:")
    with engine.connect() as c:
        rows = c.execute(text(sql), {"cluster_id": cluster_id}).fetchall()
    return [list(r.items) for r in rows]


def extract_buy_labels(cutoff_date: date, window_days: int = 7) -> set[str]:
    """Tập customer_id có ít nhất 1 giao dịch trong cửa sổ (cutoff, cutoff+window]."""
    sql = _read_section("Q3:")
    with engine.connect() as c:
        rows = c.execute(
            text(sql),
            {"cutoff_date": cutoff_date, "window_days": window_days},
        ).fetchall()
    return {r[0] for r in rows}


def build_l3_dataset(
    cutoff_date: date | None = None,
    window_days: int = 7,
    sample_size: int | None = None,
) -> tuple[pd.DataFrame, pd.Series, date]:
    """
    Lắp ráp tập dữ liệu Layer 3:
      X: đặc trưng (RFM + Fashion DNA) tính tới cutoff_date
      y: 1 nếu khách mua trong (cutoff, cutoff+window], else 0
    """
    if cutoff_date is None:
        cutoff_date = latest_cutoff_date() - timedelta(days=window_days)

    df = extract_customer_features(cutoff_date, sample_size=sample_size)
    buyers = extract_buy_labels(cutoff_date, window_days=window_days)
    df["will_buy"] = df["customer_id"].isin(buyers).astype(int)

    feature_cols = [
        "recency_days", "frequency", "monetary", "avg_price",
        "pct_online", "pct_ladieswear", "pct_divided",
        "pct_menswear", "pct_baby", "pct_sport",
    ]
    X = df[feature_cols].copy()
    y = df["will_buy"].copy()
    # giữ customer_id để log dự đoán → đính kèm như attribute
    X.attrs["customer_ids"] = df["customer_id"].tolist()
    return X, y, cutoff_date
