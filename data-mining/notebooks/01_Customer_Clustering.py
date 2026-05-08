# %% [markdown]
# # Lớp 1: Khai phá Chân dung Phong cách Khách hàng (Customer Style Profiling)
# Mục tiêu: Nhóm hơn 1.3 triệu khách hàng thành các cụm (clusters) dựa trên "Gu thời trang" (Fashion DNA) thay vì chỉ dựa trên RFM đơn thuần.
# Chiến lược chống OOM: Tính toán DNA trực tiếp trong PostgreSQL, chỉ kéo kết quả (~1 triệu dòng x 8 cột) về Python để chạy K-Means.

# %%
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings('ignore')

# Cấu hình đường dẫn để import database
from database import query_db

# %% [markdown]
# ## 1. Trích xuất Fashion DNA từ PostgreSQL
# Chúng ta sẽ tính toán % mỗi khách hàng mua đồ Ladieswear, Divided, Menswear, Baby, và Kênh mua sắm (Online vs Offline).
# Chỉ lấy những khách hàng có ít nhất 3 giao dịch để tránh nhiễu từ khách vãng lai.

# %%
query_dna = """
WITH cust_stats AS (
    SELECT 
        t.customer_id,
        COUNT(*) AS total_items,
        AVG(t.price) AS avg_price,
        SUM(CASE WHEN a.index_group_name = 'Ladieswear' THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_ladieswear,
        SUM(CASE WHEN a.index_group_name = 'Divided' THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_divided,
        SUM(CASE WHEN a.index_group_name = 'Menswear' THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_menswear,
        SUM(CASE WHEN a.index_group_name = 'Baby/Children' THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_baby,
        SUM(CASE WHEN a.index_group_name = 'Sport' THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_sport,
        SUM(CASE WHEN t.sales_channel_id = 2 THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_online
    FROM transactions t
    JOIN articles a ON t.article_id = a.article_id
    GROUP BY t.customer_id
    HAVING COUNT(*) >= 3
)
SELECT 
    cs.*, 
    c.age
FROM cust_stats cs
JOIN customers c ON cs.customer_id = c.customer_id
WHERE c.age IS NOT NULL;
"""

print("Đang truy vấn Fashion DNA từ Database (Có thể mất 2-3 phút)...")
df_dna = query_db(query_dna)
print(f"Hoàn thành! Kích thước dữ liệu: {df_dna.shape}")
df_dna.head()

# %% [markdown]
# ## 2. Tiền xử lý (Preprocessing)

# %%
# Chọn các features để phân cụm (Bỏ customer_id, age, và total_items ra khỏi thuật toán để tránh bias)

features = [
    'pct_ladieswear', 'pct_divided', 'pct_menswear', 
    'pct_baby', 'pct_sport', 'pct_online', 'avg_price'
]

X = df_dna[features].copy()

# Chuẩn hóa dữ liệu (Standardization)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

print("Đã chuẩn hóa xong.")

# %% [markdown]
# ## 3. Đánh giá số cụm tối ưu (Elbow, Silhouette, Davies-Bouldin)
# Lấy mẫu 200k để tìm k tối ưu và tính các metric nặng (tránh OOM)

# %%
from sklearn.metrics import davies_bouldin_score
from sklearn.cluster import MiniBatchKMeans

sample_size = min(200000, X_scaled.shape[0])
X_sample = X_scaled[np.random.choice(X_scaled.shape[0], sample_size, replace=False)]

inertia = []
silhouette = []
davies_bouldin = []
K_range = range(2, 8)

print(f"Đang tính toán các chỉ số đánh giá trên mẫu {sample_size} khách hàng...")
for k in K_range:
    # Dùng MiniBatchKMeans cho tập mẫu lớn (200k) để tăng tốc
    kmeans = MiniBatchKMeans(n_clusters=k, batch_size=2048, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_sample)
    
    inertia.append(kmeans.inertia_)
    silhouette.append(silhouette_score(X_sample, labels))
    davies_bouldin.append(davies_bouldin_score(X_sample, labels))
    print(f"k={k} hoàn tất.")

# Vẽ biểu đồ 3 trục để bảo vệ trước giảng viên
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# 1. Elbow
axes[0].plot(K_range, inertia, marker='o', color='b')
axes[0].set_title('Elbow Method (Inertia)\n(Tìm điểm gập)')
axes[0].set_xlabel('Số cụm (k)')
axes[0].grid(True)

# 2. Silhouette
axes[1].plot(K_range, silhouette, marker='s', color='g')
axes[1].set_title('Silhouette Score\n(Càng cao càng tốt)')
axes[1].set_xlabel('Số cụm (k)')
axes[1].grid(True)

# 3. Davies Bouldin
axes[2].plot(K_range, davies_bouldin, marker='^', color='r')
axes[2].set_title('Davies-Bouldin Index\n(Càng thấp càng tốt)')
axes[2].set_xlabel('Số cụm (k)')
axes[2].grid(True)

plt.tight_layout()
plt.savefig('k_evaluation_metrics.png', dpi=300)
print("Đã lưu biểu đồ tổng hợp: k_evaluation_metrics.png")

# %% [markdown]
# ## 4. Phân cụm chính thức (K-Means)
# Dựa vào Fashion industry, 4-5 cụm thường là đẹp nhất (GenZ, Mature, Sporty, Kids/Family).
# Ta chọn k=5.

# %%
k_optimal = 5
print(f"Tiến hành chạy K-Means với k={k_optimal} trên toàn bộ dữ liệu...")

kmeans_final = KMeans(n_clusters=k_optimal, random_state=42, n_init=10)
df_dna['cluster'] = kmeans_final.fit_predict(X_scaled)

print("Phân cụm hoàn tất!")

# Tính toán profile trung bình của từng cụm
cluster_profile = df_dna.groupby('cluster').agg({
    'customer_id': 'count',
    'age': 'median',
    'total_items': 'median',
    'avg_price': 'mean',
    'pct_ladieswear': 'mean',
    'pct_divided': 'mean',
    'pct_menswear': 'mean',
    'pct_baby': 'mean',
    'pct_sport': 'mean',
    'pct_online': 'mean'
}).reset_index()

cluster_profile.rename(columns={'customer_id': 'n_customers'}, inplace=True)
cluster_profile['pct_of_base'] = (cluster_profile['n_customers'] / len(df_dna) * 100).round(1)

# Format hiển thị
for col in ['pct_ladieswear', 'pct_divided', 'pct_menswear', 'pct_baby', 'pct_sport', 'pct_online']:
    cluster_profile[col] = (cluster_profile[col] * 100).round(1)

print("\n=== PROFILE CÁC CỤM KHÁCH HÀNG ===")
print(cluster_profile.to_string())

# %% [markdown]
# ## 5. Đặt tên (Labeling) và Trực quan hóa

# %%
# Dựa trên kết quả (giả định), ta có thể map tên. Bạn có thể sửa map này sau khi xem data thực tế.
def assign_name(row):
    if row['pct_baby'] > 30: return 'Family/Moms'
    if row['pct_divided'] > 40: return 'GenZ Trend'
    if row['pct_menswear'] > 40: return 'Menswear'
    if row['pct_sport'] > 20: return 'Sporty Active'
    if row['pct_online'] < 50: return 'Classic Offline'
    return 'Classic Online'

cluster_profile['cluster_name'] = cluster_profile.apply(assign_name, axis=1)

# Tạo từ điển map cụm sang tên
cluster_map = dict(zip(cluster_profile['cluster'], cluster_profile['cluster_name']))
df_dna['cluster_name'] = df_dna['cluster'].map(cluster_map)

# Lưu kết quả xuống CSV để dùng cho Lớp 2 (Association Rules)
output_file = 'customer_clusters.csv'
df_dna[['customer_id', 'cluster', 'cluster_name']].to_csv(output_file, index=False)
print(f"\nĐã lưu mapping khách hàng - cụm vào: {output_file}")

# Vẽ bar chart số lượng
plt.figure(figsize=(10, 6))
sns.barplot(x='cluster_name', y='n_customers', data=cluster_profile, palette='viridis')
plt.title('Số lượng Khách hàng theo Từng Cụm Phong Cách')
plt.ylabel('Số lượng KH')
plt.xlabel('Tên cụm (Style)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('cluster_distribution.png')
print("Đã lưu biểu đồ cluster_distribution.png")

print("\n=== GIAI ĐOẠN 1 HOÀN TẤT ===")
