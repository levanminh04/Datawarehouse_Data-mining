# %% [markdown]
# # Lớp 3: Dự đoán Khách hàng quay lại (Next-Week Purchase Prediction)
# Mục tiêu: Dự đoán xem một khách hàng có mua hàng trong 7 ngày tới hay không.
# Thuật toán: Decision Tree (để giải thích logic) và Random Forest (để đạt độ chính xác cao).
# Chiến lược chống OOM & Data Leakage: 
# - Lấy Cut-off date là 7 ngày cuối cùng của dataset.
# - Dùng dữ liệu TRƯỚC cut-off để tính Features (RFM + Style DNA).
# - Dùng dữ liệu TRONG 7 ngày cuối làm Target (Label 1/0).
# - Lấy mẫu 300,000 khách hàng để huấn luyện.

# %%
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..', 'datamining-version3')))
from database import query_db

# %% [markdown]
# ## 1. Truy vấn Features (Dữ liệu trước Cut-off)
# Tính RFM (Recency, Frequency, Monetary) và Style DNA của khách hàng trước ngày Cut-off.
# Dataset có giao dịch cuối cùng là 2020-09-22. Vậy Cut-off = 2020-09-15.

# %%
query_features = """
WITH cutoff AS (
    SELECT MAX(t_dat::date) - INTERVAL '7 days' AS dt FROM transactions
)
SELECT 
    t.customer_id,
    EXTRACT(DAY FROM (SELECT dt FROM cutoff) - MAX(t.t_dat::date)) AS recency_days,
    COUNT(*) AS frequency,
    SUM(t.price) AS monetary,
    AVG(t.price) AS avg_price,
    SUM(CASE WHEN a.index_group_name = 'Ladieswear' THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_ladieswear,
    SUM(CASE WHEN a.index_group_name = 'Divided' THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_divided,
    SUM(CASE WHEN a.index_group_name = 'Menswear' THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_menswear,
    SUM(CASE WHEN a.index_group_name = 'Baby/Children' THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_baby,
    SUM(CASE WHEN t.sales_channel_id = 2 THEN 1 ELSE 0 END)::float / COUNT(*) AS pct_online
FROM transactions t
JOIN articles a ON t.article_id = a.article_id
WHERE t.t_dat::date < (SELECT dt FROM cutoff)
GROUP BY t.customer_id;
"""

print("Đang truy vấn Features (RFM & Style) từ Database (Dữ liệu trước cut-off)...")
df_features = query_db(query_features)
print(f"Hoàn thành! Số khách hàng: {len(df_features)}")

# %% [markdown]
# ## 2. Truy vấn Target (Dữ liệu trong 7 ngày cuối)

# %%
query_target = """
WITH cutoff AS (
    SELECT MAX(t_dat::date) - INTERVAL '7 days' AS dt FROM transactions
)
SELECT DISTINCT customer_id, 1 AS will_buy
FROM transactions
WHERE t_dat::date >= (SELECT dt FROM cutoff);
"""

print("Đang truy vấn Labels (Khách có mua trong 7 ngày cuối)...")
df_target = query_db(query_target)
print(f"Hoàn thành! Số khách hàng mua trong 7 ngày cuối: {len(df_target)}")

# %% [markdown]
# ## 3. Gộp và Xử lý Dữ liệu

# %%
# Gộp Features và Target
df_model = df_features.merge(df_target, on='customer_id', how='left')

# Những người không có trong df_target nghĩa là không mua -> Label = 0
df_model['will_buy'] = df_model['will_buy'].fillna(0).astype(int)

print("\n=== Phân phối Target (Label) ===")
print(df_model['will_buy'].value_counts(normalize=True) * 100)

# Lấy mẫu ngẫu nhiên 300,000 dòng để tránh OOM khi train model (có phân tầng theo target)
if len(df_model) > 300000:
    df_sample = df_model.sample(n=300000, random_state=42)
else:
    df_sample = df_model.copy()

# Xóa các dòng có giá trị NULL do chia cho 0 hoặc lỗi tính toán
df_sample = df_sample.dropna()

features_cols = [
    'recency_days', 'frequency', 'monetary', 'avg_price', 
    'pct_ladieswear', 'pct_divided', 'pct_menswear', 'pct_baby', 'pct_online'
]

X = df_sample[features_cols]
y = df_sample['will_buy']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"\nDữ liệu huấn luyện: {X_train.shape}, Dữ liệu test: {X_test.shape}")

# %% [markdown]
# ## 4. Huấn luyện Mô hình Decision Tree (Dễ giải thích)

# %%
print("\n[1] Đang huấn luyện Decision Tree...")
# Giới hạn độ sâu = 4 để cây dễ hiểu, có thể vẽ vào báo cáo
dt_model = DecisionTreeClassifier(max_depth=4, class_weight='balanced', random_state=42)
dt_model.fit(X_train, y_train)

dt_preds = dt_model.predict(X_test)
dt_probs = dt_model.predict_proba(X_test)[:, 1]
dt_auc = roc_auc_score(y_test, dt_probs)

print(f"Decision Tree AUC: {dt_auc:.4f}")

# Vẽ và lưu cây quyết định
plt.figure(figsize=(25, 10))
plot_tree(dt_model, feature_names=features_cols, class_names=['No Buy', 'Buy'], filled=True, rounded=True, fontsize=10)
plt.title("Logic Dự báo Mua hàng (Decision Tree - Max Depth 4)")
plt.savefig('decision_tree_logic.png', dpi=300, bbox_inches='tight')
print("Đã lưu hình cây quyết định: decision_tree_logic.png")

# %% [markdown]
# ## 5. Huấn luyện Mô hình Random Forest (Độ chính xác cao)

# %%
print("\n[2] Đang huấn luyện Random Forest...")
# Dùng max_samples=0.4 để giảm thiểu RAM, max_depth=8 để chống overfitting
rf_model = RandomForestClassifier(
    n_estimators=100, 
    max_depth=8, 
    max_samples=0.4, 
    class_weight='balanced', 
    random_state=42,
    n_jobs=-1 # Dùng đa luồng
)
rf_model.fit(X_train, y_train)

rf_preds = rf_model.predict(X_test)
rf_probs = rf_model.predict_proba(X_test)[:, 1]
rf_auc = roc_auc_score(y_test, rf_probs)

print(f"Random Forest AUC: {rf_auc:.4f}")
print("\nBáo cáo Phân loại (Random Forest):")
print(classification_report(y_test, rf_preds))

# %% [markdown]
# ## 6. Trực quan hóa Mức độ Quan trọng của Features

# %%
feature_importance = pd.DataFrame({
    'Feature': features_cols,
    'Importance': rf_model.feature_importances_
}).sort_values('Importance', ascending=False)

print("\n=== MỨC ĐỘ QUAN TRỌNG CỦA CÁC ĐẶC TRƯNG ===")
print(feature_importance.to_string(index=False))

plt.figure(figsize=(10, 6))
sns.barplot(x='Importance', y='Feature', data=feature_importance, palette='viridis')
plt.title('Những Yếu Tố Quyết Định Việc Mua Hàng Tuần Tới (Random Forest)')
plt.tight_layout()
plt.savefig('feature_importance.png')
print("Đã lưu biểu đồ: feature_importance.png")

print("\n=== GIAI ĐOẠN 3 HOÀN TẤT ===")
