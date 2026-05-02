"""
Endpoint kích hoạt retrain thủ công (kèm scheduler tự động chạy nền).
Dùng BackgroundTasks để không block HTTP request.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.ml import layer1_kmeans, layer2_apriori, layer3_rf

router = APIRouter(prefix="/retrain", tags=["retrain"])
log = logging.getLogger(__name__)


def _run_l1():
    log.info("Bắt đầu retrain L1_KMEANS")
    res = layer1_kmeans.train_kmeans()
    log.info("Hoàn tất L1: %s", res)

def _run_l2():
    log.info("Bắt đầu retrain L2_APRIORI")
    res = layer2_apriori.train_apriori()
    log.info("Hoàn tất L2: %s", res)

def _run_l3():
    log.info("Bắt đầu retrain L3_RANDOMFOREST")
    res = layer3_rf.train_random_forest()
    log.info("Hoàn tất L3: %s", res)


@router.post("/layer1")
def retrain_layer1(background: BackgroundTasks) -> dict:
    background.add_task(_run_l1)
    return {"status": "scheduled", "layer": "L1_KMEANS"}


@router.post("/layer2")
def retrain_layer2(background: BackgroundTasks) -> dict:
    background.add_task(_run_l2)
    return {"status": "scheduled", "layer": "L2_APRIORI"}


@router.post("/layer3")
def retrain_layer3(background: BackgroundTasks) -> dict:
    background.add_task(_run_l3)
    return {"status": "scheduled", "layer": "L3_RANDOMFOREST"}


@router.post("/all")
def retrain_all(background: BackgroundTasks) -> dict:
    """Chạy lần lượt L1 → L2 (cần cụm) → L3."""
    def _chain():
        _run_l1()
        _run_l2()
        _run_l3()
    background.add_task(_chain)
    return {"status": "scheduled", "layers": ["L1", "L2", "L3"]}
