# %% [markdown]
# # LỚP 1: PHÂN CỤM KHÁCH HÀNG THEO RFM (K-Means)
#
# **Thiết kế:** Chỉ dùng `order_items` — 4 chỉ số RFM thuần.
# KHÔNG dùng `events` ở Lớp 1 để Lớp 2 có thể dùng events làm features
# mà không bị cross-layer leakage.
#
# **SQL đã xác nhận (Survey business logic):**
# - AOV KHÔNG thay đổi theo số đơn hàng ($59 flat)
# - Monetary tăng hoàn toàn do frequency, không do AOV
# → VIP thật sự = khách mua NHIỀU LẦN (frequency cao), không phải mua 1 lần đắt tiền
# → Rank clusters theo FREQUENCY, không phải monetary
#
# **Output:** customer_segments.csv (user_id, is_vip)

# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import query_db

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

# %% [markdown]
# ## Bước 1: Truy vấn RFM từ order_items
#
# **Xác nhận SQL:** 71,950 users có orders (Survey #3).
# Recency = số ngày từ lần mua cuối đến ngày tham chiếu.

# %%
query_rfm = """
SELECT
    user_id,
    COUNT(DISTINCT order_id)          AS frequency,
    SUM(sale_price)                   AS monetary,
    (SUM(sale_price) / COUNT(DISTINCT order_id)::float) AS avg_order_value,
    MAX(created_at::timestamp)        AS last_purchase_date
FROM order_items
WHERE status != 'Cancelled'
GROUP BY user_id
HAVING COUNT(DISTINCT order_id) >= 1
"""

print("Querying RFM data...")
df = query_db(query_rfm)
print(f"Loaded {len(df):,} customers")

# Tính recency (ngày)
ref_date = pd.Timestamp('2024-01-01', tz='UTC')
df['last_purchase_date'] = pd.to_datetime(df['last_purchase_date'], utc=True)
df['recency'] = (ref_date - df['last_purchase_date']).dt.days

feature_cols = ['recency', 'frequency', 'monetary', 'avg_order_value']
df = df.dropna(subset=feature_cols)
print(f"After dropna: {len(df):,} customers")
print(df[feature_cols].describe().round(2))

# %% [markdown]
# ## Bước 2: K-Means phân cụm (k=4)
#
# **Verify:** Silhouette score > 0.25 → clusters có ý nghĩa.

# %%
scaler = StandardScaler()
X = scaler.fit_transform(df[feature_cols])

km = KMeans(n_clusters=4, random_state=42, n_init=10)
df['cluster'] = km.fit_predict(X)

sil = silhouette_score(X, df['cluster'])
print(f"Silhouette Score: {sil:.4f} (target > 0.25)")

# Rank clusters by FREQUENCY (số lần mua) → gán tên
# VIP = cluster mua lại nhiều nhất (loyal), không phải mua 1 lần đắt tiền
# Business logic: AOV flat ($59) → monetary chỉ tăng do frequency, không do ticket size
rank = df.groupby('cluster')['frequency'].mean().sort_values().index.tolist()
name_map = {
    rank[0]: 'Ngu Dong',    # frequency thấp nhất, recency xa
    rank[1]: 'Vang Lai',    # frequency thấp, mua đồ đắt hơn 1 lần
    rank[2]: 'Tiem Nang',   # frequency trung bình, có tiềm năng quay lại
    rank[3]: 'VIP'          # frequency cao nhất → khách hàng trung thành thật sự
}
df['segment'] = df['cluster'].map(name_map)

# is_vip = 1 chỉ cho cluster VIP (frequency cao nhất)
# Không gộp Tiem Nang vào vì sau frequency-rank, cluster 2 là one-time buyers
df['is_vip'] = (df['segment'] == 'VIP').astype(int)

print("\nCluster summary (ranked by frequency):")
summary = df.groupby('segment')[feature_cols + ['is_vip']].mean().round(2)
summary['count'] = df.groupby('segment')['user_id'].count()
print(summary)

# %% [markdown]
# ## Bước 3: Radar Chart (4 chiều)

# %%
seg_profile = df.groupby('segment')[feature_cols].mean()
normed = (seg_profile - seg_profile.min()) / (seg_profile.max() - seg_profile.min())
normed['recency'] = 1 - normed['recency']  # recency thấp = tốt → đảo

categories = ['Recency', 'Frequency', 'Monetary', 'AOV']
N = len(categories)
angles = [n / float(N) * 2 * np.pi for n in range(N)] + [0]

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
colors = {'VIP': '#e74c3c', 'Tiem Nang': '#f39c12', 'Vang Lai': '#3498db', 'Ngu Dong': '#95a5a6'}
order = ['VIP', 'Tiem Nang', 'Vang Lai', 'Ngu Dong']

for seg in order:
    vals = normed.loc[seg].tolist() + [normed.loc[seg].iloc[0]]
    ax.plot(angles, vals, 'o-', lw=2, label=seg, color=colors[seg])
    ax.fill(angles, vals, alpha=0.07, color=colors[seg])

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories)
ax.set_title('Customer Segments - RFM (Layer 1)', fontweight='bold', pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1))
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, '01_radar_chart.png'), dpi=150, bbox_inches='tight')
plt.show()
print("Saved: 01_radar_chart.png")

# %% [markdown]
# ## Bước 4: Xuất nhãn cho Lớp 2

# %%
out_path = os.path.join(SAVE_DIR, 'customer_segments.csv')
df[['user_id', 'cluster', 'segment', 'is_vip']].to_csv(out_path, index=False)
print(f"Saved {len(df):,} labels to: {out_path}")
print(f"VIP (high-frequency loyal): {df['is_vip'].sum():,} ({df['is_vip'].mean()*100:.1f}%)")
print(f"Non-VIP: {(1 - df['is_vip']).sum():,} ({(1 - df['is_vip']).mean()*100:.1f}%)")
