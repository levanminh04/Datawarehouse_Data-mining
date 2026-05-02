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

# 1. Status distribution
run("1. Status Distribution (order_items)", """
SELECT status, COUNT(*) AS cnt, 
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM order_items GROUP BY status ORDER BY cnt DESC
""")

# 2. Event type distribution
run("2. Event Type Distribution", """
SELECT event_type, COUNT(*) AS cnt,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM events GROUP BY event_type ORDER BY cnt DESC
""")

# 3. User overlap
run("3. User Overlap (events vs orders)", """
WITH ev AS (SELECT DISTINCT user_id FROM events WHERE user_id IS NOT NULL),
     oi AS (SELECT DISTINCT user_id FROM order_items)
SELECT 
    (SELECT COUNT(*) FROM ev) AS users_with_events,
    (SELECT COUNT(*) FROM oi) AS users_with_orders,
    (SELECT COUNT(*) FROM ev e INNER JOIN oi o ON e.user_id = o.user_id) AS users_with_both
""")

# 4. Categories count
run("4. Category Counts", """
SELECT COUNT(DISTINCT category) AS num_categories FROM products
""")

# 5. Items per order
run("5. Items per Order Stats", """
SELECT 
    ROUND(AVG(item_count), 2) AS avg_items,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY item_count) AS median_items,
    MAX(item_count) AS max_items
FROM (SELECT order_id, COUNT(*) AS item_count FROM order_items GROUP BY order_id) t
""")

# 6. Return rate reality check - is it truly random?
run("6. Return Rate by Category (Top 15)", """
SELECT p.category, 
       COUNT(*) AS total_items,
       SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END) AS returned,
       ROUND(100.0 * SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 2) AS return_pct
FROM order_items oi
JOIN products p ON oi.product_id = p.id
GROUP BY p.category
ORDER BY total_items DESC
LIMIT 15
""")

# 7. Return rate by price range - is there a signal?
run("7. Return Rate by Price Range", """
SELECT 
    CASE 
        WHEN sale_price < 20 THEN '01. <20'
        WHEN sale_price < 50 THEN '02. 20-50'
        WHEN sale_price < 100 THEN '03. 50-100'
        WHEN sale_price < 200 THEN '04. 100-200'
        ELSE '05. 200+'
    END AS price_range,
    COUNT(*) AS total,
    SUM(CASE WHEN status = 'Returned' THEN 1 ELSE 0 END) AS returned,
    ROUND(100.0 * SUM(CASE WHEN status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 2) AS return_pct
FROM order_items
GROUP BY 1
ORDER BY 1
""")

# 8. Event sequence patterns - does conversion funnel exist?
run("8. Event Funnel per Session (users with orders)", """
SELECT 
    event_type,
    COUNT(*) AS total_events,
    COUNT(DISTINCT session_id) AS sessions_with_event,
    ROUND(100.0 * COUNT(DISTINCT session_id) / 
        (SELECT COUNT(DISTINCT session_id) FROM events WHERE user_id IS NOT NULL), 2) AS pct_sessions
FROM events
WHERE user_id IS NOT NULL
GROUP BY event_type
ORDER BY total_events DESC
""")

# 9. Does multi-category purchase exist (for association rules)?
run("9. Orders with Multiple Categories", """
SELECT num_categories, COUNT(*) AS num_orders, 
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM (
    SELECT oi.order_id, COUNT(DISTINCT p.category) AS num_categories
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    GROUP BY oi.order_id
) t
GROUP BY num_categories
ORDER BY num_categories
""")

# 10. Repeat buyer distribution
run("10. Repeat Buyer Distribution", """
SELECT total_orders, COUNT(*) AS num_users,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM (
    SELECT user_id, COUNT(DISTINCT order_id) AS total_orders
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id
) t
GROUP BY total_orders
ORDER BY total_orders
LIMIT 15
""")

# 11. CRITICAL: Check if return status is randomly assigned
run("11. Return Rate by Age Group (Signal Check)", """
SELECT 
    CASE 
        WHEN u.age < 25 THEN '18-24'
        WHEN u.age < 35 THEN '25-34'
        WHEN u.age < 45 THEN '35-44'
        WHEN u.age < 55 THEN '45-54'
        ELSE '55+'
    END AS age_group,
    COUNT(*) AS total,
    SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END) AS returned,
    ROUND(100.0 * SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 2) AS return_pct
FROM order_items oi
JOIN users u ON oi.user_id = u.id
GROUP BY 1
ORDER BY 1
""")

# 12. CRITICAL: Check if events have meaningful sequence_number patterns
run("12. Session Depth Distribution", """
SELECT 
    CASE 
        WHEN max_seq <= 5 THEN '01. 1-5'
        WHEN max_seq <= 10 THEN '02. 6-10'
        WHEN max_seq <= 20 THEN '03. 11-20'
        WHEN max_seq <= 50 THEN '04. 21-50'
        ELSE '05. 50+'
    END AS depth_range,
    COUNT(*) AS num_sessions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM (
    SELECT session_id, MAX(sequence_number) AS max_seq
    FROM events WHERE user_id IS NOT NULL
    GROUP BY session_id
) t
GROUP BY 1 ORDER BY 1
""")

# 13. Do purchase events correlate with order_items?
run("13. Purchase Events vs Order Items", """
SELECT 
    (SELECT COUNT(*) FROM events WHERE event_type = 'purchase' AND user_id IS NOT NULL) AS purchase_events,
    (SELECT COUNT(DISTINCT order_id) FROM order_items WHERE status != 'Cancelled') AS distinct_orders,
    (SELECT COUNT(*) FROM order_items WHERE status != 'Cancelled') AS total_order_items
""")

# 14. KEY: Does the data have product_id in events? Can we trace what they viewed?
run("14. Events Table Columns Check", """
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'events'
ORDER BY ordinal_position
""")

print("\n\n=== ALL SURVEYS COMPLETE ===")
