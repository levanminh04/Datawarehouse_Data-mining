# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'datamining-version3'))
from database import query_db

def run(label, sql):
    print(f"\n{'='*65}")
    print(f"  {label}")
    print(f"{'='*65}")
    r = query_db(sql)
    if r is not None:
        print(r.to_string())
    return r

# Q1: Kiểm tra Conversion Rate thực sự của từng Category
# So sánh Views (Anonymous) và Sales (Logged-in)
run("Q1: Conversion Rate by Category (Views vs Sales)", """
WITH views AS (
    SELECT 
        SPLIT_PART(uri, '/', 3)::int AS product_id,
        COUNT(*) AS total_views
    FROM events
    WHERE event_type = 'product' AND user_id IS NULL
    GROUP BY 1
),
sales AS (
    SELECT product_id, COUNT(*) AS total_sales
    FROM order_items
    WHERE status != 'Cancelled'
    GROUP BY 1
)
SELECT 
    p.category,
    SUM(v.total_views) AS views,
    SUM(s.total_sales) AS sales,
    ROUND(100.0 * SUM(s.total_sales) / NULLIF(SUM(v.total_views), 0), 2) AS conv_rate
FROM products p
LEFT JOIN views v ON p.id = v.product_id
LEFT JOIN sales s ON p.id = s.product_id
GROUP BY 1
HAVING SUM(v.total_views) > 100
ORDER BY conv_rate DESC
""")

# Q2: Kiểm tra tỷ lệ Abandonment (Hủy) của khách vãng lai theo Category
run("Q2: Anonymous Abandonment Rate by Category", """
WITH session_behavior AS (
    SELECT 
        session_id,
        MAX(CASE WHEN event_type = 'product' THEN SPLIT_PART(uri, '/', 3) END)::int AS product_id,
        MAX(CASE WHEN event_type = 'cancel' THEN 1 ELSE 0 END) AS is_cancelled,
        MAX(CASE WHEN event_type = 'cart' THEN 1 ELSE 0 END) AS added_to_cart
    FROM events
    WHERE user_id IS NULL
    GROUP BY session_id
)
SELECT 
    p.category,
    COUNT(*) AS total_sessions,
    SUM(is_cancelled) AS cancelled_sessions,
    ROUND(100.0 * SUM(is_cancelled) / COUNT(*), 2) AS cancel_rate
FROM session_behavior sb
JOIN products p ON sb.product_id = p.id
GROUP BY 1
ORDER BY cancel_rate DESC
""")

# Q3: Sự tương quan giữa Giá và tỷ lệ Hủy (Cancel)
run("Q3: Price vs Cancel Rate (Anonymous)", """
WITH session_behavior AS (
    SELECT 
        session_id,
        MAX(CASE WHEN event_type = 'product' THEN SPLIT_PART(uri, '/', 3) END)::int AS product_id,
        MAX(CASE WHEN event_type = 'cancel' THEN 1 ELSE 0 END) AS is_cancelled
    FROM events
    WHERE user_id IS NULL
    GROUP BY session_id
)
SELECT 
    CASE 
        WHEN p.retail_price < 20 THEN 'Under $20'
        WHEN p.retail_price < 50 THEN '$20 - $50'
        WHEN p.retail_price < 100 THEN '$50 - $100'
        ELSE 'Over $100'
    END AS price_range,
    COUNT(*) AS total_sessions,
    ROUND(100.0 * SUM(is_cancelled) / COUNT(*), 2) AS cancel_rate
FROM session_behavior sb
JOIN products p ON sb.product_id = p.id
WHERE p.retail_price IS NOT NULL
GROUP BY 1
ORDER BY 1
""")
