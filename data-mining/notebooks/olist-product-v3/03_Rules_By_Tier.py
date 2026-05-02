# %% [markdown]
# # LỚP 3: LUẬT KẾT HỢP THEO PHÂN KHÚC GIÁ (Association Rules by Price Tier)
#
# **Câu hỏi kinh doanh:**
# Khách hàng mua sản phẩm Premium thường mua kèm category nào?
# Có khác với khách hàng mua Budget không?
# → Giúp gợi ý cross-selling theo phân khúc giá của đơn hàng
#
# **SQL đã xác nhận (survey_fresh_directions.py A6):**
# - 30% đơn hàng có 2+ brands = 29,651 đơn multi-product
# - 28.6% đơn hàng có 2+ categories = đủ để mine rules
#
# **Thiết kế:**
# - Basket = categories trong 1 order_id (không đổi so với Lớp 3 cũ)
# - Stratify: Nhóm orders theo price_tier trội nhất trong đơn
#   (majority-tier: tier của category chiếm nhiều nhất trong đơn)
# - Mine rules riêng cho Budget / Mid-range / Premium orders
# → So sánh cross-sell pattern giữa các phân khúc
#
# **Yêu cầu:** Chạy 01_Product_Clustering.py trước để có product_tiers.csv

# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
import os, sys
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(__file__))
from database import query_db

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

# %% [markdown]
# ## Bước 1: Load product tiers + Truy vấn orders

# %%
tiers_path = os.path.join(SAVE_DIR, 'product_tiers.csv')
if not os.path.exists(tiers_path):
    raise FileNotFoundError("Chay 01_Product_Clustering.py truoc!")

df_tiers = pd.read_csv(tiers_path)[['product_id', 'price_tier', 'category']]
tier_lookup = df_tiers.set_index('product_id')['price_tier'].to_dict()
cat_lookup  = df_tiers.set_index('product_id')['category'].to_dict()

query = """
SELECT oi.order_id, oi.product_id
FROM order_items oi
WHERE oi.status != 'Cancelled'
"""
print("Querying orders...")
df_orders = query_db(query)
print(f"Loaded {len(df_orders):,} order-item rows")

# Map tier và category từ product_tiers.csv (local join, không query DB)
df_orders['price_tier'] = df_orders['product_id'].map(tier_lookup)
df_orders['category']   = df_orders['product_id'].map(cat_lookup)
df_orders = df_orders.dropna(subset=['price_tier', 'category'])
print(f"After mapping: {len(df_orders):,} rows ({df_orders['price_tier'].value_counts().to_dict()})")

# %% [markdown]
# ## Bước 2: Xác định tier trội nhất của mỗi đơn hàng
# Majority tier = tier xuất hiện nhiều nhất trong 1 order

# %%
order_majority_tier = (
    df_orders.groupby(['order_id', 'price_tier'])
    .size()
    .reset_index(name='cnt')
    .sort_values('cnt', ascending=False)
    .drop_duplicates('order_id')
    [['order_id', 'price_tier']]
)
order_majority_tier.columns = ['order_id', 'majority_tier']

df_orders = pd.merge(df_orders, order_majority_tier, on='order_id')
print("\nOrders per majority tier:")
print(order_majority_tier['majority_tier'].value_counts())

# %% [markdown]
# ## Bước 3: Mine Association Rules per tier

# %%
def mine_tier(df_subset, tier_name, min_support=0.01):
    baskets = (df_subset.groupby('order_id')['category']
               .apply(lambda x: list(set(x))).reset_index())
    transactions = [t for t in baskets['category'].tolist() if len(t) > 1]
    total = len(baskets)
    print(f"\n[{tier_name}] Multi-category orders: {len(transactions):,} / {total:,} "
          f"({100*len(transactions)/total:.1f}%)")
    if len(transactions) < 50:
        print(f"  Too few, skipping.")
        return None

    te = TransactionEncoder()
    te_arr = te.fit(transactions).transform(transactions)
    basket_df = pd.DataFrame(te_arr, columns=te.columns_)

    freq = apriori(basket_df, min_support=min_support, use_colnames=True)
    if freq.empty:
        print(f"  No frequent itemsets at min_support={min_support}")
        return None

    rules = association_rules(freq, metric='lift', min_threshold=1.0)
    rules['tier'] = tier_name
    rules['antecedents_str'] = rules['antecedents'].apply(lambda x: ' + '.join(sorted(x)))
    rules['consequents_str'] = rules['consequents'].apply(lambda x: ' + '.join(sorted(x)))
    print(f"  Rules found: {len(rules)} (Lift > 1.0)")
    return rules

rules_budget  = mine_tier(df_orders[df_orders['majority_tier']=='Budget'],    'Budget',    min_support=0.015)
rules_mid     = mine_tier(df_orders[df_orders['majority_tier']=='Mid-range'],  'Mid-range', min_support=0.015)
rules_premium = mine_tier(df_orders[df_orders['majority_tier']=='Premium'],    'Premium',   min_support=0.015)

all_rules = pd.concat(
    [r for r in [rules_budget, rules_mid, rules_premium] if r is not None],
    ignore_index=True
).sort_values(['tier', 'lift'], ascending=[True, False])

print(f"\nTotal rules: {len(all_rules)}")
display_cols = ['tier', 'antecedents_str', 'consequents_str', 'support', 'confidence', 'lift']
print("\nTop 5 rules per tier:")
print(all_rules.groupby('tier').head(5)[display_cols].to_string(index=False))

# %% [markdown]
# ## Bước 4: Trực quan hóa — so sánh rules giữa các tiers

# %%
fig, axes = plt.subplots(1, 3, figsize=(21, 7))
tier_colors = {'Budget': '#3498db', 'Mid-range': '#f39c12', 'Premium': '#e74c3c'}

for ax, (tier, color) in zip(axes, tier_colors.items()):
    sub = all_rules[all_rules['tier'] == tier]
    if sub.empty:
        ax.text(0.5, 0.5, 'No rules', ha='center', va='center',
                transform=ax.transAxes, fontsize=14)
        ax.set_title(f'{tier} Tier', fontweight='bold')
        continue

    top = sub.head(10).sort_values('lift')
    top['rule'] = top['antecedents_str'] + '\n→ ' + top['consequents_str']
    bars = ax.barh(range(len(top)), top['lift'], color=color, alpha=0.85)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top['rule'], fontsize=7)
    ax.set_xlabel('Lift')
    ax.set_title(f'{tier} Tier — Top Rules\n(Lift > 1.0 = non-random co-purchase)',
                 fontweight='bold', color=color)
    ax.axvline(1.0, color='black', linestyle='--', lw=1)
    # Annotate lift values
    for bar, lift_val in zip(bars, top['lift']):
        ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
                f'{lift_val:.2f}', va='center', fontsize=7)

plt.suptitle('Category Co-Purchase Rules by Product Price Tier\n'
             'Do Budget vs Premium shoppers buy different combinations?',
             fontsize=12, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, '03_rules_by_tier.png'), dpi=150, bbox_inches='tight')
plt.show()
print("Saved: 03_rules_by_tier.png")

# %% [markdown]
# ## Bước 5: Business Insights

# %%
print("\n" + "="*65)
print("  BUSINESS INSIGHTS: Cross-Sell Rules by Price Segment")
print("="*65)
for tier in ['Budget', 'Mid-range', 'Premium']:
    sub = all_rules[all_rules['tier'] == tier].head(3)
    print(f"\n  [{tier.upper()} SEGMENT] Top cross-sell rules:")
    if sub.empty:
        print("    No rules found.")
        continue
    for _, row in sub.iterrows():
        print(f"    {row['antecedents_str']}  →  {row['consequents_str']}")
        print(f"    Lift={row['lift']:.3f} | Conf={row['confidence']:.3f} | Sup={row['support']:.3f}")
