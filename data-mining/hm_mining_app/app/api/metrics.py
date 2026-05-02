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
def sample_customers(per_cluster: int = 1) -> list[dict]:
    """Trả về `per_cluster` customer_id mẫu cho mỗi cụm — phục vụ tab Suy luận
    của dashboard để demo nhanh không cần ngồi nhớ ID hex 64 ký tự.
    """
    if per_cluster < 1 or per_cluster > 20:
        raise HTTPException(400, "per_cluster phải trong khoảng 1-20.")
    with get_session() as s:
        rows = s.execute(text("""
            SELECT customer_id, cluster_id, cluster_label
            FROM (
                SELECT customer_id, cluster_id, cluster_label,
                       ROW_NUMBER() OVER (PARTITION BY cluster_id ORDER BY customer_id) AS rn
                FROM customer_clusters
            ) t
            WHERE rn <= :n
            ORDER BY cluster_id, rn
        """), {"n": per_cluster}).mappings().all()
    return [dict(r) for r in rows]
