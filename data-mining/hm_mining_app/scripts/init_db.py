"""
Khởi tạo schema PostgreSQL.
Chạy: python -m scripts.init_db
"""
from pathlib import Path
from sqlalchemy import text

from app.db import engine

SCHEMA_SQL = Path(__file__).parent.parent / "app" / "sql" / "schema.sql"


def main():
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    print("✓ Đã tạo schema thành công.")


if __name__ == "__main__":
    main()
