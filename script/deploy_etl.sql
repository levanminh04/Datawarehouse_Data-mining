-- ============================================================
-- HUONG DAN TRIEN KHAI ETL DATA WAREHOUSE - DAY DU
-- Oracle XE 21c
-- ============================================================
-- 
-- THU TU THUC HIEN:
--   BUOC 0: Kiem tra prerequisites
--   BUOC 1: Grant quyen (user SYSDBA)
--   BUOC 2: Tao bang DW (user DATAWAREHOUSE)
--   BUOC 3: Compile Package (user DATAWAREHOUSE)
--   BUOC 4: Chay ETL lan dau - Full Load
--   BUOC 5: Kiem tra ket qua
--   BUOC 6: Tao job tu dong (tuy chon)
--   BUOC 7: Test incremental load
--   BUOC 8: Phuong an de phong & Rollback
--
-- ============================================================


-- ************************************************************
-- BUOC 0: KIEM TRA PREREQUISITES
-- Chay voi user DATAWAREHOUSE
-- ************************************************************

-- 0.1 Kiem tra DB Link hoat dong
SELECT * FROM "VanPhongDaiDien"@sqlserver_banhang WHERE ROWNUM <= 3;
-- Ket qua mong doi: 3 row tu SQL Server → DB Link OK
-- Neu loi ORA-02019: khong tim thay DB Link
--   → Can tao PUBLIC DB LINK hoac tao rieng cho DATAWAREHOUSE (xem BUOC 1)

-- 0.2 Kiem tra quyen doc bang Oracle (schema LEVANMINH)
SELECT COUNT(*) AS so_kh FROM LEVANMINH.KHACHHANG;
SELECT COUNT(*) AS so_dl FROM LEVANMINH.KH_DULICH;
SELECT COUNT(*) AS so_bd FROM LEVANMINH.KH_BUUDIEN;
-- Ket qua mong doi: ~44474, ~26684, ~26684
-- Neu loi ORA-00942: chua grant quyen → chay BUOC 1

-- 0.3 Kiem tra bang DW da ton tai chua
SELECT table_name FROM user_tables
WHERE table_name IN ('DIM_TIME','DIM_LOCATION','DIM_PRODUCT','DIM_CUSTOMER',
                     'FACT_INVENTORY','FACT_ORDER','ETL_LOG')
ORDER BY table_name;
-- Neu chua co bang nao → chay BUOC 2


-- ************************************************************
-- BUOC 1: GRANT QUYEN (chay voi user SYSDBA hoac SYSTEM)
-- Chi can chay 1 LAN duy nhat
-- ************************************************************

/*  -- MO COMMENT KHOI NAY VA CHAY VOI SYSDBA --

-- 1.1 Grant quyen co ban cho DATAWAREHOUSE
GRANT CONNECT, RESOURCE TO DATAWAREHOUSE;
GRANT CREATE VIEW TO DATAWAREHOUSE;
GRANT CREATE PROCEDURE TO DATAWAREHOUSE;
GRANT CREATE JOB TO DATAWAREHOUSE;

-- 1.2 Grant SELECT tren bang Oracle nguon
GRANT SELECT ON LEVANMINH.KHACHHANG  TO DATAWAREHOUSE;
GRANT SELECT ON LEVANMINH.KH_DULICH  TO DATAWAREHOUSE;
GRANT SELECT ON LEVANMINH.KH_BUUDIEN TO DATAWAREHOUSE;

-- 1.3 Neu DB Link la PRIVATE cua user khac, tao PUBLIC DB Link:
-- (Chi can neu DATAWAREHOUSE chua co quyen dung sqlserver_banhang)
--
-- CREATE PUBLIC DATABASE LINK sqlserver_banhang
--   CONNECT TO "sa" IDENTIFIED BY "YourPassword"
--   USING '(DESCRIPTION=
--     (ADDRESS=(PROTOCOL=tcp)(HOST=localhost)(PORT=1521))
--     (CONNECT_DATA=(SID=sqlserver_banhang))
--   )';

*/  -- KET THUC KHOI SYSDBA --


-- ************************************************************
-- BUOC 2: TAO BANG DW
-- Chay voi user DATAWAREHOUSE
-- File: create_dw.sql
-- ************************************************************

-- Chay file: @"D:\PTIT\...\BTL\create_dw.sql"
-- Hoac copy-paste noi dung create_dw.sql vao SQL Developer va chay

-- Kiem tra sau khi chay:
SELECT 'DIM_TIME'        AS bang, COUNT(*) AS so_dong FROM DIM_TIME
UNION ALL SELECT 'DIM_LOCATION',   COUNT(*) FROM DIM_LOCATION
UNION ALL SELECT 'DIM_PRODUCT',    COUNT(*) FROM DIM_PRODUCT
UNION ALL SELECT 'DIM_CUSTOMER',   COUNT(*) FROM DIM_CUSTOMER
UNION ALL SELECT 'FACT_INVENTORY', COUNT(*) FROM FACT_INVENTORY
UNION ALL SELECT 'FACT_ORDER',     COUNT(*) FROM FACT_ORDER
UNION ALL SELECT 'ETL_LOG',        COUNT(*) FROM ETL_LOG;
-- Ket qua mong doi:
--   DIM_TIME:        1461 (da populate san)
--   Cac bang khac:   0 (chua co du lieu, doi ETL nap)


-- ************************************************************
-- BUOC 3: COMPILE PACKAGE
-- Chay voi user DATAWAREHOUSE
-- File: etl_package.sql
-- ************************************************************

-- Chay file: @"D:\PTIT\...\BTL\etl_package.sql"

-- Kiem tra compile:
SELECT object_name, object_type, status
FROM user_objects
WHERE object_name = 'PKG_ETL_DW';
-- Ket qua mong doi:
--   PKG_ETL_DW    PACKAGE         VALID
--   PKG_ETL_DW    PACKAGE BODY    VALID
-- Neu status = INVALID → xem loi:
SELECT line, position, text
FROM user_errors
WHERE name = 'PKG_ETL_DW'
ORDER BY sequence;


-- ************************************************************
-- BUOC 4: CHAY ETL LAN DAU (FULL LOAD)
-- Day la buoc quan trong nhat!
-- ************************************************************

-- 4.1 Bat DBMS_OUTPUT de xem ket qua
SET SERVEROUTPUT ON SIZE UNLIMITED;

-- 4.2 CACH 1 (khuyen dung): Chay tung procedure rieng le
-- Uu diem: de bug loi, biet chinh xac buoc nao gap van de
BEGIN PKG_ETL_DW.LOAD_DIM_TIME; END;
/
-- Mong doi: SKIP (vi create_dw.sql da populate 1461 rows)

BEGIN PKG_ETL_DW.LOAD_DIM_LOCATION; END;
/
-- Mong doi: 130 rows (100 vat ly + 30 online)

BEGIN PKG_ETL_DW.LOAD_DIM_PRODUCT; END;
/
-- Mong doi: ~20,506 rows

BEGIN PKG_ETL_DW.LOAD_DIM_CUSTOMER; END;
/
-- Mong doi: ~44,474 rows

BEGIN PKG_ETL_DW.LOAD_FACT_INVENTORY; END;
/
-- Mong doi: ~51,809 + ~vai nghin (online) rows

BEGIN PKG_ETL_DW.LOAD_FACT_ORDER; END;
/
-- Mong doi: ~47,825 rows

-- 4.3 CACH 2 (nhanh): Chay tat ca 1 lan
-- BEGIN PKG_ETL_DW.RUN_ALL; END;
-- /

-- 4.4 Kiem tra ETL_LOG
SELECT LogID, TenJob, TrangThai, SoBanGhi, GhiChu,
       TO_CHAR(ThoiGianKT, 'DD/MM/YYYY HH24:MI:SS') AS thoi_gian
FROM ETL_LOG
ORDER BY LogID DESC;


-- ************************************************************
-- BUOC 5: KIEM TRA KET QUA SAU FULL LOAD
-- ************************************************************

-- 5.1 Dem so row moi bang
SELECT 'DIM_TIME'        AS bang, COUNT(*) AS so_dong FROM DIM_TIME
UNION ALL SELECT 'DIM_LOCATION',   COUNT(*) FROM DIM_LOCATION
UNION ALL SELECT 'DIM_PRODUCT',    COUNT(*) FROM DIM_PRODUCT
UNION ALL SELECT 'DIM_CUSTOMER',   COUNT(*) FROM DIM_CUSTOMER
UNION ALL SELECT 'FACT_INVENTORY', COUNT(*) FROM FACT_INVENTORY
UNION ALL SELECT 'FACT_ORDER',     COUNT(*) FROM FACT_ORDER;
-- Ket qua mong doi:
-- +-----------------+--------+
-- | DIM_TIME        |  1,461 |
-- | DIM_LOCATION    |    130 |
-- | DIM_PRODUCT     | 20,506 |
-- | DIM_CUSTOMER    | 44,474 |
-- | FACT_INVENTORY  | ~55K+  |
-- | FACT_ORDER      | 47,825 |
-- +-----------------+--------+

-- 5.2 Kiem tra DIM_TIME
SELECT MIN(MaThoiGian), MAX(MaThoiGian), COUNT(*) FROM DIM_TIME;
-- Mong doi: 20150101, 20181231, 1461

-- 5.3 Kiem tra DIM_LOCATION
SELECT LoaiCuaHang, COUNT(*) FROM DIM_LOCATION GROUP BY LoaiCuaHang;
-- Mong doi: Vat ly=100, Truc tuyen=30

-- 5.4 Kiem tra DIM_CUSTOMER - phan loai KH
SELECT LoaiKH, COUNT(*) FROM DIM_CUSTOMER GROUP BY LoaiKH ORDER BY 1;
-- Mong doi: Buu dien, Ca hai, Du lich (va NULL cho KH khong thuoc loai nao)

-- 5.5 Kiem tra FACT_ORDER - kenh ban hang
SELECT KenhBanHang, COUNT(*), SUM(TongTien) FROM FACT_ORDER
GROUP BY KenhBanHang;
-- Mong doi: 2 kenh: 'Tai cua hang' va 'Truc tuyen'

-- 5.6 Kiem tra FK integrity (khong nen co orphan)
SELECT 'FACT_ORDER orphan KH' AS check_name, COUNT(*) AS cnt
FROM FACT_ORDER f WHERE NOT EXISTS (
    SELECT 1 FROM DIM_CUSTOMER c WHERE c.MaKH = f.MaKH)
UNION ALL
SELECT 'FACT_ORDER orphan MH', COUNT(*)
FROM FACT_ORDER f WHERE NOT EXISTS (
    SELECT 1 FROM DIM_PRODUCT p WHERE p.MaMH = f.MaMH)
UNION ALL
SELECT 'FACT_ORDER orphan LOC', COUNT(*)
FROM FACT_ORDER f WHERE NOT EXISTS (
    SELECT 1 FROM DIM_LOCATION l WHERE l.MaCuaHang = f.MaCuaHang)
UNION ALL
SELECT 'FACT_ORDER orphan TIME', COUNT(*)
FROM FACT_ORDER f WHERE NOT EXISTS (
    SELECT 1 FROM DIM_TIME t WHERE t.MaThoiGian = f.MaThoiGian);
-- Ket qua mong doi: tat ca cnt = 0

-- 5.7 Kiem tra sample du lieu
SELECT f.MaDon, c.TenKH, t.MaThoiGian, p.MoTa, l.TenCuaHang,
       f.KenhBanHang, f.SoLuongDat, f.GiaDat, f.TongTien
FROM FACT_ORDER f
JOIN DIM_CUSTOMER c ON f.MaKH = c.MaKH
JOIN DIM_TIME t     ON f.MaThoiGian = t.MaThoiGian
JOIN DIM_PRODUCT p  ON f.MaMH = p.MaMH
JOIN DIM_LOCATION l ON f.MaCuaHang = l.MaCuaHang
WHERE ROWNUM <= 10;


-- ************************************************************
-- BUOC 6: TAO JOB TU DONG (TUY CHON)
-- Chi can khi muon ETL chay tu dong hang dem
-- ************************************************************

-- Chay file: @"D:\PTIT\...\BTL\etl_job.sql"

-- Kiem tra:
SELECT job_name, enabled, state, next_run_date
FROM user_scheduler_jobs
WHERE job_name = 'JOB_ETL_NIGHTLY';

-- Chay thu ngay (khong doi schedule):
-- EXEC DBMS_SCHEDULER.RUN_JOB('JOB_ETL_NIGHTLY');

-- Xem ket qua chay:
-- SELECT * FROM user_scheduler_job_run_details
-- WHERE job_name = 'JOB_ETL_NIGHTLY'
-- ORDER BY log_date DESC FETCH FIRST 5 ROWS ONLY;


-- ************************************************************
-- BUOC 7: TEST INCREMENTAL LOAD
-- Sau khi Full Load thanh cong, test nap them du lieu moi
-- ************************************************************

-- 7.1 Them 1 san pham moi vao nguon SQL Server
-- (chay tren SQL Server Management Studio)
/*
INSERT INTO MatHang (MaMH, MoTa, KichCo, TrongLuong, Gia, ThoiGian)
VALUES ('TEST01', N'San pham test', N'M', 500.00, 99.99, GETDATE());
*/

-- 7.2 Chay incremental
SET SERVEROUTPUT ON SIZE UNLIMITED;
BEGIN PKG_ETL_DW.RUN_ALL; END;
/

-- 7.3 Kiem tra san pham moi da vao DW chua
SELECT * FROM DIM_PRODUCT WHERE MaMH = 'TEST01';
-- Mong doi: 1 row

-- 7.4 Kiem tra ETL_LOG — phai thay 'INCR' thay vi 'FULL'
SELECT TenJob, TrangThai, SoBanGhi, GhiChu,
       TO_CHAR(ThoiGianKT, 'HH24:MI:SS') AS gio
FROM ETL_LOG
WHERE LogID > (SELECT MAX(LogID) - 10 FROM ETL_LOG)
ORDER BY LogID DESC;
-- Mong doi: GhiChu chua 'INCR' cho cac procedure

-- 7.5 Don dep du lieu test
-- (chay tren SQL Server)
-- DELETE FROM MatHang WHERE MaMH = 'TEST01';


-- ************************************************************
-- BUOC 8: PHUONG AN DE PHONG & ROLLBACK
-- ************************************************************

-- === 8.1 NEU ETL GAP LOI GIUA CHUNG ===
-- Xem loi trong ETL_LOG:
SELECT * FROM ETL_LOG WHERE TrangThai = 'LOI' ORDER BY LogID DESC;

-- Xem loi Oracle chi tiet:
-- SHOW ERRORS PACKAGE BODY PKG_ETL_DW;

-- === 8.2 RESET VA CHAY LAI TU DAU ===
-- Xoa tat ca du lieu va chay lai FULL LOAD:
/*
TRUNCATE TABLE FACT_ORDER;
TRUNCATE TABLE FACT_INVENTORY;
DELETE FROM DIM_CUSTOMER;
DELETE FROM DIM_PRODUCT;
DELETE FROM DIM_LOCATION;
-- KHONG xoa DIM_TIME (du lieu tinh, chi tao 1 lan)
DELETE FROM ETL_LOG;
COMMIT;

-- Chay lai:
SET SERVEROUTPUT ON SIZE UNLIMITED;
BEGIN PKG_ETL_DW.RUN_ALL; END;
/
*/

-- === 8.3 XOA TOAN BO VA TAO LAI (RESET HOAN TOAN) ===
/*
-- Chay lai create_dw.sql (se DROP va tao lai tat ca bang)
-- Chay lai etl_package.sql (se CREATE OR REPLACE)
-- Chay lai deploy_etl.sql tu BUOC 4
*/

-- === 8.4 NEU LOAD_DIM_CUSTOMER LOI (ORA-00942) ===
-- Nguyen nhan: Chua grant SELECT tren LEVANMINH schema
-- Fix: Chay voi SYSDBA:
--   GRANT SELECT ON LEVANMINH.KHACHHANG  TO DATAWAREHOUSE;
--   GRANT SELECT ON LEVANMINH.KH_DULICH  TO DATAWAREHOUSE;
--   GRANT SELECT ON LEVANMINH.KH_BUUDIEN TO DATAWAREHOUSE;

-- === 8.5 NEU LOAD_FACT_ORDER QUA CHAM ===
-- FACT_ORDER xu ly ~48K rows, co the mat 1-5 phut
-- Neu timeout, kiem tra:
SELECT COUNT(*) FROM FACT_ORDER;  -- xem da insert duoc bao nhieu
-- Package co COMMIT moi 5000 rows nen du lieu da insert se an toan
-- Chi can chay lai: BEGIN PKG_ETL_DW.LOAD_FACT_ORDER; END;
-- No se skip rows da co (DUP_VAL_ON_INDEX) hoac INSERT tiep

-- === 8.6 NEU DB LINK MAT KET NOI ===
-- Kiem tra:
SELECT * FROM "VanPhongDaiDien"@sqlserver_banhang WHERE ROWNUM <= 1;
-- Neu loi: kiem tra SQL Server dang chay, Oracle Gateway dang chay
-- Restart Oracle Gateway neu can:
--   (Windows) services.msc → OracleOraDB21Home1... → Restart

-- === 8.7 CHAY LAI 1 PROCEDURE CU THE ===
-- Neu chi 1 procedure loi, chi can chay lai procedure do:
-- BEGIN PKG_ETL_DW.LOAD_DIM_CUSTOMER; END;
-- /
-- Cac procedure khac da COMMIT nen khong bi anh huong

-- === 8.8 MONITORING: Xem tien do khi dang chay ===
-- Mo 1 session SQL Developer khac va chay:
SELECT TenJob, TrangThai, SoBanGhi, GhiChu,
       TO_CHAR(ThoiGianKT, 'HH24:MI:SS') AS gio
FROM ETL_LOG
ORDER BY LogID DESC
FETCH FIRST 15 ROWS ONLY;
-- (ETL_LOG dung AUTONOMOUS_TRANSACTION nen log duoc ghi ngay
--  ke ca khi transaction chinh chua COMMIT)


-- ************************************************************
-- TOM TAT THU TU CHAY
-- ************************************************************
--
-- LAN DAU (setup):
--   1. SYSDBA: Grant quyen (BUOC 1)
--   2. DATAWAREHOUSE: @create_dw.sql
--   3. DATAWAREHOUSE: @etl_package.sql
--   4. DATAWAREHOUSE: BEGIN PKG_ETL_DW.RUN_ALL; END;
--   5. DATAWAREHOUSE: Kiem tra (BUOC 5)
--   6. (Tuy chon) DATAWAREHOUSE: @etl_job.sql
--
-- CAC LAN SAU (tu dong hoac thu cong):
--   - Tu dong: Job chay luc 2:00 AM hang dem
--   - Thu cong: BEGIN PKG_ETL_DW.RUN_ALL; END;
--
-- ************************************************************
