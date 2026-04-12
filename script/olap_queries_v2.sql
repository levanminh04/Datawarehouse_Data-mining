-- ============================================================
-- 15 CAU TRUY VAN OLAP CHUAN TREN DATA WAREHOUSE
-- Chay voi user: DATAWAREHOUSE
--
-- Su dung cac ky thuat OLAP thuc su:
--   ROLLUP, CUBE, GROUPING SETS, RANK, DENSE_RANK,
--   ROW_NUMBER, LAG, LEAD, NTILE, RATIO_TO_REPORT,
--   PERCENT_RANK, Window Aggregate (SUM OVER, AVG OVER)
--
-- Phan loai theo 5 phep toan OLAP:
--   [ROLL-UP]     Cau 1, 2, 3
--   [DRILL-DOWN]  Cau 4, 5
--   [SLICE/DICE]  Cau 6, 7, 8
--   [PIVOT]       Cau 9, 10
--   [RANKING]     Cau 11, 12, 13
--   [TREND]       Cau 14, 15
-- ============================================================

-- ============================================================
-- ======================= ROLL-UP ============================
-- ============================================================

-- ============================================================
-- CAU 1: [ROLLUP] Doanh thu theo phan cap Dia diem
--   CuaHang -> ThanhPho -> Bang -> Tong cong
-- Ky thuat: GROUP BY ROLLUP
-- Y nghia: Xem doanh thu tu chi tiet (cua hang) den tong hop (bang, toan bo)
-- ============================================================
SELECT l.Bang,
       l.TenThanhPho,
       l.MaCuaHang,
       COUNT(DISTINCT fo.MaDon)  AS SoDon,
       SUM(fo.TongTien)          AS DoanhThu,
       GROUPING(l.Bang)          AS Is_TongCong,
       GROUPING(l.TenThanhPho)   AS Is_TongBang,
       GROUPING(l.MaCuaHang)     AS Is_TongTP
FROM   FACT_ORDER fo
JOIN   DIM_LOCATION l ON fo.MaCuaHang = l.MaCuaHang
GROUP BY ROLLUP(l.Bang, l.TenThanhPho, l.MaCuaHang)
ORDER BY l.Bang NULLS LAST, l.TenThanhPho NULLS LAST, l.MaCuaHang NULLS LAST;

-- ============================================================
-- CAU 2: [ROLLUP] Doanh thu theo phan cap Thoi gian
--   Ngay -> Thang -> Quy -> Nam -> Tong cong
-- Ky thuat: GROUP BY ROLLUP
-- Y nghia: Xem doanh thu tu chi tiet (ngay) den tong hop (nam, toan bo)
-- ============================================================
SELECT t.Nam,
       t.Quy,
       t.Thang,
       COUNT(DISTINCT fo.MaDon)  AS SoDon,
       SUM(fo.SoLuongDat)       AS TongSoLuong,
       SUM(fo.TongTien)          AS DoanhThu,
       ROUND(AVG(fo.TongTien), 2) AS TBDon
FROM   FACT_ORDER fo
JOIN   DIM_TIME t ON fo.MaThoiGian = t.MaThoiGian
GROUP BY ROLLUP(t.Nam, t.Quy, t.Thang)
ORDER BY t.Nam NULLS LAST, t.Quy NULLS LAST, t.Thang NULLS LAST;

-- ============================================================
-- CAU 3: [CUBE] Doanh thu theo moi to hop Kenh ban hang × Loai KH
-- Ky thuat: GROUP BY CUBE
-- Y nghia: Xem doanh thu cho MOI TO HOP co the cua 2 chieu,
--          bao gom subtotal theo tung chieu va grand total
-- ============================================================
SELECT fo.KenhBanHang,
       c.LoaiKH,
       COUNT(DISTINCT fo.MaDon)  AS SoDon,
       COUNT(DISTINCT fo.MaKH)  AS SoKH,
       SUM(fo.TongTien)          AS DoanhThu,
       ROUND(AVG(fo.TongTien), 2) AS TBDon,
       GROUPING(fo.KenhBanHang)  AS Is_AllKenh,
       GROUPING(c.LoaiKH)       AS Is_AllLoai
FROM   FACT_ORDER fo
JOIN   DIM_CUSTOMER c ON fo.MaKH = c.MaKH
GROUP BY CUBE(fo.KenhBanHang, c.LoaiKH)
ORDER BY fo.KenhBanHang NULLS LAST, c.LoaiKH NULLS LAST;

-- ============================================================
-- ====================== DRILL-DOWN =========================
-- ============================================================

-- ============================================================
-- CAU 4: [DRILL-DOWN] Tu tong doanh thu theo Bang -> chi tiet theo TP
-- Ky thuat: GROUPING SETS (2 muc: Bang va Bang+TP)
-- Y nghia: Trong cung 1 ket qua, vua thay tong Bang vua thay chi tiet TP
-- ============================================================
SELECT l.Bang,
       l.TenThanhPho,
       COUNT(DISTINCT fo.MaDon)  AS SoDon,
       SUM(fo.TongTien)          AS DoanhThu,
       ROUND(AVG(fo.TongTien), 2) AS TBDon,
       GROUPING(l.TenThanhPho)   AS Is_TongBang
FROM   FACT_ORDER fo
JOIN   DIM_LOCATION l ON fo.MaCuaHang = l.MaCuaHang
GROUP BY GROUPING SETS (
    (l.Bang),                    -- Muc Roll-up: tong theo Bang
    (l.Bang, l.TenThanhPho)      -- Muc Drill-down: chi tiet TP trong Bang
)
ORDER BY l.Bang, l.TenThanhPho NULLS FIRST;

-- ============================================================
-- CAU 5: [DRILL-DOWN] Doanh thu theo Nam -> chi tiet theo Quy va Thang
-- Ky thuat: GROUPING SETS (3 muc)
-- Y nghia: 3 cap do zoom trong cung 1 truy van
-- ============================================================
SELECT t.Nam,
       t.Quy,
       t.Thang,
       SUM(fo.TongTien)          AS DoanhThu,
       COUNT(DISTINCT fo.MaDon)  AS SoDon,
       CASE
           WHEN GROUPING(t.Quy) = 1 AND GROUPING(t.Thang) = 1 THEN 'Tong Nam'
           WHEN GROUPING(t.Thang) = 1 THEN 'Tong Quy'
           ELSE 'Chi tiet Thang'
       END AS CapDo
FROM   FACT_ORDER fo
JOIN   DIM_TIME t ON fo.MaThoiGian = t.MaThoiGian
GROUP BY GROUPING SETS (
    (t.Nam),                     -- Muc 1: Tong theo Nam
    (t.Nam, t.Quy),              -- Muc 2: Chi tiet Quy
    (t.Nam, t.Quy, t.Thang)      -- Muc 3: Chi tiet Thang
)
ORDER BY t.Nam, t.Quy NULLS FIRST, t.Thang NULLS FIRST;

-- ============================================================
-- ===================== SLICE / DICE =========================
-- ============================================================

-- ============================================================
-- CAU 6: [SLICE] Phan tich doanh thu chi trong Quy 1 (co dinh 1 chieu)
--   + So sanh tung cua hang voi trung binh cua Thanh pho
-- Ky thuat: Window function AVG() OVER (PARTITION BY)
-- Y nghia: Cat lat Quy = 1, roi so sanh tung cua hang voi TB thanh pho
-- ============================================================
SELECT l.Bang,
       l.TenThanhPho,
       l.MaCuaHang,
       SUM(fo.TongTien)          AS DoanhThu_CH,
       ROUND(AVG(SUM(fo.TongTien)) OVER (PARTITION BY l.TenThanhPho), 2)
                                  AS TB_ThanhPho,
       ROUND(SUM(fo.TongTien) - AVG(SUM(fo.TongTien)) OVER (PARTITION BY l.TenThanhPho), 2)
                                  AS ChenhLech
FROM   FACT_ORDER fo
JOIN   DIM_LOCATION l ON fo.MaCuaHang = l.MaCuaHang
JOIN   DIM_TIME t     ON fo.MaThoiGian = t.MaThoiGian
WHERE  t.Quy = 1                           -- SLICE: co dinh Quy = 1
GROUP BY l.Bang, l.TenThanhPho, l.MaCuaHang
ORDER BY l.Bang, l.TenThanhPho, DoanhThu_CH DESC;

-- ============================================================
-- CAU 7: [DICE] Ton kho san pham gia cao tai cua hang vat ly trong 2017
--   Co dinh 3 chieu: LoaiCuaHang + khoang Gia + khoang Thoi gian
-- Ky thuat: Multi-dimension filter + aggregation
-- Y nghia: Cat khoi con: chi SP gia > 500, CH vat ly, nam 2017
-- ============================================================
SELECT l.Bang,
       l.TenThanhPho,
       l.MaCuaHang,
       COUNT(DISTINCT fi.MaMH)    AS SoMatHang,
       SUM(fi.SoLuongTon)         AS TongTonKho,
       ROUND(AVG(p.Gia), 2)      AS TBGia
FROM   FACT_INVENTORY fi
JOIN   DIM_LOCATION l ON fi.MaCuaHang = l.MaCuaHang
JOIN   DIM_PRODUCT p  ON fi.MaMH = p.MaMH
JOIN   DIM_TIME t     ON fi.MaThoiGian = t.MaThoiGian
WHERE  l.LoaiCuaHang = 'Vat ly'           -- DICE chieu 1: chi CH vat ly
  AND  p.Gia > 500                         -- DICE chieu 2: SP gia cao
  AND  t.Nam = 2017                        -- DICE chieu 3: nam 2017
GROUP BY l.Bang, l.TenThanhPho, l.MaCuaHang
ORDER BY TongTonKho DESC;

-- ============================================================
-- CAU 8: [DICE + WINDOW] So don theo thu trong tuan, chi kenh Truc tuyen
--   va ty le so voi tong tuan
-- Ky thuat: RATIO_TO_REPORT
-- Y nghia: Cat lat KenhBanHang = 'Truc tuyen', phan tich theo ngay trong tuan
-- ============================================================
SELECT t.ThuTrongTuan,
       COUNT(DISTINCT fo.MaDon)  AS SoDon,
       SUM(fo.TongTien)          AS DoanhThu,
       ROUND(RATIO_TO_REPORT(SUM(fo.TongTien)) OVER () * 100, 2)
                                  AS PhanTram_DoanhThu
FROM   FACT_ORDER fo
JOIN   DIM_TIME t ON fo.MaThoiGian = t.MaThoiGian
WHERE  fo.KenhBanHang = 'Truc tuyen'       -- SLICE: chi kenh truc tuyen
GROUP BY t.ThuTrongTuan
ORDER BY PhanTram_DoanhThu DESC;

-- ============================================================
-- ======================== PIVOT =============================
-- ============================================================

-- ============================================================
-- CAU 9: [PIVOT] Doanh thu theo Nam (cot) x Bang (hang)
-- Ky thuat: Oracle PIVOT
-- Y nghia: Xoay chieu Thoi gian tu dong thanh cot
-- ============================================================
SELECT *
FROM (
    SELECT l.Bang,
           t.Nam,
           fo.TongTien
    FROM   FACT_ORDER fo
    JOIN   DIM_LOCATION l ON fo.MaCuaHang = l.MaCuaHang
    JOIN   DIM_TIME t     ON fo.MaThoiGian = t.MaThoiGian
)
PIVOT (
    SUM(TongTien) AS DT
    FOR Nam IN (2016 AS "2016", 2017 AS "2017", 2018 AS "2018")
)
ORDER BY Bang;

-- ============================================================
-- CAU 10: [PIVOT] So don theo Kenh ban hang (cot) x Quy (hang)
-- Ky thuat: Oracle PIVOT
-- Y nghia: Xoay chieu KenhBanHang tu dong thanh cot, hang = Quy
-- ============================================================
SELECT *
FROM (
    SELECT t.Nam,
           t.Quy,
           fo.KenhBanHang,
           fo.MaDon
    FROM   FACT_ORDER fo
    JOIN   DIM_TIME t ON fo.MaThoiGian = t.MaThoiGian
)
PIVOT (
    COUNT(DISTINCT MaDon) AS SoDon
    FOR KenhBanHang IN ('Tai cua hang' AS OFFLINE, 'Truc tuyen' AS ONLINE)
)
ORDER BY Nam, Quy;

-- ============================================================
-- ======================= RANKING ============================
-- ============================================================

-- ============================================================
-- CAU 11: [RANK] Top 10 khach hang chi tieu nhieu nhat + phan nhom
-- Ky thuat: RANK, NTILE, SUM OVER
-- Y nghia: Xep hang KH theo tong chi tieu, chia 4 nhom (quartile)
-- ============================================================
SELECT * FROM (
    SELECT c.MaKH,
           c.TenKH,
           c.LoaiKH,
           c.Bang,
           COUNT(DISTINCT fo.MaDon)  AS SoDon,
           SUM(fo.TongTien)          AS TongChiTieu,
           RANK() OVER (ORDER BY SUM(fo.TongTien) DESC)
                                      AS Hang,
           NTILE(4) OVER (ORDER BY SUM(fo.TongTien) DESC)
                                      AS Nhom_4,
           ROUND(RATIO_TO_REPORT(SUM(fo.TongTien)) OVER () * 100, 4)
                                      AS PhanTram_DoanhThu
    FROM   FACT_ORDER fo
    JOIN   DIM_CUSTOMER c ON fo.MaKH = c.MaKH
    GROUP BY c.MaKH, c.TenKH, c.LoaiKH, c.Bang
)
WHERE Hang <= 10
ORDER BY Hang;

-- ============================================================
-- CAU 12: [DENSE_RANK] Xep hang san pham ban chay nhat MOI THANH PHO
-- Ky thuat: DENSE_RANK OVER (PARTITION BY)
-- Y nghia: Trong moi TP, SP nao ban nhieu nhat? (Top 3 moi TP)
-- ============================================================
SELECT * FROM (
    SELECT l.TenThanhPho,
           p.MaMH,
           p.MoTa,
           SUM(fo.SoLuongDat)       AS TongBan,
           SUM(fo.TongTien)          AS DoanhThu,
           DENSE_RANK() OVER (
               PARTITION BY l.TenThanhPho
               ORDER BY SUM(fo.SoLuongDat) DESC
           ) AS Hang_TrongTP
    FROM   FACT_ORDER fo
    JOIN   DIM_LOCATION l ON fo.MaCuaHang = l.MaCuaHang
    JOIN   DIM_PRODUCT p  ON fo.MaMH = p.MaMH
    GROUP BY l.TenThanhPho, p.MaMH, p.MoTa
)
WHERE Hang_TrongTP <= 3
ORDER BY TenThanhPho, Hang_TrongTP;

-- ============================================================
-- CAU 13: [ROW_NUMBER + PERCENTILE] Phan vi doanh thu cua hang
-- Ky thuat: ROW_NUMBER, PERCENT_RANK, CUME_DIST
-- Y nghia: Moi cua hang dung o vi tri nao trong toan he thong?
-- ============================================================
SELECT l.MaCuaHang,
       l.TenCuaHang,
       l.TenThanhPho,
       l.LoaiCuaHang,
       SUM(fo.TongTien)          AS DoanhThu,
       ROW_NUMBER() OVER (ORDER BY SUM(fo.TongTien) DESC)
                                  AS ViTri,
       ROUND(PERCENT_RANK() OVER (ORDER BY SUM(fo.TongTien)) * 100, 2)
                                  AS PhanVi_Pct,
       ROUND(CUME_DIST() OVER (ORDER BY SUM(fo.TongTien)) * 100, 2)
                                  AS TichLuy_Pct
FROM   FACT_ORDER fo
JOIN   DIM_LOCATION l ON fo.MaCuaHang = l.MaCuaHang
GROUP BY l.MaCuaHang, l.TenCuaHang, l.TenThanhPho, l.LoaiCuaHang
ORDER BY DoanhThu DESC;

-- ============================================================
-- ===================== TREND / WINDOW =======================
-- ============================================================

-- ============================================================
-- CAU 14: [LAG/LEAD] Tang truong doanh thu theo thang so voi thang truoc
-- Ky thuat: LAG, Window SUM
-- Y nghia: Moi thang doanh thu tang hay giam bao nhieu % so voi thang truoc?
-- ============================================================
SELECT Nam, Thang, DoanhThu,
       DoanhThu_ThangTruoc,
       CASE WHEN DoanhThu_ThangTruoc > 0
            THEN ROUND((DoanhThu - DoanhThu_ThangTruoc) / DoanhThu_ThangTruoc * 100, 2)
            ELSE NULL
       END AS TangTruong_Pct,
       DoanhThu_ThangSau
FROM (
    SELECT t.Nam,
           t.Thang,
           SUM(fo.TongTien)          AS DoanhThu,
           LAG(SUM(fo.TongTien))  OVER (ORDER BY t.Nam, t.Thang)
                                      AS DoanhThu_ThangTruoc,
           LEAD(SUM(fo.TongTien)) OVER (ORDER BY t.Nam, t.Thang)
                                      AS DoanhThu_ThangSau
    FROM   FACT_ORDER fo
    JOIN   DIM_TIME t ON fo.MaThoiGian = t.MaThoiGian
    GROUP BY t.Nam, t.Thang
)
ORDER BY Nam, Thang;

-- ============================================================
-- CAU 15: [RUNNING TOTAL] Doanh thu tich luy theo thoi gian + trung binh truot
-- Ky thuat: SUM OVER (ROWS UNBOUNDED PRECEDING), AVG OVER (ROWS 2 PRECEDING)
-- Y nghia: Doanh thu luy ke tu dau nam va trung binh truot 3 thang
-- ============================================================
SELECT t.Nam,
       t.Thang,
       SUM(fo.TongTien)          AS DoanhThu_Thang,
       SUM(SUM(fo.TongTien)) OVER (
           PARTITION BY t.Nam
           ORDER BY t.Thang
           ROWS UNBOUNDED PRECEDING
       )                          AS LuyKe_TuDauNam,
       ROUND(AVG(SUM(fo.TongTien)) OVER (
           ORDER BY t.Nam, t.Thang
           ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ), 2)                      AS TB_Truot_3Thang,
       ROUND(SUM(SUM(fo.TongTien)) OVER (
           PARTITION BY t.Nam
           ORDER BY t.Thang
           ROWS UNBOUNDED PRECEDING
       ) / SUM(SUM(fo.TongTien)) OVER (PARTITION BY t.Nam) * 100, 2)
                                  AS PhanTram_LuyKe
FROM   FACT_ORDER fo
JOIN   DIM_TIME t ON fo.MaThoiGian = t.MaThoiGian
GROUP BY t.Nam, t.Thang
ORDER BY t.Nam, t.Thang;
