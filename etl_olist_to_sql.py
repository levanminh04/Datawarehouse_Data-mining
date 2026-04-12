"""
ETL Script: Olist Dataset → SQL INSERT cho Kho dữ liệu đề bài
================================================================
Chuyển đổi Brazilian E-Commerce Public Dataset by Olist thành 9 bảng
theo đúng lược đồ đề bài, xuất ra file .sql (INSERT statements).

Mô hình kinh doanh: Doanh nghiệp bán lẻ truyền thống sở hữu nhiều
cửa hàng tại nhiều thành phố. KHÔNG phải marketplace.

Quy mô mục tiêu:
  - ~30 thành phố (Văn phòng đại diện)
  - ~100 cửa hàng (phân bổ across 30 TP)
  - ALL mặt hàng từ orders đã lọc (~15,000+)
  - ~20,000+ khách hàng
  - ~60,000+ đơn đặt hàng

Lưu ý quan trọng:
  - customer_id (per-order) != customer_unique_id (per-person)
  - JOIN qua customer_id để lấy customer_unique_id trước khi map
  - Olist sellers được bỏ qua — cửa hàng được sinh tự động
  - Mỗi cửa hàng stock 15-25% tổng mặt hàng, đảm bảo 100% coverage
"""

import os
import sys
import random
from collections import Counter
from datetime import date
import pandas as pd
from faker import Faker

# ============================================================
# CẤU HÌNH
# ============================================================
SEED = 42
random.seed(SEED)

fake = Faker('pt_BR')
Faker.seed(SEED)

# Đường dẫn
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Ngưỡng lọc
TOP_CITIES = 30
TOP_STORES = 100
KH_DU_LICH_RATIO = 0.60
KH_BUU_DIEN_RATIO = 0.60

# ============================================================
# LOAD DỮ LIỆU OLIST
# ============================================================
print("=" * 60)
print("BƯỚC 1: Load dữ liệu Olist")
print("=" * 60)

customers = pd.read_csv(os.path.join(DATA_DIR, 'olist_customers_dataset.csv'))
orders = pd.read_csv(os.path.join(DATA_DIR, 'olist_orders_dataset.csv'))
order_items = pd.read_csv(os.path.join(DATA_DIR, 'olist_order_items_dataset.csv'))
products = pd.read_csv(os.path.join(DATA_DIR, 'olist_products_dataset.csv'))
sellers = pd.read_csv(os.path.join(DATA_DIR, 'olist_sellers_dataset.csv'))
translation = pd.read_csv(os.path.join(DATA_DIR, 'product_category_name_translation.csv'))

print(f"  customers:   {len(customers):>10,} rows")
print(f"  orders:      {len(orders):>10,} rows")
print(f"  order_items: {len(order_items):>10,} rows")
print(f"  products:    {len(products):>10,} rows")
print(f"  sellers:     {len(sellers):>10,} rows")
print(f"  translation: {len(translation):>10,} rows")

# ============================================================
# BƯỚC 2: JOIN orders + customers để lấy customer_unique_id
# ============================================================
print("\n" + "=" * 60)
print("BƯỚC 2: JOIN orders ↔ customers (customer_id → customer_unique_id)")
print("=" * 60)

# QUAN TRỌNG: orders chứa customer_id (per-order),
# customers chứa customer_id + customer_unique_id (per-person).
# 1 người có thể có nhiều customer_id nhưng chỉ 1 customer_unique_id.
orders = orders.merge(
    customers[['customer_id', 'customer_unique_id', 'customer_city', 'customer_state', 'customer_zip_code_prefix']],
    on='customer_id',
    how='inner'
)
print(f"  orders sau JOIN: {len(orders):,} rows")

# ============================================================
# BƯỚC 3: PIPELINE LỌC — thu nhỏ quy mô thực tế
# ============================================================
# CHIẾN LƯỢC (retail model — 1 doanh nghiệp sở hữu tất cả cửa hàng):
#   1. Chọn top 30 cities (by order count)
#   2. Lọc orders từ customers thuộc 30 TP
#   3. Lấy ALL items + ALL products cho những orders đó
#   4. Loại orders "ma" (Olist ghost orders — đơn không có item nào)
#   5. Cửa hàng SINH TỰ ĐỘNG, phân bổ across 30 cities
# ============================================================
print("\n" + "=" * 60)
print("BƯỚC 3: Pipeline lọc dữ liệu")
print("=" * 60)

# 3a. TOP 30 cities (by order count) — CỐ ĐỊNH
city_order_count = orders.groupby(['customer_city', 'customer_state']).size().reset_index(name='cnt')
city_order_count = city_order_count.sort_values('cnt', ascending=False)
top_cities = city_order_count.head(TOP_CITIES)[['customer_city', 'customer_state']].copy()
top_cities.columns = ['city', 'state']
city_set = set(zip(top_cities['city'], top_cities['state']))
print(f"  3a. Top {TOP_CITIES} cities: {len(city_set)} selected")
for i, (_, row) in enumerate(top_cities.head(5).iterrows()):
    print(f"      #{i+1}: {row['city']} ({row['state']})")

# 3b. Lọc orders CHỈ từ customers thuộc 30 TP
orders['city_state'] = list(zip(orders['customer_city'], orders['customer_state']))
orders_final = orders[orders['city_state'].isin(city_set)].copy()
order_set = set(orders_final['order_id'])
customer_unique_set = set(orders_final['customer_unique_id'])
print(f"  3b. Orders trong {TOP_CITIES} cities: {len(orders_final):,}")
print(f"      Customers: {len(customer_unique_set):,}")

# 3c. Lấy ALL order_items cho orders đã lọc (KHÔNG lọc product)
items_final = order_items[order_items['order_id'].isin(order_set)].copy()
top_product_ids = set(items_final['product_id'])
print(f"  3c. Order items: {len(items_final):,}")
print(f"      Unique products: {len(top_product_ids):,}")

# 3d. Loại orders "ma" — Olist có ~362 đơn không có item nào trong dataset
orders_with_items = set(items_final['order_id'])
n_before = len(orders_final)
orders_final = orders_final[orders_final['order_id'].isin(orders_with_items)].copy()
order_set = set(orders_final['order_id'])
customer_unique_set = set(orders_final['customer_unique_id'])
n_dropped = n_before - len(orders_final)
if n_dropped > 0:
    print(f"  3d. Loại {n_dropped} orders 'ma' (không có items) → còn {len(orders_final):,} orders")
else:
    print(f"  3d. Mọi orders đều có items ✓")

# 3e. Dedup customers (1 customer_unique_id → 1 row, lấy thông tin từ đơn đầu tiên)
customers_dedup = orders_final.sort_values('order_purchase_timestamp') \
    .drop_duplicates(subset='customer_unique_id').copy()

# 3f. CỬA HÀNG — sinh tự động, phân bổ across 30 cities
# Không dùng Olist sellers — đây là doanh nghiệp sở hữu tất cả cửa hàng
city_list = sorted(city_set)
# Tính weight theo số orders mỗi city
city_weight_map = {}
for c in city_list:
    mask = (city_order_count['customer_city'] == c[0]) & (city_order_count['customer_state'] == c[1])
    city_weight_map[c] = int(city_order_count.loc[mask, 'cnt'].values[0])

# Phân bổ: mỗi city ≥1 store, phần còn lại weighted by order count
store_city_assignments = list(city_list)  # 30 stores, 1 per city
remaining = TOP_STORES - len(city_list)
if remaining > 0:
    cities_for_extra = []
    weights_for_extra = []
    for c in city_list:
        cities_for_extra.append(c)
        weights_for_extra.append(city_weight_map[c])
    for _ in range(remaining):
        r = random.random() * sum(weights_for_extra)
        cumulative = 0
        for idx, w in enumerate(weights_for_extra):
            cumulative += w
            if r <= cumulative:
                store_city_assignments.append(cities_for_extra[idx])
                break

random.shuffle(store_city_assignments)
stores_per_city = Counter(store_city_assignments)
print(f"  3f. Sinh {len(store_city_assignments)} cửa hàng across {len(city_set)} cities")
for city, cnt in stores_per_city.most_common(5):
    print(f"      {city[0]} ({city[1]}): {cnt} stores")

print(f"\n  === KẾT QUẢ LỌC ===")
print(f"  Cities:    {len(city_set)}")
print(f"  Stores:    {len(store_city_assignments)} (generated)")
print(f"  Products:  {len(top_product_ids)}")
print(f"  Orders:    {len(order_set):,}")
print(f"  Customers: {len(customer_unique_set):,}")

# ============================================================
# [BONUS] CẤY PHÉP MÀU KINH DOANH (Data Story Injector)
# ============================================================
print("\n" + "=" * 60)
print("BƯỚC 3.5: Cấy ghép logic kinh doanh (Thời gian & Mùa vụ)")
print("=" * 60)

# Lấy trọng lượng MAX và giá AVG cho từng đơn hàng
order_features = items_final.merge(products[['product_id', 'product_weight_g']], on='product_id', how='left')
order_agg = order_features.groupby('order_id').agg(
    max_weight=('product_weight_g', 'max'),
    avg_price=('price', 'mean')
).reset_index()

orders_final = orders_final.merge(order_agg, on='order_id', how='left')
orders_final['order_purchase_timestamp'] = pd.to_datetime(orders_final['order_purchase_timestamp'])

def inject_temporal_magic(row):
    ts = row['order_purchase_timestamp']
    w = row['max_weight']
    p = row['avg_price']
    
    if pd.isna(w):
        return ts
        
    # HIỆU ỨNG 1: Khách Du Lịch (Đoàn tour) mua đồ Gọn Nhẹ vào Cuối tuần
    if w < 1000:
        # Nếu đang là ngày trong tuần (T2-T6), 60% xác suất dời xe tour sang T7/CN
        if ts.weekday() < 5 and random.random() < 0.60:
            days_to_add = random.choice([5, 6]) - ts.weekday()
            ts += pd.Timedelta(days=days_to_add)
            
    # HIỆU ỨNG 2: Quà tặng Cao cấp & Gọn Nhẹ -> Bùng nổ Mùa lễ hội Quý 4
    if w < 1000 and p >= 100:
        # 50% xác suất "vá" dữ liệu của Olist bằng cách dời sang Tháng 11, 12
        if random.random() < 0.50:
            try:
                ts = ts.replace(month=random.choice([11, 12]), day=random.randint(1, 28))
            except Exception:
                pass
                
    return ts

orders_final['order_purchase_timestamp'] = orders_final.apply(inject_temporal_magic, axis=1)
print("  ✓ Đã bơm: Hàng nhẹ -> Cuối tuần (Nhờ Khách Tour); Hàng xỉn -> Quý 4 (Noel)!")

# ============================================================
# BƯỚC 4: TẠO MAPPING DICTIONARIES
# ============================================================
print("\n" + "=" * 60)
print("BƯỚC 4: Tạo mapping dictionaries")
print("=" * 60)

# City mapping
all_cities = sorted(city_set)
city_to_id = {city: i + 1 for i, city in enumerate(all_cities)}

# Store mapping (generated, not from Olist sellers)
# store_to_id: index → MaCuaHang (1-based)
# store_city_map: index → city tuple
store_to_id = {i: i + 1 for i in range(len(store_city_assignments))}
store_city_map = {i: store_city_assignments[i] for i in range(len(store_city_assignments))}

# Product mapping
product_to_id = {pid: i + 1 for i, pid in enumerate(sorted(top_product_ids))}

# Customer mapping (customer_unique_id → Mã KH)
customer_to_id = {cid: i + 1 for i, cid in enumerate(sorted(customer_unique_set))}

# Order mapping
order_to_id = {oid: i + 1 for i, oid in enumerate(sorted(order_set))}

print(f"  city_to_id:     {len(city_to_id)} entries")
print(f"  store_to_id:    {len(store_to_id)} entries")
print(f"  product_to_id:  {len(product_to_id)} entries")
print(f"  customer_to_id: {len(customer_to_id)} entries")
print(f"  order_to_id:    {len(order_to_id)} entries")

# ============================================================
# BƯỚC 5: TRANSFORM VÀ SINH DỮ LIỆU
# ============================================================
print("\n" + "=" * 60)
print("BƯỚC 5: Transform 9 bảng")
print("=" * 60)


def escape_sql(val):
    """Escape single quotes trong SQL string."""
    if pd.isna(val):
        return 'NULL'
    s = str(val).replace("'", "''")
    return f"'{s}'"


def write_sql_file(filepath, table_name, columns, rows, oracle_mode=False):
    """Ghi file SQL với INSERT statements.
    oracle_mode=False: multi-row INSERT (SQL Server)
    oracle_mode=True:  individual INSERT per row (Oracle < 23c)
    """
    batch_size = 100
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"-- {table_name}\n")
        f.write(f"-- Total rows: {len(rows)}\n\n")
        col_str = ', '.join(columns)
        if oracle_mode:
            # Oracle: set date format, rồi mỗi row là 1 INSERT riêng biệt
            f.write("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD';\n\n")
            for row in rows:
                vals = ', '.join(str(v) for v in row)
                f.write(f"INSERT INTO {table_name} ({col_str}) VALUES ({vals});\n")
            f.write('\n')
        else:
            # SQL Server: multi-row INSERT, batch 100 rows
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                f.write(f"INSERT INTO {table_name} ({col_str}) VALUES\n")
                val_lines = []
                for row in batch:
                    vals = ', '.join(str(v) for v in row)
                    val_lines.append(f"  ({vals})")
                f.write(',\n'.join(val_lines) + ';\n\n')
    print(f"  → {filepath}: {len(rows):,} rows")


# ─── 5.1 Văn phòng đại diện ───
print("\n  [1/9] Văn phòng đại diện...")
vp_rows = []
for (city, state), city_id in sorted(city_to_id.items(), key=lambda x: x[1]):
    ten_tp = escape_sql(city.title())
    dia_chi = escape_sql(fake.street_address())
    bang = escape_sql(state)
    thoi_gian = "'2016-01-01'"
    vp_rows.append((city_id, ten_tp, dia_chi, bang, thoi_gian))

write_sql_file(
    os.path.join(OUTPUT_DIR, '01_van_phong_dai_dien.sql'),
    'VanPhongDaiDien',
    ['MaThanhPho', 'TenThanhPho', 'DiaChiVP', 'Bang', 'ThoiGian'],
    vp_rows
)

# ─── 5.2 Mặt hàng ───
print("  [2/9] Mặt hàng...")
# Merge products với translation
products_sel = products[products['product_id'].isin(top_product_ids)].copy()
products_sel = products_sel.merge(translation, on='product_category_name', how='left')

# Tính giá trung vị từ order_items
price_median = items_final.groupby('product_id')['price'].median().reset_index()
price_median.columns = ['product_id', 'median_price']
products_sel = products_sel.merge(price_median, on='product_id', how='left')

mh_rows = []
category_counter = Counter()  # đếm số thứ tự trong mỗi danh mục để tên sản phẩm là duy nhất
for _, p in products_sel.iterrows():
    ma_mh = product_to_id[p['product_id']]
    cat = (
        p['product_category_name_english']
        if pd.notna(p.get('product_category_name_english'))
        else p.get('product_category_name', 'unknown')
    )
    category_counter[cat] += 1
    mo_ta = escape_sql(f"{cat} #{category_counter[cat]:04d}")
    # Kích cỡ
    l = p.get('product_length_cm', 0)
    h = p.get('product_height_cm', 0)
    w = p.get('product_width_cm', 0)
    l = int(l) if pd.notna(l) else 0
    h = int(h) if pd.notna(h) else 0
    w = int(w) if pd.notna(w) else 0
    kich_co = escape_sql(f"{l}x{h}x{w} cm")
    # Trọng lượng
    tl = p.get('product_weight_g', 0)
    trong_luong = int(tl) if pd.notna(tl) else 0
    # Giá
    gia = round(p['median_price'], 2) if pd.notna(p.get('median_price')) else 0.0
    # Thời gian: setup data trước tháng 10/2016 (tháng đầu có đơn hàng Olist)
    thoi_gian = escape_sql(fake.date_between(start_date=date(2015, 1, 1), end_date=date(2016, 9, 1)).strftime('%Y-%m-%d'))

    mh_rows.append((ma_mh, mo_ta, kich_co, trong_luong, gia, thoi_gian))

write_sql_file(
    os.path.join(OUTPUT_DIR, '02_mat_hang.sql'),
    'MatHang',
    ['MaMH', 'MoTa', 'KichCo', 'TrongLuong', 'Gia', 'ThoiGian'],
    mh_rows
)

# ─── 5.3 Cửa hàng ───
print("  [3/9] Cửa hàng...")
ch_rows = []
for store_idx in range(len(store_city_assignments)):
    ma_ch = store_to_id[store_idx]
    city = store_city_map[store_idx]
    ma_tp = city_to_id[city]
    sdt = escape_sql(fake.phone_number())
    # Thời gian: setup data trước tháng 10/2016 (tháng đầu có đơn hàng Olist)
    thoi_gian = escape_sql(fake.date_between(start_date=date(2015, 1, 1), end_date=date(2016, 9, 1)).strftime('%Y-%m-%d'))
    ch_rows.append((ma_ch, ma_tp, sdt, thoi_gian))

write_sql_file(
    os.path.join(OUTPUT_DIR, '03_cua_hang.sql'),
    'CuaHang',
    ['MaCuaHang', 'MaThanhPho', 'SoDienThoai', 'ThoiGian'],
    ch_rows
)

# ─── 5.4 Khách hàng ───
print("  [4/9] Khách hàng...")

# Pre-compute MIN(order_purchase_timestamp) per customer_unique_id
orders_final['order_purchase_timestamp'] = pd.to_datetime(orders_final['order_purchase_timestamp'])
first_order_date = orders_final.groupby('customer_unique_id')['order_purchase_timestamp'].min().reset_index()
first_order_date.columns = ['customer_unique_id', 'first_order_date']

kh_rows = []
# Tạm lưu zip_code theo cuid để build customer_zip_map sau
_cuid_zip_temp = {}

for _, c in customers_dedup.iterrows():
    cuid = c['customer_unique_id']
    if cuid not in customer_to_id:
        continue
    ma_kh = customer_to_id[cuid]
    ten_kh = escape_sql(fake.name())
    city_key = (c['customer_city'], c['customer_state'])
    ma_tp = city_to_id.get(city_key)
    if ma_tp is None:
        continue

    # Ngày đặt hàng đầu tiên (pre-computed)
    fod_row = first_order_date[first_order_date['customer_unique_id'] == cuid]
    if len(fod_row) > 0:
        ngay_dh = escape_sql(fod_row.iloc[0]['first_order_date'].strftime('%Y-%m-%d'))
    else:
        ngay_dh = 'NULL'

    kh_rows.append((ma_kh, ten_kh, ma_tp, ngay_dh))
    _cuid_zip_temp[ma_kh] = c.get('customer_zip_code_prefix', '00000')

# VALIDATION: kiểm tra không có KH nào bị drop silent
kh_inserted_set = set(row[0] for row in kh_rows)  # MaKH đã thực sự INSERT
kh_expected_set = set(customer_to_id.values())
kh_dropped = kh_expected_set - kh_inserted_set
if kh_dropped:
    print(f"    [CRITICAL] {len(kh_dropped)} customers bị DROP do city không map!")
    print(f"    → Thu hẹp customer_to_id để đảm bảo FK integrity")
    customer_to_id = {cuid: ma_kh for cuid, ma_kh in customer_to_id.items()
                      if ma_kh in kh_inserted_set}
else:
    print(f"    ✓ 0 customers dropped — FK integrity OK")

# Build customer_ids_list và customer_zip_map TỪ kh_rows (output thực tế)
# → đảm bảo KH du lịch/bưu điện CHỈ chứa MaKH đã INSERT vào KhachHang
customer_ids_list = [row[0] for row in kh_rows]
customer_zip_map = _cuid_zip_temp  # đã chỉ chứa KH inserted (vì append sau guard)

write_sql_file(
    os.path.join(OUTPUT_DIR, '04_khach_hang.sql'),
    'KhachHang',
    ['MaKH', 'TenKH', 'MaThanhPho', 'NgayDatHangDauTien'],
    kh_rows,
    oracle_mode=True
)

# ─── 5.5 Khách hàng du lịch ───
print("  [5/9] Phân bổ khách hàng (Mô hình Xác suất theo Trọng lượng)...")

# Tính Max Weight của sản phẩm mà mỗi khách hàng đã mua
c_weights = items_final.merge(orders_final[['order_id', 'customer_unique_id']], on='order_id', how='inner')
c_weights = c_weights.merge(products[['product_id', 'product_weight_g']], on='product_id', how='left')
c_weights['product_weight_g'] = c_weights['product_weight_g'].fillna(0)

cw_agg = c_weights.groupby('customer_unique_id')['product_weight_g'].max().reset_index()

customer_max_weight = {}
for _, row in cw_agg.iterrows():
    cuid = row['customer_unique_id']
    ma_kh = customer_to_id.get(cuid)
    if ma_kh and ma_kh in kh_inserted_set:
        customer_max_weight[ma_kh] = row['product_weight_g']

for ma_kh in customer_ids_list:
    if ma_kh not in customer_max_weight:
        customer_max_weight[ma_kh] = 0

kh_du_lich_ids = []
kh_buu_dien_ids = []

for ma_kh in customer_ids_list:
    w = customer_max_weight[ma_kh]
    
    # Logic Xác suất (Tránh sự "giả trân" của cắt cứng 60-60)
    if w >= 3000:
        # Đồ quá nặng: Đại đa số sẽ gọi bưu điện ship, một số ít cố xách về
        p_buu_dien, p_du_lich = 0.70, 0.30
    elif w < 1000:
        # Đồ gọn nhẹ: Đại đa số là khách du lịch xách tay, phần dôi ra khách online mua
        p_buu_dien, p_du_lich = 0.20, 0.80
    else:
        # Đồ tầm trung: 50% - 50%
        p_buu_dien, p_du_lich = 0.60, 0.60
        
    if random.random() < p_du_lich:
        kh_du_lich_ids.append(ma_kh)
    if random.random() < p_buu_dien:
        kh_buu_dien_ids.append(ma_kh)

overlap = set(kh_du_lich_ids) & set(kh_buu_dien_ids)
print(f"    Du lịch: {len(kh_du_lich_ids):,}, Bưu điện: {len(kh_buu_dien_ids):,}, Overlap: {len(overlap):,}")

# Danh sách ~20 hướng dẫn viên để reuse
tour_guides = [fake.name() for _ in range(20)]

# Map MaKH → first_order_date từ first_order_date dataframe
fod_map = {}
for _, row in first_order_date.iterrows():
    cuid = row['customer_unique_id']
    ma_kh = customer_to_id.get(cuid)
    if ma_kh:
        fod_map[ma_kh] = row['first_order_date'].strftime('%Y-%m-%d')

kh_dl_rows = []
for ma_kh in kh_du_lich_ids:
    hdv = escape_sql(random.choice(tour_guides))
    # ThoiGian = first_order_date của khách hàng đó
    thoi_gian = escape_sql(fod_map.get(ma_kh, '2017-01-01'))
    kh_dl_rows.append((ma_kh, hdv, thoi_gian))

write_sql_file(
    os.path.join(OUTPUT_DIR, '05_khach_hang_du_lich.sql'),
    'KH_DuLich',
    ['MaKH', 'HuongDanVien', 'ThoiGian'],
    kh_dl_rows,
    oracle_mode=True
)

# ─── 5.6 Khách hàng bưu điện ───
print("  [6/9] Khách hàng bưu điện...")
kh_bd_rows = []
for ma_kh in kh_buu_dien_ids:
    zip_code = customer_zip_map.get(ma_kh, '00000')
    dia_chi = escape_sql(f"{zip_code}-{fake.building_number()}, {fake.street_name()}")
    # ThoiGian = first_order_date của khách hàng đó
    thoi_gian = escape_sql(fod_map.get(ma_kh, '2017-01-01'))
    kh_bd_rows.append((ma_kh, dia_chi, thoi_gian))

write_sql_file(
    os.path.join(OUTPUT_DIR, '06_khach_hang_buu_dien.sql'),
    'KH_BuuDien',
    ['MaKH', 'DiaChiBuuDien', 'ThoiGian'],
    kh_bd_rows,
    oracle_mode=True
)

# ─── 5.7 Mặt hàng được lưu trữ ───
# Mô hình retail: doanh nghiệp sở hữu tất cả cửa hàng.
# Mỗi cửa hàng stock random 15-25% tổng sản phẩm.
# Với 100 stores × ~20%, P(product không ở store nào) ≈ 0 → gần như chắc chắn coverage.
# Fallback bổ sung products còn sót để đảm bảo BC2.
print("  [7/9] Mặt hàng được lưu trữ...")

all_product_ids = sorted(product_to_id.values())
all_store_ids = sorted(store_to_id.values())
n_total_products = len(all_product_ids)

mh_lt_rows = []
products_covered = set()

# Tính min_order_date từ orders_final để MatHang_LuuTru phải trước đó
min_order_date = orders_final['order_purchase_timestamp'].min()

# Bước 1: Mỗi store stocks 15-25% sản phẩm (tỉ lệ, không cố định số)
for ma_ch in all_store_ids:
    pct = random.uniform(0.15, 0.25)
    n_products = random.randint(400, 600)

    store_products = random.sample(all_product_ids, min(n_products, n_total_products))
    for ma_mh in store_products:
        so_luong_kho = random.randint(10, 200)
        # ThoiGian: kho phải tồn tại trước đơn hàng đầu (Oct 2016)
        thoi_gian = escape_sql(fake.date_between(start_date=date(2015, 1, 1), end_date=date(2016, 9, 1)).strftime('%Y-%m-%d'))
        mh_lt_rows.append((ma_ch, ma_mh, so_luong_kho, thoi_gian))
        products_covered.add(ma_mh)

# Bước 2: Đảm bảo mọi product có ≥1 entry (fallback cho trường hợp hiếm)
missing = set(all_product_ids) - products_covered
if missing:
    print(f"    Bổ sung {len(missing)} products chưa có kho → gán random store")
    for ma_mh in sorted(missing):
        ma_ch = random.choice(all_store_ids)
        so_luong_kho = random.randint(10, 200)
        thoi_gian = escape_sql(fake.date_between(start_date=date(2015, 1, 1), end_date=date(2016, 9, 1)).strftime('%Y-%m-%d'))
        mh_lt_rows.append((ma_ch, ma_mh, so_luong_kho, thoi_gian))
else:
    print(f"    Mọi {n_total_products:,} products đều có trong kho ✓")

avg_per_store = len(mh_lt_rows) // len(all_store_ids)
print(f"    MatHangDuocLuuTru: {len(mh_lt_rows):,} entries ({len(all_store_ids)} stores × ~{avg_per_store:,} products)")

write_sql_file(
    os.path.join(OUTPUT_DIR, '07_mat_hang_duoc_luu_tru.sql'),
    'MatHang_LuuTru',
    ['MaCuaHang', 'MaMH', 'SoLuongKho', 'ThoiGian'],
    mh_lt_rows
)

# ─── 5.8 Đơn đặt hàng ───
print("  [8/9] Đơn đặt hàng...")

# Cần map order → customer_unique_id → Mã KH
# CHỈ reference MaKH đã thực sự INSERT vào bảng KhachHang
ddh_rows = []
skipped_orders = 0
for _, o in orders_final.iterrows():
    oid = o['order_id']
    if oid not in order_to_id:
        continue
    ma_don = order_to_id[oid]
    ngay_dh = escape_sql(o['order_purchase_timestamp'].strftime('%Y-%m-%d'))
    cuid = o['customer_unique_id']
    ma_kh = customer_to_id.get(cuid)
    if ma_kh is None or ma_kh not in kh_inserted_set:
        skipped_orders += 1
        continue
    ddh_rows.append((ma_don, ngay_dh, ma_kh))

ddh_inserted_set = set(row[0] for row in ddh_rows)  # MaDon đã thực sự INSERT

if skipped_orders > 0:
    print(f"    [WARN] Skipped {skipped_orders} orders (customer not in KhachHang)")
    pct = skipped_orders / len(orders_final) * 100
    if pct > 1.0:
        print(f"    [CRITICAL] {pct:.2f}% orders bị drop — kiểm tra lại pipeline!")
else:
    print(f"    ✓ 0 orders skipped — FK → KhachHang OK")

write_sql_file(
    os.path.join(OUTPUT_DIR, '08_don_dat_hang.sql'),
    'DonDatHang',
    ['MaDon', 'NgayDatHang', 'MaKH'],
    ddh_rows
)

# ─── 5.9 Mặt hàng được đặt ───
print("  [9/9] Mặt hàng được đặt...")

# GROUP BY (order_id, product_id) → SoLuongDat = COUNT(*), GiaDat = AVG(price)
items_grouped = items_final.groupby(['order_id', 'product_id']).agg(
    so_luong=('price', 'count'),
    gia_dat=('price', 'mean')
).reset_index()

# JOIN với orders để lấy timestamp
items_grouped = items_grouped.merge(
    orders_final[['order_id', 'order_purchase_timestamp']].drop_duplicates(),
    on='order_id',
    how='inner'
)

mhdd_rows = []
skipped_items = 0
for _, item in items_grouped.iterrows():
    ma_don = order_to_id.get(item['order_id'])
    ma_mh = product_to_id.get(item['product_id'])
    # CHỈ reference MaDon đã thực sự INSERT vào DonDatHang
    if ma_don is None or ma_mh is None or ma_don not in ddh_inserted_set:
        skipped_items += 1
        continue
    so_luong = int(item['so_luong'])
    gia_dat = round(item['gia_dat'], 2)
    # ThoiGian = order_purchase_timestamp (từ dữ liệu gốc 2017-2018)
    thoi_gian = escape_sql(item['order_purchase_timestamp'].strftime('%Y-%m-%d'))
    mhdd_rows.append((ma_don, ma_mh, so_luong, gia_dat, thoi_gian))

if skipped_items > 0:
    print(f"    [WARN] Skipped {skipped_items} item rows (order/product not in inserted set)")
    pct = skipped_items / len(items_grouped) * 100
    if pct > 1.0:
        print(f"    [CRITICAL] {pct:.2f}% items bị drop — kiểm tra lại pipeline!")
else:
    print(f"    ✓ 0 items skipped — FK → DonDatHang + MatHang OK")

write_sql_file(
    os.path.join(OUTPUT_DIR, '09_mat_hang_duoc_dat.sql'),
    'MatHang_DuocDat',
    ['MaDon', 'MaMH', 'SoLuongDat', 'GiaDat', 'ThoiGian'],
    mhdd_rows
)

# ============================================================
# BƯỚC 6: VALIDATION — Kiểm tra FK Integrity toàn bộ
# ============================================================
print("\n" + "=" * 60)
print("BƯỚC 6: VALIDATION — FK Integrity Check")
print("=" * 60)

# Collect all inserted IDs from actual rows
vp_ids = set(row[0] for row in vp_rows)           # MaThanhPho
mh_ids = set(row[0] for row in mh_rows)            # MaMH
ch_ids = set(row[0] for row in ch_rows)             # MaCuaHang
kh_ids = set(row[0] for row in kh_rows)             # MaKH
dl_ids = set(row[0] for row in kh_dl_rows)          # MaKH (du lịch)
bd_ids = set(row[0] for row in kh_bd_rows)          # MaKH (bưu điện)
lt_ch_ids = set(row[0] for row in mh_lt_rows)       # MaCuaHang (lưu trữ)
lt_mh_ids = set(row[1] for row in mh_lt_rows)       # MaMatHang (lưu trữ)
ddh_ids = set(row[0] for row in ddh_rows)            # MaDon
ddh_kh_ids = set(row[2] for row in ddh_rows)         # MaKhachHang (trong đơn)
mhdd_don_ids = set(row[0] for row in mhdd_rows)      # MaDon (trong mặt hàng đặt)
mhdd_mh_ids = set(row[1] for row in mhdd_rows)       # MaMatHang (trong mặt hàng đặt)

checks = [
    ("CuaHang.MaThanhPho → VanPhongDaiDien",
     set(row[1] for row in ch_rows), vp_ids),
    ("KhachHang.MaThanhPho → VanPhongDaiDien",
     set(row[2] for row in kh_rows), vp_ids),
    ("KhachHangDuLich.MaKH → KhachHang",
     dl_ids, kh_ids),
    ("KhachHangBuuDien.MaKH → KhachHang",
     bd_ids, kh_ids),
    ("MatHangDuocLuuTru.MaCuaHang → CuaHang",
     lt_ch_ids, ch_ids),
    ("MatHangDuocLuuTru.MaMatHang → MatHang",
     lt_mh_ids, mh_ids),
    ("DonDatHang.MaKhachHang → KhachHang",
     ddh_kh_ids, kh_ids),
    ("MatHangDuocDat.MaDon → DonDatHang",
     mhdd_don_ids, ddh_ids),
    ("MatHangDuocDat.MaMatHang → MatHang",
     mhdd_mh_ids, mh_ids),
]

all_ok = True
for desc, child_set, parent_set in checks:
    orphans = child_set - parent_set
    if orphans:
        print(f"  ✗ {desc}: {len(orphans)} orphan(s)!")
        all_ok = False
    else:
        print(f"  ✓ {desc}")

# Business Constraint 1: Mọi DonDatHang có ≥1 MatHangDuocDat
orders_without_items = ddh_ids - mhdd_don_ids
if orders_without_items:
    print(f"  ✗ BC1: {len(orders_without_items)} DonDatHang không có MatHangDuocDat")
    all_ok = False
else:
    print(f"  ✓ BC1: Mọi DonDatHang đều có ≥1 MatHangDuocDat")

# Business Constraint 2: Mọi MaMH trong MatHangDuocDat có ≥1 MatHangDuocLuuTru
products_not_stocked = mhdd_mh_ids - lt_mh_ids
if products_not_stocked:
    print(f"  ✗ BC2: {len(products_not_stocked)} products được đặt nhưng không có trong kho")
    all_ok = False
else:
    print(f"  ✓ BC2: Mọi product được đặt đều có trong kho")

if all_ok:
    print("\n  ★★★ FK + BUSINESS CONSTRAINTS: 100% PASS ★★★")
else:
    print("\n  ⚠ VALIDATION FAILED — xem chi tiết ở trên")
    print("  → Xóa output files và dừng script.")
    # Xóa tất cả SQL files đã xuất để tránh import dữ liệu lỗi
    import glob
    for f in glob.glob(os.path.join(OUTPUT_DIR, '*.sql')):
        os.remove(f)
    sys.exit(1)

# ============================================================
# BƯỚC 7: TỔNG KẾT
# ============================================================
print("\n" + "=" * 60)
print("TỔNG KẾT")
print("=" * 60)
summary = [
    ("01 - Văn phòng đại diện", len(vp_rows)),
    ("02 - Mặt hàng", len(mh_rows)),
    ("03 - Cửa hàng", len(ch_rows)),
    ("04 - Khách hàng", len(kh_rows)),
    ("05 - KH du lịch", len(kh_dl_rows)),
    ("06 - KH bưu điện", len(kh_bd_rows)),
    ("07 - MH được lưu trữ", len(mh_lt_rows)),
    ("08 - Đơn đặt hàng", len(ddh_rows)),
    ("09 - MH được đặt", len(mhdd_rows)),
]
total = 0
for name, count in summary:
    print(f"  {name:<30s} {count:>10,} rows")
    total += count
print(f"  {'TỔNG':<30s} {total:>10,} rows")
print(f"\nOutput: {OUTPUT_DIR}")
print("DONE!")
