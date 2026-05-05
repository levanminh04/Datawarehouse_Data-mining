"""
Lớp 3 — Dự báo will_buy_7d bằng Random Forest.

Tham số khớp đúng báo cáo mục 4.3.2:
    class_weight='balanced' → ép mô hình chú ý lớp 1 (chỉ ~5%).
    max_samples=0.4         → mỗi cây train trên 40% mẫu (chống overfit).
    max_depth=8             → giới hạn độ sâu.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

from app.config import settings
from app.ml import registry
from app.ml.features import build_l3_dataset


def train_random_forest(
    cutoff_date: date | None = None,
    sample_size: int | None = None,
    window_days: int | None = None,
    random_state: int = 42,
) -> dict:
    sample_size = sample_size or settings.RF_SAMPLE_SIZE
    window_days = window_days or settings.RF_PREDICTION_WINDOW_DAYS

    X, y, used_cutoff = build_l3_dataset(
        cutoff_date=cutoff_date,
        window_days=window_days,
        sample_size=sample_size,
    )
    feature_cols = list(X.columns)

    # Stratify để giữ nguyên tỉ lệ ~5% lớp 1
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y,
    )

    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        max_samples=0.4,
        class_weight="balanced",
        n_jobs=-1,
        random_state=random_state,
    )
    rf.fit(X_train.values, y_train.values)

    # Cây quyết định nông để diễn giải (báo cáo mục 4.3.2.a)
    dtree = DecisionTreeClassifier(
        max_depth=4, class_weight="balanced", random_state=random_state,
    )
    dtree.fit(X_train.values, y_train.values)

    proba = rf.predict_proba(X_test.values)[:, 1]
    pred = (proba >= 0.5).astype(int)
    auc = float(roc_auc_score(y_test, proba))
    p, r, f1, _ = precision_recall_fscore_support(y_test, pred, average=None, zero_division=0)
    report = classification_report(y_test, pred, output_dict=True, zero_division=0)

    feature_importance = sorted(
        [{"feature": f, "importance": float(imp)}
         for f, imp in zip(feature_cols, rf.feature_importances_)],
        key=lambda d: d["importance"], reverse=True,
    )

    metrics = {
        "auc": auc,
        "precision_class0": float(p[0]),
        "precision_class1": float(p[1]) if len(p) > 1 else 0.0,
        "recall_class0":    float(r[0]),
        "recall_class1":    float(r[1]) if len(r) > 1 else 0.0,
        "f1_class1":        float(f1[1]) if len(f1) > 1 else 0.0,
        "support_class1":   int(report.get("1", {}).get("support", 0)),
        "positive_rate":    float(y.mean()),
        "feature_importance": feature_importance,
        "window_days": window_days,
    }

    artifact = {
        "rf": rf,
        "dtree": dtree,
        "feature_cols": feature_cols,
    }
    metrics["training_mode"] = "batch"
    info = registry.save_model(
        layer="L3_RANDOMFOREST",
        artifact=artifact,
        metrics=metrics,
        n_samples_train=len(X_train),
        cutoff_date=str(used_cutoff),
        is_incremental=False,
    )
    return {**info, "metrics": metrics}


def train_rf_incremental(
    n_new_trees: int = 20,
    cutoff_date: date | None = None,
    sample_size: int | None = None,
    window_days: int | None = None,
    random_state: int = 42,
) -> dict:
    """Học tiếp (incremental) — load RF active, dùng warm_start để THÊM
    n_new_trees cây mới vào ensemble. Cây cũ giữ nguyên, chỉ cây mới fit
    trên data hiện tại.
    """
    loaded = registry.load_active_model("L3_RANDOMFOREST")
    if loaded is None:
        raise ValueError(
            "Chưa có phiên bản L3 active để học tiếp. "
            "Gọi train_random_forest() trước để có model nền (cold start)."
        )
    artifact, parent_row = loaded
    parent_version = parent_row["version"]

    rf: RandomForestClassifier = artifact["rf"]
    feature_cols = artifact["feature_cols"]

    sample_size = sample_size or settings.RF_SAMPLE_SIZE
    window_days = window_days or settings.RF_PREDICTION_WINDOW_DAYS

    X, y, used_cutoff = build_l3_dataset(
        cutoff_date=cutoff_date,
        window_days=window_days,
        sample_size=sample_size,
    )
    # Sắp xếp cột khớp với feature_cols cũ (đề phòng order khác)
    X = X[feature_cols]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y,
    )

    # CORE: warm_start=True + tăng n_estimators → fit chỉ thêm n_new_trees cây
    n_old = rf.n_estimators
    rf.set_params(warm_start=True, n_estimators=n_old + n_new_trees)
    rf.fit(X_train.values, y_train.values)

    # Đánh giá lại trên test
    proba = rf.predict_proba(X_test.values)[:, 1]
    pred = (proba >= 0.5).astype(int)
    auc = float(roc_auc_score(y_test, proba))
    p, r, f1, _ = precision_recall_fscore_support(y_test, pred, average=None, zero_division=0)

    feature_importance = sorted(
        [{"feature": f, "importance": float(imp)}
         for f, imp in zip(feature_cols, rf.feature_importances_)],
        key=lambda d: d["importance"], reverse=True,
    )

    metrics = {
        "auc": auc,
        "precision_class1": float(p[1]) if len(p) > 1 else 0.0,
        "recall_class1":    float(r[1]) if len(r) > 1 else 0.0,
        "f1_class1":        float(f1[1]) if len(f1) > 1 else 0.0,
        "positive_rate":    float(y.mean()),
        "feature_importance": feature_importance,
        "window_days": window_days,
        "training_mode": "incremental",
        "n_trees_before": n_old,
        "n_trees_after":  rf.n_estimators,
        "n_new_trees":    n_new_trees,
        "parent_version": parent_version,
    }
    artifact_new = {
        "rf": rf,
        "dtree": artifact.get("dtree"),  # giữ nguyên dtree cũ — chỉ để diễn giải
        "feature_cols": feature_cols,
    }
    info = registry.save_model(
        layer="L3_RANDOMFOREST",
        artifact=artifact_new,
        metrics=metrics,
        n_samples_train=len(X_train),
        cutoff_date=str(used_cutoff),
        parent_version=parent_version,
        is_incremental=True,
    )
    return {**info, "metrics": metrics}


def predict_will_buy(features: dict) -> dict | None:
    """features là dict các cột giống feature_cols. Trả về {will_buy, proba}."""
    loaded = registry.load_active_model("L3_RANDOMFOREST")
    if loaded is None:
        return None
    artifact, _ = loaded
    rf = artifact["rf"]
    cols = artifact["feature_cols"]
    x = np.array([[features.get(c, 0.0) for c in cols]], dtype=float)
    proba = float(rf.predict_proba(x)[0, 1])
    return {"will_buy": int(proba >= 0.5), "proba": proba}
