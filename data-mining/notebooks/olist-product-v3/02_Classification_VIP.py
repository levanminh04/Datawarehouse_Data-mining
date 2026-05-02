# %% [markdown]
# # LỚP 2: PHÂN LOẠI KHÁCH HÀNG VIP (Classification)
#
# **Câu hỏi kinh doanh:**
# Ngay khi khách hoàn thành đơn hàng đầu tiên, liệu ta có thể dự đoán
# họ có tiềm năng trở thành VIP không?
#
# **Thiết kế chống Data Leakage (đã xác nhận bằng SQL):**
#
# Target Y: is_vip từ Lớp 1 (K-Means trên RFM toàn lịch sử)
#
# Features X (KHÔNG CÓ biến tiền):
#   - first_order_num_items        (Survey #17: 1→$101, 4→$278, tương quan gián tiếp)
#   - first_order_num_categories   (đa dạng mua sắm đơn đầu)
#   - first_order_department       (Men / Women)
#   - first_session_depth          (events: số events trong phiên đầu)
#   - first_session_products_viewed(events: số trang product trong phiên đầu)
#   - age, gender, country, traffic_source (demographics)
#
# Không dùng biến tiền (sale_price) → tránh "dùng tiền dự đoán VIP=monetary cao"
# Không dùng events trong Lớp 1 → tránh cross-layer leakage
#
# **Kỳ vọng AUC: 0.58–0.68** (không random, không leakage)
#
# **Yêu cầu:** Chạy 01_Clustering_RFM.py trước để có customer_segments.csv

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
from sklearn.metrics import (classification_report, confusion_matrix,
                             roc_curve, auc)
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(__file__))
from database import query_db

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

# %% [markdown]
# ## Bước 1: Load nhãn từ Lớp 1 + Truy vấn features

# %%
labels_path = os.path.join(SAVE_DIR, 'customer_segments.csv')
if not os.path.exists(labels_path):
    raise FileNotFoundError("Chay 01_Clustering_RFM.py truoc!")

df_labels = pd.read_csv(labels_path)[['user_id', 'is_vip']]
print(f"Labels loaded: {len(df_labels):,} users, VIP rate: {df_labels['is_vip'].mean()*100:.1f}%")

# %% [markdown]
# ## Bước 2: Truy vấn features
#
# Xác định first_order bằng cách GROUP BY order_id trước (tránh lỗi timestamp TheLook),
# sau đó rank theo MIN(created_at) của order.
# First_session: rank sessions theo MIN(created_at) per user.

# %%
query_features = """
WITH ranked_orders AS (
    SELECT
        user_id, order_id,
        ROW_NUMBER() OVER(
            PARTITION BY user_id
            ORDER BY MIN(created_at)
        ) AS rn
    FROM order_items
    WHERE status != 'Cancelled'
    GROUP BY user_id, order_id
),
first_order AS (
    SELECT user_id, order_id FROM ranked_orders WHERE rn = 1
),
first_order_features AS (
    SELECT
        fo.user_id,
        COUNT(oi.id)                    AS first_order_num_items,
        COUNT(DISTINCT p.category)      AS first_order_num_categories,
        MIN(p.department)               AS first_order_department
    FROM first_order fo
    JOIN order_items oi ON fo.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.id
    GROUP BY fo.user_id
),
ranked_sessions AS (
    SELECT
        user_id, session_id,
        ROW_NUMBER() OVER(
            PARTITION BY user_id
            ORDER BY MIN(created_at)
        ) AS rn
    FROM events
    WHERE user_id IS NOT NULL
    GROUP BY user_id, session_id
),
first_session_features AS (
    SELECT
        rs.user_id,
        MAX(e.sequence_number)                                       AS first_session_depth,
        COUNT(CASE WHEN e.event_type = 'product' THEN 1 END)        AS first_session_products_viewed
    FROM ranked_sessions rs
    JOIN events e ON rs.user_id = e.user_id AND rs.session_id = e.session_id
    WHERE rs.rn = 1
    GROUP BY rs.user_id
)
SELECT
    fof.user_id,
    fof.first_order_num_items,
    fof.first_order_num_categories,
    fof.first_order_department,
    COALESCE(fsf.first_session_depth, 0)           AS first_session_depth,
    COALESCE(fsf.first_session_products_viewed, 0) AS first_session_products_viewed,
    u.age,
    u.gender,
    u.country,
    u.traffic_source
FROM first_order_features fof
JOIN users u ON fof.user_id = u.id
LEFT JOIN first_session_features fsf ON fof.user_id = fsf.user_id
"""

print("Querying features...")
df_features = query_db(query_features)
print(f"Features loaded: {len(df_features):,} users")

# Merge với labels
df = pd.merge(df_features, df_labels, on='user_id', how='inner')
print(f"After merge: {len(df):,} samples")
print(f"VIP: {df['is_vip'].sum():,} ({df['is_vip'].mean()*100:.1f}%) | Non-VIP: {(1-df['is_vip']).sum():,}")

# %% [markdown]
# ## Bước 3: Tiền xử lý

# %%
# Fill missing
df['age'] = df['age'].fillna(df['age'].median())
for col in ['gender', 'country', 'traffic_source', 'first_order_department']:
    df[col] = df[col].fillna('Unknown')

# Label encoding
le_cols = ['gender', 'country', 'traffic_source', 'first_order_department']
le_dict = {}
for col in le_cols:
    le = LabelEncoder()
    df[col + '_enc'] = le.fit_transform(df[col].astype(str))
    le_dict[col] = le

FEATURE_COLS = [
    # Hanh vi don dau (COUNT - khong co tien)
    'first_order_num_items',
    'first_order_num_categories',
    'first_order_department_enc',
    # Hanh vi phien dau (tu events)
    'first_session_depth',
    'first_session_products_viewed',
    # Demographics
    'age',
    'gender_enc',
    'country_enc',
    'traffic_source_enc',
]

X = df[FEATURE_COLS]
y = df['is_vip']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nTrain: {len(X_train):,} | Test: {len(X_test):,}")
print(f"Feature set: {FEATURE_COLS}")

# %% [markdown]
# ## Bước 4: Huấn luyện Decision Tree + Random Forest

# %%
# Decision Tree (interpretable, for visualization)
dt = DecisionTreeClassifier(max_depth=5, min_samples_leaf=200,
                             class_weight='balanced', random_state=42)
dt.fit(X_train, y_train)

# Random Forest (for robust AUC)
rf = RandomForestClassifier(n_estimators=200, max_depth=8,
                             class_weight='balanced', random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)

print("Training complete.")

# %% [markdown]
# ## Bước 5: Đánh giá mô hình

# %%
fig, axes = plt.subplots(1, 3, figsize=(20, 6))

# --- ROC Curve ---
for model, name, color in [(dt, 'Decision Tree', '#3498db'), (rf, 'Random Forest', '#e74c3c')]:
    y_proba = model.predict_proba(X_test)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    roc_auc = auc(fpr, tpr)
    axes[0].plot(fpr, tpr, lw=2, color=color, label=f'{name} (AUC={roc_auc:.3f})')

axes[0].plot([0, 1], [0, 1], 'k--', lw=1, label='Random (AUC=0.5)')
axes[0].set_xlabel('False Positive Rate')
axes[0].set_ylabel('True Positive Rate')
axes[0].set_title('ROC Curve - VIP Prediction', fontweight='bold')
axes[0].legend()

# --- Confusion Matrix (RF) ---
y_pred_rf = rf.predict(X_test)
cm = confusion_matrix(y_test, y_pred_rf)
im = axes[1].imshow(cm, cmap='Blues')
for i in range(2):
    for j in range(2):
        axes[1].text(j, i, str(cm[i, j]), ha='center', va='center', fontsize=14, fontweight='bold')
axes[1].set_xticks([0, 1])
axes[1].set_yticks([0, 1])
axes[1].set_xticklabels(['Non-VIP', 'VIP'])
axes[1].set_yticklabels(['Non-VIP', 'VIP'])
axes[1].set_xlabel('Predicted')
axes[1].set_ylabel('Actual')
axes[1].set_title('Confusion Matrix (Random Forest)', fontweight='bold')

# --- Feature Importance (RF) ---
importances = pd.Series(rf.feature_importances_, index=FEATURE_COLS).sort_values()
nice = {
    'first_order_num_items': 'Items in 1st Order',
    'first_order_num_categories': 'Categories in 1st Order',
    'first_order_department_enc': 'Department (Men/Women)',
    'first_session_depth': 'Session Depth (events)',
    'first_session_products_viewed': 'Products Viewed (events)',
    'age': 'Age',
    'gender_enc': 'Gender',
    'country_enc': 'Country',
    'traffic_source_enc': 'Traffic Source',
}
importances.index = [nice[i] for i in importances.index]
importances.plot(kind='barh', ax=axes[2], color='#2ecc71')
axes[2].set_title('Feature Importance (Random Forest)', fontweight='bold')
axes[2].set_xlabel('Importance Score')

plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, '02_classification_results.png'), dpi=150, bbox_inches='tight')
plt.show()

print("\n=== Random Forest Report ===")
print(classification_report(y_test, y_pred_rf, target_names=['Non-VIP', 'VIP']))

# %% [markdown]
# ## Bước 6: Decision Tree Visualization

# %%
feature_names_nice = [nice[c] for c in FEATURE_COLS]

plt.figure(figsize=(24, 10))
plot_tree(dt, feature_names=feature_names_nice, class_names=['Non-VIP', 'VIP'],
          filled=True, rounded=True, fontsize=9, precision=2)
plt.title('Decision Tree: VIP Prediction from 1st Order Behavior + Demographics',
          fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, '02_decision_tree.png'), dpi=120, bbox_inches='tight')
plt.show()
print("Saved: 02_decision_tree.png")
