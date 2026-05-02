"""Pydantic schemas dùng chung cho các endpoint."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------- Ingest ----------
class TransactionIn(BaseModel):
    t_dat: date
    customer_id: str
    article_id: str
    price: float
    sales_channel_id: Literal[1, 2]


class TransactionBatchIn(BaseModel):
    transactions: list[TransactionIn] = Field(..., min_length=1, max_length=10_000)


class CustomerIn(BaseModel):
    customer_id: str
    age: int | None = None
    club_member_status: str | None = None
    fashion_news_frequency: str | None = None
    postal_code: str | None = None


# ---------- Predict ----------
class PredictWillBuyIn(BaseModel):
    customer_id: str


class PredictWillBuyOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    customer_id: str
    will_buy: int
    proba: float
    model_version: str | None = None


class ClusterOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    customer_id: str
    cluster_id: int
    cluster_label: str
    model_version: str | None = None


class RecommendOut(BaseModel):
    customer_id: str
    cluster_id: int
    recommendations: list[dict]


# ---------- Retrain ----------
class RetrainOut(BaseModel):
    layer: str
    version: str
    artifact_path: str
    metrics: dict[str, Any]


# ---------- Metrics dashboard ----------
class ModelVersionRow(BaseModel):
    version: str
    metrics: dict | None
    n_samples_train: int | None
    cutoff_date: date | None
    is_active: bool
    created_at: datetime
