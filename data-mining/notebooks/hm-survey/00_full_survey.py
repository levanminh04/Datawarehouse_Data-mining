# -*- coding: utf-8 -*-
"""
Giai đoạn 0 + 1: Khảo sát Schema + EDA tìm Signal thật
Chạy toàn bộ trong 1 script duy nhất.
"""
import sys, io, os
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.getcwd(), '..', 'datamining-version3'))
from database import query_db

def run(label, sql):
    print(f"\n{'='*70}\n  {label}\n{'='*70}")
    r = query_db(sql)
    if r is not None:
        pd.set_option('display.max_columns', 30)
        pd.set_option('display.width', 200)
        print(r.to_string())
    return r

# ===== PHASE 0: Schema Check =====

# 0.0 List all tables
run("0.0 All tables", """
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name
""")

# 0.1 Row counts (try both 'customers' and 'customer')
run("0.1 Row counts", """
SELECT 'articles' AS tbl, COUNT(*) AS cnt FROM articles
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
""")

# Try to find customer table name
for tbl_name in ['customers', 'customer']:
    r = query_db(f"SELECT COUNT(*) AS cnt FROM {tbl_name}")
    if r is not None:
        print(f"\n>>> Customer table found as: '{tbl_name}' with {r['cnt'].iloc[0]} rows")
        CUST_TABLE = tbl_name
        break
else:
    print("\n>>> ERROR: No customer table found!")
    sys.exit(1)

# 0.2 Schema of customer table
run(f"0.2 Schema: {CUST_TABLE}", f"""
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = '{CUST_TABLE}'
ORDER BY ordinal_position
""")

# 0.3 Sample customer data
run(f"0.3 Sample: {CUST_TABLE}", f"SELECT * FROM {CUST_TABLE} LIMIT 5")

# 0.4 Null rates for customer table
run(f"0.4 Null rates: {CUST_TABLE}", f"""
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS customer_id_null,
    SUM(CASE WHEN age IS NULL THEN 1 ELSE 0 END) AS age_null
FROM {CUST_TABLE}
""")

# Try FN and Active columns (may not exist)
r = query_db(f"""
SELECT column_name FROM information_schema.columns
WHERE table_name = '{CUST_TABLE}' ORDER BY ordinal_position
""")
if r is not None:
    cust_cols = r['column_name'].tolist()
    print(f"\n>>> Customer columns: {cust_cols}")

# 0.5 Transaction time range + count
run("0.5 Transaction time range", """
SELECT
    COUNT(*) AS total_rows,
    MIN(t_dat) AS earliest,
    MAX(t_dat) AS latest,
    MAX(t_dat)::date - MIN(t_dat)::date AS span_days,
    COUNT(DISTINCT customer_id) AS unique_customers,
    COUNT(DISTINCT article_id) AS unique_articles
FROM transactions
""")

# 0.6 Price distribution
run("0.6 Price stats", """
SELECT
    ROUND(MIN(price)::numeric, 5) AS min_p,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price)::numeric, 5) AS p25,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price)::numeric, 5) AS median,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price)::numeric, 5) AS p75,
    ROUND(MAX(price)::numeric, 5) AS max_p,
    ROUND(AVG(price)::numeric, 5) AS avg_p
FROM transactions
""")

# ===== PHASE 1: EDA Signal Detection =====

# 1A.1 Age distribution (bimodal check)
run("1A.1 Age distribution buckets", f"""
SELECT
    CASE
        WHEN age < 20 THEN '< 20'
        WHEN age < 30 THEN '20-29'
        WHEN age < 40 THEN '30-39'
        WHEN age < 50 THEN '40-49'
        WHEN age < 60 THEN '50-59'
        ELSE '60+'
    END AS age_group,
    COUNT(*) AS n_customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM {CUST_TABLE}
WHERE age IS NOT NULL
GROUP BY 1
ORDER BY 1
""")

# 1B.1 index_group_name values
run("1B.1 Index groups in articles", """
SELECT index_group_name, COUNT(*) AS n_articles
FROM articles GROUP BY 1 ORDER BY 2 DESC
""")

# 1C.1 Monthly transaction volume (seasonality check)
run("1C.1 Monthly sales volume", """
SELECT
    TO_CHAR(t_dat, 'YYYY-MM') AS month,
    COUNT(*) AS n_transactions,
    COUNT(DISTINCT customer_id) AS n_customers,
    ROUND(SUM(price)::numeric, 2) AS total_revenue
FROM transactions
GROUP BY 1 ORDER BY 1
""")

# 1C.2 Transactions per customer distribution
run("1C.2 Purchase frequency distribution", """
WITH cust_freq AS (
    SELECT customer_id, COUNT(*) AS n_purchases
    FROM transactions GROUP BY 1
)
SELECT
    CASE
        WHEN n_purchases = 1 THEN '1 (one-time)'
        WHEN n_purchases <= 5 THEN '2-5'
        WHEN n_purchases <= 10 THEN '6-10'
        WHEN n_purchases <= 20 THEN '11-20'
        WHEN n_purchases <= 50 THEN '21-50'
        ELSE '51+'
    END AS freq_bucket,
    COUNT(*) AS n_customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM cust_freq
GROUP BY 1
ORDER BY MIN(n_purchases)
""")

# 1C.3 Sales channel distribution
run("1C.3 Sales channel breakdown", """
SELECT
    sales_channel_id,
    COUNT(*) AS n_transactions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM transactions GROUP BY 1 ORDER BY 1
""")

# 1C.4 Items per shopping trip (same customer + same day)
run("1C.4 Items per shopping trip", """
WITH trips AS (
    SELECT customer_id, t_dat::date AS d, COUNT(*) AS n_items
    FROM transactions GROUP BY 1, 2
)
SELECT
    CASE
        WHEN n_items = 1 THEN '1 item'
        WHEN n_items <= 3 THEN '2-3 items'
        WHEN n_items <= 5 THEN '4-5 items'
        WHEN n_items <= 10 THEN '6-10 items'
        ELSE '11+ items'
    END AS trip_size,
    COUNT(*) AS n_trips,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM trips
GROUP BY 1
ORDER BY MIN(n_items)
""")

# 1C.5 THE KEY SIGNAL CHECK: Age group vs Index group (cross-tab)
run("1C.5 KEY SIGNAL: Age vs Product Style", f"""
SELECT
    CASE
        WHEN c.age < 25 THEN 'GenZ (< 25)'
        WHEN c.age < 35 THEN 'Young (25-34)'
        WHEN c.age < 50 THEN 'Middle (35-49)'
        ELSE 'Senior (50+)'
    END AS age_group,
    a.index_group_name,
    COUNT(*) AS n_purchases,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(
        PARTITION BY CASE
            WHEN c.age < 25 THEN 'GenZ (< 25)'
            WHEN c.age < 35 THEN 'Young (25-34)'
            WHEN c.age < 50 THEN 'Middle (35-49)'
            ELSE 'Senior (50+)'
        END
    ), 2) AS pct_within_age
FROM transactions t
JOIN articles a ON t.article_id = a.article_id
JOIN {CUST_TABLE} c ON t.customer_id = c.customer_id
WHERE c.age IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 4 DESC
""")

print("\n\n=== SURVEY HOÀN TẤT ===")
