# -*- coding: utf-8 -*-
"""
Giai đoạn 0: Khảo sát Schema & Dữ liệu Thô — H&M Dataset
Checklist: 0.1 → 0.10
"""
import sys, io, os
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Reuse database connection from datamining-version3
sys.path.insert(0, os.path.join(os.getcwd(), '..', 'datamining-version3'))
from database import query_db

def run(label, sql):
    print(f"\n{'='*70}\n  {label}\n{'='*70}")
    r = query_db(sql)
    if r is not None:
        print(r.to_string())
    return r

# =====================================================================
# 0.1 Schema of all 3 tables
# =====================================================================
run("0.1a Schema: articles", """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'articles'
ORDER BY ordinal_position
""")

run("0.1b Schema: customers", """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'customers'
ORDER BY ordinal_position
""")

run("0.1c Schema: transactions", """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'transactions'
ORDER BY ordinal_position
""")

# =====================================================================
# 0.2 Row counts
# =====================================================================
run("0.2 Row counts", """
SELECT 'articles' AS tbl, COUNT(*) AS row_count FROM articles
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'transactions', COUNT(*) FROM transactions
""")

# =====================================================================
# 0.3 Null rate for EVERY column in articles
# =====================================================================
run("0.3 Null rate: articles", """
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN article_id IS NULL THEN 1 ELSE 0 END) AS article_id_null,
    SUM(CASE WHEN product_code IS NULL THEN 1 ELSE 0 END) AS product_code_null,
    SUM(CASE WHEN prod_name IS NULL THEN 1 ELSE 0 END) AS prod_name_null,
    SUM(CASE WHEN product_type_no IS NULL THEN 1 ELSE 0 END) AS product_type_no_null,
    SUM(CASE WHEN product_type_name IS NULL THEN 1 ELSE 0 END) AS product_type_name_null,
    SUM(CASE WHEN product_group_name IS NULL THEN 1 ELSE 0 END) AS product_group_name_null,
    SUM(CASE WHEN graphical_appearance_no IS NULL THEN 1 ELSE 0 END) AS graphical_appearance_no_null,
    SUM(CASE WHEN graphical_appearance_name IS NULL THEN 1 ELSE 0 END) AS graphical_appearance_name_null,
    SUM(CASE WHEN colour_group_code IS NULL THEN 1 ELSE 0 END) AS colour_group_code_null,
    SUM(CASE WHEN colour_group_name IS NULL THEN 1 ELSE 0 END) AS colour_group_name_null,
    SUM(CASE WHEN perceived_colour_value_id IS NULL THEN 1 ELSE 0 END) AS perceived_colour_value_id_null,
    SUM(CASE WHEN perceived_colour_value_name IS NULL THEN 1 ELSE 0 END) AS perceived_colour_value_name_null,
    SUM(CASE WHEN perceived_colour_master_id IS NULL THEN 1 ELSE 0 END) AS perceived_colour_master_id_null,
    SUM(CASE WHEN perceived_colour_master_name IS NULL THEN 1 ELSE 0 END) AS perceived_colour_master_name_null,
    SUM(CASE WHEN department_no IS NULL THEN 1 ELSE 0 END) AS department_no_null,
    SUM(CASE WHEN department_name IS NULL THEN 1 ELSE 0 END) AS department_name_null,
    SUM(CASE WHEN index_code IS NULL THEN 1 ELSE 0 END) AS index_code_null,
    SUM(CASE WHEN index_name IS NULL THEN 1 ELSE 0 END) AS index_name_null,
    SUM(CASE WHEN index_group_no IS NULL THEN 1 ELSE 0 END) AS index_group_no_null,
    SUM(CASE WHEN index_group_name IS NULL THEN 1 ELSE 0 END) AS index_group_name_null,
    SUM(CASE WHEN section_no IS NULL THEN 1 ELSE 0 END) AS section_no_null,
    SUM(CASE WHEN section_name IS NULL THEN 1 ELSE 0 END) AS section_name_null,
    SUM(CASE WHEN garment_group_no IS NULL THEN 1 ELSE 0 END) AS garment_group_no_null,
    SUM(CASE WHEN garment_group_name IS NULL THEN 1 ELSE 0 END) AS garment_group_name_null,
    SUM(CASE WHEN detail_desc IS NULL THEN 1 ELSE 0 END) AS detail_desc_null
FROM articles
""")

# =====================================================================
# 0.4 Null rate for EVERY column in customers
# =====================================================================
run("0.4 Null rate: customers", """
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS customer_id_null,
    SUM(CASE WHEN fn IS NULL THEN 1 ELSE 0 END) AS fn_null,
    SUM(CASE WHEN active IS NULL THEN 1 ELSE 0 END) AS active_null,
    SUM(CASE WHEN club_member_status IS NULL THEN 1 ELSE 0 END) AS club_member_status_null,
    SUM(CASE WHEN fashion_news_frequency IS NULL THEN 1 ELSE 0 END) AS fashion_news_frequency_null,
    SUM(CASE WHEN age IS NULL THEN 1 ELSE 0 END) AS age_null,
    SUM(CASE WHEN postal_code IS NULL THEN 1 ELSE 0 END) AS postal_code_null
FROM customers
""")

# =====================================================================
# 0.5 Null rate for EVERY column in transactions
# =====================================================================
run("0.5 Null rate: transactions", """
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN t_dat IS NULL THEN 1 ELSE 0 END) AS t_dat_null,
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS customer_id_null,
    SUM(CASE WHEN article_id IS NULL THEN 1 ELSE 0 END) AS article_id_null,
    SUM(CASE WHEN price IS NULL THEN 1 ELSE 0 END) AS price_null,
    SUM(CASE WHEN sales_channel_id IS NULL THEN 1 ELSE 0 END) AS sales_channel_id_null
FROM transactions
""")

# =====================================================================
# 0.6 Cardinality of hierarchical columns in articles
# =====================================================================
run("0.6 Cardinality: articles hierarchy", """
SELECT
    COUNT(DISTINCT product_type_name) AS n_product_types,
    COUNT(DISTINCT product_group_name) AS n_product_groups,
    COUNT(DISTINCT index_group_name) AS n_index_groups,
    COUNT(DISTINCT index_name) AS n_indexes,
    COUNT(DISTINCT department_name) AS n_departments,
    COUNT(DISTINCT section_name) AS n_sections,
    COUNT(DISTINCT garment_group_name) AS n_garment_groups,
    COUNT(DISTINCT colour_group_name) AS n_colour_groups,
    COUNT(DISTINCT graphical_appearance_name) AS n_graphical_appearances
FROM articles
""")

# =====================================================================
# 0.7 Sample 5 rows from each table
# =====================================================================
run("0.7a Sample: articles (5 rows)", """
SELECT * FROM articles LIMIT 5
""")

run("0.7b Sample: customers (5 rows)", """
SELECT * FROM customers LIMIT 5
""")

run("0.7c Sample: transactions (5 rows)", """
SELECT * FROM transactions LIMIT 5
""")

# =====================================================================
# 0.8 Time range of transactions
# =====================================================================
run("0.8 Time range: transactions", """
SELECT
    MIN(t_dat) AS earliest_date,
    MAX(t_dat) AS latest_date,
    MAX(t_dat)::date - MIN(t_dat)::date AS span_days
FROM transactions
""")

# =====================================================================
# 0.9 Price distribution
# =====================================================================
run("0.9 Price distribution", """
SELECT
    COUNT(*) AS total,
    ROUND(MIN(price)::numeric, 4) AS min_price,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price)::numeric, 4) AS p25,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price)::numeric, 4) AS median,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price)::numeric, 4) AS p75,
    ROUND(MAX(price)::numeric, 4) AS max_price,
    ROUND(AVG(price)::numeric, 4) AS avg_price,
    ROUND(STDDEV(price)::numeric, 4) AS std_price
FROM transactions
""")

# =====================================================================
# 0.10 Age distribution
# =====================================================================
run("0.10 Age distribution", """
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN age IS NULL THEN 1 ELSE 0 END) AS null_count,
    ROUND(MIN(age)::numeric, 1) AS min_age,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY age)::numeric, 1) AS p25,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY age)::numeric, 1) AS median,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY age)::numeric, 1) AS p75,
    ROUND(MAX(age)::numeric, 1) AS max_age,
    ROUND(AVG(age)::numeric, 1) AS avg_age
FROM customers
""")

print("\n\n=== GIAI ĐOẠN 0 HOÀN TẤT ===")
