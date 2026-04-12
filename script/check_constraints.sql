-- ============================================================
-- VALIDATION SCRIPT: Kiểm tra ràng buộc & edge cases toàn bộ 9 bảng
-- Chạy tại Oracle (SQL Server truy cập qua @sqlserver_banhang)
-- Kết quả mong đợi: mọi "violations" = 0
-- ============================================================

-- ============================================================
-- PHẦN 0: ĐẾM SỐ DÒNG (xác nhận dữ liệu đã import đúng)
-- ============================================================
PROMPT === PHẦN 0: ROW COUNTS ===

-- Oracle tables
SELECT 'KhachHang'  AS bang, COUNT(*) AS so_dong FROM KhachHang
UNION ALL
SELECT 'KH_DuLich', COUNT(*) FROM KH_DuLich
UNION ALL
SELECT 'KH_BuuDien', COUNT(*) FROM KH_BuuDien;

-- SQL Server tables (via DB link)
SELECT 'VanPhongDaiDien'  AS bang, COUNT(*) AS so_dong FROM "VanPhongDaiDien"@sqlserver_banhang
UNION ALL
SELECT 'MatHang',         COUNT(*) FROM "MatHang"@sqlserver_banhang
UNION ALL
SELECT 'CuaHang',         COUNT(*) FROM "CuaHang"@sqlserver_banhang
UNION ALL
SELECT 'MatHang_LuuTru',  COUNT(*) FROM "MatHang_LuuTru"@sqlserver_banhang
UNION ALL
SELECT 'DonDatHang',      COUNT(*) FROM "DonDatHang"@sqlserver_banhang
UNION ALL
SELECT 'MatHang_DuocDat', COUNT(*) FROM "MatHang_DuocDat"@sqlserver_banhang;


-- ============================================================
-- PHẦN 1: KIỂM TRA KHÓA NGOẠI (FK)
-- Kết quả mong đợi: tất cả = 0
-- ============================================================
PROMPT === PHẦN 1: FK INTEGRITY ===

-- FK-1: KhachHang.MaThanhPho → VanPhongDaiDien.MaThanhPho
-- Oracle → SQL Server
SELECT 'FK-1 KhachHang→VanPhongDaiDien' AS check_name,
       COUNT(*) AS violations
FROM KhachHang kh
WHERE NOT EXISTS (
    SELECT 1 FROM "VanPhongDaiDien"@sqlserver_banhang vp
    WHERE TO_CHAR(vp.MaThanhPho) = kh.MaThanhPho
);

-- FK-2: CuaHang.MaThanhPho → VanPhongDaiDien.MaThanhPho
-- SQL Server → SQL Server
SELECT 'FK-2 CuaHang→VanPhongDaiDien' AS check_name,
       COUNT(*) AS violations
FROM "CuaHang"@sqlserver_banhang ch
WHERE NOT EXISTS (
    SELECT 1 FROM "VanPhongDaiDien"@sqlserver_banhang vp
    WHERE vp.MaThanhPho = ch.MaThanhPho
);

-- FK-3: KH_DuLich.MaKH → KhachHang.MaKH
-- Oracle → Oracle
SELECT 'FK-3 KH_DuLich→KhachHang' AS check_name,
       COUNT(*) AS violations
FROM KH_DuLich dl
WHERE NOT EXISTS (
    SELECT 1 FROM KhachHang kh
    WHERE kh.MaKH = dl.MaKH
);

-- FK-4: KH_BuuDien.MaKH → KhachHang.MaKH
-- Oracle → Oracle
SELECT 'FK-4 KH_BuuDien→KhachHang' AS check_name,
       COUNT(*) AS violations
FROM KH_BuuDien bd
WHERE NOT EXISTS (
    SELECT 1 FROM KhachHang kh
    WHERE kh.MaKH = bd.MaKH
);

-- FK-5: MatHang_LuuTru.MaCuaHang → CuaHang.MaCuaHang
-- SQL Server → SQL Server
SELECT 'FK-5 MatHang_LuuTru→CuaHang' AS check_name,
       COUNT(*) AS violations
FROM "MatHang_LuuTru"@sqlserver_banhang lt
WHERE NOT EXISTS (
    SELECT 1 FROM "CuaHang"@sqlserver_banhang ch
    WHERE ch.MaCuaHang = lt.MaCuaHang
);

-- FK-6: MatHang_LuuTru.MaMH → MatHang.MaMH
-- SQL Server → SQL Server
SELECT 'FK-6 MatHang_LuuTru→MatHang' AS check_name,
       COUNT(*) AS violations
FROM "MatHang_LuuTru"@sqlserver_banhang lt
WHERE NOT EXISTS (
    SELECT 1 FROM "MatHang"@sqlserver_banhang mh
    WHERE mh.MaMH = lt.MaMH
);

-- FK-7: DonDatHang.MaKH → KhachHang.MaKH
-- SQL Server → Oracle (cross-DB FK!)
SELECT 'FK-7 DonDatHang→KhachHang' AS check_name,
       COUNT(*) AS violations
FROM "DonDatHang"@sqlserver_banhang ddh
WHERE NOT EXISTS (
    SELECT 1 FROM KhachHang kh
    WHERE kh.MaKH = TO_CHAR(ddh.MaKH)
);

-- FK-8: MatHang_DuocDat.MaDon → DonDatHang.MaDon
-- SQL Server → SQL Server
SELECT 'FK-8 MatHang_DuocDat→DonDatHang' AS check_name,
       COUNT(*) AS violations
FROM "MatHang_DuocDat"@sqlserver_banhang mhdd
WHERE NOT EXISTS (
    SELECT 1 FROM "DonDatHang"@sqlserver_banhang ddh
    WHERE ddh.MaDon = mhdd.MaDon
);

-- FK-9: MatHang_DuocDat.MaMH → MatHang.MaMH
-- SQL Server → SQL Server
SELECT 'FK-9 MatHang_DuocDat→MatHang' AS check_name,
       COUNT(*) AS violations
FROM "MatHang_DuocDat"@sqlserver_banhang mhdd
WHERE NOT EXISTS (
    SELECT 1 FROM "MatHang"@sqlserver_banhang mh
    WHERE mh.MaMH = mhdd.MaMH
);


-- ============================================================
-- PHẦN 2: BUSINESS CONSTRAINTS
-- Kết quả mong đợi: tất cả = 0
-- ============================================================
PROMPT === PHẦN 2: BUSINESS CONSTRAINTS ===

-- BC-1: Mọi DonDatHang phải có ít nhất 1 dòng trong MatHang_DuocDat
-- (Không có đơn hàng "ma")
SELECT 'BC-1 DonDatHang co min 1 item' AS check_name,
       COUNT(*) AS violations
FROM "DonDatHang"@sqlserver_banhang ddh
WHERE NOT EXISTS (
    SELECT 1 FROM "MatHang_DuocDat"@sqlserver_banhang mhdd
    WHERE mhdd.MaDon = ddh.MaDon
);

-- BC-2: Mọi MaMH xuất hiện trong MatHang_DuocDat phải có trong MatHang_LuuTru
-- (Không đặt hàng sản phẩm chưa từng được lưu kho)
SELECT 'BC-2 ordered product phai co trong kho' AS check_name,
       COUNT(*) AS violations
FROM (
    SELECT DISTINCT MaMH FROM "MatHang_DuocDat"@sqlserver_banhang
) od
WHERE NOT EXISTS (
    SELECT 1 FROM "MatHang_LuuTru"@sqlserver_banhang lt
    WHERE lt.MaMH = od.MaMH
);


-- ============================================================
-- PHẦN 3: DUPLICATE & NULL CHECKS
-- Kết quả mong đợi: tất cả = 0
-- ============================================================
PROMPT === PHẦN 3: DUPLICATE & NULL ===

-- DUP-1: Duplicate MaKH trong KhachHang (vi phạm PK)
SELECT 'DUP-1 Duplicate MaKH KhachHang' AS check_name,
       COUNT(*) AS violations
FROM (
    SELECT MaKH FROM KhachHang
    GROUP BY MaKH HAVING COUNT(*) > 1
) t;

-- DUP-2: Duplicate MaKH trong KH_DuLich
SELECT 'DUP-2 Duplicate MaKH KH_DuLich' AS check_name,
       COUNT(*) AS violations
FROM (
    SELECT MaKH FROM KH_DuLich
    GROUP BY MaKH HAVING COUNT(*) > 1
) t;

-- DUP-3: Duplicate MaKH trong KH_BuuDien
SELECT 'DUP-3 Duplicate MaKH KH_BuuDien' AS check_name,
       COUNT(*) AS violations
FROM (
    SELECT MaKH FROM KH_BuuDien
    GROUP BY MaKH HAVING COUNT(*) > 1
) t;

-- NULL-1: KhachHang có MaThanhPho NULL
SELECT 'NULL-1 KhachHang.MaThanhPho IS NULL' AS check_name,
       COUNT(*) AS violations
FROM KhachHang WHERE MaThanhPho IS NULL;

-- NULL-2: KhachHang có TenKH NULL
SELECT 'NULL-2 KhachHang.TenKH IS NULL' AS check_name,
       COUNT(*) AS violations
FROM KhachHang WHERE TenKH IS NULL;

-- NULL-3: DonDatHang có MaKH NULL
SELECT 'NULL-3 DonDatHang.MaKH IS NULL' AS check_name,
       COUNT(*) AS violations
FROM "DonDatHang"@sqlserver_banhang WHERE MaKH IS NULL;

-- NULL-4: MatHang_DuocDat có SoLuongDat hoặc GiaDat NULL
SELECT 'NULL-4 MatHang_DuocDat NULL values' AS check_name,
       COUNT(*) AS violations
FROM "MatHang_DuocDat"@sqlserver_banhang
WHERE SoLuongDat IS NULL OR GiaDat IS NULL;


-- ============================================================
-- PHẦN 4: EDGE CASES / DATA QUALITY
-- ============================================================
PROMPT === PHẦN 4: EDGE CASES ===

-- EC-1: Số liệu âm hoặc 0 trong MatHang_LuuTru.SoLuongKho
SELECT 'EC-1 SoLuongKho <= 0' AS check_name,
       COUNT(*) AS violations
FROM "MatHang_LuuTru"@sqlserver_banhang
WHERE SoLuongKho <= 0;

-- EC-2: Số liệu âm hoặc 0 trong MatHang_DuocDat
SELECT 'EC-2 SoLuongDat <= 0 hoac GiaDat <= 0' AS check_name,
       COUNT(*) AS violations
FROM "MatHang_DuocDat"@sqlserver_banhang
WHERE SoLuongDat <= 0 OR GiaDat <= 0;

-- EC-3: MatHang tồn tại nhưng KHÔNG có trong kho bất kỳ cửa hàng nào
SELECT 'EC-3 MatHang khong co trong kho' AS check_name,
       COUNT(*) AS violations
FROM "MatHang"@sqlserver_banhang mh
WHERE NOT EXISTS (
    SELECT 1 FROM "MatHang_LuuTru"@sqlserver_banhang lt
    WHERE lt.MaMH = mh.MaMH
);

-- EC-4: MatHang tồn tại nhưng CHƯA được đặt lần nào
SELECT 'EC-4 MatHang chua duoc dat bao gio' AS check_name,
       COUNT(*) AS count_info
FROM "MatHang"@sqlserver_banhang mh
WHERE NOT EXISTS (
    SELECT 1 FROM "MatHang_DuocDat"@sqlserver_banhang mhdd
    WHERE mhdd.MaMH = mh.MaMH
);

-- EC-5: CuaHang không có sản phẩm nào trong kho
SELECT 'EC-5 CuaHang khong co mat hang' AS check_name,
       COUNT(*) AS violations
FROM "CuaHang"@sqlserver_banhang ch
WHERE NOT EXISTS (
    SELECT 1 FROM "MatHang_LuuTru"@sqlserver_banhang lt
    WHERE lt.MaCuaHang = ch.MaCuaHang
);

-- EC-6: KhachHang tồn tại nhưng chưa đặt hàng nào
-- (Không phải lỗi, nhưng cần biết)
SELECT 'EC-6 KhachHang chua dat hang bao gio' AS check_name,
       COUNT(*) AS count_info
FROM KhachHang kh
WHERE NOT EXISTS (
    SELECT 1 FROM "DonDatHang"@sqlserver_banhang ddh
    WHERE TO_CHAR(ddh.MaKH) = kh.MaKH
);

-- EC-7: Overlap KH_DuLich ∩ KH_BuuDien (KH thuộc cả 2 loại)
-- (Được thiết kế có overlap ~20%, đây là thông tin xác nhận)
SELECT 'EC-7 KH thuoc ca DuLich va BuuDien (overlap)' AS check_name,
       COUNT(*) AS count_info
FROM KH_DuLich dl
WHERE EXISTS (
    SELECT 1 FROM KH_BuuDien bd
    WHERE bd.MaKH = dl.MaKH
);

-- EC-8: VanPhongDaiDien không có KhachHang nào
SELECT 'EC-8 VanPhong khong co KhachHang nao' AS check_name,
       COUNT(*) AS violations
FROM "VanPhongDaiDien"@sqlserver_banhang vp
WHERE NOT EXISTS (
    SELECT 1 FROM KhachHang kh
    WHERE kh.MaThanhPho = TO_CHAR(vp.MaThanhPho)
);

-- EC-9: Ngày đặt hàng trong tương lai (NgayDatHang > SYSDATE)
SELECT 'EC-9 DonDatHang ngay trong tuong lai' AS check_name,
       COUNT(*) AS violations
FROM "DonDatHang"@sqlserver_banhang
WHERE NgayDatHang > SYSDATE;

-- EC-10: KhachHang có NgayDatHangDauTien sau ngày đặt hàng đầu tiên thực tế
SELECT 'EC-10 NgayDatHangDauTien sau thuc te' AS check_name,
       COUNT(*) AS violations
FROM KhachHang kh
JOIN (
    SELECT TO_CHAR(MaKH) AS MaKH, MIN(NgayDatHang) AS min_order_date
    FROM "DonDatHang"@sqlserver_banhang
    GROUP BY MaKH
) actual ON actual.MaKH = kh.MaKH
WHERE kh.NgayDatHangDauTien > actual.min_order_date;


-- ============================================================
-- PHẦN 5: THỐNG KÊ TỔNG QUAN
-- ============================================================
PROMPT === PHẦN 5: STATISTICS ===

-- STAT-1: Số đơn hàng trung bình mỗi khách hàng
SELECT ROUND(COUNT(*) / NULLIF((SELECT COUNT(*) FROM KhachHang), 0), 2)
       AS avg_orders_per_customer
FROM "DonDatHang"@sqlserver_banhang;

-- STAT-2: Số item trung bình mỗi đơn hàng
SELECT ROUND(COUNT(*) / NULLIF((SELECT COUNT(*) FROM "DonDatHang"@sqlserver_banhang), 0), 2)
       AS avg_items_per_order
FROM "MatHang_DuocDat"@sqlserver_banhang;

-- STAT-3: Top 10 sản phẩm được đặt nhiều nhất
SELECT mh.MaMH,
       mh.MoTa,
       SUM(mhdd.SoLuongDat) AS tong_so_luong_dat
FROM "MatHang"@sqlserver_banhang mh
JOIN "MatHang_DuocDat"@sqlserver_banhang mhdd ON mh.MaMH = mhdd.MaMH
GROUP BY mh.MaMH, mh.MoTa
ORDER BY tong_so_luong_dat DESC
FETCH FIRST 10 ROWS ONLY;

-- STAT-4: Top 10 cửa hàng có nhiều sản phẩm lưu trữ nhất
SELECT ch.MaCuaHang,
       ch.MaThanhPho,
       COUNT(lt.MaMH) AS so_mat_hang_trong_kho
FROM "CuaHang"@sqlserver_banhang ch
JOIN "MatHang_LuuTru"@sqlserver_banhang lt ON ch.MaCuaHang = lt.MaCuaHang
GROUP BY ch.MaCuaHang, ch.MaThanhPho
ORDER BY so_mat_hang_trong_kho DESC
FETCH FIRST 10 ROWS ONLY;

-- STAT-5: Số khách hàng theo thành phố (top 10)
SELECT vp.TenThanhPho,
       COUNT(kh.MaKH) AS so_khach_hang
FROM KhachHang kh
JOIN "VanPhongDaiDien"@sqlserver_banhang vp ON TO_CHAR(vp.MaThanhPho) = kh.MaThanhPho
GROUP BY vp.TenThanhPho
ORDER BY so_khach_hang DESC
FETCH FIRST 10 ROWS ONLY;

PROMPT === VALIDATION COMPLETE ===
PROMPT Tat ca violations phai = 0. count_info la thong tin tham khao.


-- ============================================================
-- PHẦN 6: KIỂM TRA TIME RANGES (tất cả 9 bảng)
-- Mục tiêu: mọi cột thời gian phải nằm trong khoảng 2015-2019
-- DonDatHang.NgayDatHang: ~2016-10 đến ~2018-10 (từ Olist)
-- Setup tables (VanPhong, CuaHang, MatHang, MatHang_LuuTru): trước 2016-10
-- Customer tables (KhachHang, KH_DuLich, KH_BuuDien): ~2016-2018
-- ============================================================
PROMPT === PHẦN 6: TIME RANGES CHECK ===

-- [Oracle] KhachHang
SELECT
    'KhachHang.NgayDatHangDauTien' AS col_name,
    TO_CHAR(MIN(NgayDatHangDauTien), 'YYYY-MM-DD') AS min_date,
    TO_CHAR(MAX(NgayDatHangDauTien), 'YYYY-MM-DD') AS max_date,
    COUNT(*) AS total_rows,
    COUNT(NgayDatHangDauTien) AS non_null_rows
FROM KhachHang;

-- [Oracle] KhachHang.ThoiGian (TIMESTAMP, DEFAULT SYSTIMESTAMP)
SELECT
    'KhachHang.ThoiGian (TIMESTAMP)' AS col_name,
    TO_CHAR(MIN(ThoiGian), 'YYYY-MM-DD') AS min_date,
    TO_CHAR(MAX(ThoiGian), 'YYYY-MM-DD') AS max_date,
    COUNT(*) AS total_rows,
    COUNT(ThoiGian) AS non_null_rows
FROM KhachHang;

-- [Oracle] KH_DuLich.ThoiGian
SELECT
    'KH_DuLich.ThoiGian' AS col_name,
    TO_CHAR(MIN(ThoiGian), 'YYYY-MM-DD') AS min_date,
    TO_CHAR(MAX(ThoiGian), 'YYYY-MM-DD') AS max_date,
    COUNT(*) AS total_rows,
    COUNT(ThoiGian) AS non_null_rows
FROM KH_DuLich;

-- [Oracle] KH_BuuDien.ThoiGian
SELECT
    'KH_BuuDien.ThoiGian' AS col_name,
    TO_CHAR(MIN(ThoiGian), 'YYYY-MM-DD') AS min_date,
    TO_CHAR(MAX(ThoiGian), 'YYYY-MM-DD') AS max_date,
    COUNT(*) AS total_rows,
    COUNT(ThoiGian) AS non_null_rows
FROM KH_BuuDien;

-- [SQL Server] VanPhongDaiDien.ThoiGian
SELECT
    'VanPhongDaiDien.ThoiGian' AS col_name,
    TO_CHAR(MIN(ThoiGian), 'YYYY-MM-DD') AS min_date,
    TO_CHAR(MAX(ThoiGian), 'YYYY-MM-DD') AS max_date,
    COUNT(*) AS total_rows,
    COUNT(ThoiGian) AS non_null_rows
FROM "VanPhongDaiDien"@sqlserver_banhang;

-- [SQL Server] CuaHang.ThoiGian
SELECT
    'CuaHang.ThoiGian' AS col_name,
    TO_CHAR(MIN(ThoiGian), 'YYYY-MM-DD') AS min_date,
    TO_CHAR(MAX(ThoiGian), 'YYYY-MM-DD') AS max_date,
    COUNT(*) AS total_rows,
    COUNT(ThoiGian) AS non_null_rows
FROM "CuaHang"@sqlserver_banhang;

-- [SQL Server] MatHang.ThoiGian
SELECT
    'MatHang.ThoiGian' AS col_name,
    TO_CHAR(MIN(ThoiGian), 'YYYY-MM-DD') AS min_date,
    TO_CHAR(MAX(ThoiGian), 'YYYY-MM-DD') AS max_date,
    COUNT(*) AS total_rows,
    COUNT(ThoiGian) AS non_null_rows
FROM "MatHang"@sqlserver_banhang;

-- [SQL Server] MatHang_LuuTru.ThoiGian
SELECT
    'MatHang_LuuTru.ThoiGian' AS col_name,
    TO_CHAR(MIN(ThoiGian), 'YYYY-MM-DD') AS min_date,
    TO_CHAR(MAX(ThoiGian), 'YYYY-MM-DD') AS max_date,
    COUNT(*) AS total_rows,
    COUNT(ThoiGian) AS non_null_rows
FROM "MatHang_LuuTru"@sqlserver_banhang;

-- [SQL Server] DonDatHang.NgayDatHang (không có ThoiGian)
SELECT
    'DonDatHang.NgayDatHang' AS col_name,
    TO_CHAR(MIN(NgayDatHang), 'YYYY-MM-DD') AS min_date,
    TO_CHAR(MAX(NgayDatHang), 'YYYY-MM-DD') AS max_date,
    COUNT(*) AS total_rows,
    COUNT(NgayDatHang) AS non_null_rows
FROM "DonDatHang"@sqlserver_banhang;

-- [SQL Server] MatHang_DuocDat.ThoiGian
SELECT
    'MatHang_DuocDat.ThoiGian' AS col_name,
    TO_CHAR(MIN(ThoiGian), 'YYYY-MM-DD') AS min_date,
    TO_CHAR(MAX(ThoiGian), 'YYYY-MM-DD') AS max_date,
    COUNT(*) AS total_rows,
    COUNT(ThoiGian) AS non_null_rows
FROM "MatHang_DuocDat"@sqlserver_banhang;

-- Tóm tắt kỳ vọng:
-- ┌─────────────────────────────────────────────────────────────────┐
-- │ Bảng                      │ Kỳ vọng min  │ Kỳ vọng max        │
-- ├─────────────────────────────────────────────────────────────────┤
-- │ KhachHang.NgayDatHangDauTien │ 2016-09   │ 2018-10            │
-- │ KhachHang.ThoiGian (TS)    │ sysdate     │ sysdate (tự động)  │
-- │ KH_DuLich.ThoiGian         │ 2016-09     │ 2018-10            │
-- │ KH_BuuDien.ThoiGian        │ 2016-09     │ 2018-10            │
-- │ VanPhongDaiDien.ThoiGian   │ 2015-xx     │ 2016-09 (trước đơn)│
-- │ CuaHang.ThoiGian           │ 2015-xx     │ 2016-09 (trước đơn)│
-- │ MatHang.ThoiGian           │ 2015-xx     │ 2016-09 (trước đơn)│
-- │ MatHang_LuuTru.ThoiGian    │ 2015-xx     │ 2016-09 (trước đơn)│
-- │ DonDatHang.NgayDatHang     │ 2016-09     │ 2018-10            │
-- │ MatHang_DuocDat.ThoiGian   │ 2016-09     │ 2018-10            │
-- └─────────────────────────────────────────────────────────────────┘
-- Nếu thấy năm 2023-2026 → cần regenerate ETL với ThoiGian đã sửa

PROMPT === TIME RANGE CHECK COMPLETE ===
