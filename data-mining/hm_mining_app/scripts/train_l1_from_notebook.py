"""Train L1 (KMeans) theo logic notebook 01_Customer_Clustering.py mới
và đăng ký vào model_registry của app.

Khác với app/ml/layer1_kmeans.py (dùng MiniBatchKMeans + filter rỗng),
script này dùng đúng:
  - SQL của notebook: HAVING COUNT(*) >= 3 (loại khách vãng lai)
  - StandardScaler + plain KMeans (k=5, n_init=10)
  - Đánh giá k với Elbow + Silhouette + Davies-Bouldin trên 200k mẫu
  - Naming rule với threshold 30/40/20% như notebook

Để giữ coverage 1.36M cho bảng customer_clusters, sau khi train xong
script TỰ predict cluster cho TẤT CẢ KH (kể cả <3 giao dịch) bằng
extract_customer_features rồi UPSERT.
"""
from __future__ import annotations

import sys
from pathlib import Path

import datetime
import io

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import engine, get_session  # noqa: E402
from app.ml import registry  # noqa: E402
from app.ml.features import extract_customer_features, latest_cutoff_date  # noqa: E402

OUT_DIR = ROOT.parent / "notebooks" / "outputs_l1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = OUT_DIR / "train_log.txt"


def log(msg: str) -> None:
    print(msg, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ---- Notebook SQL (file 01) ----------------------------------------
QUERY_DNA = """
WITH cust_stats AS (
    SELECT
        t.customer_id,
        COUNT(*) AS total_items,
        AVG(t.price) AS avg_price,
        SUM(CASE WHEN a.index_group_name = 'Ladieswear'    THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_ladieswear,
        SUM(CASE WHEN a.index_group_name = 'Divided'       THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_divided,
        SUM(CASE WHEN a.index_group_name = 'Menswear'      THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_menswear,
        SUM(CASE WHEN a.index_group_name = 'Baby/Children' THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_baby,
        SUM(CASE WHEN a.index_group_name = 'Sport'         THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_sport,
        SUM(CASE WHEN t.sales_channel_id = 2 THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_online
    FROM transactions t
    JOIN articles a ON t.article_id = a.article_id
    GROUP BY t.customer_id
    HAVING COUNT(*) >= 3
)
SELECT cs.*, c.age
FROM   cust_stats cs
JOIN   customers c ON cs.customer_id = c.customer_id
WHERE  c.age IS NOT NULL;
"""

FEATURES = [
    "pct_ladieswear", "pct_divided", "pct_menswear",
    "pct_baby", "pct_sport", "pct_online", "avg_price",
]

K_RANGE = range(2, 8)
# Notebook dùng 200k cho tuning. silhouette_score O(n²) → ~10 phút / k.
# Giảm xuống 30k để rút thời gian (~45× nhanh hơn) mà vẫn ổn định cho việc
# CHỌN k (so sánh tương đối giữa các k chứ không cần tuyệt đối).
SAMPLE_FOR_TUNING = 30_000
K_OPTIMAL = 5
RANDOM_STATE = 42


def _assign_name(row: dict) -> str:
    """Naming rule từ notebook (threshold 30 / 40 / 20%)."""
    if row["pct_baby"] > 30: return "Family/Moms"
    if row["pct_divided"] > 40: return "GenZ Trend"
    if row["pct_menswear"] > 40: return "Menswear"
    if row["pct_sport"] > 20: return "Sporty Active"
    if row["pct_online"] < 50: return "Classic Offline"
    return "Classic Online"


def main() -> None:
    LOG_PATH.unlink(missing_ok=True)

    log("[1/6] Truy vấn Fashion DNA (HAVING COUNT(*) >= 3)…")
    df_dna = pd.read_sql(text(QUERY_DNA), engine)
    log(f"      → {len(df_dna):,} khách hàng có ≥3 giao dịch.")

    log("[2/6] Standardize + tuning k với Elbow / Silhouette / Davies-Bouldin…")
    X = df_dna[FEATURES].copy()
    scaler = StandardScaler().fit(X)
    X_scaled = scaler.transform(X)

    sample_size = min(SAMPLE_FOR_TUNING, X_scaled.shape[0])
    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(X_scaled.shape[0], sample_size, replace=False)
    X_sample = X_scaled[idx]

    inertia, silhouette, davies_bouldin = [], [], []
    for k in K_RANGE:
        km = MiniBatchKMeans(n_clusters=k, batch_size=2048, random_state=RANDOM_STATE, n_init=10)
        labels = km.fit_predict(X_sample)
        inertia.append(km.inertia_)
        silhouette.append(silhouette_score(X_sample, labels))
        davies_bouldin.append(davies_bouldin_score(X_sample, labels))
        log(f"      k={k} | inertia={km.inertia_:.1f} | silhouette={silhouette[-1]:.4f} | DB={davies_bouldin[-1]:.4f}")

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    axes[0].plot(list(K_RANGE), inertia, marker="o", color="b")
    axes[0].set_title("Elbow (Inertia)"); axes[0].set_xlabel("k"); axes[0].grid(True)
    axes[1].plot(list(K_RANGE), silhouette, marker="s", color="g")
    axes[1].set_title("Silhouette (cao = tốt)"); axes[1].set_xlabel("k"); axes[1].grid(True)
    axes[2].plot(list(K_RANGE), davies_bouldin, marker="^", color="r")
    axes[2].set_title("Davies-Bouldin (thấp = tốt)"); axes[2].set_xlabel("k"); axes[2].grid(True)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "k_evaluation_metrics.png", dpi=300)
    plt.close(fig)
    log(f"      → đã lưu {OUT_DIR/'k_evaluation_metrics.png'}")

    log(f"[3/6] Fit KMeans cuối cùng (k={K_OPTIMAL}) trên {len(X_scaled):,} dòng…")
    kmeans = KMeans(n_clusters=K_OPTIMAL, random_state=RANDOM_STATE, n_init=10)
    df_dna["cluster"] = kmeans.fit_predict(X_scaled)

    profile = df_dna.groupby("cluster").agg({
        "customer_id": "count", "age": "median", "total_items": "median",
        "avg_price": "mean",
        "pct_ladieswear": "mean", "pct_divided": "mean", "pct_menswear": "mean",
        "pct_baby": "mean", "pct_sport": "mean", "pct_online": "mean",
    }).reset_index().rename(columns={"customer_id": "n_customers"})
    profile["pct_of_base"] = (profile["n_customers"] / len(df_dna) * 100).round(1)
    for c in ["pct_ladieswear", "pct_divided", "pct_menswear", "pct_baby", "pct_sport", "pct_online"]:
        profile[c] = (profile[c] * 100).round(1)

    profile["cluster_name"] = profile.apply(lambda r: _assign_name(r), axis=1)
    cluster_map: dict[int, str] = dict(zip(profile["cluster"], profile["cluster_name"]))
    df_dna["cluster_name"] = df_dna["cluster"].map(cluster_map)

    log("\n=== PROFILE CÁC CỤM ===")
    log(profile.to_string())

    df_dna[["customer_id", "cluster", "cluster_name"]].to_csv(OUT_DIR / "customer_clusters.csv", index=False)
    log(f"      → đã lưu {OUT_DIR/'customer_clusters.csv'}")

    plt.figure(figsize=(10, 6))
    sns.barplot(x="cluster_name", y="n_customers", data=profile, palette="viridis")
    plt.title("Số lượng KH theo cụm phong cách")
    plt.xticks(rotation=45); plt.tight_layout()
    plt.savefig(OUT_DIR / "cluster_distribution.png")
    plt.close()
    log(f"      → đã lưu {OUT_DIR/'cluster_distribution.png'}")

    # ---- 4. Predict cho TOÀN BỘ KH (kể cả <3 giao dịch) ---------
    log("[4/6] Predict cluster cho toàn bộ KH (full coverage 1.36M)…")
    cutoff = latest_cutoff_date()
    df_all = extract_customer_features(cutoff, sample_size=None)
    log(f"      → extract_customer_features: {len(df_all):,} dòng.")

    Xs_all = scaler.transform(df_all[FEATURES].values)
    df_all["cluster_id"] = kmeans.predict(Xs_all).astype(int)
    df_all["cluster_label"] = df_all["cluster_id"].map(cluster_map)

    # ---- 5. TRUNCATE + COPY customer_clusters --------------------
    # COPY FROM nhanh hơn execute_values ~50× cho bulk load 1M+ rows.
    # Tất cả nằm trong 1 transaction: nếu COPY fail, TRUNCATE rollback.
    log("[5/6] TRUNCATE + COPY customer_clusters (atomic)…")
    version_for_table = pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M%S")
    ts = datetime.datetime.utcnow().isoformat(sep=" ", timespec="seconds")

    buf = io.StringIO()
    for r in df_all.itertuples(index=False):
        label = (r.cluster_label or "").replace("\t", " ").replace("\n", " ")
        buf.write(f"{r.customer_id}\t{int(r.cluster_id)}\t{label}\t{version_for_table}\t{ts}\n")
    buf.seek(0)

    raw = engine.raw_connection()
    try:
        with raw.cursor() as cur:
            cur.execute("TRUNCATE customer_clusters")
            cur.copy_from(
                buf, "customer_clusters",
                columns=("customer_id", "cluster_id", "cluster_label", "model_version", "assigned_at"),
            )
        raw.commit()
    finally:
        raw.close()
    log(f"      → đã COPY {len(df_all):,} dòng (model_version={version_for_table}).")

    # ---- 6. Save artifact + register -----------------------------
    log("[6/6] Lưu artifact + đăng ký vào model_registry…")
    artifact = {
        "kmeans": kmeans,
        "scaler": scaler,
        "feature_cols": FEATURES,
        "cluster_labels": cluster_map,
    }
    metrics = {
        "n_clusters": K_OPTIMAL,
        "inertia_full": float(kmeans.inertia_),
        "k_tuning": {
            "k_range": list(K_RANGE),
            "inertia": [float(x) for x in inertia],
            "silhouette": [float(x) for x in silhouette],
            "davies_bouldin": [float(x) for x in davies_bouldin],
        },
        "training_size": int(len(df_dna)),
        "n_total_assigned": int(len(df_all)),
        "cluster_labels": cluster_map,
        "cluster_sizes": profile.set_index("cluster_name")["n_customers"].to_dict(),
        "training_mode": "batch",
        "source": "notebook_01_Customer_Clustering.py",
        "filter": "HAVING COUNT(*) >= 3",
    }
    info = registry.save_model(
        layer="L1_KMEANS",
        artifact=artifact,
        metrics=metrics,
        n_samples_train=len(df_dna),
        cutoff_date=str(cutoff),
        is_incremental=False,
    )
    for k, v in info.items():
        log(f"  {k}: {v}")
    log("\n=== L1 TRAINING DONE ===")


if __name__ == "__main__":
    main()
