# %% [markdown]
# # LỚP 3: KHAI PHÁ LUẬT KẾT HỢP (Association Rules)
#
# **Câu hỏi kinh doanh:**
# Khách hàng khi mua Category A thường mua kèm Category nào?
# → Gợi ý cross-selling, không gợi ý combo có tỉ lệ hoàn trả cao.
#
# **SQL đã xác nhận (Survey #9):**
# - 29% đơn hàng có từ 2 categories trở lên (~35,000 đơn)
# - 26 categories trong products
# - Top pair: Jeans + Tops&Tees (633 đơn, support 0.60%)
#
# **Thuật toán:** Apriori với min_support=0.003 (0.3%)
# → đủ thấp để tìm được rules, đủ cao để lọc nhiễu
#
# **Basket:** 1 đơn hàng = 1 transaction, các category trong đơn = items

# %%
import pandas as pd
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
# ## Bước 1: Truy vấn giỏ hàng (category-level baskets)

# %%
query = """
SELECT oi.order_id, p.department, p.category
FROM order_items oi
JOIN products p ON oi.product_id = p.id
WHERE oi.status != 'Cancelled'
"""

print("Querying transaction data...")
df = query_db(query)
print(f"Loaded {len(df):,} order-item rows")

# Business survey Q2: 100% orders are same-department (no Men+Women mix)
# → Mine per-department to avoid trivial cross-category rules driven by popularity bias
# (Intimates dominates Women's side making all Women rules point to Intimates)

# %% [markdown]
# ## Bước 2: Mine riêng Men's và Women's baskets
#
# **Lý do tách:** SQL survey Q2 xác nhận 100% đơn hàng là same-department.
# Mine chung sẽ tạo rules giả (Intimates phổ biến nhất Women → xuất hiện trong mọi rule Women's).
# Mine riêng mới tìm được pattern cross-sell có ý nghĩa thực tế.

# %%
def mine_department(df_dept, dept_name, min_support=0.005):
    """Mine association rules for one department's orders."""
    baskets = (df_dept.groupby('order_id')['category']
               .apply(lambda x: list(set(x))).reset_index())
    transactions = [t for t in baskets['category'].tolist() if len(t) > 1]
    print(f"\n[{dept_name}] Multi-category orders: {len(transactions):,} "
          f"/ {len(baskets):,} ({100*len(transactions)/len(baskets):.1f}%)")
    if len(transactions) < 50:
        print(f"  Too few transactions, skipping.")
        return None

    te = TransactionEncoder()
    te_arr = te.fit(transactions).transform(transactions)
    basket_df = pd.DataFrame(te_arr, columns=te.columns_)

    freq = apriori(basket_df, min_support=min_support, use_colnames=True)
    if freq.empty:
        print(f"  No frequent itemsets at min_support={min_support}")
        return None

    rules = association_rules(freq, metric='lift', min_threshold=1.0)
    rules['department'] = dept_name
    rules['antecedents_str'] = rules['antecedents'].apply(lambda x: ' + '.join(sorted(x)))
    rules['consequents_str'] = rules['consequents'].apply(lambda x: ' + '.join(sorted(x)))
    print(f"  Rules found: {len(rules)} (Lift > 1.0)")
    return rules

rules_men   = mine_department(df[df['department'] == 'Men'],   "Men")
rules_women = mine_department(df[df['department'] == 'Women'], "Women")

# Combine
all_rules = pd.concat([r for r in [rules_men, rules_women] if r is not None], ignore_index=True)
all_rules = all_rules.sort_values(['lift', 'confidence'], ascending=[False, False]).reset_index(drop=True)

print(f"\nTotal rules: {len(all_rules)}")
print("\nTop 15 rules by Lift:")
display_cols = ['department', 'antecedents_str', 'consequents_str', 'support', 'confidence', 'lift']
print(all_rules[display_cols].head(15).to_string(index=False))

rules = all_rules  # alias for visualization below

# %% [markdown]
# ## Bước 5: Trực quan hóa

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# --- Scatter: Support vs Confidence, màu = Department ---
dept_colors = {'Men': '#3498db', 'Women': '#e74c3c'}
for dept, grp in rules.groupby('department'):
    axes[0].scatter(grp['support'], grp['confidence'],
                    c=dept_colors[dept], alpha=0.7, s=80,
                    edgecolors='gray', linewidth=0.3, label=dept)
axes[0].axhline(rules['confidence'].mean(), color='gray', linestyle='--', alpha=0.5)
axes[0].axvline(rules['support'].mean(), color='gray', linestyle='--', alpha=0.5)
axes[0].set_xlabel('Support')
axes[0].set_ylabel('Confidence')
axes[0].set_title('Association Rules by Department\n(Men=Blue, Women=Red)', fontweight='bold')
axes[0].legend(fontsize=10)

# --- Bar: Top 8 per department by Lift ---
top_each = pd.concat([
    rules[rules['department']=='Men'].head(8),
    rules[rules['department']=='Women'].head(8)
]).copy()
top_each['rule'] = '[' + top_each['department'] + '] ' + top_each['antecedents_str'] + ' → ' + top_each['consequents_str']
top_each = top_each.sort_values('lift')
bar_colors = [dept_colors[d] for d in top_each['department']]
axes[1].barh(range(len(top_each)), top_each['lift'], color=bar_colors, alpha=0.85)
axes[1].set_yticks(range(len(top_each)))
axes[1].set_yticklabels(top_each['rule'], fontsize=7)
axes[1].set_xlabel('Lift')
axes[1].set_title('Top Rules by Lift — per Department\n(Blue=Men, Red=Women)', fontweight='bold')
axes[1].axvline(1.0, color='black', linestyle='--', lw=1)

plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, '03_association_rules.png'), dpi=150, bbox_inches='tight')
plt.show()
print("Saved: 03_association_rules.png")

# %% [markdown]
# ## Bước 6: Business Insights

# %%
print("\n=== TOP 5 MEN'S CROSS-SELLING RULES ===")
for _, row in rules[rules['department']=='Men'].head(5).iterrows():
    print(f"  [{row['antecedents_str']}]  →  [{row['consequents_str']}]")
    print(f"    Support={row['support']:.3f} | Confidence={row['confidence']:.3f} | Lift={row['lift']:.3f}")

print("\n=== TOP 5 WOMEN'S CROSS-SELLING RULES ===")
for _, row in rules[rules['department']=='Women'].head(5).iterrows():
    print(f"  [{row['antecedents_str']}]  →  [{row['consequents_str']}]")
    print(f"    Support={row['support']:.3f} | Confidence={row['confidence']:.3f} | Lift={row['lift']:.3f}")
