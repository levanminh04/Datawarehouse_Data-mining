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

# So sánh 3 nước lớn: China, USA, Brasil về phân bổ Category
run("Category Distribution Comparison: China vs USA vs Brasil", """
WITH user_orders AS (
    SELECT 
        u.country,
        p.category
    FROM users u
    JOIN order_items oi ON u.id = oi.user_id
    JOIN products p ON oi.product_id = p.id
    WHERE u.country IN ('China', 'United States', 'Brasil')
),
country_counts AS (
    SELECT country, COUNT(*) as total_sold
    FROM user_orders
    GROUP BY country
),
cat_counts AS (
    SELECT country, category, COUNT(*) as cat_sold
    FROM user_orders
    GROUP BY country, category
)
SELECT 
    cc.category,
    ROUND(100.0 * MAX(CASE WHEN cc.country = 'China' THEN cc.cat_sold ELSE 0 END) / 
          MAX(CASE WHEN c_tot.country = 'China' THEN c_tot.total_sold ELSE 1 END), 2) AS china_pct,
          
    ROUND(100.0 * MAX(CASE WHEN cc.country = 'United States' THEN cc.cat_sold ELSE 0 END) / 
          MAX(CASE WHEN c_tot.country = 'United States' THEN c_tot.total_sold ELSE 1 END), 2) AS usa_pct,
          
    ROUND(100.0 * MAX(CASE WHEN cc.country = 'Brasil' THEN cc.cat_sold ELSE 0 END) / 
          MAX(CASE WHEN c_tot.country = 'Brasil' THEN c_tot.total_sold ELSE 1 END), 2) AS brasil_pct
FROM cat_counts cc
JOIN country_counts c_tot ON cc.country = c_tot.country
GROUP BY cc.category
ORDER BY china_pct DESC
""")

# So sánh hành vi mua hàng (Category) giữa Newbie (1 đơn) và VIP (>3 đơn)
run("Category Distribution Comparison: Newbie vs VIP", """
WITH user_order_counts AS (
    SELECT user_id, COUNT(DISTINCT order_id) as num_orders
    FROM orders
    GROUP BY user_id
),
user_segments AS (
    SELECT 
        user_id,
        CASE WHEN num_orders = 1 THEN 'Newbie'
             WHEN num_orders > 3 THEN 'VIP'
             ELSE 'Normal' END AS segment
    FROM user_order_counts
),
segment_purchases AS (
    SELECT 
        s.segment,
        p.category
    FROM user_segments s
    JOIN order_items oi ON s.user_id = oi.user_id
    JOIN products p ON oi.product_id = p.id
    WHERE s.segment IN ('Newbie', 'VIP')
),
segment_totals AS (
    SELECT segment, COUNT(*) as total_items
    FROM segment_purchases
    GROUP BY segment
),
segment_cat_counts AS (
    SELECT segment, category, COUNT(*) as cat_items
    FROM segment_purchases
    GROUP BY segment, category
)
SELECT 
    scc.category,
    ROUND(100.0 * MAX(CASE WHEN scc.segment = 'Newbie' THEN scc.cat_items ELSE 0 END) / 
          MAX(CASE WHEN st.segment = 'Newbie' THEN st.total_items ELSE 1 END), 2) AS newbie_pct,
          
    ROUND(100.0 * MAX(CASE WHEN scc.segment = 'VIP' THEN scc.cat_items ELSE 0 END) / 
          MAX(CASE WHEN st.segment = 'VIP' THEN st.total_items ELSE 1 END), 2) AS vip_pct
FROM segment_cat_counts scc
JOIN segment_totals st ON scc.segment = st.segment
GROUP BY scc.category
ORDER BY newbie_pct DESC
""")
