# Ghi chú: Lỗi ORA-01002 fetch out of sequence

## Ngày gặp lỗi
2026-04-02

## Mô tả lỗi
```
ORA-01002: fetch out of sequence
ORA-06512: at "DATAWAREHOUSE.PKG_ETL_DW", line 551
ORA-02063: preceding line from SQLSERVER_BANHANG
```

## Nguyên nhân gốc
Trong procedure `LOAD_FACT_ORDER`, dùng **REF CURSOR qua DB Link** (`sqlserver_banhang`) 
để FETCH từng row trong vòng lặp, đồng thời **COMMIT mỗi 5000 rows**.

**Vấn đề**: Khi COMMIT xảy ra giữa vòng FETCH qua DB Link, Oracle sẽ **đóng cursor remote**.
Lần FETCH tiếp theo không còn cursor hợp lệ → `ORA-01002`.

### Code gây lỗi (trước khi fix)
```sql
OPEN c_items FOR
    SELECT ... FROM "DonDatHang"@sqlserver_banhang d ...;

LOOP
    FETCH c_items INTO v_ma_don, v_ma_kh, ...;
    EXIT WHEN c_items%NOTFOUND;
    
    INSERT INTO FACT_ORDER (...) VALUES (...);
    
    IF MOD(v_rows, 5000) = 0 THEN
        COMMIT;  -- ← SAI: dong cursor remote, lan FETCH sau se loi
    END IF;
END LOOP;
```

## Cách fix
Dùng **BULK COLLECT** để lấy toàn bộ data vào PL/SQL arrays trước, 
đóng cursor ngay, rồi xử lý từ bộ nhớ:

```sql
-- Khai bao arrays
TYPE t_arr_vc10 IS TABLE OF VARCHAR2(10) INDEX BY PLS_INTEGER;
a_ma_don   t_arr_vc10;
...

-- Lay toan bo 1 lan
OPEN c_items FOR SELECT ... FROM ...@sqlserver_banhang ...;
FETCH c_items BULK COLLECT INTO a_ma_don, a_ma_kh, ...;
CLOSE c_items;  -- Cursor dong ngay → DB Link giai phong

-- Xu ly tu bo nho → COMMIT thoai mai
FOR i IN 1..a_ma_don.COUNT LOOP
    INSERT INTO FACT_ORDER (...) VALUES (a_ma_don(i), ...);
    IF MOD(i, 5000) = 0 THEN
        COMMIT;  -- OK vi cursor da dong roi
    END IF;
END LOOP;
```

## Quy tắc rút ra
1. **KHÔNG BAO GIỜ** COMMIT bên trong vòng FETCH cursor qua DB Link
2. Nếu cần COMMIT giữa chừng → dùng BULK COLLECT trước, đóng cursor, rồi xử lý
3. Quy tắc này chỉ áp dụng cho **cursor qua DB Link** (remote cursor).
   Cursor local (trên cùng DB) vẫn COMMIT được (nhưng không khuyến khích)

## Hậu quả khi lỗi
- 5000 rows đầu tiên đã COMMIT thành công vào FACT_ORDER
- Từ row 5001 trở đi bị lỗi, không INSERT được
- **Phải TRUNCATE TABLE FACT_ORDER trước khi chạy lại** (tránh DUP_VAL_ON_INDEX)

## Áp dụng tương tự
- `LOAD_FACT_INVENTORY`: cũng dùng cursor qua DB Link nhưng KHÔNG có COMMIT 
  giữa vòng lặp (dùng implicit cursor FOR r IN (...) nên an toàn)
- Các procedure khác (DIM_LOCATION, DIM_PRODUCT): dùng implicit cursor loop 
  nên không bị ảnh hưởng
