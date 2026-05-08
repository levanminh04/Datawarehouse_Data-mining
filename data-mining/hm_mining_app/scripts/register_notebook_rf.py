"""Đăng ký rf_model.pkl đã train từ notebook 03 vào model_registry của app.

Wrap sklearn RF thuần (notebook format) thành dict format mà
app/ml/layer3_rf.py mong đợi: {"rf", "dtree", "feature_cols"}.

Notebook dùng 9 features (thiếu pct_sport so với app), nên feature_cols
được lưu đúng 9 cột — predict_will_buy sẽ chỉ request 9 cột này.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ml import registry  # noqa: E402


NOTEBOOK_OUTPUTS = ROOT.parent / "notebooks" / "outputs_l3"
RF_PKL = NOTEBOOK_OUTPUTS / "rf_model.pkl"
DT_PKL = NOTEBOOK_OUTPUTS / "dt_model.pkl"

NOTEBOOK_FEATURE_COLS = [
    "recency_days", "frequency", "monetary", "avg_price",
    "pct_ladieswear", "pct_divided", "pct_menswear", "pct_baby", "pct_online",
]

# Metrics lấy từ train_log.txt sau khi chạy 03_Purchase_Prediction.py
NOTEBOOK_METRICS = {
    "auc": 0.798666,
    "auc_train": 0.820918,
    "generalization_gap": 0.022252,
    "precision_class0": 0.98,
    "precision_class1": 0.12,
    "recall_class0": 0.71,
    "recall_class1": 0.748863,
    "f1_class1": 0.21,
    "support_class1": 3078,
    "positive_rate": 0.0511,
    "window_days": 7,
    "training_mode": "batch",
    "source": "notebook_03_Purchase_Prediction.py",
    "comparison_models": {
        "logistic_regression": {"auc_test": 0.793719, "recall": 0.798246},
        "decision_tree":       {"auc_test": 0.780054, "recall": 0.775179},
        "random_forest":       {"auc_test": 0.798666, "recall": 0.748863},
        "xgboost":             {"auc_test": 0.784450, "recall": 0.701754},
    },
}

CUTOFF_DATE = "2020-09-15"
N_SAMPLES_TRAIN = 240_000


def main() -> None:
    if not RF_PKL.exists():
        sys.exit(f"Không tìm thấy {RF_PKL}. Hãy chạy notebook 03 trước.")

    rf = joblib.load(RF_PKL)
    dtree = joblib.load(DT_PKL) if DT_PKL.exists() else None

    feature_importance = sorted(
        [{"feature": f, "importance": float(imp)}
         for f, imp in zip(NOTEBOOK_FEATURE_COLS, rf.feature_importances_)],
        key=lambda d: d["importance"], reverse=True,
    )
    metrics = {**NOTEBOOK_METRICS, "feature_importance": feature_importance}

    artifact = {
        "rf": rf,
        "dtree": dtree,
        "feature_cols": NOTEBOOK_FEATURE_COLS,
    }

    info = registry.save_model(
        layer="L3_RANDOMFOREST",
        artifact=artifact,
        metrics=metrics,
        n_samples_train=N_SAMPLES_TRAIN,
        cutoff_date=CUTOFF_DATE,
        is_incremental=False,
    )
    print("Đã đăng ký:")
    for k, v in info.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
