"""
Lớp 2 — Apriori chạy RIÊNG cho từng cụm (Segment-then-Mine, báo cáo mục 4.2.2).

Output: dict {cluster_id: DataFrame các luật kết hợp}.
Khi predict, hệ thống tra cụm khách hàng → trả luật của cụm đó.
"""
from __future__ import annotations

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from sqlalchemy import text

from app.config import settings
from app.db import get_session
from app.ml import registry
from app.ml.features import extract_baskets


def _list_clusters() -> list[int]:
    with get_session() as s:
        rows = s.execute(
            text("SELECT DISTINCT cluster_id FROM customer_clusters ORDER BY cluster_id")
        ).fetchall()
    return [r[0] for r in rows]


def _mine_one(baskets: list[list[str]], min_sup: float, min_conf: float) -> pd.DataFrame:
    if len(baskets) < 50:
        return pd.DataFrame(columns=["antecedents", "consequents", "support", "confidence", "lift"])
    te = TransactionEncoder()
    arr = te.fit_transform(baskets)
    df = pd.DataFrame(arr, columns=te.columns_)
    freq = apriori(df, min_support=min_sup, use_colnames=True, max_len=3)
    if freq.empty:
        return pd.DataFrame(columns=["antecedents", "consequents", "support", "confidence", "lift"])
    rules = association_rules(freq, metric="confidence", min_threshold=min_conf)
    rules = rules[rules["lift"] > 1.0].copy()
    rules["antecedents"] = rules["antecedents"].apply(lambda s: sorted(list(s)))
    rules["consequents"] = rules["consequents"].apply(lambda s: sorted(list(s)))
    return rules.sort_values("lift", ascending=False).head(50).reset_index(drop=True)


def train_apriori(
    min_support: float | None = None,
    min_confidence: float | None = None,
) -> dict:
    """Huấn luyện Apriori cho mỗi cụm và lưu artifact tổng hợp."""
    min_support = min_support or settings.APRIORI_MIN_SUPPORT
    min_confidence = min_confidence or settings.APRIORI_MIN_CONFIDENCE

    rules_per_cluster: dict[int, pd.DataFrame] = {}
    cluster_ids = _list_clusters()
    if not cluster_ids:
        raise RuntimeError("Chưa có customer_clusters — cần chạy Layer 1 trước.")

    for cid in cluster_ids:
        baskets = extract_baskets(cid)
        rules_per_cluster[cid] = _mine_one(baskets, min_support, min_confidence)

    metrics = {
        "min_support": min_support,
        "min_confidence": min_confidence,
        "rules_count_per_cluster": {cid: int(len(df)) for cid, df in rules_per_cluster.items()},
        "total_rules": int(sum(len(df) for df in rules_per_cluster.values())),
    }
    info = registry.save_model(
        layer="L2_APRIORI",
        artifact={"rules_per_cluster": rules_per_cluster},
        metrics=metrics,
        n_samples_train=metrics["total_rules"],
    )
    return {**info, "metrics": metrics}


def recommend_for_basket(cluster_id: int, items: list[str], top_k: int = 5) -> list[dict]:
    """
    Cho 1 cụm + 1 giỏ hàng hiện tại → trả về top_k sản phẩm có lift cao nhất
    mà các luật của cụm đó đề xuất.
    """
    loaded = registry.load_active_model("L2_APRIORI")
    if loaded is None:
        return []
    artifact, _ = loaded
    rules: pd.DataFrame = artifact["rules_per_cluster"].get(cluster_id)
    if rules is None or rules.empty:
        return []

    items_set = set(items)
    matched = rules[rules["antecedents"].apply(lambda ant: set(ant).issubset(items_set))]
    if matched.empty:
        return []

    seen = set()
    out = []
    for _, row in matched.sort_values("lift", ascending=False).iterrows():
        for cons in row["consequents"]:
            if cons in items_set or cons in seen:
                continue
            seen.add(cons)
            out.append({
                "recommend": cons,
                "from_items": row["antecedents"],
                "support": float(row["support"]),
                "confidence": float(row["confidence"]),
                "lift": float(row["lift"]),
            })
            if len(out) >= top_k:
                return out
    return out
