"""
Sổ đăng ký mô hình — phục vụ "học liên tục".

Mỗi lần retrain:
    1. Lưu file joblib vào MODEL_STORE/{layer}/v{ts}.joblib
    2. INSERT 1 dòng vào model_registry với metrics
    3. Cập nhật is_active=TRUE cho phiên bản mới, FALSE cho phiên bản cũ

Predict luôn nạp phiên bản is_active=TRUE → triển khai zero-downtime.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
from sqlalchemy import text

from app.config import settings
from app.db import get_session


VALID_LAYERS = {"L1_KMEANS", "L2_APRIORI", "L3_RANDOMFOREST"}


def _new_version() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def save_model(
    layer: str,
    artifact: Any,
    metrics: dict,
    n_samples_train: int | None = None,
    cutoff_date: str | None = None,
    parent_version: str | None = None,
    is_incremental: bool = False,
) -> dict:
    """Lưu file joblib + ghi vào model_registry, đánh dấu phiên bản này active.

    parent_version + is_incremental phục vụ "học tiếp" (incremental learning):
    nếu version này dẫn xuất từ model cũ (qua partial_fit / warm_start) thì
    parent_version trỏ tới phiên bản gốc, is_incremental=TRUE.
    """
    if layer not in VALID_LAYERS:
        raise ValueError(f"layer phải thuộc {VALID_LAYERS}, nhận {layer!r}")

    version = _new_version()
    layer_dir = settings.model_store_path / layer
    layer_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = layer_dir / f"v{version}.joblib"
    joblib.dump(artifact, artifact_path)

    with get_session() as s:
        # Hạ active của phiên bản cũ
        s.execute(
            text("UPDATE model_registry SET is_active = FALSE WHERE layer = :layer AND is_active = TRUE"),
            {"layer": layer},
        )
        # Insert phiên bản mới
        s.execute(
            text("""
                INSERT INTO model_registry
                    (layer, version, artifact_path, metrics, n_samples_train,
                     cutoff_date, is_active, parent_version, is_incremental)
                VALUES
                    (:layer, :version, :artifact_path, CAST(:metrics AS JSONB),
                     :n_samples_train, :cutoff_date, TRUE,
                     :parent_version, :is_incremental)
            """),
            {
                "layer": layer,
                "version": version,
                "artifact_path": str(artifact_path),
                "metrics": json.dumps(metrics),
                "n_samples_train": n_samples_train,
                "cutoff_date": cutoff_date,
                "parent_version": parent_version,
                "is_incremental": is_incremental,
            },
        )

    return {
        "layer": layer,
        "version": version,
        "artifact_path": str(artifact_path),
        "parent_version": parent_version,
        "is_incremental": is_incremental,
    }


def load_active_model(layer: str) -> tuple[Any, dict] | None:
    """Trả về (artifact, registry_row) cho phiên bản is_active=TRUE; None nếu chưa có."""
    if layer not in VALID_LAYERS:
        raise ValueError(f"layer không hợp lệ: {layer}")

    with get_session() as s:
        row = s.execute(
            text("""
                SELECT version, artifact_path, metrics, cutoff_date, created_at
                FROM   model_registry
                WHERE  layer = :layer AND is_active = TRUE
                ORDER  BY created_at DESC
                LIMIT  1
            """),
            {"layer": layer},
        ).mappings().first()

    if row is None:
        return None

    artifact = joblib.load(row["artifact_path"])
    return artifact, dict(row)


def list_versions(layer: str, limit: int = 20) -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            text("""
                SELECT version, metrics, n_samples_train, cutoff_date,
                       is_active, created_at
                FROM   model_registry
                WHERE  layer = :layer
                ORDER  BY created_at DESC
                LIMIT  :limit
            """),
            {"layer": layer, "limit": limit},
        ).mappings().all()
    return [dict(r) for r in rows]
