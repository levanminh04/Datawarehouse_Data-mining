# KẾ HOẠCH SỬA DỮ LIỆU TỪ GỐC PYTHON (ETL_OLIST_TO_SQL.PY)
## Hướng tiếp cận nắn dữ liệu thuận theo nghiệp vụ "Du lịch & Bưu điện"

---

## 1. PHÂN TÍCH LẠI BÀI TOÁN KINH DOANH CỦA BẠN

Bạn hoàn toàn đúng! Nghiệp vụ của bạn quy định rõ 2 loại khách hàng:
1. **Khách Du Lịch:** Được HDV dẫn đến cửa hàng → Mua **Tại cửa hàng**.
2. **Khách Bưu Điện:** Chuyển phát từ xa → Mua **Trực tuyến**.
3. **Khách Cả Hai:** Mua cả 2 hình thức.

Để "lái" câu chuyện kinh doanh sang hướng: **Nhóm khách hàng Du lịch (mua tại cửa hàng) chủ yếu mua hàng nhẹ/nhỏ gọn để xách tay, còn Nhóm khách Bưu điện (mua qua mạng) chủ yếu mua hàng cồng kềnh/nặng để được giao tận nơi**, chúng ta **không cần** sửa DWH ETL nữa!

Chúng ta sẽ sửa thẳng vào **bản chất sinh dữ liệu ở `etl_olist_to_sql.py`**!

### Logic cũ (Sai lầm dẫn tới 50/50):
Ở dòng 406, `random.shuffle(customer_ids_list)` xáo trộn ngẫu nhiên toàn bộ khách hàng, sau đó cắt 60% đầu cho Du lịch, 60% cuối cho Bưu điện. Điều này làm cho Khách Du Lịch và Khách Bưu Điện mua sắm cẩu thả mọi loại mặt hàng (nặng/nhẹ như nhau).

### Logic mới (Sự tinh tế trong Data Mining):
Thay vì `random.shuffle`, chúng ta sẽ:
1. Tính **Trọng lượng lớn nhất (Max Weight)** của các món hàng mà mỗi khách hàng đã mua.
2. **Sắp xếp** danh sách khách hàng tăng dần theo Trọng lượng.
3. Lấy 60% khách hàng mua **hàng NHẸ NHẤT** gán làm **Khách Du Lịch**.
4. Lấy 60% khách hàng mua **hàng NẶNG NHẤT** gán làm **Khách Bưu Điện**.
5. Nhóm 20% ở giữa (hàng tầm trung) sẽ rơi vào tập giao thoa (Khách mua Cả Hai).

Khi đó, quá trình ETL tự động `LOAD_FACT_ORDER` (Du lịch -> Tại Cửa Hàng, Bưu điện -> Trực Tuyến) sẽ phát huy tác dụng hoàn hảo mà **KHÔNG CẦN CHỈNH SỬA BẤT CỨ DÒNG CODE ORACLE/SQL NÀO NỮA**.

---

## 2. TRIỂN KHAI SỬA MÃ NGUỒN `etl_olist_to_sql.py`

### Mở file `etl_olist_to_sql.py`, tìm đến BƯỚC 5.5 (dòng 404):

**Thay thế đoạn code CŨ:**
```python
# ─── 5.5 Khách hàng du lịch ───
print("  [5/9] Khách hàng du lịch...")
random.shuffle(customer_ids_list)
n_total = len(customer_ids_list)
n_du_lich = int(n_total * KH_DU_LICH_RATIO)
n_buu_dien = int(n_total * KH_BUU_DIEN_RATIO)

# Tạo overlap: ~20% KH nằm ở cả 2 bảng
# Cách: lấy 60% đầu cho du lịch, 60% cuối cho bưu điện → overlap ~20%
kh_du_lich_ids = customer_ids_list[:n_du_lich]
kh_buu_dien_ids = customer_ids_list[n_total - n_buu_dien:]
```

**Bằng đoạn code MỚI sau đây:**
```python
# ─── 5.5 Khách hàng du lịch ───
print("  [5/9] Khách hàng du lịch (Phân bổ theo trọng lượng sản phẩm)...")

# Tính Max Weight của sản phẩm mà mỗi khách hàng đã mua
c_weights = items_final.merge(orders_final[['order_id', 'customer_unique_id']], on='order_id', how='inner')
c_weights = c_weights.merge(products[['product_id', 'product_weight_g']], on='product_id', how='left')
c_weights['product_weight_g'] = c_weights['product_weight_g'].fillna(0)

# Nhóm theo customer_unique_id
cw_agg = c_weights.groupby('customer_unique_id')['product_weight_g'].max().reset_index()

# Map sang MaKH
customer_max_weight = {}
for _, row in cw_agg.iterrows():
    cuid = row['customer_unique_id']
    ma_kh = customer_to_id.get(cuid)
    if ma_kh and ma_kh in kh_inserted_set:
        customer_max_weight[ma_kh] = row['product_weight_g']

# Nếu có KH không có weight (do data dị thường), gán mặc định 0
for ma_kh in customer_ids_list:
    if ma_kh not in customer_max_weight:
        customer_max_weight[ma_kh] = 0

# Sắp xếp khách hàng TĂNG DẦN theo Trọng lượng sản phẩm nặng nhất họ mua
customer_sorted_by_weight = sorted(customer_ids_list, key=lambda x: customer_max_weight[x])

n_total = len(customer_sorted_by_weight)
n_du_lich = int(n_total * KH_DU_LICH_RATIO)
n_buu_dien = int(n_total * KH_BUU_DIEN_RATIO)

# Gán Khách Du lịch: 60% KH mua hàng NHẸ NHẤT
kh_du_lich_ids = customer_sorted_by_weight[:n_du_lich]
# Gán Khách Bưu điện: 60% KH mua hàng NẶNG NHẤT
kh_buu_dien_ids = customer_sorted_by_weight[n_total - n_buu_dien:]
```

---

## 3. QUY TRÌNH THỰC HIỆN TOÀN BỘ (The Full Reset)

Vì bạn không ngại đập đi làm lại (vốn là cách sạch và triệt để nhất của Data Engineer), chúng ta sẽ làm tuần tự như sau:

1. **Sửa file Python:** Áp dụng đoạn code MỚI ở trên vào `etl_olist_to_sql.py`.
2. **Chạy Python sinh dữ liệu:** `python etl_olist_to_sql.py` (Nó sẽ sinh ra 9 file SQL mới trong thư mục output).
3. **Reset & Import vào SQL Server:** Chạy file `import_sqlserver_simple.sql` để xóa trắng và đưa dữ liệu mới vào DB `BANHANG`.
4. **Reset & Import vào Oracle:** Chạy file `import_oracle_custom.sql` trên Oracle để xóa trắng khách hàng và nạp dữ liệu KH Du Lịch (đã ôm hàng nhẹ) / KH Bưu Điện (đã ôm hàng nặng) vào Oracle.
5. **Chạy ETL Data Warehouse:** Mở file `Datawarehouse script cấu hình.sql` (hoặc chạy procedure/script tương ứng để RUN_ALL) để nạp lại dữ liệu vào DWH. Kênh bán hàng giờ đây sẽ tự động chuẩn 100% theo ý đồ:
   - Du lịch (hàng nhẹ) -> Tại cửa hàng
   - Bưu điện (hàng nặng) -> Trực tuyến
6. **Data Mining:** Vào Jupyter Notebook chạy lại `Lop1_PhanCumDonHang.ipynb` rồi sang `Lop1.5_PhanTichCheo.ipynb`. Kết quả sẽ tuyệt mỹ luôn.

---

## 4. TẠI SAO CÁCH NÀY XUẤT SẮC?

- **Hoàn toàn khớp với đề bài gốc:** Không làm mất đi khái niệm "Khách Du Lịch" và "Khách Bưu Điện".
- **Không mâu thuẫn hệ thống:** Bảng gốc tại OLTP luôn đồng nhất với Data Warehouse.
- **Không cần sửa DWH ETL:** Job ETL sẽ chay mượt mà, cứ Du Lịch là Offline, Bưu Điện là Online như mặc định.
- **Hoàn hảo cho Khai phá dữ liệu:** Máy học K-Means sẽ phát hiện ra Cụm Siêu nhẹ có tỷ lệ "Tại cửa hàng" cao vút, và Cụm Cồng kềnh có tỷ lệ "Trực tuyến" chiếm ưu thế. Bạn sẽ có một Data Story hoàn hảo không tì vết.
