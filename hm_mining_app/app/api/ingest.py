"""
Endpoint nhập dữ liệu mới — phục vụ yêu cầu "hệ thống thu thập được dữ liệu".

POST /ingest/customer       — đăng ký khách hàng mới
POST /ingest/transactions   — nhận lô giao dịch (batch tới 10k dòng)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.db import get_session
from app.schemas import CustomerIn, TransactionBatchIn

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/customer", status_code=status.HTTP_201_CREATED)
def ingest_customer(payload: CustomerIn) -> dict:
    """Đăng ký khách hàng. Idempotent — đã tồn tại thì update."""
    sql = text("""
        INSERT INTO customers (customer_id, age, club_member_status,
                               fashion_news_frequency, postal_code)
        VALUES (:customer_id, :age, :club_member_status,
                :fashion_news_frequency, :postal_code)
        ON CONFLICT (customer_id) DO UPDATE
        SET age = COALESCE(EXCLUDED.age, customers.age),
            club_member_status = COALESCE(EXCLUDED.club_member_status, customers.club_member_status),
            fashion_news_frequency = COALESCE(EXCLUDED.fashion_news_frequency, customers.fashion_news_frequency),
            postal_code = COALESCE(EXCLUDED.postal_code, customers.postal_code)
    """)
    with get_session() as s:
        s.execute(sql, payload.model_dump())
    return {"status": "ok", "customer_id": payload.customer_id}


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def ingest_transactions(payload: TransactionBatchIn) -> dict:
    """Insert hàng loạt giao dịch. FK đến customers/articles phải tồn tại."""
    rows = [t.model_dump() for t in payload.transactions]

    # Kiểm tra trước customer_id và article_id còn thiếu
    customer_ids = {r["customer_id"] for r in rows}
    article_ids = {r["article_id"] for r in rows}
    with get_session() as s:
        existing_customers = {
            row[0] for row in s.execute(
                text("SELECT customer_id FROM customers WHERE customer_id = ANY(:ids)"),
                {"ids": list(customer_ids)},
            ).fetchall()
        }
        existing_articles = {
            row[0] for row in s.execute(
                text("SELECT article_id FROM articles WHERE article_id = ANY(:ids)"),
                {"ids": list(article_ids)},
            ).fetchall()
        }

    missing_customers = customer_ids - existing_customers
    missing_articles = article_ids - existing_articles
    if missing_customers or missing_articles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Một số customer_id hoặc article_id chưa tồn tại — hãy gọi /ingest/customer trước.",
                "missing_customers": sorted(missing_customers)[:20],
                "missing_articles": sorted(missing_articles)[:20],
            },
        )

    insert_sql = text("""
        INSERT INTO transactions (t_dat, customer_id, article_id, price, sales_channel_id)
        VALUES (:t_dat, :customer_id, :article_id, :price, :sales_channel_id)
    """)
    with get_session() as s:
        s.execute(insert_sql, rows)
    return {"status": "ok", "inserted": len(rows)}
