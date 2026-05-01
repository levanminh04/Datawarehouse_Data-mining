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
    else:
        print("QUERY FAILED")
    return r

# 15. What does URI look like?
run("15. URI samples from events", """
SELECT uri, event_type, COUNT(*) AS cnt
FROM events
WHERE user_id IS NOT NULL
GROUP BY uri, event_type
ORDER BY cnt DESC
LIMIT 30
""")

# 16. Cancel events - do they have user_id?
run("16. Cancel events with/without user_id", """
SELECT 
    event_type,
    COUNT(CASE WHEN user_id IS NOT NULL THEN 1 END) AS with_user,
    COUNT(CASE WHEN user_id IS NULL THEN 1 END) AS without_user,
    COUNT(*) AS total
FROM events
WHERE event_type IN ('cancel', 'purchase', 'cart')
GROUP BY event_type
""")

# 17. CRITICAL: Does first_order_num_items correlate with total monetary?
run("17. First order items vs total monetary quartile", """
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
    ROUND(AVG(ut.total_monetary), 2) AS avg_monetary,
    ROUND(AVG(ut.total_orders), 2) AS avg_orders,
    ROUND(AVG(CASE WHEN ut.total_orders >= 2 THEN 1.0 ELSE 0.0 END) * 100, 2) AS repeat_pct
FROM first_order_stats fos
JOIN user_total ut ON fos.user_id = ut.user_id
GROUP BY fos.first_order_items
ORDER BY fos.first_order_items
""")

# 18. Does traffic_source or browser have ANY signal for repeat buying?
run("18. Repeat rate by traffic_source", """
WITH user_orders AS (
    SELECT user_id, COUNT(DISTINCT order_id) AS total_orders
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id
)
SELECT u.traffic_source,
       COUNT(*) AS num_users,
       ROUND(AVG(CASE WHEN uo.total_orders >= 2 THEN 1.0 ELSE 0.0 END) * 100, 2) AS repeat_pct,
       ROUND(AVG(uo.total_orders), 2) AS avg_orders
FROM users u
JOIN user_orders uo ON u.id = uo.user_id
GROUP BY u.traffic_source
ORDER BY num_users DESC
""")

# 19. Does gender have signal for monetary?
run("19. Monetary by gender", """
SELECT u.gender, 
       COUNT(DISTINCT u.id) AS num_users,
       ROUND(AVG(t.total_monetary), 2) AS avg_monetary,
       ROUND(AVG(t.total_orders), 2) AS avg_orders
FROM users u
JOIN (
    SELECT user_id, SUM(sale_price) AS total_monetary, COUNT(DISTINCT order_id) AS total_orders
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id
) t ON u.id = t.user_id
GROUP BY u.gender
""")

# 20. CRITICAL: Category-pair co-purchase frequency (for Association Rules viability)
run("20. Top 15 category pairs bought together", """
WITH order_cats AS (
    SELECT DISTINCT oi.order_id, p.category
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE oi.status != 'Cancelled'
),
pairs AS (
    SELECT a.category AS cat_a, b.category AS cat_b, COUNT(DISTINCT a.order_id) AS pair_count
    FROM order_cats a
    JOIN order_cats b ON a.order_id = b.order_id AND a.category < b.category
    GROUP BY a.category, b.category
)
SELECT cat_a, cat_b, pair_count,
       ROUND(100.0 * pair_count / (SELECT COUNT(DISTINCT order_id) FROM order_items WHERE status != 'Cancelled'), 2) AS support_pct
FROM pairs
ORDER BY pair_count DESC
LIMIT 15
""")

# 21. Department distribution
run("21. Department distribution in products", """
SELECT department, COUNT(*) AS num_products,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM products
GROUP BY department
ORDER BY num_products DESC
""")

# 22. Can we extract product_id from URI? Sample URI patterns
run("22. URI pattern analysis", """
SELECT 
    CASE 
        WHEN uri LIKE '/product/%' THEN 'product_page'
        WHEN uri LIKE '/category/%' THEN 'category_page'
        WHEN uri LIKE '/' THEN 'home'
        ELSE 'other: ' || LEFT(uri, 30)
    END AS uri_pattern,
    COUNT(*) AS cnt
FROM events
WHERE user_id IS NOT NULL
GROUP BY 1
ORDER BY cnt DESC
LIMIT 20
""")

print("\n\n=== SURVEY 2 COMPLETE ===")
