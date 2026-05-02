# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'datamining-version2'))
from database import query_db

def run(label, sql):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    r = query_db(sql)
    if r is not None:
        print(r.to_string())
    return r

# 17 FIX: First order items vs total monetary
run("17. First order items vs total engagement", """
WITH first_order AS (
    SELECT user_id, order_id,
           ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY created_at) AS rn
    FROM order_items
    WHERE status != 'Cancelled'
),
first_order_stats AS (
    SELECT fo.user_id, COUNT(*) AS first_order_items
    FROM first_order fo
    JOIN order_items oi ON fo.order_id = oi.order_id AND fo.user_id = oi.user_id
    WHERE fo.rn = 1
    GROUP BY fo.user_id
),
user_total AS (
    SELECT user_id, SUM(sale_price) AS total_monetary,
           COUNT(DISTINCT order_id) AS total_orders
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id
)
SELECT 
    fos.first_order_items,
    COUNT(*) AS num_users,
    ROUND(AVG(ut.total_monetary)::numeric, 2) AS avg_monetary,
    ROUND(AVG(ut.total_orders)::numeric, 2) AS avg_orders,
    ROUND(AVG(CASE WHEN ut.total_orders >= 2 THEN 1.0 ELSE 0.0 END)::numeric * 100, 2) AS repeat_pct
FROM first_order_stats fos
JOIN user_total ut ON fos.user_id = ut.user_id
GROUP BY fos.first_order_items
ORDER BY fos.first_order_items
""")

# 19 FIX: Monetary by gender
run("19. Monetary by gender", """
SELECT u.gender, 
       COUNT(DISTINCT u.id) AS num_users,
       ROUND(AVG(t.total_monetary)::numeric, 2) AS avg_monetary,
       ROUND(AVG(t.total_orders)::numeric, 2) AS avg_orders
FROM users u
JOIN (
    SELECT user_id, SUM(sale_price) AS total_monetary, COUNT(DISTINCT order_id) AS total_orders
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id
) t ON u.id = t.user_id
GROUP BY u.gender
""")

# 23. CRITICAL: Can we extract category from URI for browsed-vs-bought analysis?
run("23. Category extraction from product URIs", """
SELECT 
    SPLIT_PART(uri, '/', 5) AS browsed_category,
    COUNT(*) AS view_count
FROM events
WHERE event_type = 'product' AND user_id IS NOT NULL
AND uri LIKE '/product/%'
GROUP BY 1
ORDER BY view_count DESC
LIMIT 20
""")

# 24. How many unique products (from URI) does each user browse per session?
run("24. Products browsed per session", """
SELECT 
    CASE 
        WHEN products_browsed = 1 THEN '1'
        WHEN products_browsed = 2 THEN '2'
        WHEN products_browsed = 3 THEN '3'
        WHEN products_browsed >= 4 THEN '4+'
    END AS products_per_session,
    COUNT(*) AS num_sessions,
    ROUND(100.0 * COUNT(*)::numeric / SUM(COUNT(*)) OVER(), 2) AS pct
FROM (
    SELECT session_id, COUNT(CASE WHEN event_type = 'product' THEN 1 END) AS products_browsed
    FROM events WHERE user_id IS NOT NULL
    GROUP BY session_id
) t
GROUP BY 1 ORDER BY 1
""")

# 25. CRITICAL: Check if browsed category matches purchased category
run("25. Browse-vs-Buy match rate (sample)", """
WITH session_browsed AS (
    SELECT user_id, session_id,
           SPLIT_PART(uri, '/', 5) AS browsed_cat
    FROM events
    WHERE event_type = 'department' AND user_id IS NOT NULL
    AND uri LIKE '/department/%'
),
session_purchased AS (
    SELECT e.user_id, e.session_id, p.category AS purchased_cat
    FROM events e
    JOIN order_items oi ON e.user_id = oi.user_id
    JOIN products p ON oi.product_id = p.id
    WHERE e.event_type = 'purchase' AND e.user_id IS NOT NULL
)
SELECT COUNT(*) AS total_browse_events
FROM session_browsed
LIMIT 1
""")

print("\n=== SURVEY 3 COMPLETE ===")
