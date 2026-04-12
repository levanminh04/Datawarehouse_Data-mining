--------------------------------------------------------
--  File created - Saturday-April-11-2026   
--------------------------------------------------------
--------------------------------------------------------
--  DDL for Package Body PKG_ETL_DW
--------------------------------------------------------

  CREATE OR REPLACE EDITIONABLE PACKAGE BODY "DATAWAREHOUSE"."PKG_ETL_DW" AS

    PROCEDURE LOG_ETL(
        p_job    IN VARCHAR2,
        p_status IN VARCHAR2,
        p_rows   IN NUMBER   DEFAULT 0,
        p_note   IN VARCHAR2 DEFAULT NULL
    ) IS
        PRAGMA AUTONOMOUS_TRANSACTION;
    BEGIN
        INSERT INTO ETL_LOG (TenJob, ThoiGianKT, TrangThai, SoBanGhi, GhiChu)
        VALUES (p_job, SYSTIMESTAMP, p_status, p_rows, p_note);
        COMMIT;
    END LOG_ETL;

    -- ========================================================
    -- Helper: Lay thoi gian chay thanh cong cuoi cung cua 1 job
    -- Tra ve NULL neu chua bao gio chay → day la tin hieu FULL LOAD
    -- ========================================================
    FUNCTION GET_LAST_RUN(p_job IN VARCHAR2) RETURN TIMESTAMP IS
        v_ts TIMESTAMP;
    BEGIN
        SELECT MAX(ThoiGianKT) INTO v_ts
        FROM ETL_LOG
        WHERE TenJob = p_job AND TrangThai = 'THANH CONG';
        RETURN v_ts;
    END GET_LAST_RUN;

    -- ========================================================
    -- Helper: Chuyen DATE thanh MaThoiGian (YYYYMMDD)
    -- Chu y: Khong dung trong SQL statement, chi dung trong PL/SQL
    -- ========================================================
    FUNCTION TO_TIME_KEY(p_val IN DATE) RETURN NUMBER IS
    BEGIN
        IF p_val IS NULL THEN RETURN 20170101; END IF;
        RETURN TO_NUMBER(TO_CHAR(TRUNC(p_val), 'YYYYMMDD'));
    END TO_TIME_KEY;

    -- ========================================================
    -- Helper macro: Inline date->key conversion cho SQL statements
    -- Su dung: NVL(TO_NUMBER(TO_CHAR(date_col, 'YYYYMMDD')), 20170101)
    -- ========================================================

    -- ========================================================
    -- 1. LOAD_DIM_TIME (du lieu tinh, chi load 1 lan)
    -- 2015-01-01 → 2018-12-31 = 1,461 rows
    -- ========================================================
    PROCEDURE LOAD_DIM_TIME IS
        v_cnt  NUMBER;
        v_date DATE := TO_DATE('2015-01-01', 'YYYY-MM-DD');
        v_end  DATE := TO_DATE('2018-12-31', 'YYYY-MM-DD');
        v_rows NUMBER := 0;
    BEGIN
        SELECT COUNT(*) INTO v_cnt FROM DIM_TIME;
        IF v_cnt > 0 THEN
            LOG_ETL('LOAD_DIM_TIME', 'SKIP', v_cnt, 'Da co du lieu');
            RETURN;
        END IF;

        WHILE v_date <= v_end LOOP
            INSERT INTO DIM_TIME (MaThoiGian, Ngay, Thang, Quy, Nam, ThuTrongTuan)
            VALUES (
                TO_NUMBER(TO_CHAR(v_date, 'YYYYMMDD')),
                EXTRACT(DAY FROM v_date),
                EXTRACT(MONTH FROM v_date),
                TO_NUMBER(TO_CHAR(v_date, 'Q')), -- lấy quý (quarter)
                EXTRACT(YEAR FROM v_date),
                TRIM(TO_CHAR(v_date, 'Day', 'NLS_DATE_LANGUAGE=AMERICAN'))
            );
            v_date := v_date + 1;
            v_rows := v_rows + 1; 
        END LOOP; 
        COMMIT;
        LOG_ETL('LOAD_DIM_TIME', 'THANH CONG', v_rows);
    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK;
            LOG_ETL('LOAD_DIM_TIME', 'LOI', 0, SQLERRM);
            RAISE;
    END LOAD_DIM_TIME;

    -- ========================================================
    -- 2. LOAD_DIM_LOCATION
    --    Full:        INSERT 100 vat ly + 30 kho online = 130
    --    Incremental: chi INSERT cua hang/kho moi (ThoiGian > last_run)
    -- ========================================================
    PROCEDURE LOAD_DIM_LOCATION IS
        v_last_run TIMESTAMP;
        v_rows     NUMBER := 0;
    BEGIN
        v_last_run := GET_LAST_RUN('LOAD_DIM_LOCATION');

        IF v_last_run IS NULL THEN
            -- ===== FULL LOAD (lan dau) =====
            INSERT INTO DIM_LOCATION (
                MaCuaHang, TenCuaHang, SoDienThoai, LoaiCuaHang,
                MaThanhPho, TenThanhPho, DiaChiVP, Bang)
            SELECT ch."MaCuaHang", 'Cua hang ' || ch."MaCuaHang",
                   ch."SoDienThoai", 'Vat ly',
                   vp."MaThanhPho", vp."TenThanhPho", vp."DiaChiVP", vp."Bang"
            FROM "CuaHang"@sqlserver_banhang ch
            JOIN "VanPhongDaiDien"@sqlserver_banhang vp
                ON ch."MaThanhPho" = vp."MaThanhPho";
            v_rows := SQL%ROWCOUNT;

            INSERT INTO DIM_LOCATION (
                MaCuaHang, TenCuaHang, SoDienThoai, LoaiCuaHang,
                MaThanhPho, TenThanhPho, DiaChiVP, Bang)
            SELECT 'OL_' || vp."MaThanhPho", 'Kho truc tuyen ' || vp."TenThanhPho",
                   NULL, 'Truc tuyen',
                   vp."MaThanhPho", vp."TenThanhPho", vp."DiaChiVP", vp."Bang"
            FROM "VanPhongDaiDien"@sqlserver_banhang vp;
            v_rows := v_rows + SQL%ROWCOUNT;
        ELSE
            -- ===== INCREMENTAL (cac lan sau) =====
            -- Upsert cua hang vat ly moi/thay doi
            FOR r IN (
                SELECT ch."MaCuaHang" AS ma_ch, ch."SoDienThoai" AS sdt,
                       vp."MaThanhPho" AS ma_tp, vp."TenThanhPho" AS ten_tp,
                       vp."DiaChiVP" AS dc, vp."Bang" AS bang
                FROM "CuaHang"@sqlserver_banhang ch
                JOIN "VanPhongDaiDien"@sqlserver_banhang vp
                    ON ch."MaThanhPho" = vp."MaThanhPho"
                WHERE CAST(ch."ThoiGian" AS TIMESTAMP) > v_last_run
            ) LOOP
                UPDATE DIM_LOCATION SET
                    TenCuaHang  = 'Cua hang ' || r.ma_ch,
                    SoDienThoai = r.sdt,
                    MaThanhPho  = r.ma_tp,
                    TenThanhPho = r.ten_tp,
                    DiaChiVP    = r.dc,
                    Bang        = r.bang
                WHERE MaCuaHang = r.ma_ch;

                IF SQL%ROWCOUNT = 0 THEN
                    INSERT INTO DIM_LOCATION VALUES (
                        r.ma_ch, 'Cua hang ' || r.ma_ch, r.sdt, 'Vat ly',
                        r.ma_tp, r.ten_tp, r.dc, r.bang);
                END IF;
                v_rows := v_rows + 1;
            END LOOP;

            -- Upsert kho online (them moi hoac cap nhat dia chi VP)
            FOR r IN (
                SELECT vp."MaThanhPho" AS ma_tp, vp."TenThanhPho" AS ten_tp,
                       vp."DiaChiVP" AS dc, vp."Bang" AS bang
                FROM "VanPhongDaiDien"@sqlserver_banhang vp
                WHERE CAST(vp."ThoiGian" AS TIMESTAMP) > v_last_run
                   OR NOT EXISTS (
                       SELECT 1 FROM DIM_LOCATION dl
                       WHERE dl.MaCuaHang = 'OL_' || vp."MaThanhPho")
            ) LOOP
                UPDATE DIM_LOCATION SET
                    TenCuaHang  = 'Kho truc tuyen ' || r.ten_tp,
                    TenThanhPho = r.ten_tp,
                    DiaChiVP    = r.dc,
                    Bang        = r.bang
                WHERE MaCuaHang = 'OL_' || r.ma_tp;

                IF SQL%ROWCOUNT = 0 THEN
                    INSERT INTO DIM_LOCATION VALUES (
                        'OL_' || r.ma_tp, 'Kho truc tuyen ' || r.ten_tp,
                        NULL, 'Truc tuyen', r.ma_tp, r.ten_tp, r.dc, r.bang);
                END IF;
                v_rows := v_rows + 1;
            END LOOP;
        END IF;

        COMMIT;
        LOG_ETL('LOAD_DIM_LOCATION', 'THANH CONG', v_rows,
                CASE WHEN v_last_run IS NULL THEN 'FULL' ELSE 'INCR' END);
    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK;
            LOG_ETL('LOAD_DIM_LOCATION', 'LOI', 0, SQLERRM);
            RAISE;
    END LOAD_DIM_LOCATION;
    -- ========================================================
    -- 3. LOAD_DIM_PRODUCT
    --    Full:        INSERT tat ca ~20,506 san pham
    --    Incremental: UPSERT san pham moi/thay doi (ThoiGian > last_run)
    -- ========================================================
    PROCEDURE LOAD_DIM_PRODUCT IS
        v_last_run TIMESTAMP;
        v_rows     NUMBER := 0;
    BEGIN
        v_last_run := GET_LAST_RUN('LOAD_DIM_PRODUCT');

        IF v_last_run IS NULL THEN
            -- ===== FULL LOAD =====
            INSERT INTO DIM_PRODUCT (MaMH, MoTa, KichCo, TrongLuong, Gia)
            SELECT m."MaMH", m."MoTa", m."KichCo", m."TrongLuong", m."Gia"
            FROM "MatHang"@sqlserver_banhang m;
            v_rows := SQL%ROWCOUNT;
        ELSE
            -- ===== INCREMENTAL: upsert =====
            FOR r IN (
                SELECT m."MaMH" AS mh, m."MoTa" AS mt, m."KichCo" AS kc,
                       m."TrongLuong" AS tl, m."Gia" AS gia
                FROM "MatHang"@sqlserver_banhang m
                WHERE CAST(m."ThoiGian" AS TIMESTAMP) > v_last_run
            ) LOOP
                UPDATE DIM_PRODUCT SET
                    MoTa = r.mt, KichCo = r.kc,
                    TrongLuong = r.tl, Gia = r.gia
                WHERE MaMH = r.mh;

                IF SQL%ROWCOUNT = 0 THEN
                    INSERT INTO DIM_PRODUCT (MaMH, MoTa, KichCo, TrongLuong, Gia)
                    VALUES (r.mh, r.mt, r.kc, r.tl, r.gia);
                END IF;
                v_rows := v_rows + 1;
            END LOOP;
        END IF;

        COMMIT;
        LOG_ETL('LOAD_DIM_PRODUCT', 'THANH CONG', v_rows,
                CASE WHEN v_last_run IS NULL THEN 'FULL' ELSE 'INCR' END);
    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK;
            LOG_ETL('LOAD_DIM_PRODUCT', 'LOI', 0, SQLERRM);
            RAISE;
    END LOAD_DIM_PRODUCT;

    -- ========================================================
    -- 4. LOAD_DIM_CUSTOMER
    --    Full:        INSERT tat ca ~44,474 KH
    --    Incremental: UPSERT KH moi/thay doi (ThoiGian > last_run)
    --                 Bao gom: KhachHang moi, hoac KH_DuLich/KH_BuuDien
    --                 thay doi (VD: KH tu 'Du lich' → 'Ca hai')
    -- ========================================================
    PROCEDURE LOAD_DIM_CUSTOMER IS
        v_last_run TIMESTAMP;
        v_rows     NUMBER := 0;
    BEGIN
        v_last_run := GET_LAST_RUN('LOAD_DIM_CUSTOMER');

        IF v_last_run IS NULL THEN
            -- ===== FULL LOAD =====
            INSERT INTO DIM_CUSTOMER (
                MaKH, TenKH, NgayDatHangDauTien, LoaiKH,
                HuongDanVien, DiaChiBuuDien,
                MaThanhPho, TenThanhPho, Bang)
            SELECT k.MAKH, k.TENKH, k.NGAYDATHANGDAUTIEN,
                   CASE
                       WHEN dl.MAKH IS NOT NULL AND bd.MAKH IS NOT NULL THEN 'Ca hai'
                       WHEN dl.MAKH IS NOT NULL THEN 'Du lich'
                       WHEN bd.MAKH IS NOT NULL THEN 'Buu dien'
                       ELSE NULL
                   END,
                   dl.HUONGDANVIEN, bd.DIACHIBUUDIEN,
                   k.MATHANHPHO, vp."TenThanhPho", vp."Bang"
            FROM LEVANMINH.KHACHHANG k
            LEFT JOIN LEVANMINH.KH_DULICH dl ON k.MAKH = dl.MAKH
            LEFT JOIN LEVANMINH.KH_BUUDIEN bd ON k.MAKH = bd.MAKH
            LEFT JOIN "VanPhongDaiDien"@sqlserver_banhang vp
                ON k.MATHANHPHO = vp."MaThanhPho";
            v_rows := SQL%ROWCOUNT;
        ELSE
            -- ===== INCREMENTAL: upsert KH co thay doi =====
            -- Lay KH co bat ky thay doi nao (KhachHang/DuLich/BuuDien)
            FOR r IN (
                SELECT k.MAKH AS ma, k.TENKH AS ten,
                       k.NGAYDATHANGDAUTIEN AS ngay,
                       CASE
                           WHEN dl.MAKH IS NOT NULL AND bd.MAKH IS NOT NULL THEN 'Ca hai'
                           WHEN dl.MAKH IS NOT NULL THEN 'Du lich'
                           WHEN bd.MAKH IS NOT NULL THEN 'Buu dien'
                           ELSE NULL
                       END AS loai,
                       dl.HUONGDANVIEN AS hdv, bd.DIACHIBUUDIEN AS dcbd,
                       k.MATHANHPHO AS ma_tp,
                       vp."TenThanhPho" AS ten_tp, vp."Bang" AS bang
                FROM LEVANMINH.KHACHHANG k
                LEFT JOIN LEVANMINH.KH_DULICH dl ON k.MAKH = dl.MAKH
                LEFT JOIN LEVANMINH.KH_BUUDIEN bd ON k.MAKH = bd.MAKH
                LEFT JOIN "VanPhongDaiDien"@sqlserver_banhang vp
                    ON k.MATHANHPHO = vp."MaThanhPho"
                WHERE k.THOIGIAN > v_last_run
                   OR (dl.MAKH IS NOT NULL AND dl.THOIGIAN > v_last_run)
                   OR (bd.MAKH IS NOT NULL AND bd.THOIGIAN > v_last_run)
            ) LOOP
                UPDATE DIM_CUSTOMER SET
                    TenKH = r.ten, NgayDatHangDauTien = r.ngay,
                    LoaiKH = r.loai, HuongDanVien = r.hdv,
                    DiaChiBuuDien = r.dcbd, MaThanhPho = r.ma_tp,
                    TenThanhPho = r.ten_tp, Bang = r.bang
                WHERE MaKH = r.ma;

                IF SQL%ROWCOUNT = 0 THEN
                    INSERT INTO DIM_CUSTOMER (
                        MaKH, TenKH, NgayDatHangDauTien, LoaiKH,
                        HuongDanVien, DiaChiBuuDien,
                        MaThanhPho, TenThanhPho, Bang)
                    VALUES (r.ma, r.ten, r.ngay, r.loai,
                            r.hdv, r.dcbd, r.ma_tp, r.ten_tp, r.bang);
                END IF;
                v_rows := v_rows + 1;
            END LOOP;
        END IF;

        COMMIT;
        LOG_ETL('LOAD_DIM_CUSTOMER', 'THANH CONG', v_rows,
                CASE WHEN v_last_run IS NULL THEN 'FULL' ELSE 'INCR' END);
    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK;
            LOG_ETL('LOAD_DIM_CUSTOMER', 'LOI', 0, SQLERRM);
            RAISE;
    END LOAD_DIM_CUSTOMER;

    -- ========================================================
    -- 5. LOAD_FACT_INVENTORY
    --    Full:        INSERT tat ca 51K + online aggregate
    --    Incremental: INSERT ton kho moi (ThoiGian > last_run)
    --                 + cap nhat ton kho online cho SP bi anh huong
    -- ========================================================
    PROCEDURE LOAD_FACT_INVENTORY IS
        v_last_run   TIMESTAMP;
        v_rows_phys  NUMBER := 0;
        v_rows_ol    NUMBER := 0;
    BEGIN
        v_last_run := GET_LAST_RUN('LOAD_FACT_INVENTORY');

        IF v_last_run IS NULL THEN
            -- ===== FULL LOAD =====
            -- Ton kho vat ly
            INSERT INTO FACT_INVENTORY (MaCuaHang, MaMH, MaThoiGian, SoLuongTon)
            SELECT lt."MaCuaHang", lt."MaMH",
                   NVL(TO_NUMBER(TO_CHAR(CAST(lt."ThoiGian" AS DATE), 'YYYYMMDD')), 20170101),
                   lt."SoLuongKho"
            FROM "MatHang_LuuTru"@sqlserver_banhang lt;
            v_rows_phys := SQL%ROWCOUNT;

            -- Ton kho online = SUM vat ly cung TP
            INSERT INTO FACT_INVENTORY (MaCuaHang, MaMH, MaThoiGian, SoLuongTon)
            SELECT 'OL_' || ch."MaThanhPho", lt."MaMH",
                   NVL(TO_NUMBER(TO_CHAR(MIN(CAST(lt."ThoiGian" AS DATE)), 'YYYYMMDD')), 20170101),
                   SUM(lt."SoLuongKho")
            FROM "MatHang_LuuTru"@sqlserver_banhang lt
            JOIN "CuaHang"@sqlserver_banhang ch
                ON lt."MaCuaHang" = ch."MaCuaHang"
            GROUP BY 'OL_' || ch."MaThanhPho", lt."MaMH";
            v_rows_ol := SQL%ROWCOUNT;
        ELSE
            -- ===== INCREMENTAL =====
            -- Them ton kho vat ly moi (snapshot moi, ngay moi)
            FOR r IN (
                SELECT lt."MaCuaHang" AS ch, lt."MaMH" AS mh,
                       NVL(TO_NUMBER(TO_CHAR(CAST(lt."ThoiGian" AS DATE), 'YYYYMMDD')), 20170101) AS tk,
                       lt."SoLuongKho" AS qty
                FROM "MatHang_LuuTru"@sqlserver_banhang lt
                WHERE CAST(lt."ThoiGian" AS TIMESTAMP) > v_last_run
            ) LOOP
                -- Upsert: update neu PK da ton tai, insert neu moi
                UPDATE FACT_INVENTORY SET SoLuongTon = r.qty
                WHERE MaCuaHang = r.ch AND MaMH = r.mh AND MaThoiGian = r.tk;

                IF SQL%ROWCOUNT = 0 THEN
                    INSERT INTO FACT_INVENTORY (MaCuaHang, MaMH, MaThoiGian, SoLuongTon)
                    VALUES (r.ch, r.mh, r.tk, r.qty);
                END IF;
                v_rows_phys := v_rows_phys + 1;
            END LOOP;

            -- Cap nhat ton kho online cho san pham bi thay doi
--            Nếu có thay đổi tồn kho vật lý thì mới cần update online
            -- Xoa ton kho online cu cua SP bi anh huong, tinh lai 
            IF v_rows_phys > 0 THEN
                -- Lay danh sach SP thay doi
                FOR r_mh IN (
                    SELECT DISTINCT lt."MaMH" AS mh
                    FROM "MatHang_LuuTru"@sqlserver_banhang lt
                    WHERE CAST(lt."ThoiGian" AS TIMESTAMP) > v_last_run
                ) LOOP
                    -- Xoa ton kho online cu cho SP nay
                    DELETE FROM FACT_INVENTORY
                    WHERE MaCuaHang LIKE 'OL_%' AND MaMH = r_mh.mh;

                    -- Tinh lai aggregate
                    INSERT INTO FACT_INVENTORY (MaCuaHang, MaMH, MaThoiGian, SoLuongTon)
                    SELECT 'OL_' || ch."MaThanhPho", lt."MaMH",
                           NVL(TO_NUMBER(TO_CHAR(MIN(CAST(lt."ThoiGian" AS DATE)), 'YYYYMMDD')), 20170101),
                           SUM(lt."SoLuongKho")
                    FROM "MatHang_LuuTru"@sqlserver_banhang lt
                    JOIN "CuaHang"@sqlserver_banhang ch
                        ON lt."MaCuaHang" = ch."MaCuaHang"
                    WHERE lt."MaMH" = r_mh.mh
                    GROUP BY 'OL_' || ch."MaThanhPho", lt."MaMH";
                    v_rows_ol := v_rows_ol + SQL%ROWCOUNT;
                END LOOP;
            END IF;
        END IF;

        COMMIT;
        LOG_ETL('LOAD_FACT_INVENTORY', 'THANH CONG',
                v_rows_phys + v_rows_ol,
                CASE WHEN v_last_run IS NULL THEN 'FULL' ELSE 'INCR' END
                || ' | Phys=' || v_rows_phys || ' OL=' || v_rows_ol);
    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK;
            LOG_ETL('LOAD_FACT_INVENTORY', 'LOI', 0, SQLERRM);
            RAISE;
    END LOAD_FACT_INVENTORY;

    -- ========================================================
    -- 6. LOAD_FACT_ORDER
    --    Full:        Xu ly tat ca ~47,825 order items
    --    Incremental: Chi xu ly don hang MOI (ThoiGian > last_run)
    --
    --    Business logic (giong nhau cho ca 2 mode):
    --      KH 'Du lich'  → 'Tai cua hang' → cua hang vat ly
    --      KH 'Buu dien' → 'Truc tuyen'   → kho online
    --      KH 'Ca hai'   → 50/50 (MaDon chan/le)
    --      KH NULL       → default offline
    -- ========================================================
    PROCEDURE LOAD_FACT_ORDER IS
        -- kiểu dữ liệu RECORD, giống struct/object
        TYPE t_cust_rec IS RECORD (
            loai_kh VARCHAR2(20),
            ma_tp   VARCHAR2(10)
        );
        TYPE t_cust_map   IS TABLE OF t_cust_rec INDEX BY VARCHAR2(10);   -- Map<String, t_cust_rec>
        TYPE t_store_map  IS TABLE OF VARCHAR2(10) INDEX BY VARCHAR2(25); -- Map<String, String>

        -- BULK COLLECT types (tranh ORA-01002: "fetch out of sequence" khi COMMIT qua DB Link)
        TYPE t_arr_vc10 IS TABLE OF VARCHAR2(10) INDEX BY PLS_INTEGER;  -- Array<String>  t_arr_vc10(1) := 'A'; t_arr_vc10(2) := 'B';
        TYPE t_arr_date IS TABLE OF DATE          INDEX BY PLS_INTEGER; -- Array<Date>
        TYPE t_arr_num  IS TABLE OF NUMBER        INDEX BY PLS_INTEGER; -- Array<Integer>

        a_ma_don   t_arr_vc10; -- danh sách Mã Đơn Hàng
        a_ma_kh    t_arr_vc10; -- danh sách mã khác hàng
        a_ngay_dat t_arr_date; -- mảng chứa ngày đặt hàng
        a_ma_mh    t_arr_vc10; -- mảng danh sách mặt hàng
        a_so_luong t_arr_num;  -- mảng số lượng đặt của từng mặt hàng
        a_gia_dat  t_arr_num;  -- mảng giá trị đặt cảu từng mặt hàng

        v_last_run        TIMESTAMP;  
        v_customers       t_cust_map;  -- thông tin toàn bộ khách hàng
        v_city_prod_store t_store_map; -- check xem mặt hàng A ở thành phố B thì nên lấy từ cửa hàng vật lý nào, key: MaTP|MaMH
        v_any_store       t_store_map; -- key: MaMH, value: MaCH

        v_kenh     VARCHAR2(20);
        v_store    VARCHAR2(10);
        v_key      VARCHAR2(25);
        v_rows     NUMBER := 0;
        v_skip     NUMBER := 0;
        v_time_key NUMBER;

        TYPE t_ref_cur IS REF CURSOR;
        c_items t_ref_cur;

    BEGIN
        v_last_run := GET_LAST_RUN('LOAD_FACT_ORDER');

        -- ---- PRE-LOAD LOOKUP MAPS (luon luon can, ca full va incremental) ----

        -- Map 1: Customer info (tu DIM_CUSTOMER da load)
        FOR r IN (SELECT MaKH, LoaiKH, MaThanhPho FROM DIM_CUSTOMER) LOOP
            v_customers(r.MaKH).loai_kh := r.LoaiKH;
            v_customers(r.MaKH).ma_tp   := r.MaThanhPho;
        END LOOP;

        -- Map 2: (ThanhPho, MatHang) => CuaHang vat ly
        -- Khách ở đâu, tìm cửa hàng ở thành phố đó. nếu không có thì sang Map 3, lấy hàng ở thành phố khác
        FOR r IN (
            SELECT ch."MaThanhPho" || '|' || lt."MaMH" AS map_key,
                   MIN(lt."MaCuaHang") AS best_store
            FROM "MatHang_LuuTru"@sqlserver_banhang lt
            JOIN "CuaHang"@sqlserver_banhang ch
                ON lt."MaCuaHang" = ch."MaCuaHang"
            GROUP BY ch."MaThanhPho" || '|' || lt."MaMH"
        ) LOOP
            v_city_prod_store(r.map_key) := r.best_store;
        END LOOP;

        -- Map 3: Fallback — bat ky store nao co san pham
        FOR r IN (
            SELECT "MaMH" AS mh, MIN("MaCuaHang") AS store_id
            FROM "MatHang_LuuTru"@sqlserver_banhang
            GROUP BY "MaMH"
        ) LOOP
            v_any_store(r.mh) := r.store_id;
        END LOOP;

        -- ---- BULK COLLECT: Lay toan bo data vao bo nho truoc ----
        -- (Tranh ORA-01002: COMMIT trong vong FETCH qua DB Link se dong cursor)
        -- c_items quản lý bởi Oracle, nhưng mỗi lần FETCH nó vẫn phải giữ kết nối sang SQL Server để lấy thêm data. Vì vậy COMMIT làm đứt kết nối đó.
        IF v_last_run IS NULL THEN
            OPEN c_items FOR
                SELECT d."MaDon", d."MaKH", CAST(d."NgayDatHang" AS DATE),
                       md."MaMH", md."SoLuongDat", md."GiaDat"
                FROM "DonDatHang"@sqlserver_banhang d
                JOIN "MatHang_DuocDat"@sqlserver_banhang md
                    ON d."MaDon" = md."MaDon";
        ELSE
            OPEN c_items FOR
                SELECT d."MaDon", d."MaKH", CAST(d."NgayDatHang" AS DATE),
                       md."MaMH", md."SoLuongDat", md."GiaDat"
                FROM "DonDatHang"@sqlserver_banhang d
                JOIN "MatHang_DuocDat"@sqlserver_banhang md
                    ON d."MaDon" = md."MaDon"
                WHERE CAST(d."ThoiGian" AS TIMESTAMP) > v_last_run;
        END IF;

        FETCH c_items BULK COLLECT INTO
            a_ma_don, a_ma_kh, a_ngay_dat, a_ma_mh, a_so_luong, a_gia_dat;
        CLOSE c_items;
        -- toàn bộ các dòng đã nằm trong RAM của Oracle server. Mọi xử lý tiếp theo chỉ đọc từ mảng, không còn phụ thuộc DB Link nữa 
        -- Cursor da dong → co the COMMIT thoai mai ben duoi

        -- ---- PROCESS ORDER ITEMS (tu bo nho, khong con phu thuoc DB Link) ----
        FOR i IN 1..a_ma_don.COUNT LOOP

--          nếu không tìm thấy khách trong DIM => bỏ luôn, tránh mồ côi
            IF NOT v_customers.EXISTS(a_ma_kh(i)) THEN 
                v_skip := v_skip + 1;
                CONTINUE;
            END IF;

            -- Xac dinh kenh ban hang -- v_customers(a_ma_kh(i)).loai_kh
            CASE v_customers(a_ma_kh(i)).loai_kh
                WHEN 'Buu dien' THEN
                    v_kenh := 'Truc tuyen';
                WHEN 'Ca hai' THEN    -- số lẻ: online  số chẵn: tại cửa hàng
                    IF MOD(TO_NUMBER(a_ma_don(i)), 2) = 1 THEN
                        v_kenh := 'Truc tuyen';
                    ELSE
                        v_kenh := 'Tai cua hang';
                    END IF;
                ELSE
                    v_kenh := 'Tai cua hang';
            END CASE;

            -- Gan cua hang
            IF v_kenh = 'Truc tuyen' THEN
                v_store := 'OL_' || v_customers(a_ma_kh(i)).ma_tp;
            ELSE
                v_key := v_customers(a_ma_kh(i)).ma_tp || '|' || a_ma_mh(i);
                IF v_city_prod_store.EXISTS(v_key) THEN
                    v_store := v_city_prod_store(v_key);
                ELSIF v_any_store.EXISTS(a_ma_mh(i)) THEN
                    v_store := v_any_store(a_ma_mh(i));
                ELSE
                    v_store := 'OL_' || v_customers(a_ma_kh(i)).ma_tp;
                END IF;
            END IF;

            -- Tinh MaThoiGian truoc
            v_time_key := TO_TIME_KEY(a_ngay_dat(i));

            -- Upsert: UPDATE neu PK (MaDon, MaMH) da ton tai, INSERT neu moi
            UPDATE FACT_ORDER SET
                MaKH        = a_ma_kh(i),
                MaCuaHang   = v_store,
                MaThoiGian  = v_time_key,
                KenhBanHang = v_kenh,
                SoLuongDat  = a_so_luong(i),
                GiaDat      = a_gia_dat(i),
                TongTien    = a_so_luong(i) * a_gia_dat(i)
            WHERE MaDon = a_ma_don(i) AND MaMH = a_ma_mh(i);

            IF SQL%ROWCOUNT = 0 THEN
                INSERT INTO FACT_ORDER (
                    MaDon, MaKH, MaMH, MaCuaHang, MaThoiGian,
                    KenhBanHang, SoLuongDat, GiaDat, TongTien
                ) VALUES (
                    a_ma_don(i), a_ma_kh(i), a_ma_mh(i), v_store,
                    v_time_key,
                    v_kenh, a_so_luong(i), a_gia_dat(i),
                    a_so_luong(i) * a_gia_dat(i)
                );
            END IF;

            v_rows := v_rows + 1;
            IF MOD(v_rows, 5000) = 0 THEN --Oracle ghi mọi thay đổi chưa COMMIT vào Undo Segment để có thể ROLLBACK. 
                COMMIT;
            END IF;
        END LOOP;

        COMMIT;
        LOG_ETL('LOAD_FACT_ORDER', 'THANH CONG', v_rows,
                CASE WHEN v_last_run IS NULL THEN 'FULL' ELSE 'INCR' END
                || ' | Skip=' || v_skip);
    EXCEPTION
        WHEN OTHERS THEN
            IF c_items%ISOPEN THEN CLOSE c_items; END IF;
            ROLLBACK;
            LOG_ETL('LOAD_FACT_ORDER', 'LOI', v_rows, SQLERRM);
            RAISE;
    END LOAD_FACT_ORDER;
    
    -- ========================================================
    -- RUN_ALL: Orchestrator
    --   Lan dau: DW trong → tu dong FULL LOAD
    --   Cac lan sau (job): tu dong INCREMENTAL
    --   KHONG DELETE du lieu cu — moi procedure tu quyet dinh
    -- ========================================================
    PROCEDURE RUN_ALL IS
        v_start   TIMESTAMP := SYSTIMESTAMP;
        v_elapsed VARCHAR2(50);
    BEGIN
        LOG_ETL('RUN_ALL', 'BAT DAU');

        -- Dat NLS cho session (tranh loi date format qua DB link)
        EXECUTE IMMEDIATE 'ALTER SESSION SET NLS_DATE_FORMAT = ''YYYY-MM-DD''';

        -- Load theo thu tu FK (moi proc tu biet full hay incremental)
        LOAD_DIM_TIME;
        LOAD_DIM_LOCATION;
        LOAD_DIM_PRODUCT;
        LOAD_DIM_CUSTOMER;
        LOAD_FACT_INVENTORY;
        LOAD_FACT_ORDER;

        v_elapsed := EXTRACT(MINUTE FROM (SYSTIMESTAMP - v_start))
                     || 'm '
                     || ROUND(EXTRACT(SECOND FROM (SYSTIMESTAMP - v_start)))
                     || 's';
        LOG_ETL('RUN_ALL', 'THANH CONG', NULL,
                'Tong thoi gian: ' || v_elapsed);

        -- In ket qua kiem tra
        DBMS_OUTPUT.PUT_LINE('=== ETL HOAN TAT (' || v_elapsed || ') ===');
        FOR r IN (
            SELECT 'DIM_TIME'        AS t, COUNT(*) AS c FROM DIM_TIME        UNION ALL
            SELECT 'DIM_LOCATION',          COUNT(*)      FROM DIM_LOCATION    UNION ALL
            SELECT 'DIM_PRODUCT',           COUNT(*)      FROM DIM_PRODUCT     UNION ALL
            SELECT 'DIM_CUSTOMER',          COUNT(*)      FROM DIM_CUSTOMER    UNION ALL
            SELECT 'FACT_INVENTORY',        COUNT(*)      FROM FACT_INVENTORY  UNION ALL
            SELECT 'FACT_ORDER',            COUNT(*)      FROM FACT_ORDER
        ) LOOP
            DBMS_OUTPUT.PUT_LINE('  ' || RPAD(r.t, 20) || r.c || ' rows');
        END LOOP;
    EXCEPTION
        WHEN OTHERS THEN
            LOG_ETL('RUN_ALL', 'LOI', NULL, SQLERRM);
            RAISE;
    END RUN_ALL;

END PKG_ETL_DW; 



---- ============================================================
---- KIEM TRA COMPILE
---- ============================================================
--      SELECT object_name, object_type, status
--      FROM user_objects
--      WHERE object_name = 'PKG_ETL_DW';
--
---- Xem loi compile (neu co)
--      SELECT line, position, text
--      FROM user_errors
--      WHERE name = 'PKG_ETL_DW'
--      ORDER BY sequence;










--  Chay tung procedure rieng le
--  de bug loi, biet chinh xac buoc nao gap van de

/
