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
        last_tx     = s.execute(text("SELECT MAX(t_dat::date) FROM transactions")).scalar()

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
