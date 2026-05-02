# -*- coding: utf-8 -*-
import sys, io, os
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'datamining-version3'))
from database import query_db

def run(label, sql):
    print(f"\n{'='*65}\n  {label}\n{'='*65}")
    r = query_db(sql)
    if r is not None:
        print(r.to_string())
    return r

# Q1: Return rate by Brand for brands with HIGH volume (>= 500 sales)
# If it's just random noise around 10%, all high-volume brands will be ~10%.
# If there's real signal, some high-volume brands will be >15% or <5%.
run("Q1: Return rate for High-Volume Brands (>= 500 sales)", """
WITH brand_stats AS (
    SELECT 
        p.brand,
        COUNT(*) AS total_sold,
        SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END) AS total_returned
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE p.brand IS NOT NULL AND p.brand != ''
    GROUP BY p.brand
    HAVING COUNT(*) >= 500
)
SELECT 
    brand,
    total_sold,
    total_returned,
    ROUND(100.0 * total_returned / total_sold, 2) AS return_rate
FROM brand_stats
ORDER BY return_rate DESC
LIMIT 20
""")

run("Q1.2: Return rate for High-Volume Brands (Bottom 10)", """
WITH brand_stats AS (
    SELECT 
        p.brand,
        COUNT(*) AS total_sold,
        SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END) AS total_returned
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE p.brand IS NOT NULL AND p.brand != ''
    GROUP BY p.brand
    HAVING COUNT(*) >= 500
)
SELECT 
    brand,
    total_sold,
    total_returned,
    ROUND(100.0 * total_returned / total_sold, 2) AS return_rate
FROM brand_stats
ORDER BY return_rate ASC
LIMIT 10
""")

# Q2: Return rate by Category for high volume categories (>= 5000 sales)
run("Q2: Return rate by Category", """
WITH cat_stats AS (
    SELECT 
        p.category,
        COUNT(*) AS total_sold,
        SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END) AS total_returned
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    GROUP BY p.category
    HAVING COUNT(*) >= 1000
)
SELECT 
    category,
    total_sold,
    total_returned,
    ROUND(100.0 * total_returned / total_sold, 2) AS return_rate
FROM cat_stats
ORDER BY return_rate DESC
""")

# Q3: Margin vs Return Rate (Are high margin products returned more?)
run("Q3: Margin vs Return Rate at Product Level (Min 50 sales)", """
WITH prod_stats AS (
    SELECT 
        p.id,
        (p.retail_price - p.cost) / p.retail_price AS margin_pct,
        COUNT(*) AS total_sold,
        SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END) AS total_returned,
        ROUND(100.0 * SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 2) AS return_rate
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    GROUP BY p.id, p.retail_price, p.cost
    HAVING COUNT(*) >= 50
)
SELECT 
    CASE 
        WHEN margin_pct < 0.4 THEN 'Low Margin (<40%)'
        WHEN margin_pct < 0.55 THEN 'Mid Margin (40-55%)'
        ELSE 'High Margin (>55%)'
    END AS margin_band,
    COUNT(*) AS num_products,
    ROUND(AVG(return_rate)::numeric, 2) AS avg_return_rate,
    ROUND(MIN(return_rate)::numeric, 2) AS min_return_rate,
    ROUND(MAX(return_rate)::numeric, 2) AS max_return_rate
FROM prod_stats
GROUP BY 1
ORDER BY 1
""")

print("\n=== VERIFICATION COMPLETE ===")
