"""
Endpoints suy luận:
  GET  /predict/cluster/{customer_id}        — Cụm phong cách (Layer 1)
  GET  /predict/recommend/{customer_id}      — Gợi ý cross-sell (Layer 2)
  GET  /predict/will-buy/{customer_id}       — Xác suất mua 7 ngày tới (Layer 3)
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.db import get_session
from app.ml import layer1_kmeans, layer2_apriori, layer3_rf, registry
from app.ml.features import extract_customer_features, latest_cutoff_date
from app.schemas import ClusterOut, PredictWillBuyOut, RecommendOut

router = APIRouter(prefix="/predict", tags=["predict"])


@router.get("/cluster/{customer_id}", response_model=ClusterOut)
def predict_cluster(customer_id: str) -> ClusterOut:
    res = layer1_kmeans.predict_cluster(customer_id)
    if res is None:
        raise HTTPException(404, "Khách hàng chưa có dữ liệu hoặc Layer 1 chưa được huấn luyện.")
    _log_prediction(customer_id, "L1_KMEANS", res.get("model_version") or "unknown",
                    {"cluster_id": res["cluster_id"]})
    return ClusterOut(
        customer_id=customer_id,
        cluster_id=int(res["cluster_id"]),
        cluster_label=res["cluster_label"] or f"cluster_{res['cluster_id']}",
        model_version=res.get("model_version"),
    )


@router.get("/recommend/{customer_id}", response_model=RecommendOut)
def recommend(customer_id: str, top_k: int = Query(5, ge=1, le=20)) -> RecommendOut:
    cluster = layer1_kmeans.predict_cluster(customer_id)
    if cluster is None:
        raise HTTPException(404, "Cần Layer 1 active + customer tồn tại.")

    # Lấy giỏ hàng hôm nay (hoặc 30 ngày gần nhất nếu hôm nay rỗng)
    with get_session() as s:
        rows = s.execute(text("""
            SELECT DISTINCT a.product_group_name
            FROM transactions t
            JOIN articles a USING (article_id)
            WHERE t.customer_id = :cid
              AND t.t_dat >= CURRENT_DATE - INTERVAL '30 days'
        """), {"cid": customer_id}).fetchall()
    items = [r[0] for r in rows]

    recs = layer2_apriori.recommend_for_basket(int(cluster["cluster_id"]), items, top_k=top_k)
    return RecommendOut(
        customer_id=customer_id,
        cluster_id=int(cluster["cluster_id"]),
        recommendations=recs,
    )


@router.get("/will-buy/{customer_id}", response_model=PredictWillBuyOut)
def predict_will_buy(customer_id: str) -> PredictWillBuyOut:
    loaded = registry.load_active_model("L3_RANDOMFOREST")
    if loaded is None:
        raise HTTPException(404, "Layer 3 chưa được huấn luyện.")
    artifact, reg = loaded

    df = extract_customer_features(latest_cutoff_date(), sample_size=None)
    df = df[df["customer_id"] == customer_id]
    if df.empty:
        raise HTTPException(404, f"Không có dữ liệu cho customer_id={customer_id}.")
    feats = df.iloc[0].to_dict()

    res = layer3_rf.predict_will_buy(feats)
    if res is None:
        raise HTTPException(500, "Mô hình Layer 3 không nạp được.")

    _log_prediction(customer_id, "L3_RANDOMFOREST", reg["version"], res)
    return PredictWillBuyOut(
        customer_id=customer_id,
        will_buy=res["will_buy"],
        proba=res["proba"],
        model_version=reg["version"],
    )


def _log_prediction(customer_id: str, layer: str, version: str, value: dict) -> None:
    with get_session() as s:
        s.execute(
            text("""
                INSERT INTO prediction_log (customer_id, layer, model_version, predicted_value)
                VALUES (:cid, :layer, :ver, CAST(:val AS JSONB))
            """),
            {"cid": customer_id, "layer": layer, "ver": version, "val": json.dumps(value)},
        )
