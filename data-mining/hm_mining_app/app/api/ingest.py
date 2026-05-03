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
    """Đăng ký khách hàng. Idempotent — đã tồn tại thì update.

    Note: bảng `customers` trên DB không có UNIQUE/PRIMARY KEY trên
    customer_id (do load CSV không cast constraint), nên không dùng
    được `ON CONFLICT`. Dùng SELECT-then-INSERT-or-UPDATE thay thế.
    """
    data = payload.model_dump()
    with get_session() as s:
        exists = s.execute(
            text("SELECT 1 FROM customers WHERE customer_id = :customer_id"),
            {"customer_id": payload.customer_id},
        ).first() is not None

        if exists:
            s.execute(text("""
                UPDATE customers
                SET age                    = COALESCE(:age, age),
                    club_member_status     = COALESCE(:club_member_status, club_member_status),
                    fashion_news_frequency = COALESCE(:fashion_news_frequency, fashion_news_frequency),
                    postal_code            = COALESCE(:postal_code, postal_code)
                WHERE customer_id = :customer_id
            """), data)
            action = "updated"
        else:
            s.execute(text("""
                INSERT INTO customers (customer_id, age, club_member_status,
                                       fashion_news_frequency, postal_code)
                VALUES (:customer_id, :age, :club_member_status,
                        :fashion_news_frequency, :postal_code)
            """), data)
            action = "inserted"
    return {"status": "ok", "action": action, "customer_id": payload.customer_id}


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def ingest_transactions(payload: TransactionBatchIn) -> dict:
    """Insert hàng loạt giao dịch. customer_id/article_id phải tồn tại.

    Note: cột `articles.article_id` trên DB là INTEGER (do load CSV của
    levanminh04). Pydantic schema chấp nhận str cho thân thiện input,
    nhưng app cast sang int trước khi query/INSERT.
    """
    rows = [t.model_dump() for t in payload.transactions]
    for r in rows:
        try:
            r["article_id"] = int(r["article_id"])
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"article_id phải parse được sang số nguyên: {r['article_id']!r}",
            )

    customer_ids = {r["customer_id"] for r in rows}
    article_ids  = {r["article_id"] for r in rows}
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
    missing_articles  = article_ids - existing_articles
    if missing_customers or missing_articles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Một số customer_id hoặc article_id chưa tồn tại — hãy gọi /ingest/customer trước hoặc check article_id.",
                "missing_customers": sorted(missing_customers)[:20],
                "missing_articles":  [str(a) for a in sorted(missing_articles)[:20]],
            },
        )

    insert_sql = text("""
        INSERT INTO transactions (t_dat, customer_id, article_id, price, sales_channel_id)
        VALUES (:t_dat, :customer_id, :article_id, :price, :sales_channel_id)
    """)
    with get_session() as s:
        s.execute(insert_sql, rows)
    return {"status": "ok", "inserted": len(rows)}
