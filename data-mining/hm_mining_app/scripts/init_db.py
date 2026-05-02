"""
Khởi tạo schema PostgreSQL.

Mỗi statement commit độc lập (AUTOCOMMIT) — nếu connection drop hoặc 1
statement nào fail giữa chừng, các statement đã chạy trước KHÔNG bị
rollback. Lần chạy lại sẽ skip nhờ `IF NOT EXISTS` và tiếp từ chỗ dở.

Chạy: python -m scripts.init_db
"""
from pathlib import Path
from sqlalchemy import text

from app.db import engine

SCHEMA_SQL = Path(__file__).parent.parent / "app" / "sql" / "schema.sql"


def _statement_label(stmt: str) -> str:
    """Tạo label gọn cho 1 statement để log progress."""
    s = " ".join(stmt.split())  # collapse whitespace
    return s[:80] + ("…" if len(s) > 80 else "")


def main():
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    print(f"→ Sẽ chạy {len(statements)} statement (AUTOCOMMIT, không lock).")
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for i, stmt in enumerate(statements, 1):
            label = _statement_label(stmt)
            print(f"  [{i}/{len(statements)}] {label}", flush=True)
            conn.execute(text(stmt))
    print("✓ Đã tạo schema thành công.")


if __name__ == "__main__":
    main()
