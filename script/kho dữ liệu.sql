CREATE TABLE KhachHang (
  MaKH                 VARCHAR2(10)  CONSTRAINT pk_kh PRIMARY KEY,
  TenKH                VARCHAR2(100) NOT NULL,
  MaThanhPho           VARCHAR2(10)  NOT NULL,
  NgayDatHangDauTien   DATE,
  ThoiGian             TIMESTAMP     DEFAULT SYSTIMESTAMP
);
 
CREATE TABLE KH_DuLich (
  MaKH          VARCHAR2(10)  CONSTRAINT pk_khdl PRIMARY KEY,
  HuongDanVien  VARCHAR2(200),
  ThoiGian      TIMESTAMP     DEFAULT SYSTIMESTAMP,
  CONSTRAINT fk_khdl_kh FOREIGN KEY (MaKH) REFERENCES KhachHang(MaKH)
);
 
CREATE TABLE KH_BuuDien (
  MaKH          VARCHAR2(10)  CONSTRAINT pk_khbd PRIMARY KEY,
  DiaChiBuuDien VARCHAR2(300),
  ThoiGian      TIMESTAMP     DEFAULT SYSTIMESTAMP,
  CONSTRAINT fk_khbd_kh FOREIGN KEY (MaKH) REFERENCES KhachHang(MaKH)
);




-- INSERT KhachHang (10 ban ghi)
INSERT INTO KhachHang VALUES ('KH01','Nguyen Van An',  'TP01',DATE'2022-03-10',SYSTIMESTAMP);
INSERT INTO KhachHang VALUES ('KH02','Tran Thi Bich',  'TP01',DATE'2022-05-22',SYSTIMESTAMP);
INSERT INTO KhachHang VALUES ('KH03','Le Minh Cuong',  'TP02',DATE'2022-07-14',SYSTIMESTAMP);
INSERT INTO KhachHang VALUES ('KH04','Pham Thi Dung',  'TP02',DATE'2023-01-08',SYSTIMESTAMP);
INSERT INTO KhachHang VALUES ('KH05','Hoang Van Em',   'TP03',DATE'2023-04-17',SYSTIMESTAMP);
INSERT INTO KhachHang VALUES ('KH06','Ngo Thi Phuong', 'TP03',DATE'2023-06-30',SYSTIMESTAMP);
INSERT INTO KhachHang VALUES ('KH07','Dinh Van Giang', 'TP04',DATE'2023-09-05',SYSTIMESTAMP);
INSERT INTO KhachHang VALUES ('KH08','Vo Thi Huong',   'TP01',DATE'2024-02-14',SYSTIMESTAMP);
INSERT INTO KhachHang VALUES ('KH09','Bui Quoc Hung',  'TP03',DATE'2024-05-20',SYSTIMESTAMP);
INSERT INTO KhachHang VALUES ('KH10','Duong Thi Lan',  'TP04',DATE'2024-08-01',SYSTIMESTAMP);
COMMIT;
 
-- INSERT KH_DuLich (6 ban ghi - KH01,02,03,05,06,07)
INSERT INTO KH_DuLich VALUES ('KH01','HDV Nguyen Thanh Tung - Tour HN City', SYSTIMESTAMP);
INSERT INTO KH_DuLich VALUES ('KH02','HDV Le Thi Mai - Tour Mien Bac',       SYSTIMESTAMP);
INSERT INTO KH_DuLich VALUES ('KH03','HDV Pham Van Duc - Tour DN Hoi An',    SYSTIMESTAMP);
INSERT INTO KH_DuLich VALUES ('KH05','HDV Tran Van Hoa - Tour SG Express',   SYSTIMESTAMP);
INSERT INTO KH_DuLich VALUES ('KH06','HDV Nguyen Minh Tri - Tour Mien Nam',  SYSTIMESTAMP);
INSERT INTO KH_DuLich VALUES ('KH07','HDV Vo Thi Nga - Tour Tay Nguyen',     SYSTIMESTAMP);
COMMIT;
 
-- INSERT KH_BuuDien (6 ban ghi - KH02,04,06,08,09,10)
INSERT INTO KH_BuuDien VALUES ('KH02','45 Pho Hue, Hai Ba Trung, Ha Noi',        SYSTIMESTAMP);
INSERT INTO KH_BuuDien VALUES ('KH04','78 Bach Dang, Hai Chau, Da Nang',         SYSTIMESTAMP);
INSERT INTO KH_BuuDien VALUES ('KH06','123 Nguyen Trai, Q1, Ho Chi Minh',        SYSTIMESTAMP);
INSERT INTO KH_BuuDien VALUES ('KH08','12 Hang Bai, Hoan Kiem, Ha Noi',          SYSTIMESTAMP);
INSERT INTO KH_BuuDien VALUES ('KH09','55 Nam Ky Khoi Nghia, Q3, Ho Chi Minh',   SYSTIMESTAMP);
INSERT INTO KH_BuuDien VALUES ('KH10','34 Phan Dinh Phung, Da Lat, Lam Dong',    SYSTIMESTAMP);
COMMIT;

select 
    'khachhang' as table_name,
    (select count(*) from KhachHang) as cnt
from dual
union all
select 
    'kh_buudien' as table_name,
    (select count(*) from kh_buudien) as cnt
from dual
union all
select 
    'kh_dulich' as table_name,
    (select count(*) from kh_dulich) as cnt
from dual
;



select * from khachhang;
select * from kh_dulich;
select * from kh_buudien;

--DESC khachhang;
--Name               Null?    Type          
-------------------- -------- ------------- 
--MAKH               NOT NULL VARCHAR2(10)  
--TENKH              NOT NULL VARCHAR2(100) 
--MATHANHPHO         NOT NULL VARCHAR2(10)  
--NGAYDATHANGDAUTIEN          DATE          
--THOIGIAN                    TIMESTAMP(6)
--DESC kh_dulich;
--Name         Null?    Type          
-------------- -------- ------------- 
--MAKH         NOT NULL VARCHAR2(10)  
--HUONGDANVIEN          VARCHAR2(200) 
--THOIGIAN              TIMESTAMP(6)  
--DESC kh_buudien;
--Name          Null?    Type          
--------------- -------- ------------- 
--MAKH          NOT NULL VARCHAR2(10)  
--DIACHIBUUDIEN          VARCHAR2(300) 
--THOIGIAN               TIMESTAMP(6)  

-- Tao Database Link tu Oracle sang SQL Server
-- (Chay voi user oracle_etl)
 DROP DATABASE LINK sqlserver_banhang;



-- không có từ khóa PUBLIC => Private Database Link => chỉ có tác dụng với duy nhất user thực hiện lệnh này, cụ thể là user levanminh.
CREATE DATABASE LINK sqlserver_banhang
  CONNECT TO oracle_etl IDENTIFIED BY "123456"
  USING 'SQLSERVER_BANHANG';  -- Ten ODBC DSN da tao o tren
 
 
 
-- Test ket noi: thu doc bang VanPhongDaiDien tu SQL Server
SELECT * FROM "VanPhongDaiDien"@sqlserver_banhang;
 
 
SELECT COUNT(*) FROM "VanPhongDaiDien"@sqlserver_banhang;   -- phai ra 4
SELECT COUNT(*) FROM "CuaHang"@sqlserver_banhang;           -- phai ra 9
SELECT COUNT(*) FROM "MatHang"@sqlserver_banhang;           -- phai ra 6
SELECT COUNT(*) FROM "DonDatHang"@sqlserver_banhang;        -- phai ra 12
SELECT COUNT(*) FROM "MatHang_DuocDat"@sqlserver_banhang;        
SELECT COUNT(*) FROM "MatHang_LuuTru"@sqlserver_banhang;        

 
SELECT * FROM "VanPhongDaiDien"@sqlserver_banhang;   -- phai ra 4
SELECT * FROM "CuaHang"@sqlserver_banhang;           -- phai ra 9
SELECT * FROM "MatHang"@sqlserver_banhang;           -- phai ra 6
SELECT * FROM "DonDatHang"@sqlserver_banhang;        -- phai ra 12
SELECT * FROM "MatHang_DuocDat"@sqlserver_banhang;        
SELECT * FROM "MatHang_LuuTru"@sqlserver_banhang;        
 
-- Neu thay du lieu hien ra la thanh cong!

SELECT COUNT(DISTINCT mh."MaMH") FROM "MatHang"@sqlserver_banhang mh; -- 20506 BẢN GHI
SELECT COUNT(DISTINCT mh."MoTa") FROM "MatHang"@sqlserver_banhang mh; -- => 73 BẢN GHI 



SELECT SYS_CONTEXT('USERENV','SERVICE_NAME') FROM DUAL;
SELECT SYS_CONTEXT('USERENV','DB_NAME') FROM DUAL;
SELECT DB_LINK, USERNAME, HOST FROM USER_DB_LINKS;
SELECT USERNAME FROM ALL_USERS ORDER BY USERNAME;

SELECT USER FROM DUAL;

SHOW USER;

SELECT TABLE_NAME FROM ALL_TABLES 
WHERE OWNER = 'DWH_ADMIN'
ORDER BY TABLE_NAME;
SELECT TABLE_NAME FROM ALL_TABLES 
WHERE OWNER = 'LEVANMINH'
ORDER BY TABLE_NAME;



-- CHECK XEM USER HIỆN TẠI CÓ NHỮNG QUYỀN NÀO
SELECT 'ROLE' AS Loai_Quyen, GRANTED_ROLE AS Ten_Quyen 
FROM USER_ROLE_PRIVS
UNION ALL
SELECT 'SYSTEM PRIVILEGE' AS Loai_Quyen, PRIVILEGE AS Ten_Quyen 
FROM USER_SYS_PRIVS
ORDER BY Loai_Quyen, Ten_Quyen;




-- 4. Kiểm tra: Mọi DonDatHang thuộc 1 KhachHang
SELECT COUNT(*) AS DonDatHangOrphan
FROM DonDatHang
WHERE MaKH NOT IN (SELECT MaKH FROM KhachHang);





















;