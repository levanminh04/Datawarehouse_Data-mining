-- check xem mình đang ở đâu, CDB hay PDB
SHOW CON_NAME; 
-- check tablespace
SELECT tablespace_name FROM dba_tablespaces;



-- tạo tablespace

CREATE TABLESPACE USERS 
DATAFILE 'users01.dbf' SIZE 10M -- Chỉ lấy 10MB ban đầu thôi
AUTOEXTEND ON NEXT 5M 
MAXSIZE 400M; -- Giới hạn tối đa là 500MB để tránh việc nó "ăn" hết ổ cứng nếu bạn lỡ tay chạy vòng lặp vô tận


CREATE USER datawarehouse IDENTIFIED BY 123456
  DEFAULT TABLESPACE USERS
  QUOTA UNLIMITED ON USERS;

GRANT CONNECT, RESOURCE, CREATE VIEW, CREATE SYNONYM TO datawarehouse;
GRANT CREATE DATABASE LINK TO datawarehouse; -- Quyen dung DB Link (de doc SQL Server)


-- cấp quyền cho user datawarehouse được quyền đọc dữ liệu từ user levanminh
GRANT SELECT ON levanminh.KhachHang TO datawarehouse;
GRANT SELECT ON levanminh.KH_DuLich TO datawarehouse;
GRANT SELECT ON levanminh.KH_BuuDien TO datawarehouse;



--  => hiện đang có 2 user"
-- - user levanminh      => lưu dữ liệu khách hàng (đúng ra phải đặt tên user là vanphong hoặc khachhang cho đỡ hiểu nhầm) 
-- - user datawarehouse  => lưu datawarehouse



-- tạo Private Database Link => chỉ có tác dụng với duy nhất user thực hiện lệnh này, cụ thể là user datawarehouse.
CREATE DATABASE LINK sqlserver_banhang
  CONNECT TO oracle_etl IDENTIFIED BY "123456"
  USING 'SQLSERVER_BANHANG';


SELECT COUNT(*) FROM "MatHang"@sqlserver_banhang;       





-- ============================================================
-- SCRIPT TAO DATA WAREHOUSE - STAR SCHEMA (v2)
-- Chay voi user: DATAWAREHOUSE
-- Oracle XE 21c
-- ============================================================
--
-- THIET KE:
--   4 Dimension: DIM_TIME, DIM_LOCATION, DIM_PRODUCT, DIM_CUSTOMER
--   2 Fact:      FACT_INVENTORY, FACT_ORDER
--   1 Log:       ETL_LOG
--
-- HE PHAN CAP (Concept Hierarchy):
--   DIM_LOCATION: CuaHang -> ThanhPho -> Bang
--                 (bao gom ca cua hang vat ly va kho truc tuyen)
--   DIM_TIME:     Ngay -> Thang -> Quy -> Nam
--   DIM_CUSTOMER: phi chuan hoa (khong FK den DIM nao)
--
-- ============================================================

-- Xoa bang cu neu ton tai (theo thu tu nguoc FK)
BEGIN EXECUTE IMMEDIATE 'DROP TABLE FACT_ORDER CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE FACT_INVENTORY CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE DIM_CUSTOMER CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE DIM_PRODUCT CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE DIM_LOCATION CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE DIM_TIME CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE ETL_LOG CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- ============================================================
-- 1. DIM_TIME
-- He phan cap: Ngay -> Thang -> Quy -> Nam
-- Khong phu thuoc gi, tao dau tien
-- ============================================================
CREATE TABLE DIM_TIME (
    MaThoiGian    NUMBER(8)     CONSTRAINT pk_dim_time PRIMARY KEY,  -- YYYYMMDD
    Ngay          NUMBER(2)     NOT NULL,
    Thang         NUMBER(2)     NOT NULL,
    Quy           NUMBER(1)     NOT NULL,  -- 1,2,3,4
    Nam           NUMBER(4)     NOT NULL,
    ThuTrongTuan  VARCHAR2(20)  NOT NULL   -- Monday, Tuesday, ...
);

-- ============================================================
-- 2. DIM_LOCATION (thay the DIM_CITY + DIM_STORE cu)
-- He phan cap: CuaHang -> ThanhPho -> Bang
--
-- Gop thong tin tu:
--   - VanPhongDaiDien@sqlserver_banhang (cap ThanhPho/Bang)
--   - CuaHang@sqlserver_banhang         (cap CuaHang vat ly)
--   + Sinh them kho truc tuyen          (1 kho/thanh pho)
--
-- MaCuaHang la cap thap nhat (finest grain) = khoa chinh
-- ============================================================
CREATE TABLE DIM_LOCATION (
    -- Cap 1: Cua hang (finest grain)
    MaCuaHang     VARCHAR2(10)   CONSTRAINT pk_dim_location PRIMARY KEY,
    TenCuaHang    VARCHAR2(100),
    SoDienThoai   VARCHAR2(20),
    LoaiCuaHang   VARCHAR2(20)   NOT NULL,  -- 'Vat ly' | 'Truc tuyen'
    -- Cap 2: Thanh pho (roll-up level 1)
    MaThanhPho    VARCHAR2(10)   NOT NULL,
    TenThanhPho   VARCHAR2(100)  NOT NULL,
    DiaChiVP      VARCHAR2(200),
    -- Cap 3: Bang (roll-up level 2)
    Bang          VARCHAR2(50)
);

-- ============================================================
-- 3. DIM_PRODUCT
-- Map tu: MatHang@sqlserver_banhang
-- ============================================================
CREATE TABLE DIM_PRODUCT (
    MaMH          VARCHAR2(10)   CONSTRAINT pk_dim_product PRIMARY KEY,
    MoTa          VARCHAR2(200),
    KichCo        VARCHAR2(50),
    TrongLuong    NUMBER(10,2),  -- gram
    Gia           NUMBER(15,2)
);

-- ============================================================
-- 4. DIM_CUSTOMER (phi chuan hoa — khong FK den DIM nao)
-- Gop tu 3 bang Oracle: KhachHang + KH_DuLich + KH_BuuDien
-- Thong tin dia ly duoc nhung truc tiep (denormalized)
-- ============================================================
CREATE TABLE DIM_CUSTOMER (
    MaKH               VARCHAR2(10)   CONSTRAINT pk_dim_customer PRIMARY KEY,
    TenKH              VARCHAR2(100)  NOT NULL,
    NgayDatHangDauTien  DATE,
    LoaiKH             VARCHAR2(20),   -- 'Du lich' | 'Buu dien' | 'Ca hai'
    HuongDanVien       VARCHAR2(200),  -- NULL neu khong phai KH du lich
    DiaChiBuuDien      VARCHAR2(300),  -- NULL neu khong phai KH buu dien
    -- Dia ly khach hang (denormalized, KHONG FK)
    MaThanhPho         VARCHAR2(10),
    TenThanhPho        VARCHAR2(100),
    Bang               VARCHAR2(50)
);

-- ============================================================
-- 5. FACT_INVENTORY (ton kho)
-- Map tu: MatHang_LuuTru@sqlserver_banhang
-- Chi reference DIM_LOCATION (thong qua MaCuaHang)
-- Khong can MaThanhPho rieng — roll-up qua DIM_LOCATION
-- ============================================================
CREATE TABLE FACT_INVENTORY (
    MaCuaHang     VARCHAR2(10)   NOT NULL,
    MaMH          VARCHAR2(10)   NOT NULL,
    MaThoiGian    NUMBER(8)      NOT NULL,
    SoLuongTon    NUMBER(10)     NOT NULL,
    CONSTRAINT pk_fact_inventory PRIMARY KEY (MaCuaHang, MaMH, MaThoiGian),
    CONSTRAINT fk_inv_location FOREIGN KEY (MaCuaHang)  REFERENCES DIM_LOCATION(MaCuaHang),
    CONSTRAINT fk_inv_product FOREIGN KEY (MaMH)       REFERENCES DIM_PRODUCT(MaMH),
    CONSTRAINT fk_inv_time    FOREIGN KEY (MaThoiGian)  REFERENCES DIM_TIME(MaThoiGian)
);

-- ============================================================
-- 6. FACT_ORDER (don hang — bang fact chinh)
-- Map tu: DonDatHang + MatHang_DuocDat (SQL Server)
--         + KhachHang, KH_DuLich, KH_BuuDien (Oracle)
--
-- MaCuaHang: derived boi ETL (gan cua hang vat ly hoac kho online)
-- KenhBanHang: derived tu loai khach hang
--   KH_DuLich  -> 'Tai cua hang'
--   KH_BuuDien -> 'Truc tuyen'
-- ============================================================
CREATE TABLE FACT_ORDER (
    MaDon         VARCHAR2(10)   NOT NULL,
    MaKH          VARCHAR2(10)   NOT NULL,
    MaMH          VARCHAR2(10)   NOT NULL,
    MaCuaHang     VARCHAR2(10)   NOT NULL,  -- cua hang vat ly hoac kho online
    MaThoiGian    NUMBER(8)      NOT NULL,  -- tu NgayDatHang -> YYYYMMDD
    KenhBanHang   VARCHAR2(20)   NOT NULL,  -- 'Tai cua hang' | 'Truc tuyen'
    SoLuongDat    NUMBER(10)     NOT NULL,
    GiaDat        NUMBER(15,2)   NOT NULL,
    TongTien      NUMBER(15,2)   NOT NULL,  -- = SoLuongDat * GiaDat
    CONSTRAINT pk_fact_order PRIMARY KEY (MaDon, MaMH),
    CONSTRAINT fk_ord_customer FOREIGN KEY (MaKH)       REFERENCES DIM_CUSTOMER(MaKH),
    CONSTRAINT fk_ord_product  FOREIGN KEY (MaMH)       REFERENCES DIM_PRODUCT(MaMH),
    CONSTRAINT fk_ord_location FOREIGN KEY (MaCuaHang)   REFERENCES DIM_LOCATION(MaCuaHang),
    CONSTRAINT fk_ord_time     FOREIGN KEY (MaThoiGian)  REFERENCES DIM_TIME(MaThoiGian)
);

-- ============================================================
-- 7. ETL_LOG (ghi lich su chay ETL)
-- ============================================================
CREATE TABLE ETL_LOG (
    LogID         NUMBER         GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    TenJob        VARCHAR2(100)  NOT NULL,
    ThoiGianBD    TIMESTAMP      DEFAULT SYSTIMESTAMP,
    ThoiGianKT    TIMESTAMP,
    TrangThai     VARCHAR2(20),  -- 'THANH CONG' | 'LOI'
    SoBanGhi      NUMBER,
    GhiChu        VARCHAR2(500)
);

-- ============================================================
-- 8. POPULATE DIM_TIME (2015-01-01 den 2018-12-31)
-- 1,461 rows
-- ============================================================
DECLARE
    v_date DATE := TO_DATE('2015-01-01', 'YYYY-MM-DD');
    v_end  DATE := TO_DATE('2018-12-31', 'YYYY-MM-DD');
    v_key  NUMBER(8);
    v_dow  VARCHAR2(20);
BEGIN
    WHILE v_date <= v_end LOOP
        v_key := TO_NUMBER(TO_CHAR(v_date, 'YYYYMMDD'));
        v_dow := TO_CHAR(v_date, 'Day', 'NLS_DATE_LANGUAGE=AMERICAN');

        INSERT INTO DIM_TIME (MaThoiGian, Ngay, Thang, Quy, Nam, ThuTrongTuan)
        VALUES (
            v_key,
            EXTRACT(DAY FROM v_date),
            EXTRACT(MONTH FROM v_date),
            TO_NUMBER(TO_CHAR(v_date, 'Q')),
            EXTRACT(YEAR FROM v_date),
            TRIM(v_dow)
        );

        v_date := v_date + 1;
    END LOOP;
    COMMIT;
    DBMS_OUTPUT.PUT_LINE('DIM_TIME populated: ' ||
        TO_CHAR(v_end - TO_DATE('2015-01-01','YYYY-MM-DD') + 1) || ' rows');
END;
/

-- ============================================================
-- KIEM TRA SAU KHI CHAY
-- ============================================================
SELECT 'DIM_TIME'        AS bang, COUNT(*) AS so_dong FROM DIM_TIME
UNION ALL SELECT 'DIM_LOCATION',   COUNT(*) FROM DIM_LOCATION
UNION ALL SELECT 'DIM_PRODUCT',    COUNT(*) FROM DIM_PRODUCT
UNION ALL SELECT 'DIM_CUSTOMER',   COUNT(*) FROM DIM_CUSTOMER
UNION ALL SELECT 'FACT_INVENTORY', COUNT(*) FROM FACT_INVENTORY
UNION ALL SELECT 'FACT_ORDER',     COUNT(*) FROM FACT_ORDER
UNION ALL SELECT 'ETL_LOG',        COUNT(*) FROM ETL_LOG;

select * from FACT_ORDER;
select count(*) from DIM_TIME;

SELECT * FROM "MatHang_DuocDat"@sqlserver_banhang d where d."MaDon" = 6835;       
SELECT * FROM "DonDatHang"@sqlserver_banhang  d where d."MaDon" = 6835;  
-- 6835 - 6

select *  
FROM "DonDatHang"@sqlserver_banhang d
JOIN "MatHang_DuocDat"@sqlserver_banhang md
    ON d."MaDon" = md."MaDon"
    where d."MaDon" = 21475;


SELECT COUNT(d."MaDon") AS cnt
FROM "DonDatHang"@sqlserver_banhang d
GROUP BY d."MaDon"
HAVING COUNT(d."MaDon") > 1;


-- Don hang co nhieu san pham KHAC NHAU
SELECT md."MaDon", COUNT(*) AS SoSanPham
FROM "MatHang_DuocDat"@sqlserver_banhang md
GROUP BY md."MaDon"
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC;


SELECT count(*)
FROM "DonDatHang"@sqlserver_banhang d
JOIN "MatHang_DuocDat"@sqlserver_banhang md
    ON d."MaDon" = md."MaDon";




