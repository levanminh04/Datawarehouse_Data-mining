"""
Lớp 1 — Phân cụm Fashion DNA bằng K-Means.

Đặc trưng: 7 biến (5 tỉ trọng ngành hàng + pct_online + avg_price).
Cố ý KHÔNG đưa age và total_items vào — như báo cáo mục 4.1.1 đã giải thích.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

from app.config import settings
from app.db import get_session
from app.ml import registry
from app.ml.features import extract_customer_features, latest_cutoff_date


FEATURE_COLS = [
    "pct_ladieswear", "pct_divided", "pct_menswear",
    "pct_baby", "pct_sport", "pct_online", "avg_price",
]

# Tên cụm dựa trên đặc trưng nổi bật (ngưỡng tỉ trọng)
def _label_cluster(centroid: dict) -> str:
    if centroid["pct_baby"]    > 0.40: return "Family/Moms"
    if centroid["pct_sport"]   > 0.40: return "Sporty Active"
    if centroid["pct_menswear"] > 0.40: return "Menswear"
    if centroid["pct_divided"] > 0.40: return "GenZ Trend"
    if centroid["pct_ladieswear"] > 0.40: return "Classic Ladieswear"
    return f"Mixed (top: {max(centroid, key=centroid.get)})"


def train_kmeans(
    n_clusters: int | None = None,
    sample_size: int | None = None,
    random_state: int = 42,
) -> dict:
    """Huấn luyện K-Means trên một mẫu, sau đó GÁN cụm cho TOÀN BỘ khách hàng."""
    n_clusters = n_clusters or settings.KMEANS_N_CLUSTERS
    sample_size = sample_size or settings.KMEANS_SAMPLE_SIZE
    cutoff = latest_cutoff_date()

    # 1. Lấy mẫu để fit (tránh OOM)
    df_sample = extract_customer_features(cutoff, sample_size=sample_size)
    X = df_sample[FEATURE_COLS].values
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)

    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
    km.fit(Xs)

    # 2. Đặt tên cụm dựa trên centroid (đã chuẩn hoá ngược)
    centroids_orig = scaler.inverse_transform(km.cluster_centers_)
    cluster_labels: dict[int, str] = {}
    for cid in range(n_clusters):
        c_dict = {col: float(centroids_orig[cid, i]) for i, col in enumerate(FEATURE_COLS)}
        cluster_labels[cid] = _label_cluster(c_dict)

    # 3. Suy luận theo BATCH cho toàn bộ khách hàng + ghi vào customer_clusters
    n_total = _assign_all_customers(km, scaler, cluster_labels, cutoff)

    metrics = {
        "n_clusters": n_clusters,
        "inertia_sample": float(km.inertia_),
        "sample_size": int(len(df_sample)),
        "n_total_assigned": int(n_total),
        "cluster_labels": cluster_labels,
    }
    artifact = {
        "kmeans": km,
        "scaler": scaler,
        "feature_cols": FEATURE_COLS,
        "cluster_labels": cluster_labels,
    }
    info = registry.save_model(
        layer="L1_KMEANS",
        artifact=artifact,
        metrics=metrics,
        n_samples_train=len(df_sample),
        cutoff_date=str(cutoff),
    )
    return {**info, "metrics": metrics}


def _assign_all_customers(km, scaler, cluster_labels, cutoff: date, batch: int = 100_000) -> int:
    """Suy luận cụm cho mọi khách hàng theo từng lô, UPSERT vào customer_clusters."""
    df = extract_customer_features(cutoff, sample_size=None)
    if df.empty:
        return 0
    Xs = scaler.transform(df[FEATURE_COLS].values)
    pred = km.predict(Xs).astype(int)
    df["cluster_id"] = pred
    df["cluster_label"] = df["cluster_id"].map(cluster_labels)

    version = pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M%S")
    sql = text("""
        INSERT INTO customer_clusters (customer_id, cluster_id, cluster_label, model_version, assigned_at)
        VALUES (:customer_id, :cluster_id, :cluster_label, :model_version, NOW())
        ON CONFLICT (customer_id) DO UPDATE
        SET cluster_id = EXCLUDED.cluster_id,
            cluster_label = EXCLUDED.cluster_label,
            model_version = EXCLUDED.model_version,
            assigned_at = NOW()
    """)
    with get_session() as s:
        for i in range(0, len(df), batch):
            chunk = df.iloc[i:i+batch]
            s.execute(sql, [
                {
                    "customer_id": r.customer_id,
                    "cluster_id": int(r.cluster_id),
                    "cluster_label": r.cluster_label,
                    "model_version": version,
                }
                for r in chunk.itertuples(index=False)
            ])
    return len(df)


def predict_cluster(customer_id: str) -> dict | None:
    """Tra cứu cụm đã gán; nếu chưa có thì tính on-the-fly từ mô hình active."""
    with get_session() as s:
        row = s.execute(
            text("SELECT cluster_id, cluster_label, model_version, assigned_at "
                 "FROM customer_clusters WHERE customer_id = :cid"),
            {"cid": customer_id},
        ).mappings().first()
    if row:
        return dict(row)

    # Tính lại on-the-fly (khách hàng mới)
    loaded = registry.load_active_model("L1_KMEANS")
    if loaded is None:
        return None
    artifact, _ = loaded

    df = extract_customer_features(latest_cutoff_date(), sample_size=None)
    df = df[df["customer_id"] == customer_id]
    if df.empty:
        return None
    Xs = artifact["scaler"].transform(df[FEATURE_COLS].values)
    cid = int(artifact["kmeans"].predict(Xs)[0])
    return {
        "cluster_id": cid,
        "cluster_label": artifact["cluster_labels"].get(cid, f"cluster_{cid}"),
        "model_version": "on_the_fly",
        "assigned_at": None,
    }
