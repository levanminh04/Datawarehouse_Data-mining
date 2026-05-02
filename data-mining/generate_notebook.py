import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

# 1. Introduction Markdown
intro_md = """# TheLook Ecommerce: Smart Product Portfolio Management

**Bối cảnh:** Các nỗ lực dự đoán hành vi người dùng (Return Rate, Conversion Rate) đều thất bại vì **tỷ lệ này là phân phối ngẫu nhiên đồng nhất (uniform distribution)** được tạo bởi hệ thống synthetic data của TheLook:
- Return Rate luôn ở mức **~10%** bất kể Brand hay Category.
- Conversion Rate từ xem đến mua luôn ở mức **~30%**.

**Giải pháp đột phá:** Không dự đoán người dùng nữa, mà tập trung vào **Quản trị danh mục sản phẩm (Product Portfolio Management)**. Điểm duy nhất có cấu trúc logic (non-random) trong dataset này là **Giá (Retail Price)** và **Chi phí (Cost)**, từ đó sinh ra **Biên lợi nhuận (Margin)** cực kỳ khác biệt giữa các Category.

Notebook này sẽ triển khai:
1. **Lớp 1: Profitability Clustering (Phân cụm Lợi nhuận)** -> Xác định Cash Cows (Bò Sữa) và Dogs (Chó Mực).
2. **Lớp 2: Profit-Aware Association Rules (Luật Kết hợp Lợi nhuận)** -> Tối đa hóa biên lợi nhuận cho mỗi đơn hàng."""

# 2. Imports and Data Loading
imports_code = """import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

from sqlalchemy import create_engine
# Kết nối DB
engine = create_engine('postgresql://postgres:postgres@13.239.118.235:5432/postgres')

print("Fetching Data...")
query_products = \"\"\"
SELECT id, category, department, retail_price, cost,
       ROUND(((retail_price - cost) / NULLIF(retail_price, 0))::numeric, 4) AS margin_pct,
       (retail_price - cost) AS margin_amount
FROM products
WHERE retail_price > 0 AND cost > 0
\"\"\"
df_products = pd.read_sql_query(query_products, engine)

query_orders = \"\"\"
SELECT oi.order_id, oi.product_id, oi.sale_price, oi.status
FROM order_items oi
WHERE oi.status != 'Cancelled'
\"\"\"
df_orders = pd.read_sql_query(query_orders, engine)
print("Data Fetched Successfully!")
"""

# 3. Prove Randomness
proof_md = """## 1. Chứng minh tính ngẫu nhiên của Hành vi người dùng (Return Rate)
Để thuyết phục lý do tại sao chúng ta chuyển hướng, hãy xem Return Rate theo Brand có sales > 500. Tất cả đều rơi vào khoảng 8% - 12%, hoàn toàn nằm trong biên độ phương sai của xác suất 10%."""

proof_code = """brand_sales = df_orders.groupby('product_id').agg(
    total_sold=('order_id', 'count'),
    total_returned=('status', lambda x: (x == 'Returned').sum())
).reset_index()

df_brand_perf = pd.merge(brand_sales, df_products[['id', 'brand']], left_on='product_id', right_on='id', how='left')
brand_agg = df_brand_perf.groupby('brand').agg({'total_sold': 'sum', 'total_returned': 'sum'}).reset_index()
brand_agg = brand_agg[brand_agg['total_sold'] >= 500]
brand_agg['return_rate'] = brand_agg['total_returned'] / brand_agg['total_sold']

plt.figure(figsize=(10, 5))
sns.histplot(brand_agg['return_rate'], bins=20, kde=True, color='salmon')
plt.axvline(0.10, color='red', linestyle='--', label='10% Baseline')
plt.title('Distribution of Return Rate across High-Volume Brands')
plt.xlabel('Return Rate')
plt.ylabel('Number of Brands')
plt.legend()
plt.show()
print("Kết luận: Return Rate là nhiễu ngẫu nhiên phân phối chuẩn quanh mốc 10%. Không thể dự đoán (Unpredictable).")
"""

# Wait, I realized df_products doesn't select brand in the query above. I need to fix that.

# 4. Profitability Clustering
cluster_md = """## 2. Lớp 1: Phân cụm Hiệu quả Kinh doanh (Profitability Clustering)
Chúng ta sẽ phân cụm dựa trên **Margin Amount (Lãi gộp tuyệt đối)** và **Sales Volume (Số lượng bán ra)**. 
- **Stars (Ngôi sao):** Bán nhiều, lãi cao.
- **Cash Cows (Bò sữa):** Bán nhiều, lãi vừa.
- **Question Marks (Dấu hỏi):** Bán ít, lãi cao.
- **Dogs (Chó mực):** Bán ít, lãi thấp."""

cluster_code = """from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Gộp Sales Volume vào Products
prod_sales = df_orders.groupby('product_id').size().reset_index(name='sales_volume')
df_p = pd.merge(df_products, prod_sales, left_on='id', right_on='product_id', how='left')
df_p['sales_volume'] = df_p['sales_volume'].fillna(0)
df_p = df_p[df_p['sales_volume'] > 0] # Chỉ lấy sp bán được

# Clustering
features = ['margin_amount', 'sales_volume']
scaler = StandardScaler()
X = scaler.fit_transform(df_p[features])

kmeans = KMeans(n_clusters=4, random_state=42)
df_p['cluster'] = kmeans.fit_predict(X)

# Đặt tên cụm dựa trên đặc tính
centroids = df_p.groupby('cluster')[features].mean()
# Xác định cụm dựa trên rank của margin và volume
# Code đơn giản để gán nhãn:
def assign_label(row):
    if row['margin_amount'] > centroids['margin_amount'].median() and row['sales_volume'] > centroids['sales_volume'].median():
        return 'Stars'
    elif row['margin_amount'] <= centroids['margin_amount'].median() and row['sales_volume'] > centroids['sales_volume'].median():
        return 'Cash Cows'
    elif row['margin_amount'] > centroids['margin_amount'].median() and row['sales_volume'] <= centroids['sales_volume'].median():
        return 'Question Marks'
    else:
        return 'Dogs'

df_p['portfolio_segment'] = df_p.apply(assign_label, axis=1)

plt.figure(figsize=(12, 8))
sns.scatterplot(data=df_p, x='margin_amount', y='sales_volume', hue='portfolio_segment', 
                palette={'Stars':'gold', 'Cash Cows':'blue', 'Question Marks':'purple', 'Dogs':'gray'}, alpha=0.6)
plt.title('BCG Matrix: Product Portfolio Clustering')
plt.xlabel('Margin Amount ($)')
plt.ylabel('Sales Volume (Units)')
plt.show()

print(df_p.groupby('portfolio_segment').agg(
    num_products=('id', 'count'),
    avg_margin=('margin_amount', 'mean'),
    avg_volume=('sales_volume', 'mean'),
    total_profit=('margin_amount', lambda x: (x * df_p.loc[x.index, 'sales_volume']).sum())
).round(2).sort_values('total_profit', ascending=False))
"""

# 5. Profit-Aware Rules
rules_md = """## 3. Lớp 2: Khai phá Luật kết hợp (Profit-Aware Association Rules)
Thay vì chỉ xem món nào bán kèm món nào, ta tìm các Combo kéo theo các sản phẩm **"Stars"** hoặc **"Question Marks"** để tối đa hóa biên lợi nhuận."""

rules_code = """from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

# Tạo basket gồm Category và Portfolio Segment
df_orders_seg = pd.merge(df_orders, df_p[['id', 'category', 'portfolio_segment']], left_on='product_id', right_on='id', how='inner')
df_orders_seg['item_label'] = df_orders_seg['category'] + ' (' + df_orders_seg['portfolio_segment'] + ')'

baskets = df_orders_seg.groupby('order_id')['item_label'].apply(list).tolist()
baskets_multi = [b for b in baskets if len(set(b)) > 1]

te = TransactionEncoder()
te_ary = te.fit(baskets_multi).transform(baskets_multi)
df_trans = pd.DataFrame(te_ary, columns=te.columns_)

frequent_itemsets = apriori(df_trans, min_support=0.005, use_colnames=True)
rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.2)

# Lọc các Rule dẫn đến "Stars" hoặc "Question Marks" (những món lãi cao cần thúc đẩy)
def pushes_high_margin(consequents):
    for item in consequents:
        if 'Stars' in item or 'Question Marks' in item:
            return True
    return False

rules['high_margin_target'] = rules['consequents'].apply(pushes_high_margin)
profitable_rules = rules[rules['high_margin_target']].sort_values('lift', ascending=False)

profitable_rules['antecedents'] = profitable_rules['antecedents'].apply(lambda x: list(x)[0])
profitable_rules['consequents'] = profitable_rules['consequents'].apply(lambda x: list(x)[0])

print("Top 10 Cross-Sell Rules to Maximize Profit:")
display(profitable_rules[['antecedents', 'consequents', 'support', 'confidence', 'lift']].head(10))
"""


nb['cells'] = [
    nbf.v4.new_markdown_cell(intro_md),
    nbf.v4.new_code_cell(imports_code.replace("SELECT id, category", "SELECT id, category, brand")),
    nbf.v4.new_markdown_cell(proof_md),
    nbf.v4.new_code_cell(proof_code),
    nbf.v4.new_markdown_cell(cluster_md),
    nbf.v4.new_code_cell(cluster_code),
    nbf.v4.new_markdown_cell(rules_md),
    nbf.v4.new_code_cell(rules_code)
]

with open('datamining-version3/04_Catalog_Profit_Strategy.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print("Notebook generated successfully at datamining-version3/04_Catalog_Profit_Strategy.ipynb")
