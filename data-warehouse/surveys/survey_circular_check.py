# -*- coding: utf-8 -*-
"""
Xác nhận: category có DETERMINISTIC predict price_tier không?
Nếu yes → Layer 2 là trivial lookup, không phải ML có giá trị.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'datamining-version3'))
from database import query_db
import pandas as pd

def run(label, sql):
    print(f"\n{'='*60}\n  {label}\n{'='*60}")
    r = query_db(sql)
    if r is not None: print(r.to_string())
    return r

# Q1: Mỗi category rơi vào mấy tier? Nếu 1 tier = deterministic = trivial
run("Q1: Tier distribution per category", """
WITH product_tiers AS (
    SELECT id AS product_id, category, department, retail_price, cost,
           (retail_price - cost) / NULLIF(retail_price, 0) AS margin_pct
    FROM products WHERE retail_price > 0 AND cost > 0
)
SELECT category,
       COUNT(*) AS total,
       COUNT(CASE WHEN retail_price < 28 THEN 1 END) AS budget_count,
       COUNT(CASE WHEN retail_price BETWEEN 28 AND 58 THEN 1 END) AS mid_count,
       COUNT(CASE WHEN retail_price > 58 THEN 1 END) AS premium_count,
       ROUND(100.0 * COUNT(CASE WHEN retail_price > 58 THEN 1 END) / COUNT(*)::numeric, 1) AS pct_premium
FROM products WHERE retail_price > 0
GROUP BY category
ORDER BY pct_premium DESC
""")

# Q2: Nếu chỉ dùng department (Men/Women), AUC là bao nhiêu?
# Proxy: compare tier distribution Men vs Women
run("Q2: Department vs tier — có signal gì không?", """
WITH tiers AS (
    SELECT department,
           CASE
               WHEN retail_price < 28 THEN 'Budget'
               WHEN retail_price <= 58 THEN 'Mid-range'
               ELSE 'Premium'
           END AS tier
    FROM products WHERE retail_price > 0
)
SELECT department, tier, COUNT(*) AS cnt,
       ROUND(100.0 * COUNT(*)::numeric / SUM(COUNT(*)) OVER(PARTITION BY department), 2) AS pct
FROM tiers
GROUP BY department, tier
ORDER BY department, tier
""")

# Q3: Trong cùng category, có variation về price không?
# Nếu 1 category có cả Budget và Premium thì classification mới không trivial
run("Q3: Price variance WITHIN each category (std/median)", """
SELECT category,
       COUNT(*) AS num_products,
       ROUND(MIN(retail_price)::numeric, 2) AS min_price,
       ROUND(MAX(retail_price)::numeric, 2) AS max_price,
       ROUND(AVG(retail_price)::numeric, 2) AS avg_price,
       ROUND(STDDEV(retail_price)::numeric, 2) AS std_price,
       ROUND(MAX(retail_price)::numeric - MIN(retail_price)::numeric, 2) AS price_range
FROM products WHERE retail_price > 0
GROUP BY category
ORDER BY std_price DESC
""")
