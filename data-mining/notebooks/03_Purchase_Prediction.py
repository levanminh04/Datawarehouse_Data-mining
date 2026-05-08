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
import joblib
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
    SELECT MAX(t_dat::date) - INTERVAL '7 days' AS dt FROM transactions WHERE t_dat < '2021-01-01'
)
SELECT 
    t.customer_id,
    (SELECT dt FROM cutoff)::date - MAX(t.t_dat::date) AS recency_days,
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
    SELECT MAX(t_dat::date) - INTERVAL '7 days' AS dt FROM transactions WHERE t_dat < '2021-01-01'
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

# Xóa các dòng có giá trị NULL do chia cho 0 hoặc lỗi tính toán trước khi lấy mẫu
df_model = df_model.dropna()

# Lấy mẫu ngẫu nhiên 300,000 dòng để tránh OOM khi train model (có phân tầng theo target)
if len(df_model) > 300000:
    df_sample = df_model.sample(n=300000, random_state=42)
else:
    df_sample = df_model.copy()

features_cols = [
    'recency_days', 'frequency', 'monetary', 'avg_price', 
    'pct_ladieswear', 'pct_divided', 'pct_menswear', 'pct_baby', 'pct_online'
]

X = df_sample[features_cols]
y = df_sample['will_buy']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"\nDữ liệu huấn luyện: {X_train.shape}, Dữ liệu test: {X_test.shape}")

# %% [markdown]
# ## 4. Huấn luyện Các Mô hình (Logistic Regression, Decision Tree, Random Forest, XGBoost)
# Mục tiêu: Đánh giá và so sánh hiệu năng các họ thuật toán từ đơn giản đến phức tạp.

# %%
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
try:
    from xgboost import XGBClassifier
except ImportError:
    import sys
    print("\n[ERROR] Missing XGBoost library.")
    print("Please run: pip install xgboost")
    sys.exit(1)

metrics_list = []

# --- 4.1. Logistic Regression (Baseline) ---
print("\n[1] Đang huấn luyện Logistic Regression (Baseline)...")
lr_model = LogisticRegression(class_weight='balanced', random_state=42, max_iter=500)
lr_model.fit(X_train, y_train)

lr_preds = lr_model.predict(X_test)
lr_probs_train = lr_model.predict_proba(X_train)[:, 1]
lr_probs_test = lr_model.predict_proba(X_test)[:, 1]

metrics_list.append({
    'Model': 'Logistic Regression',
    'AUC Train': roc_auc_score(y_train, lr_probs_train),
    'AUC Test': roc_auc_score(y_test, lr_probs_test),
    'Recall Test': recall_score(y_test, lr_preds)
})
print("\nBáo cáo phân loại chi tiết (Logistic Regression):")
print(classification_report(y_test, lr_preds))

# --- 4.2. Decision Tree (White-box) ---
print("\n[2] Đang huấn luyện Decision Tree...")
# Giới hạn độ sâu = 3 để cây cực kỳ dễ hiểu và không bị đè chữ khi vẽ
dt_model = DecisionTreeClassifier(max_depth=3, class_weight='balanced', random_state=42)
dt_model.fit(X_train, y_train)

dt_preds = dt_model.predict(X_test)
dt_probs_train = dt_model.predict_proba(X_train)[:, 1]
dt_probs_test = dt_model.predict_proba(X_test)[:, 1]

metrics_list.append({
    'Model': 'Decision Tree',
    'AUC Train': roc_auc_score(y_train, dt_probs_train),
    'AUC Test': roc_auc_score(y_test, dt_probs_test),
    'Recall Test': recall_score(y_test, dt_preds)
})
print("\nBáo cáo phân loại chi tiết (Decision Tree):")
print(classification_report(y_test, dt_preds))

# Vẽ và lưu cây quyết định
plt.figure(figsize=(30, 12))
plot_tree(dt_model, feature_names=features_cols, class_names=['No Buy', 'Buy'], filled=True, rounded=True, fontsize=12)
plt.title("Logic Dự báo Mua hàng (Decision Tree - Max Depth 3)")
plt.savefig('decision_tree_logic.png', dpi=300, bbox_inches='tight')
print("Đã lưu hình cây quyết định: decision_tree_logic.png (Đã fix lỗi đè chữ)")

# --- 4.3. Random Forest (Bagging) ---
print("\n[3] Đang huấn luyện Random Forest...")
rf_model = RandomForestClassifier(n_estimators=100, max_depth=8, max_samples=0.4, class_weight='balanced', random_state=42, n_jobs=-1)
rf_model.fit(X_train, y_train)

rf_preds = rf_model.predict(X_test)
rf_probs_train = rf_model.predict_proba(X_train)[:, 1]
rf_probs_test = rf_model.predict_proba(X_test)[:, 1]

metrics_list.append({
    'Model': 'Random Forest',
    'AUC Train': roc_auc_score(y_train, rf_probs_train),
    'AUC Test': roc_auc_score(y_test, rf_probs_test),
    'Recall Test': recall_score(y_test, rf_preds)
})

# --- 4.4. XGBoost (Boosting) ---
print("\n[4] Đang huấn luyện XGBoost...")
# Do XGBoost mặc định không có tham số class_weight='balanced', ta dùng scale_pos_weight
pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)
xgb_model = XGBClassifier(n_estimators=100, max_depth=6, scale_pos_weight=pos_weight, random_state=42, eval_metric='auc')
xgb_model.fit(X_train, y_train)

xgb_preds = xgb_model.predict(X_test)
xgb_probs_train = xgb_model.predict_proba(X_train)[:, 1]
xgb_probs_test = xgb_model.predict_proba(X_test)[:, 1]

metrics_list.append({
    'Model': 'XGBoost',
    'AUC Train': roc_auc_score(y_train, xgb_probs_train),
    'AUC Test': roc_auc_score(y_test, xgb_probs_test),
    'Recall Test': recall_score(y_test, xgb_preds)
})
print("\nBáo cáo phân loại chi tiết (XGBoost):")
print(classification_report(y_test, xgb_preds))

# %% [markdown]
# ## 5. Đánh giá và So sánh Tổng thể
# %%
df_metrics = pd.DataFrame(metrics_list)
df_metrics['Generalization Gap'] = df_metrics['AUC Train'] - df_metrics['AUC Test']

print("\n=== BẢNG SO SÁNH HIỆU NĂNG CÁC MÔ HÌNH ===")
print(df_metrics.to_string(index=False))

# Trực quan hóa So sánh Model
fig, axes = plt.subplots(1, 3, figsize=(20, 6))

# Đảo thứ tự để Logistic lên đầu khi vẽ ngang
df_metrics_viz = df_metrics.iloc[::-1]

sns.barplot(x='AUC Test', y='Model', data=df_metrics_viz, ax=axes[0], palette='Blues')
axes[0].set_title('AUC Test (Độ chính xác phân loại)')
axes[0].set_xlim(0.5, 1.0)

sns.barplot(x='Generalization Gap', y='Model', data=df_metrics_viz, ax=axes[1], palette='Oranges')
axes[1].set_title('Generalization Gap (Độ ổn định - Càng thấp càng tốt)')

sns.barplot(x='Recall Test', y='Model', data=df_metrics_viz, ax=axes[2], palette='Greens')
axes[2].set_title('Recall Test (Khả năng không bỏ sót khách mua)')

plt.tight_layout()
plt.savefig('model_comparison.png', dpi=300, bbox_inches='tight')
print("Đã lưu biểu đồ so sánh: model_comparison.png")

# %% [markdown]
# ## 6. Đánh giá chi tiết Mô hình được chọn (Random Forest)
# %%
print("\n=== BÁO CÁO PHÂN LOẠI CHI TIẾT (RANDOM FOREST) ===")
print("Lưu ý: Nhãn 0 = Không mua, Nhãn 1 = Có mua")
print(classification_report(y_test, rf_preds))

# Vẽ Confusion Matrix
plt.figure(figsize=(8, 6))
cm = confusion_matrix(y_test, rf_preds)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=['Dự báo Không Mua', 'Dự báo Có Mua'],
            yticklabels=['Thực tế Không Mua', 'Thực tế Có Mua'])
plt.title('Ma trận nhầm lẫn (Confusion Matrix) - Random Forest')
plt.savefig('confusion_matrix_rf.png', dpi=300, bbox_inches='tight')
print("Đã lưu biểu đồ: confusion_matrix_rf.png")

# %% [markdown]
# ## 7. Trực quan hóa Mức độ Quan trọng của Features (Random Forest)
# %%
feature_importance = pd.DataFrame({
    'Feature': features_cols,
    'Importance': rf_model.feature_importances_
}).sort_values('Importance', ascending=False)

plt.figure(figsize=(10, 6))
sns.barplot(x='Importance', y='Feature', data=feature_importance, palette='viridis')
plt.title('Những Yếu Tố Quyết Định Việc Mua Hàng Tuần Tới (Random Forest)')
plt.tight_layout()
plt.savefig('feature_importance.png')
print("Đã lưu biểu đồ: feature_importance.png")

print("\n[5] Đang lưu các mô hình (Model Artifacts)...")
joblib.dump(dt_model, 'dt_model.pkl')
joblib.dump(rf_model, 'rf_model.pkl')
joblib.dump(xgb_model, 'xgb_model.pkl')
print("Đã lưu thành công: dt_model.pkl, rf_model.pkl và xgb_model.pkl")

print("\n=== GIAI ĐOẠN 3 HOÀN TẤT ===")

