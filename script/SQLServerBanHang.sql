
USE BanHang;
GO
-- Tạo bảng Backup và copy dữ liệu cũ ngay lập tức
SELECT * INTO VanPhongDaiDien_BAK FROM VanPhongDaiDien;
SELECT * INTO CuaHang_BAK           FROM CuaHang;
SELECT * INTO MatHang_BAK           FROM MatHang;
SELECT * INTO MatHang_LuuTru_BAK    FROM MatHang_LuuTru;
SELECT * INTO DonDatHang_BAK        FROM DonDatHang;
SELECT * INTO MatHang_DuocDat_BAK   FROM MatHang_DuocDat;
GO



CREATE DATABASE BanHang;
GO
USE BanHang;
GO
 
CREATE TABLE VanPhongDaiDien (
  MaThanhPho  VARCHAR(10)  PRIMARY KEY,
  TenThanhPho NVARCHAR(100),
  DiaChiVP    NVARCHAR(200),
  Bang        NVARCHAR(50),
  ThoiGian    DATETIME     DEFAULT GETDATE()
);
 
CREATE TABLE CuaHang (
  MaCuaHang   VARCHAR(10)  PRIMARY KEY,
  MaThanhPho  VARCHAR(10)  REFERENCES VanPhongDaiDien(MaThanhPho),
  SoDienThoai VARCHAR(20),
  ThoiGian    DATETIME     DEFAULT GETDATE()
);
 
CREATE TABLE MatHang (
  MaMH        VARCHAR(10)  PRIMARY KEY,
  MoTa        NVARCHAR(200),
  KichCo      NVARCHAR(50),
  TrongLuong  DECIMAL(10,2),
  Gia         DECIMAL(15,2),
  ThoiGian    DATETIME     DEFAULT GETDATE()
);
 
CREATE TABLE MatHang_LuuTru (
  MaCuaHang   VARCHAR(10)  REFERENCES CuaHang(MaCuaHang),
  MaMH        VARCHAR(10)  REFERENCES MatHang(MaMH),
  SoLuongKho  INT          DEFAULT 0,
  ThoiGian    DATETIME     DEFAULT GETDATE(),
  PRIMARY KEY (MaCuaHang, MaMH)
);
 
CREATE TABLE DonDatHang (
  MaDon        VARCHAR(10)  PRIMARY KEY,
  NgayDatHang  DATE,
  MaKH         VARCHAR(10),   -- logic FK sang Oracle
  ThoiGian     DATETIME       DEFAULT GETDATE()
);
 
CREATE TABLE MatHang_DuocDat (
  MaDon        VARCHAR(10)   REFERENCES DonDatHang(MaDon),
  MaMH         VARCHAR(10)   REFERENCES MatHang(MaMH),
  SoLuongDat   INT,
  GiaDat       DECIMAL(15,2),
  ThoiGian     DATETIME      DEFAULT GETDATE(),
  PRIMARY KEY (MaDon, MaMH)
);



-- ============================================
-- SQL SERVER: DATABASE BANHANG
-- Chạy trong SSMS sau khi đã tạo bảng
-- ============================================

USE BanHang;

-- ── 1. VanPhongDaiDien (4 thành phố) ────────
INSERT INTO VanPhongDaiDien VALUES ('TP01','Ha Noi',      '15 Trang Thi, Hoan Kiem, Ha Noi',   'Mien Bac',   GETDATE());
INSERT INTO VanPhongDaiDien VALUES ('TP02','Da Nang',     '22 Bach Dang, Hai Chau, Da Nang',    'Mien Trung', GETDATE());
INSERT INTO VanPhongDaiDien VALUES ('TP03','Ho Chi Minh', '100 Nguyen Hue, Q1, Ho Chi Minh',    'Mien Nam',   GETDATE());
INSERT INTO VanPhongDaiDien VALUES ('TP04','Da Lat',      '8 Tran Hung Dao, Da Lat, Lam Dong',  'Mien Nam',   GETDATE());

-- ── 2. CuaHang (9 cửa hàng) ─────────────────
-- TP01 - Ha Noi: 3 cửa hàng
INSERT INTO CuaHang VALUES ('CH01','TP01','024-3825-1111', GETDATE());
INSERT INTO CuaHang VALUES ('CH02','TP01','024-3826-2222', GETDATE());
INSERT INTO CuaHang VALUES ('CH03','TP01','024-3827-3333', GETDATE());
-- TP02 - Da Nang: 2 cửa hàng
INSERT INTO CuaHang VALUES ('CH04','TP02','0236-382-4444', GETDATE());
INSERT INTO CuaHang VALUES ('CH05','TP02','0236-382-5555', GETDATE());
-- TP03 - Ho Chi Minh: 3 cửa hàng
INSERT INTO CuaHang VALUES ('CH06','TP03','028-3822-6666', GETDATE());
INSERT INTO CuaHang VALUES ('CH07','TP03','028-3823-7777', GETDATE());
INSERT INTO CuaHang VALUES ('CH08','TP03','028-3824-8888', GETDATE());
-- TP04 - Da Lat: 1 cửa hàng
INSERT INTO CuaHang VALUES ('CH09','TP04','0263-382-9999', GETDATE());

-- ── 3. MatHang (6 mặt hàng) ─────────────────
INSERT INTO MatHang VALUES ('MH01', N'Banh Com Ha Noi',   N'500g', 0.50, 50000,  GETDATE());
INSERT INTO MatHang VALUES ('MH02', N'O Mai Mo',          N'200g', 0.20, 35000,  GETDATE());
INSERT INTO MatHang VALUES ('MH03', N'Tra Sen Tay Ho',    N'100g', 0.10, 120000, GETDATE());
INSERT INTO MatHang VALUES ('MH04', N'Mut Dau Da Lat',    N'300g', 0.30, 45000,  GETDATE());
INSERT INTO MatHang VALUES ('MH05', N'Kho Bo Tay Nguyen', N'250g', 0.25, 80000,  GETDATE());
INSERT INTO MatHang VALUES ('MH06', N'Banh Trang Me',     N'500g', 0.50, 25000,  GETDATE());

-- ── 4. MatHang_LuuTru (21 bản ghi tồn kho) ──
-- CH01 - Ha Noi
INSERT INTO MatHang_LuuTru VALUES ('CH01','MH01',120, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH01','MH02', 80, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH01','MH03', 50, GETDATE());
-- CH02 - Ha Noi
INSERT INTO MatHang_LuuTru VALUES ('CH02','MH01', 90, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH02','MH02', 60, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH02','MH06',200, GETDATE());
-- CH03 - Ha Noi
INSERT INTO MatHang_LuuTru VALUES ('CH03','MH01', 45, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH03','MH03', 30, GETDATE());
-- CH04 - Da Nang
INSERT INTO MatHang_LuuTru VALUES ('CH04','MH05',100, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH04','MH06',150, GETDATE());
-- CH05 - Da Nang
INSERT INTO MatHang_LuuTru VALUES ('CH05','MH04', 70, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH05','MH05', 55, GETDATE());
-- CH06 - Ho Chi Minh
INSERT INTO MatHang_LuuTru VALUES ('CH06','MH05', 85, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH06','MH06',130, GETDATE());
-- CH07 - Ho Chi Minh
INSERT INTO MatHang_LuuTru VALUES ('CH07','MH02', 95, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH07','MH05', 60, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH07','MH06',110, GETDATE());
-- CH08 - Ho Chi Minh
INSERT INTO MatHang_LuuTru VALUES ('CH08','MH04', 40, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH08','MH05', 75, GETDATE());
-- CH09 - Da Lat
INSERT INTO MatHang_LuuTru VALUES ('CH09','MH04', 90, GETDATE());
INSERT INTO MatHang_LuuTru VALUES ('CH09','MH05', 35, GETDATE());

-- ── 5. DonDatHang (12 đơn) ──────────────────
-- Lưu ý: MaKH ở đây phải khớp với Oracle
-- KH01,KH02,KH08 → Ha Noi    → CH01/CH02/CH03
-- KH03,KH04      → Da Nang   → CH04/CH05
-- KH05,KH06,KH09 → Ho Chi Minh→ CH06/CH07/CH08
-- KH07,KH10      → Da Lat    → CH09
INSERT INTO DonDatHang VALUES ('DH001', '2024-01-15', 'KH01', GETDATE());
INSERT INTO DonDatHang VALUES ('DH002', '2024-01-22', 'KH02', GETDATE());
INSERT INTO DonDatHang VALUES ('DH003', '2024-02-05', 'KH03', GETDATE());
INSERT INTO DonDatHang VALUES ('DH004', '2024-02-18', 'KH04', GETDATE());
INSERT INTO DonDatHang VALUES ('DH005', '2024-03-10', 'KH05', GETDATE());
INSERT INTO DonDatHang VALUES ('DH006', '2024-03-25', 'KH06', GETDATE());
INSERT INTO DonDatHang VALUES ('DH007', '2024-04-02', 'KH07', GETDATE());
INSERT INTO DonDatHang VALUES ('DH008', '2024-04-20', 'KH01', GETDATE());
INSERT INTO DonDatHang VALUES ('DH009', '2024-05-08', 'KH03', GETDATE());
INSERT INTO DonDatHang VALUES ('DH010', '2024-06-14', 'KH08', GETDATE());
INSERT INTO DonDatHang VALUES ('DH011', '2024-07-30', 'KH09', GETDATE());
INSERT INTO DonDatHang VALUES ('DH012', '2024-08-15', 'KH10', GETDATE());

-- ── 6. MatHang_DuocDat (27 dòng chi tiết) ───
-- DH001 - KH01 - Ha Noi (MH01,02,03 có ở CH01)
INSERT INTO MatHang_DuocDat VALUES ('DH001','MH01',3, 50000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH001','MH02',2, 35000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH001','MH03',1, 120000, GETDATE());
-- DH002 - KH02 - Ha Noi
INSERT INTO MatHang_DuocDat VALUES ('DH002','MH01',5, 50000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH002','MH06',4, 25000,  GETDATE());
-- DH003 - KH03 - Da Nang (MH05,06 có ở CH04)
INSERT INTO MatHang_DuocDat VALUES ('DH003','MH05',2, 80000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH003','MH06',3, 25000,  GETDATE());
-- DH004 - KH04 - Da Nang (MH04,05 có ở CH05)
INSERT INTO MatHang_DuocDat VALUES ('DH004','MH04',2, 45000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH004','MH05',1, 80000,  GETDATE());
-- DH005 - KH05 - Ho Chi Minh
INSERT INTO MatHang_DuocDat VALUES ('DH005','MH05',4, 80000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH005','MH06',6, 25000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH005','MH02',2, 35000,  GETDATE());
-- DH006 - KH06 - Ho Chi Minh
INSERT INTO MatHang_DuocDat VALUES ('DH006','MH04',3, 45000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH006','MH05',2, 80000,  GETDATE());
-- DH007 - KH07 - Da Lat (MH04,05 có ở CH09)
INSERT INTO MatHang_DuocDat VALUES ('DH007','MH04',5, 45000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH007','MH05',3, 80000,  GETDATE());
-- DH008 - KH01 - Ha Noi lần 2
INSERT INTO MatHang_DuocDat VALUES ('DH008','MH02',4, 35000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH008','MH03',2, 120000, GETDATE());
-- DH009 - KH03 - Da Nang lần 2
INSERT INTO MatHang_DuocDat VALUES ('DH009','MH05',3, 80000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH009','MH04',2, 45000,  GETDATE());
-- DH010 - KH08 - Ha Noi
INSERT INTO MatHang_DuocDat VALUES ('DH010','MH01',2, 50000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH010','MH02',3, 35000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH010','MH06',5, 25000,  GETDATE());
-- DH011 - KH09 - Ho Chi Minh
INSERT INTO MatHang_DuocDat VALUES ('DH011','MH05',6, 80000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH011','MH06',4, 25000,  GETDATE());
-- DH012 - KH10 - Da Lat
INSERT INTO MatHang_DuocDat VALUES ('DH012','MH04',4, 45000,  GETDATE());
INSERT INTO MatHang_DuocDat VALUES ('DH012','MH05',2, 80000,  GETDATE());

-- ── Kiểm tra nhanh ───────────────────────────

SELECT 'VanPhongDaiDien' AS Bang, COUNT(*) AS SoBanGhi FROM VanPhongDaiDien UNION ALL
SELECT 'CuaHang',                 COUNT(*) FROM CuaHang          UNION ALL
SELECT 'MatHang',                 COUNT(*) FROM MatHang           UNION ALL
SELECT 'MatHang_LuuTru',          COUNT(*) FROM MatHang_LuuTru    UNION ALL
SELECT 'DonDatHang',              COUNT(*) FROM DonDatHang         UNION ALL
SELECT 'MatHang_DuocDat',         COUNT(*) FROM MatHang_DuocDat;
-- Kết quả đúng: 4, 9, 6, 21, 12, 27


select * from  VanPhongDaiDien;
select * from  CuaHang;
select * from  MatHang;
select * from  MatHang_LuuTru;
select * from  DonDatHang;
select * from  MatHang_DuocDat;


--  tạo user kết nối (Login) vào server, nhưng chưa có quyền xem, sửa
CREATE LOGIN oracle_etl WITH PASSWORD = '123456';

-- Cấp quyền "xem" các bảng nằm trong Schema dbo (DataBase Owner)
USE BanHang;
CREATE USER oracle_etl FOR LOGIN oracle_etl;
GRANT SELECT ON SCHEMA::dbo TO oracle_etl;


-- test thử xem có quyền chưa:
SELECT COUNT(*) FROM VanPhongDaiDien; 



USE BanHang;
SELECT HAS_PERMS_BY_NAME('dbo.VanPhongDaiDien', 'OBJECT', 'SELECT') AS CanSelect;
-- Chạy với context của oracle_etl
EXECUTE AS LOGIN = 'oracle_etl';
SELECT HAS_PERMS_BY_NAME('dbo.VanPhongDaiDien', 'OBJECT', 'SELECT') AS CanSelect;
REVERT;





USE BANHANG;
GO

-- Kiểm tra trạng thái FK constraints
SELECT 
    OBJECT_NAME(parent_object_id) AS TableName,
    name AS ConstraintName,
    is_disabled AS IsDisabled
FROM sys.foreign_keys
ORDER BY TableName;



USE BANHANG;
GO

-- 1. Kiểm tra: Mọi DonDatHang có ≥1 MatHang_DuocDat
SELECT COUNT(DISTINCT MaDon) AS DonDatHangKhongCoMatHang
FROM DonDatHang
WHERE MaDon NOT IN (SELECT DISTINCT MaDon FROM MatHang_DuocDat);

-- 2. Kiểm tra: Mọi MatHang được đặt có trong kho
SELECT COUNT(DISTINCT MaMH) AS MatHangDatNhungKhongCoKho
FROM MatHang_DuocDat
WHERE MaMH NOT IN (SELECT DISTINCT MaMH FROM MatHang_LuuTru);

-- 3. Kiểm tra: Mọi CuaHang thuộc 1 VanPhongDaiDien
SELECT COUNT(*) AS CuaHangOrphan
FROM CuaHang
WHERE MaThanhPho NOT IN (SELECT MaThanhPho FROM VanPhongDaiDien);

-- 4. Kiểm tra: Mọi DonDatHang thuộc 1 KhachHang
--SELECT COUNT(*) AS DonDatHangOrphan
--FROM DonDatHang
--WHERE MaKH NOT IN (SELECT MaKH FROM KhachHang);



select * from  VanPhongDaiDien;
select * from  CuaHang;
select * from  MatHang;
select * from  MatHang_LuuTru;
select * from  DonDatHang;
select * from  MatHang_DuocDat;

USE BANHANG;
GO

select d.madon, count(md.MaMH) from  DonDatHang d 
join MatHang_DuocDat md
on d.madon = md.MaDon
group by d.madon
having count(md.MaMH)  >1
;

select * from mathang_duocdat md where md.madon= '10007';