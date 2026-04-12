-- ============================================================
-- DBMS_SCHEDULER JOB: Chay ETL hang dem luc 2:00 AM
-- Chay voi user: DATAWAREHOUSE
-- ============================================================
--
-- PREREQUISITE (chay voi SYSDBA):
--   GRANT CREATE JOB TO DATAWAREHOUSE;
--
-- ============================================================

-- 1. Xoa job cu neu ton tai
BEGIN
    DBMS_SCHEDULER.DROP_JOB('JOB_ETL_NIGHTLY');
EXCEPTION
    WHEN OTHERS THEN NULL;
END;
/

-- 2. Tao job moi
BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'JOB_ETL_NIGHTLY',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'PKG_ETL_DW.RUN_ALL',
        start_date      => TRUNC(SYSTIMESTAMP) + INTERVAL '26' HOUR,  -- 2 AM ngay mai
        repeat_interval => 'FREQ=DAILY; BYHOUR=2; BYMINUTE=0; BYSECOND=0',
        enabled         => TRUE,
        comments        => 'ETL nightly: Source DBs -> Data Warehouse (Star Schema)'
    );
    DBMS_OUTPUT.PUT_LINE('Job JOB_ETL_NIGHTLY da duoc tao thanh cong.');
END;
/

-- ============================================================
-- KIEM TRA TRANG THAI JOB
-- ============================================================
SELECT job_name, enabled, state, last_start_date, next_run_date, repeat_interval
FROM user_scheduler_jobs
WHERE job_name = 'JOB_ETL_NIGHTLY';

-- ============================================================
-- CAC LENH QUAN LY JOB HUU ICH
-- ============================================================

-- Chay thu ngay (khong doi schedule):
-- EXEC DBMS_SCHEDULER.RUN_JOB('JOB_ETL_NIGHTLY');

-- Tam dung job:
-- EXEC DBMS_SCHEDULER.DISABLE('JOB_ETL_NIGHTLY');

-- Bat lai job:
-- EXEC DBMS_SCHEDULER.ENABLE('JOB_ETL_NIGHTLY');

-- Xem lich su chay:
-- SELECT * FROM user_scheduler_job_run_details
-- WHERE job_name = 'JOB_ETL_NIGHTLY'
-- ORDER BY log_date DESC;

-- Xem log ETL tu bang ETL_LOG:
-- SELECT * FROM ETL_LOG ORDER BY LogID DESC;
