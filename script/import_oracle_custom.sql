select 'khachhang', count(*) from khachhang
union all
select 'kh_dulich', count(*) from kh_dulich
union all
select 'kh_buudien', count(*) from kh_buudien;

SELECT * FROM KH_BuuDien;
SELECT * FROM KH_DuLich;
SELECT * FROM KhachHang;
-- dọn dẹp trước khi insert

SELECT user FROM dual;


ALTER TABLE KH_BuuDien DISABLE CONSTRAINT fk_khbd_kh;
ALTER TABLE KH_DuLich DISABLE CONSTRAINT fk_khdl_kh;

TRUNCATE TABLE KH_BuuDien;

TRUNCATE TABLE KH_DuLich;

TRUNCATE TABLE KhachHang;

ALTER TABLE KH_BuuDien ENABLE CONSTRAINT fk_khbd_kh;
ALTER TABLE KH_DuLich ENABLE CONSTRAINT fk_khdl_kh;

COMMIT;

ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD';
ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD';
INSERT INTO KH_DuLich (MaKH, HuongDanVien, ThoiGian) VALUES (6675, 'Breno Aragão', '2018-01-22');


-- import dữ liệu


@"D:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\output\04_khach_hang.sql"


@"D:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\output/05_khach_hang_du_lich.sql"


@"D:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\output/06_khach_hang_buu_dien.sql"

COMMIT;


