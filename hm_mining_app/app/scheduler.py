"""
Scheduler — đáp ứng yêu cầu "hệ thống học liên tục".

Cron mặc định (sửa trong .env):
  L1 K-Means       — Chủ nhật 02:00 (cụm phong cách hiếm khi đổi nhanh)
  L2 Apriori       — Chủ nhật 03:00 (sau khi L1 đã chạy xong)
  L3 Random Forest — Hằng ngày 01:00 (hành vi 7-day rolling, cần update sớm)
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.ml import layer1_kmeans, layer2_apriori, layer3_rf

log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _job_l1():
    try:
        log.info("[CRON] L1 K-Means bắt đầu")
        res = layer1_kmeans.train_kmeans()
        log.info("[CRON] L1 xong: version=%s", res.get("version"))
    except Exception as e:
        log.exception("[CRON] L1 lỗi: %s", e)


def _job_l2():
    try:
        log.info("[CRON] L2 Apriori bắt đầu")
        res = layer2_apriori.train_apriori()
        log.info("[CRON] L2 xong: version=%s", res.get("version"))
    except Exception as e:
        log.exception("[CRON] L2 lỗi: %s", e)


def _job_l3():
    try:
        log.info("[CRON] L3 Random Forest bắt đầu")
        res = layer3_rf.train_random_forest()
        log.info("[CRON] L3 xong: version=%s, AUC=%s",
                 res.get("version"), res.get("metrics", {}).get("auc"))
    except Exception as e:
        log.exception("[CRON] L3 lỗi: %s", e)


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.ENABLE_SCHEDULER:
        log.info("ENABLE_SCHEDULER=false → không khởi động scheduler.")
        return None
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(_job_l1, CronTrigger.from_crontab(settings.RETRAIN_L1_CRON), id="retrain_l1")
    sched.add_job(_job_l2, CronTrigger.from_crontab(settings.RETRAIN_L2_CRON), id="retrain_l2")
    sched.add_job(_job_l3, CronTrigger.from_crontab(settings.RETRAIN_L3_CRON), id="retrain_l3")
    sched.start()
    _scheduler = sched
    log.info("Scheduler đã chạy. Crons: L1=%s | L2=%s | L3=%s",
             settings.RETRAIN_L1_CRON, settings.RETRAIN_L2_CRON, settings.RETRAIN_L3_CRON)
    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
