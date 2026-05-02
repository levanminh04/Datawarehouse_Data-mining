from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

import oracledb

from app.core.config import settings


@contextmanager
def get_connection() -> Generator[oracledb.Connection, None, None]:
    conn = oracledb.connect(
        user=settings.oracle_user,
        password=settings.oracle_password,
        dsn=settings.oracle_dsn,
    )
    try:
        yield conn
    finally:
        conn.close()


def fetch_one(sql: str, params: dict[str, Any] | None = None) -> tuple[Any, ...] | None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or {})
            return cursor.fetchone()


def fetch_all(sql: str, params: dict[str, Any] | None = None) -> list[tuple[Any, ...]]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or {})
            return cursor.fetchall()


def fetch_all_with_columns(
    sql: str, params: dict[str, Any] | None = None
) -> tuple[list[str], list[tuple[Any, ...]]]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or {})
            columns = [col[0] for col in (cursor.description or [])]
            rows = cursor.fetchall()
            return columns, rows


def execute_sql(sql: str, params: dict[str, Any] | None = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or {})
        conn.commit()
