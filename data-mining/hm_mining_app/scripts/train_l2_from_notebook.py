"""Train L2 (Apriori) theo logic notebook 02_Association_Rules.py mới
và đăng ký vào model_registry.

Khác với app/ml/layer2_apriori.py:
  - Basket SQL: GROUP BY (customer, ngày), HAVING ≥2 product_group_name
    KHÔNG join customer_clusters trong SQL (notebook merge ở Python)
  - Lọc theo cluster_name (string) sau khi merge với customer_clusters table
  - min_support = 0.01, min_lift = 1.2, top 5 luật / cụm

Yêu cầu: chạy SAU train_l1_from_notebook.py (cần customer_clusters mới).

Output:
  notebooks/outputs_l2/fashion_association_rules.csv  (notebook compat)
  notebooks/outputs_l2/train_log.txt
  hm_mining_app/models_store/L2_APRIORI/v<ts>.joblib  (auto)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import engine  # noqa: E402
from app.ml import registry  # noqa: E402

OUT_DIR = ROOT.parent / "notebooks" / "outputs_l2"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = OUT_DIR / "train_log.txt"


def log(msg: str) -> None:
    print(msg, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ---- Notebook SQL (file 02) ----------------------------------------
QUERY_BASKETS = """
SELECT
    t.customer_id,
    t.t_dat::date AS purchase_date,
    ARRAY_AGG(DISTINCT a.product_group_name) AS basket
FROM transactions t
JOIN articles a ON t.article_id = a.article_id
GROUP BY t.customer_id, t.t_dat::date
HAVING COUNT(DISTINCT a.product_group_name) >= 2;
"""

MIN_SUPPORT = 0.01
MIN_LIFT = 1.2
TOP_N = 5


def mine_rules(baskets: pd.Series) -> pd.DataFrame:
    """Trả về DataFrame top_n luật, sort theo lift desc."""
    if len(baskets) < 100:
        return pd.DataFrame(columns=["antecedents", "consequents", "support", "confidence", "lift"])

    te = TransactionEncoder()
    arr = te.fit(baskets).transform(baskets)
    df_te = pd.DataFrame(arr, columns=te.columns_)

    freq = apriori(df_te, min_support=MIN_SUPPORT, use_colnames=True)
    if freq.empty:
        return pd.DataFrame(columns=["antecedents", "consequents", "support", "confidence", "lift"])

    rules = association_rules(freq, metric="lift", min_threshold=MIN_LIFT)
    rules["antecedents"] = rules["antecedents"].apply(lambda s: sorted(list(s)))
    rules["consequents"] = rules["consequents"].apply(lambda s: sorted(list(s)))
    rules = rules.sort_values(["lift", "confidence"], ascending=[False, False])
    return rules[["antecedents", "consequents", "support", "confidence", "lift"]].head(TOP_N).reset_index(drop=True)


def main() -> None:
    LOG_PATH.unlink(missing_ok=True)

    log("[1/4] Truy vấn baskets từ Postgres (≥2 sản phẩm/ngày)…")
    df_baskets = pd.read_sql(text(QUERY_BASKETS), engine)
    log(f"      → {len(df_baskets):,} baskets.")

    # Postgres array → Python list (pandas tự ra list, an toàn fallback)
    if not df_baskets.empty and not isinstance(df_baskets["basket"].iloc[0], list):
        log("      → cast basket cột về list…")
        df_baskets["basket"] = df_baskets["basket"].apply(
            lambda v: v if isinstance(v, list) else list(v)
        )

    log("[2/4] Lấy mapping customer_id → cluster_label từ customer_clusters…")
    df_clusters = pd.read_sql(
        text("SELECT customer_id, cluster_id, cluster_label FROM customer_clusters"),
        engine,
    )
    log(f"      → {len(df_clusters):,} mappings.")

    df_baskets = df_baskets.merge(
        df_clusters[["customer_id", "cluster_id", "cluster_label"]],
        on="customer_id",
        how="inner",
    )
    log(f"      → sau merge: {len(df_baskets):,} baskets có cluster.")

    # ---- 3. Mine apriori per cluster ---------------------------
    log("[3/4] Mine Apriori theo TỪNG cụm (min_sup=0.01, min_lift=1.2, top 5)…")
    rules_per_cluster_id: dict[int, pd.DataFrame] = {}
    rules_count_per_cluster: dict[int, int] = {}
    cluster_label_map: dict[int, str] = {}
    all_dfs: list[pd.DataFrame] = []

    for (cid, cname), grp in df_baskets.groupby(["cluster_id", "cluster_label"]):
        log(f"      [cluster_id={cid} / {cname}] {len(grp):,} baskets…")
        rules_df = mine_rules(grp["basket"])
        rules_per_cluster_id[int(cid)] = rules_df
        rules_count_per_cluster[int(cid)] = int(len(rules_df))
        cluster_label_map[int(cid)] = cname
        if not rules_df.empty:
            tmp = rules_df.copy()
            tmp.insert(0, "Style_Cluster", cname)
            tmp.insert(0, "cluster_id", cid)
            all_dfs.append(tmp)
            log(f"         → {len(rules_df)} luật mạnh.")
        else:
            log("         → không có luật nào đạt ngưỡng.")

    csv_path = OUT_DIR / "fashion_association_rules.csv"
    if all_dfs:
        pd.concat(all_dfs, ignore_index=True).to_csv(csv_path, index=False)
        log(f"      → đã lưu {csv_path}")
    else:
        log("      → không có luật nào, bỏ qua CSV.")

    # ---- 4. Save artifact + register ---------------------------
    log("[4/4] Lưu artifact + đăng ký vào model_registry…")
    artifact = {
        "rules_per_cluster": rules_per_cluster_id,
        "cluster_labels": cluster_label_map,
    }
    metrics = {
        "min_support": MIN_SUPPORT,
        "min_lift": MIN_LIFT,
        "top_n_per_cluster": TOP_N,
        "rules_count_per_cluster": {str(k): v for k, v in rules_count_per_cluster.items()},
        "total_rules": int(sum(rules_count_per_cluster.values())),
        "n_baskets": int(len(df_baskets)),
        "training_mode": "batch",
        "source": "notebook_02_Association_Rules.py",
    }
    info = registry.save_model(
        layer="L2_APRIORI",
        artifact=artifact,
        metrics=metrics,
        n_samples_train=metrics["total_rules"],
        cutoff_date=None,
        is_incremental=False,
    )
    for k, v in info.items():
        log(f"  {k}: {v}")
    log("\n=== L2 TRAINING DONE ===")


if __name__ == "__main__":
    main()
