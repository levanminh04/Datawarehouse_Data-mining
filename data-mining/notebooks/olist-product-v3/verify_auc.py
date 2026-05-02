# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_curve, auc
import warnings
warnings.filterwarnings('ignore')
from database import query_db

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

labels_path = os.path.join(SAVE_DIR, 'customer_segments.csv')
df_labels = pd.read_csv(labels_path)[['user_id', 'is_vip']]

query_features = """
WITH ranked_orders AS (
    SELECT user_id, order_id,
           ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY MIN(created_at)) AS rn
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id, order_id
),
first_order AS (SELECT user_id, order_id FROM ranked_orders WHERE rn = 1),
first_order_features AS (
    SELECT fo.user_id,
           COUNT(oi.id) AS first_order_num_items,
           COUNT(DISTINCT p.category) AS first_order_num_categories,
           MIN(p.department) AS first_order_department
    FROM first_order fo
    JOIN order_items oi ON fo.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.id
    GROUP BY fo.user_id
),
ranked_sessions AS (
    SELECT user_id, session_id,
           ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY MIN(created_at)) AS rn
    FROM events WHERE user_id IS NOT NULL GROUP BY user_id, session_id
),
first_session_features AS (
    SELECT rs.user_id,
           MAX(e.sequence_number) AS first_session_depth,
           COUNT(CASE WHEN e.event_type = 'product' THEN 1 END) AS first_session_products_viewed
    FROM ranked_sessions rs
    JOIN events e ON rs.user_id = e.user_id AND rs.session_id = e.session_id
    WHERE rs.rn = 1 GROUP BY rs.user_id
)
SELECT fof.user_id, fof.first_order_num_items, fof.first_order_num_categories,
       fof.first_order_department,
       COALESCE(fsf.first_session_depth, 0) AS first_session_depth,
       COALESCE(fsf.first_session_products_viewed, 0) AS first_session_products_viewed,
       u.age, u.gender, u.country, u.traffic_source
FROM first_order_features fof
JOIN users u ON fof.user_id = u.id
LEFT JOIN first_session_features fsf ON fof.user_id = fsf.user_id
"""

df_features = query_db(query_features)
df = pd.merge(df_features, df_labels, on='user_id', how='inner')

df['age'] = df['age'].fillna(df['age'].median())
for col in ['gender', 'country', 'traffic_source', 'first_order_department']:
    df[col] = df[col].fillna('Unknown')

for col in ['gender', 'country', 'traffic_source', 'first_order_department']:
    le = LabelEncoder()
    df[col + '_enc'] = le.fit_transform(df[col].astype(str))

FEATURE_COLS = ['first_order_num_items', 'first_order_num_categories',
                'first_order_department_enc', 'first_session_depth',
                'first_session_products_viewed', 'age', 'gender_enc',
                'country_enc', 'traffic_source_enc']

X = df[FEATURE_COLS]
y = df['is_vip']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

dt = DecisionTreeClassifier(max_depth=5, min_samples_leaf=200, class_weight='balanced', random_state=42)
dt.fit(X_train, y_train)
fpr, tpr, _ = roc_curve(y_test, dt.predict_proba(X_test)[:, 1])
dt_auc = auc(fpr, tpr)

rf = RandomForestClassifier(n_estimators=200, max_depth=8, class_weight='balanced', random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)
fpr, tpr, _ = roc_curve(y_test, rf.predict_proba(X_test)[:, 1])
rf_auc = auc(fpr, tpr)

print(f"Decision Tree AUC: {dt_auc:.4f}")
print(f"Random Forest AUC: {rf_auc:.4f}")
print(f"Target range: 0.55 - 0.85 -> {'PASS' if 0.55 < rf_auc < 0.85 else 'FAIL'}")
