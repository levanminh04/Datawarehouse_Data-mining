# -*- coding: utf-8 -*-
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

# Q: Do first_order_num_items correlate with frequency (not monetary)?
run("first_order_items vs frequency & repeat_pct", """
WITH first_order AS (
    SELECT user_id, order_id,
           ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY MIN(created_at)) AS rn
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id, order_id
),
first_order_stats AS (
    SELECT fo.user_id, COUNT(*) AS first_order_items
    FROM first_order fo
    JOIN order_items oi ON fo.order_id = oi.order_id AND fo.user_id = oi.user_id
    WHERE fo.rn = 1
    GROUP BY fo.user_id
),
user_total AS (
    SELECT user_id, COUNT(DISTINCT order_id) AS total_orders
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id
)
SELECT
    fos.first_order_items,
    COUNT(*) AS num_users,
    ROUND(AVG(ut.total_orders)::numeric, 3) AS avg_total_orders,
    ROUND(100.0 * AVG(CASE WHEN ut.total_orders >= 2 THEN 1.0 ELSE 0.0 END)::numeric, 2) AS repeat_pct
FROM first_order_stats fos
JOIN user_total ut ON fos.user_id = ut.user_id
GROUP BY fos.first_order_items
ORDER BY fos.first_order_items
""")

# Q: What actually differs between VIP (freq=2.84) and Vang Lai (freq=1.23)?
run("VIP cluster vs Vang Lai: first_order features", """
WITH ranked_orders AS (
    SELECT user_id, order_id,
           ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY MIN(created_at)) AS rn
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id, order_id
),
first_order_features AS (
    SELECT fo.user_id,
           COUNT(oi.id) AS first_order_num_items,
           COUNT(DISTINCT p.category) AS first_order_num_categories
    FROM (SELECT user_id, order_id FROM ranked_orders WHERE rn=1) fo
    JOIN order_items oi ON fo.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.id
    GROUP BY fo.user_id
)
SELECT 
    CASE 
        WHEN total_orders >= 2 THEN 'Repeat (>=2 orders)'
        ELSE 'One-time (1 order)'
    END AS buyer_type,
    COUNT(*) AS num_users,
    ROUND(AVG(fof.first_order_num_items)::numeric, 3) AS avg_first_items,
    ROUND(AVG(fof.first_order_num_categories)::numeric, 3) AS avg_first_cats
FROM first_order_features fof
JOIN (
    SELECT user_id, COUNT(DISTINCT order_id) AS total_orders
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id
) ut ON fof.user_id = ut.user_id
GROUP BY 1 ORDER BY 1
""")
