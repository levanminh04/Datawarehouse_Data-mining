# %% [markdown]
# # LỚP 1: PHÂN CỤM SẢN PHẨM THEO GIÁ (K-Means)
#
# **Câu hỏi kinh doanh:**
# Trong 29,000+ sản phẩm, có thể nhóm chúng thành các phân khúc giá
# Budget / Mid-range / Premium không? Phân khúc nào có margin tốt hơn?
#
# **SQL đã xác nhận (survey_product_verify.py):**
# - Suits/Women: median $122 → Premium rõ ràng
# - Socks: median $14 → Budget rõ ràng
# - Price cutoffs tự nhiên: ~$28 và ~$58
# - Margin: Mid(30-50%) và High(50-70%) — tách biệt theo category
#
# **Thiết kế:** Cluster PRODUCT, không cluster USER
# → Tránh hoàn toàn mọi flaws về user behavior, events, demographics
#
# **Output:** product_tiers.csv (product_id, price_tier)

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
# ## Bước 1: Truy vấn dữ liệu sản phẩm

# %%
query = """
SELECT
    id AS product_id,
    category,
    department,
    retail_price,
    cost,
    ROUND(((retail_price - cost) / NULLIF(retail_price, 0))::numeric, 4) AS margin_pct
FROM products
WHERE retail_price > 0 AND cost > 0
"""

print("Querying products...")
df = query_db(query)
df = df.dropna(subset=['retail_price', 'cost', 'margin_pct'])
print(f"Products loaded: {len(df):,}")
print(df[['retail_price', 'cost', 'margin_pct']].describe().round(2))

# %% [markdown]
# ## Bước 2: K-Means phân cụm (k=3: Budget / Mid-range / Premium)
#
# **Verify SQL:** p33=$27.95, p67=$58 → 3 cụm tự nhiên tồn tại
# Cluster trên [retail_price, cost, margin_pct] sau StandardScaler

# %%
FEATURE_COLS = ['retail_price', 'cost', 'margin_pct']
scaler = StandardScaler()
X = scaler.fit_transform(df[FEATURE_COLS])

km = KMeans(n_clusters=3, random_state=42, n_init=10)
df['cluster'] = km.fit_predict(X)

sil = silhouette_score(X, df['cluster'])
print(f"\nSilhouette Score: {sil:.4f} (target > 0.25)")

# Rank by retail_price trung bình → gán tên
rank = df.groupby('cluster')['retail_price'].mean().sort_values().index.tolist()
tier_map = {rank[0]: 'Budget', rank[1]: 'Mid-range', rank[2]: 'Premium'}
df['price_tier'] = df['cluster'].map(tier_map)

print("\nProduct tier summary:")
summary = df.groupby('price_tier').agg(
    num_products=('product_id', 'count'),
    avg_price=('retail_price', 'mean'),
    avg_cost=('cost', 'mean'),
    avg_margin_pct=('margin_pct', 'mean')
).round(2)
print(summary)

# %% [markdown]
# ## Bước 3: Trực quan hóa

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

colors = {'Budget': '#3498db', 'Mid-range': '#f39c12', 'Premium': '#e74c3c'}

# --- Scatter: retail_price vs margin_pct ---
for tier, grp in df.groupby('price_tier'):
    axes[0].scatter(grp['retail_price'], grp['margin_pct'],
                    c=colors[tier], alpha=0.3, s=15, label=tier)
axes[0].set_xlabel('Retail Price ($)')
axes[0].set_ylabel('Profit Margin (%)')
axes[0].set_title('Product Clusters: Price vs Margin', fontweight='bold')
axes[0].legend()

# --- Bar: Top categories per tier ---
cat_tier = df.groupby(['price_tier', 'category'])['product_id'].count().reset_index()
cat_tier.columns = ['price_tier', 'category', 'count']

tier_order = ['Budget', 'Mid-range', 'Premium']
x = np.arange(len(tier_order))
width = 0.6
bottom = np.zeros(len(tier_order))

# Stacked bar — top 5 categories
top_cats = cat_tier.groupby('category')['count'].sum().nlargest(8).index
for cat in top_cats:
    vals = [cat_tier[(cat_tier['price_tier']==t) & (cat_tier['category']==cat)]['count'].sum()
            for t in tier_order]
    axes[1].bar(tier_order, vals, bottom=bottom, label=cat, width=width)
    bottom += np.array(vals)

axes[1].set_title('Product Count by Tier & Category', fontweight='bold')
axes[1].set_ylabel('Number of Products')
axes[1].legend(loc='upper right', fontsize=7, ncol=2)

plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, '01_product_tiers.png'), dpi=150, bbox_inches='tight')
plt.show()
print("Saved: 01_product_tiers.png")

# %% [markdown]
# ## Bước 4: Xuất nhãn cho Lớp 2

# %%
out_path = os.path.join(SAVE_DIR, 'product_tiers.csv')
df[['product_id', 'category', 'department', 'retail_price', 'margin_pct', 'price_tier']].to_csv(
    out_path, index=False)
print(f"\nSaved {len(df):,} product labels to: {out_path}")
print(df['price_tier'].value_counts())
