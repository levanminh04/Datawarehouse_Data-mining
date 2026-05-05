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


# ====================================================================
# INCREMENTAL — "học tiếp" (giữ state cũ, chỉ update với data mới)
# ====================================================================
# Khác với /retrain/* (học lại từ đầu, reset state), nhóm endpoint dưới
# dùng partial_fit (L1 MiniBatchKMeans) hoặc warm_start (L3 RandomForest)
# để cập nhật mô hình cũ mà không reset.
#
# Layer 2 Apriori bản chất là batch — không hỗ trợ học tiếp natively, nên
# bị bỏ qua trong /train/incremental/all.
# ====================================================================

def _run_l1_incremental():
    log.info("Bắt đầu HỌC TIẾP L1_KMEANS (partial_fit)")
    res = layer1_kmeans.train_kmeans_incremental()
    log.info("Hoàn tất L1 incremental: %s", res)

def _run_l3_incremental():
    log.info("Bắt đầu HỌC TIẾP L3_RANDOMFOREST (warm_start)")
    res = layer3_rf.train_rf_incremental()
    log.info("Hoàn tất L3 incremental: %s", res)


@router.post("/incremental/layer1", tags=["retrain"])
def incremental_layer1(background: BackgroundTasks) -> dict:
    """Học tiếp L1: load model active → MiniBatchKMeans.partial_fit → save mới."""
    background.add_task(_run_l1_incremental)
    return {"status": "scheduled", "layer": "L1_KMEANS", "mode": "incremental"}


@router.post("/incremental/layer3", tags=["retrain"])
def incremental_layer3(background: BackgroundTasks) -> dict:
    """Học tiếp L3: load RF active → warm_start thêm 20 cây mới → save mới."""
    background.add_task(_run_l3_incremental)
    return {"status": "scheduled", "layer": "L3_RANDOMFOREST", "mode": "incremental"}


@router.post("/incremental/all", tags=["retrain"])
def incremental_all(background: BackgroundTasks) -> dict:
    """Học tiếp L1 + L3 (Layer 2 Apriori bản chất batch — bỏ qua)."""
    def _chain():
        _run_l1_incremental()
        _run_l3_incremental()
    background.add_task(_chain)
    return {
        "status": "scheduled",
        "layers": ["L1", "L3"],
        "skipped": ["L2 (Apriori is batch-only)"],
        "mode": "incremental",
    }
