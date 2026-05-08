# %% [markdown]
# # Lớp 2: Khai phá Luật phối đồ (Fashion Combo Mining bằng Apriori)
# Mục tiêu: Tìm quy luật khách hàng thường mua kết hợp những loại trang phục nào trong cùng 1 lần mua sắm.
# Điểm đặc biệt: Chạy luật kết hợp RIÊNG cho từng cụm khách hàng (từ Lớp 1) để tìm ra sự khác biệt phong cách.
# Chiến lược chống OOM: Dùng `product_group_name` (19 loại) thay vì `article_id` (105k mã). Gom nhóm Basket trực tiếp bằng SQL.

# %%
import os
import sys
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..', 'datamining-version3')))
from database import query_db

# %% [markdown]
# ## 1. Lấy dữ liệu Giỏ hàng (Baskets) từ PostgreSQL
# Một giỏ hàng = Tất cả các loại sản phẩm (product_group_name) được MỘT khách hàng mua trong MỘT ngày.
# Chỉ lấy những giỏ hàng có từ 2 sản phẩm KHÁC NHAU trở lên.

# %%
query_baskets = """
SELECT 
    t.customer_id,
    t.t_dat::date AS purchase_date,
    ARRAY_AGG(DISTINCT a.product_group_name) AS basket
FROM transactions t
JOIN articles a ON t.article_id = a.article_id
GROUP BY t.customer_id, t.t_dat::date
HAVING COUNT(DISTINCT a.product_group_name) >= 2;
"""

print("Đang tạo Baskets từ Database (Chạy trên 31 triệu giao dịch, có thể mất 3-5 phút)...")
df_baskets = query_db(query_baskets)
print(f"Hoàn thành! Có tổng cộng {len(df_baskets)} giỏ hàng hợp lệ.")

# Chuyển string representation của array (nếu có) thành list Python thực sự
import ast
def parse_basket(val):
    if isinstance(val, str):
        val = val.replace('{', '[').replace('}', ']')
        try:
            return ast.literal_eval(val)
        except:
            return []
    return val

df_baskets['basket'] = df_baskets['basket'].apply(parse_basket)

# Đọc kết quả phân cụm từ Lớp 1
cluster_file = os.path.join(os.getcwd(), 'customer_clusters.csv')
if os.path.exists(cluster_file):
    df_clusters = pd.read_csv(cluster_file)
    # Merge baskets với cluster
    df_baskets = df_baskets.merge(df_clusters[['customer_id', 'cluster_name']], on='customer_id', how='inner')
    print(f"Đã merge với Lớp 1. Số giỏ hàng thuộc các KH đã phân cụm: {len(df_baskets)}")
else:
    print("Không tìm thấy file customer_clusters.csv, sẽ chỉ chạy Global Rules.")
    df_baskets['cluster_name'] = 'All'

# %% [markdown]
# ## 2. Hàm chạy Apriori và xuất luật
# Chúng ta dùng min_support = 0.005 (0.5% số giỏ hàng) và min_lift = 1.2 (sức mạnh kết hợp > 1.2).

# %%
def mine_association_rules(baskets_series, min_support=0.005, min_lift=1.2, top_n=5):
    if len(baskets_series) < 100:
        return pd.DataFrame()
        
    te = TransactionEncoder()
    te_ary = te.fit(baskets_series).transform(baskets_series)
    df_te = pd.DataFrame(te_ary, columns=te.columns_)
    
    # Tìm tập phổ biến (Frequent Itemsets)
    frequent_itemsets = apriori(df_te, min_support=min_support, use_colnames=True)
    if frequent_itemsets.empty:
        return pd.DataFrame()
        
    # Tạo luật kết hợp (Association Rules)
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
    
    # Làm đẹp kết quả
    rules['antecedents'] = rules['antecedents'].apply(lambda x: ', '.join(list(x)))
    rules['consequents'] = rules['consequents'].apply(lambda x: ', '.join(list(x)))
    
    # Sắp xếp theo độ tự tin (Confidence) và sức mạnh (Lift)
    rules = rules.sort_values(['lift', 'confidence'], ascending=[False, False])
    
    return rules[['antecedents', 'consequents', 'support', 'confidence', 'lift']].head(top_n)

# %% [markdown]
# ## 3. Chạy Luật kết hợp cho TỪNG CỤM Khách hàng
# Khám phá sự khác biệt trong gu phối đồ giữa các cụm.

# %%
results_list = []

# Lặp qua từng nhóm phong cách
for cluster in df_baskets['cluster_name'].unique():
    print(f"\n[{cluster}] Đang phân tích Market Basket...")
    cluster_baskets = df_baskets[df_baskets['cluster_name'] == cluster]['basket']
    
    rules = mine_association_rules(cluster_baskets, min_support=0.01, min_lift=1.2, top_n=5)
    
    if not rules.empty:
        rules.insert(0, 'Style_Cluster', cluster)
        results_list.append(rules)
        print(rules.to_string(index=False))
    else:
        print("Không tìm thấy luật mạnh nào.")

# Gộp tất cả luật lại
if results_list:
    df_all_rules = pd.concat(results_list, ignore_index=True)
    output_rules = 'fashion_association_rules.csv'
    df_all_rules.to_csv(output_rules, index=False)
    print(f"\nĐã xuất toàn bộ luật phối đồ ra file: {output_rules}")

print("\n=== GIAI ĐOẠN 2 HOÀN TẤT ===")
