# %% [markdown]
# # LỚP 2: PHÂN LOẠI SẢN PHẨM THEO PHÂN KHÚC GIÁ (Classification)
#
# **Câu hỏi kinh doanh:**
# Chỉ dựa vào TYPE của sản phẩm (category, department) và
# mức độ PHỔ BIẾN (num_sold), có thể xác định sản phẩm thuộc
# phân khúc Budget / Mid / Premium không?
#
# **SQL đã xác nhận (survey_product_verify.py):**
# - Suits/Women: median $122 → Premium (confirmed)
# - Socks Men: median $15 → Budget (confirmed)
# - Spread: $14 → $122 → clear 3-tier structure
# → Category + Department LÀ predictors của price tier
#
# **Thiết kế chống Data Leakage:**
# - Target: price_tier từ Lớp 1 (dựa trên retail_price + cost + margin)
# - Features: KHÔNG dùng retail_price, cost, margin_pct (đây là leakage)
# - Chỉ dùng: category (what type?), department (Men/Women?), num_sold (how popular?)
# - Model học: "Blazers + Women → likely Premium" từ DATA, không phải từ price
#
# **Kỳ vọng:** AUC 0.80+ (category là predictor mạnh đã xác nhận bằng SQL)
#
# **Yêu cầu:** Chạy 01_Product_Clustering.py trước để có product_tiers.csv

# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
import os, sys
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import label_binarize
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(__file__))
from database import query_db

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

# %% [markdown]
# ## Bước 1: Load nhãn tier + Truy vấn features

# %%
tiers_path = os.path.join(SAVE_DIR, 'product_tiers.csv')
if not os.path.exists(tiers_path):
    raise FileNotFoundError("Chay 01_Product_Clustering.py truoc!")

df_tiers = pd.read_csv(tiers_path)
print(f"Tiers loaded: {len(df_tiers):,} products")
print(df_tiers['price_tier'].value_counts())

# Truy vấn num_sold per product từ order_items
query_sold = """
SELECT product_id, COUNT(*) AS num_sold
FROM order_items
WHERE status != 'Cancelled'
GROUP BY product_id
"""
print("\nQuerying sales volume per product...")
df_sold = query_db(query_sold)
print(f"Products with sales: {len(df_sold):,}")

# Merge
df = pd.merge(df_tiers, df_sold, on='product_id', how='left')
df['num_sold'] = df['num_sold'].fillna(0)
print(f"\nAfter merge: {len(df):,} products")
print(df[['num_sold', 'price_tier']].groupby('price_tier')['num_sold'].mean().round(2))

# %% [markdown]
# ## Bước 2: Feature engineering
#
# Features: category_enc, department_enc, num_sold
# KHÔNG dùng retail_price / cost / margin_pct → tránh leakage
# (Target price_tier được define TỪ retail_price/cost)

# %%
le_cat = LabelEncoder()
le_dep = LabelEncoder()
df['category_enc'] = le_cat.fit_transform(df['category'].astype(str))
df['department_enc'] = le_dep.fit_transform(df['department'].astype(str))

FEATURE_COLS = ['category_enc', 'department_enc', 'num_sold']
X = df[FEATURE_COLS]
y = df['price_tier']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

print(f"\nTrain: {len(X_train):,} | Test: {len(X_test):,}")
print(f"Features: {FEATURE_COLS}")

# %% [markdown]
# ## Bước 3: Huấn luyện Decision Tree + Random Forest

# %%
dt = DecisionTreeClassifier(max_depth=6, min_samples_leaf=50,
                             random_state=42)
dt.fit(X_train, y_train)

rf = RandomForestClassifier(n_estimators=200, max_depth=10,
                             random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)
print("Training complete.")

# %% [markdown]
# ## Bước 4: Đánh giá

# %%
classes = ['Budget', 'Mid-range', 'Premium']

# AUC (one-vs-rest cho multi-class)
y_test_bin = label_binarize(y_test, classes=classes)
rf_proba = rf.predict_proba(X_test)
dt_proba = dt.predict_proba(X_test)

# Align proba columns to classes order
rf_proba_aligned = np.column_stack([
    rf_proba[:, list(rf.classes_).index(c)] for c in classes])
dt_proba_aligned = np.column_stack([
    dt_proba[:, list(dt.classes_).index(c)] for c in classes])

rf_auc = roc_auc_score(y_test_bin, rf_proba_aligned, multi_class='ovr', average='macro')
dt_auc = roc_auc_score(y_test_bin, dt_proba_aligned, multi_class='ovr', average='macro')

print(f"\nDecision Tree AUC (macro OvR): {dt_auc:.4f}")
print(f"Random Forest AUC (macro OvR): {rf_auc:.4f}")
print(f"Target range: 0.70 - 0.95 → {'PASS' if 0.70 < rf_auc else 'REVIEW'}")

y_pred = rf.predict(X_test)
print("\n=== Random Forest Classification Report ===")
print(classification_report(y_test, y_pred, target_names=classes))

# %% [markdown]
# ## Bước 5: Trực quan hóa

# %%
fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# --- Feature Importance ---
importances = pd.Series(rf.feature_importances_, index=FEATURE_COLS).sort_values()
nice_names = {
    'category_enc': 'Product Category (26 types)',
    'department_enc': 'Department (Men / Women)',
    'num_sold': 'Sales Volume'
}
importances.index = [nice_names[i] for i in importances.index]
importances.plot(kind='barh', ax=axes[0],
                 color=['#3498db', '#f39c12', '#e74c3c'])
axes[0].set_title('Feature Importance — Price Tier Prediction\n(Random Forest)',
                   fontweight='bold')
axes[0].set_xlabel('Importance Score')
for i, v in enumerate(importances):
    axes[0].text(v + 0.002, i, f'{v:.3f}', va='center')

# --- Prediction accuracy per tier ---
from sklearn.metrics import confusion_matrix
cm = confusion_matrix(y_test, y_pred, labels=classes)
im = axes[1].imshow(cm, cmap='Blues')
plt.colorbar(im, ax=axes[1])
for i in range(len(classes)):
    for j in range(len(classes)):
        axes[1].text(j, i, str(cm[i, j]), ha='center', va='center',
                     fontsize=12, fontweight='bold',
                     color='white' if cm[i, j] > cm.max()/2 else 'black')
axes[1].set_xticks(range(len(classes)))
axes[1].set_yticks(range(len(classes)))
axes[1].set_xticklabels(classes)
axes[1].set_yticklabels(classes)
axes[1].set_xlabel('Predicted Tier')
axes[1].set_ylabel('Actual Tier')
axes[1].set_title('Confusion Matrix — Product Price Tier\n(Random Forest)',
                   fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, '02_classification_results.png'), dpi=150, bbox_inches='tight')
plt.show()

# %% [markdown]
# ## Bước 6: Decision Tree Visualization

# %%
feature_names_nice = [nice_names[c] for c in FEATURE_COLS]
plt.figure(figsize=(22, 10))
plot_tree(dt, feature_names=feature_names_nice, class_names=classes,
          filled=True, rounded=True, fontsize=9, precision=2)
plt.title('Decision Tree: Product Price Tier Classification\n'
          '"What makes a product Budget vs Premium?"',
          fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, '02_decision_tree.png'), dpi=120, bbox_inches='tight')
plt.show()
print("Saved: 02_decision_tree.png")
print(f"\nTop split feature in Decision Tree: {feature_names_nice[dt.tree_.feature[0]]}")
