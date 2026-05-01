# -*- coding: utf-8 -*-
"""Final viability check for Product Intelligence Pipeline Layer 2"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'datamining-version3'))
from database import query_db

def run(label, sql):
    print(f"\n{'='*60}\n  {label}\n{'='*60}")
    r = query_db(sql)
    if r is not None: print(r.to_string())
    return r

# KEY CHECK: Does category predict retail_price (absolute level)?
# If category spreads are large → classification is learnable
run("Category → avg retail_price (absolute, not margin)", """
SELECT category, department,
       COUNT(*) AS num_products,
       ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY retail_price)::numeric, 2) AS p25,
       ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY retail_price)::numeric, 2) AS median,
       ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY retail_price)::numeric, 2) AS p75,
       ROUND(AVG(retail_price)::numeric, 2) AS avg_price
FROM products
WHERE retail_price > 0
GROUP BY category, department
ORDER BY median DESC
""")

# Confirm K-Means k=3 territory: what price thresholds make sense?
run("Price quantiles for Budget/Mid/Premium cutoffs", """
SELECT
    ROUND(PERCENTILE_CONT(0.33) WITHIN GROUP (ORDER BY retail_price)::numeric, 2) AS p33_budget_cutoff,
    ROUND(PERCENTILE_CONT(0.67) WITHIN GROUP (ORDER BY retail_price)::numeric, 2) AS p67_premium_cutoff,
    ROUND(MIN(retail_price)::numeric, 2) AS min_price,
    ROUND(MAX(retail_price)::numeric, 2) AS max_price,
    ROUND(AVG(retail_price)::numeric, 2) AS avg_price,
    COUNT(*) AS total_products
FROM products WHERE retail_price > 0
""")

# Check num_sold distribution (for Layer 2 feature)
run("Sales volume per product distribution", """
SELECT
    CASE
        WHEN num_sold = 0 THEN '0 (not sold)'
        WHEN num_sold <= 5 THEN '1-5'
        WHEN num_sold <= 10 THEN '6-10'
        ELSE '11+'
    END AS sales_band,
    COUNT(*) AS num_products
FROM (
    SELECT p.id, COUNT(oi.id) AS num_sold
    FROM products p
    LEFT JOIN order_items oi ON p.id = oi.product_id AND oi.status != 'Cancelled'
    GROUP BY p.id
) t
GROUP BY 1 ORDER BY 1
""")
