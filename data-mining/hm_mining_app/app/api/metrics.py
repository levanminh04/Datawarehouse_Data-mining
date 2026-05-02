"""
Endpoints phục vụ dashboard:
  GET  /metrics/summary                       — overview
  GET  /metrics/models/{layer}                — lịch sử các phiên bản mô hình
  GET  /metrics/cluster-distribution          — phân bố cụm
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db import get_session
from app.ml import registry

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary")
def summary() -> dict:
    with get_session() as s:
        n_customers = s.execute(text("SELECT COUNT(*) FROM customers")).scalar()
        n_articles  = s.execute(text("SELECT COUNT(*) FROM articles")).scalar()
        n_tx        = s.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
        n_clustered = s.execute(text("SELECT COUNT(*) FROM customer_clusters")).scalar()
        # MAX(t_dat) thay vì MAX(t_dat::date) để dùng được idx_tx_date (text)
        last_tx     = s.execute(text("SELECT MAX(t_dat) FROM transactions")).scalar()

    out = {
        "n_customers": n_customers,
        "n_articles": n_articles,
        "n_transactions": n_tx,
        "n_clustered_customers": n_clustered,
        "latest_transaction_date": str(last_tx) if last_tx else None,
        "active_models": {},
    }
    for layer in ("L1_KMEANS", "L2_APRIORI", "L3_RANDOMFOREST"):
        loaded = registry.load_active_model(layer)
        if loaded is None:
            out["active_models"][layer] = None
            continue
        _, reg = loaded
        out["active_models"][layer] = {
            "version": reg["version"],
            "metrics": reg["metrics"],
            "cutoff_date": str(reg["cutoff_date"]) if reg["cutoff_date"] else None,
        }
    return out


@router.get("/models/{layer}")
def models_history(layer: str, limit: int = 20) -> list[dict]:
    if layer not in {"L1_KMEANS", "L2_APRIORI", "L3_RANDOMFOREST"}:
        raise HTTPException(400, "layer phải là L1_KMEANS, L2_APRIORI hoặc L3_RANDOMFOREST.")
    return registry.list_versions(layer, limit=limit)


@router.get("/cluster-distribution")
def cluster_distribution() -> list[dict]:
    with get_session() as s:
        rows = s.execute(text("""
            SELECT cluster_id, cluster_label, COUNT(*) AS n
            FROM   customer_clusters
            GROUP  BY cluster_id, cluster_label
            ORDER  BY n DESC
        """)).mappings().all()
    return [dict(r) for r in rows]


@router.get("/sample-customers")
def sample_customers(per_cluster: int = 5) -> list[dict]:
    """Trả về `per_cluster` khách hàng mẫu cho mỗi cụm với info cơ bản
    (age, club status, tổng số giao dịch, tổng tiền, ngày mua cuối) —
    phục vụ tab Suy luận của dashboard để demo có context.
    """
    if per_cluster < 1 or per_cluster > 20:
        raise HTTPException(400, "per_cluster phải trong khoảng 1-20.")
    with get_session() as s:
        rows = s.execute(text("""
            WITH picked AS (
                SELECT customer_id, cluster_id, cluster_label
                FROM (
                    SELECT customer_id, cluster_id, cluster_label,
                           ROW_NUMBER() OVER (PARTITION BY cluster_id ORDER BY customer_id) AS rn
                    FROM customer_clusters
                ) t
                WHERE rn <= :n
            )
            SELECT
                p.customer_id,
                p.cluster_id,
                p.cluster_label,
                c.age,
                c.club_member_status,
                COALESCE(stats.n_tx, 0)              AS n_transactions,
                ROUND(COALESCE(stats.spent, 0)::numeric, 2) AS total_spent,
                stats.last_purchase
            FROM picked p
            LEFT JOIN customers c ON c.customer_id = p.customer_id
            LEFT JOIN LATERAL (
                SELECT  COUNT(*)        AS n_tx,
                        SUM(price)      AS spent,
                        MAX(t_dat::date) AS last_purchase
                FROM    transactions
                WHERE   customer_id = p.customer_id
            ) stats ON TRUE
            ORDER BY p.cluster_id, p.customer_id
        """), {"n": per_cluster}).mappings().all()
    return [
        {
            **dict(r),
            "total_spent": float(r["total_spent"]) if r["total_spent"] is not None else 0.0,
            "last_purchase": str(r["last_purchase"]) if r["last_purchase"] else None,
        }
        for r in rows
    ]


@router.get("/customer-profile/{customer_id}")
def customer_profile(customer_id: str) -> dict:
    """Profile chi tiết 1 khách hàng — phục vụ card 'thông tin khách' trên dashboard."""
    with get_session() as s:
        cust = s.execute(text("""
            SELECT customer_id, age, club_member_status, fashion_news_frequency, postal_code
            FROM   customers
            WHERE  customer_id = :cid
        """), {"cid": customer_id}).mappings().first()
        if cust is None:
            raise HTTPException(404, f"Không tìm thấy customer_id = {customer_id}")

        stats = s.execute(text("""
            SELECT  COUNT(*)        AS n_transactions,
                    COUNT(DISTINCT t_dat)  AS n_days_active,
                    SUM(price)      AS total_spent,
                    AVG(price)      AS avg_price,
                    MIN(t_dat::date) AS first_purchase,
                    MAX(t_dat::date) AS last_purchase,
                    AVG(CASE WHEN sales_channel_id = 2 THEN 1.0 ELSE 0.0 END) AS pct_online
            FROM    transactions
            WHERE   customer_id = :cid
        """), {"cid": customer_id}).mappings().first()

        top_groups = s.execute(text("""
            SELECT  a.product_group_name AS group_name, COUNT(*) AS n
            FROM    transactions t
            JOIN    articles a USING (article_id)
            WHERE   t.customer_id = :cid
            GROUP   BY a.product_group_name
            ORDER   BY n DESC
            LIMIT 5
        """), {"cid": customer_id}).mappings().all()

        cluster = s.execute(text("""
            SELECT cluster_id, cluster_label, model_version, assigned_at
            FROM   customer_clusters
            WHERE  customer_id = :cid
        """), {"cid": customer_id}).mappings().first()

    return {
        "customer_id": customer_id,
        "demographics": {
            "age": cust["age"],
            "club_member_status": cust["club_member_status"],
            "fashion_news_frequency": cust["fashion_news_frequency"],
            "postal_code": cust["postal_code"],
        },
        "stats": {
            "n_transactions": stats["n_transactions"] or 0,
            "n_days_active":  stats["n_days_active"] or 0,
            "total_spent":    float(stats["total_spent"] or 0),
            "avg_price":      float(stats["avg_price"] or 0),
            "first_purchase": str(stats["first_purchase"]) if stats["first_purchase"] else None,
            "last_purchase":  str(stats["last_purchase"]) if stats["last_purchase"] else None,
            "pct_online":     float(stats["pct_online"] or 0),
        },
        "top_product_groups": [{"group_name": r["group_name"], "n": r["n"]} for r in top_groups],
        "cluster": {
            "cluster_id":    cluster["cluster_id"]    if cluster else None,
            "cluster_label": cluster["cluster_label"] if cluster else None,
        } if cluster else None,
    }
