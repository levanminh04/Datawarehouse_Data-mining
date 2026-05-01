# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'datamining-version3'))
from database import query_db

def run(label, sql):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    r = query_db(sql)
    if r is not None:
        print(r.to_string())
    return r

# Q1: Is "Intimates" just the most common Women's category?
run("Q1: Category frequency by department", """
SELECT p.department, p.category, COUNT(DISTINCT oi.order_id) AS orders_with_category,
       ROUND(100.0 * COUNT(DISTINCT oi.order_id)::numeric / 
             (SELECT COUNT(DISTINCT order_id) FROM order_items WHERE status != 'Cancelled'), 2) AS pct_of_all_orders
FROM order_items oi
JOIN products p ON oi.product_id = p.id
WHERE oi.status != 'Cancelled'
GROUP BY p.department, p.category
ORDER BY orders_with_category DESC
LIMIT 15
""")

# Q2: Do categories pair more within same department or cross-department?
run("Q2: Same-dept vs cross-dept pairs", """
WITH order_dept_cats AS (
    SELECT DISTINCT oi.order_id, p.department, p.category
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE oi.status != 'Cancelled'
),
pairs AS (
    SELECT a.order_id, a.department AS dept_a, b.department AS dept_b
    FROM order_dept_cats a
    JOIN order_dept_cats b ON a.order_id = b.order_id AND a.category < b.category
)
SELECT 
    CASE WHEN dept_a = dept_b THEN 'Same Department' ELSE 'Cross Department' END AS pair_type,
    COUNT(*) AS pair_count,
    ROUND(100.0 * COUNT(*)::numeric / SUM(COUNT(*)) OVER(), 2) AS pct
FROM pairs
GROUP BY 1
""")

# Q3: What does a truly frequency-based VIP look like?
run("Q3: Users with 3+ orders - profile", """
SELECT 
    CASE 
        WHEN total_orders = 1 THEN '1 order'
        WHEN total_orders = 2 THEN '2 orders'
        WHEN total_orders = 3 THEN '3 orders'
        WHEN total_orders = 4 THEN '4 orders'
    END AS order_group,
    COUNT(*) AS num_users,
    ROUND(AVG(monetary)::numeric, 2) AS avg_monetary,
    ROUND(AVG(aov)::numeric, 2) AS avg_aov,
    ROUND(AVG(num_categories)::numeric, 2) AS avg_categories
FROM (
    SELECT user_id,
           COUNT(DISTINCT order_id) AS total_orders,
           SUM(sale_price) AS monetary,
           AVG(sale_price) AS aov,
           COUNT(DISTINCT p_cat) AS num_categories
    FROM (
        SELECT oi.user_id, oi.order_id, oi.sale_price, p.category AS p_cat
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.status != 'Cancelled'
    ) t
    GROUP BY user_id
) u
GROUP BY total_orders
ORDER BY total_orders
""")

# Q4: Do multi-department orders exist and have different return patterns?
run("Q4: Multi-dept orders", """
SELECT num_departments, COUNT(*) AS num_orders,
       ROUND(100.0 * COUNT(*)::numeric / SUM(COUNT(*)) OVER(), 2) AS pct
FROM (
    SELECT oi.order_id, COUNT(DISTINCT p.department) AS num_departments
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE oi.status != 'Cancelled'
    GROUP BY oi.order_id
) t
GROUP BY num_departments ORDER BY num_departments
""")

# Q5: Do Men and Women have different purchasing patterns?
run("Q5: Men vs Women purchasing (by user gender)", """
SELECT u.gender,
       COUNT(DISTINCT oi.user_id) AS num_users,
       ROUND(AVG(user_stats.total_orders)::numeric, 2) AS avg_orders,
       ROUND(AVG(user_stats.monetary)::numeric, 2) AS avg_monetary,
       ROUND(AVG(user_stats.avg_price)::numeric, 2) AS avg_item_price
FROM users u
JOIN (
    SELECT user_id,
           COUNT(DISTINCT order_id) AS total_orders,
           SUM(sale_price) AS monetary,
           AVG(sale_price) AS avg_price
    FROM order_items WHERE status != 'Cancelled'
    GROUP BY user_id
) user_stats ON u.id = user_stats.user_id
JOIN order_items oi ON u.id = oi.user_id
GROUP BY u.gender
""")

# Q6: Top category pairs WITHIN same department
run("Q6: Top pairs within Women's dept", """
WITH women_order_cats AS (
    SELECT DISTINCT oi.order_id, p.category
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE oi.status != 'Cancelled' AND p.department = 'Women'
),
pairs AS (
    SELECT a.category AS cat_a, b.category AS cat_b, COUNT(DISTINCT a.order_id) AS pair_count
    FROM women_order_cats a
    JOIN women_order_cats b ON a.order_id = b.order_id AND a.category < b.category
    GROUP BY a.category, b.category
)
SELECT cat_a, cat_b, pair_count FROM pairs ORDER BY pair_count DESC LIMIT 10
""")

run("Q7: Top pairs within Men's dept", """
WITH men_order_cats AS (
    SELECT DISTINCT oi.order_id, p.category
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE oi.status != 'Cancelled' AND p.department = 'Men'
),
pairs AS (
    SELECT a.category AS cat_a, b.category AS cat_b, COUNT(DISTINCT a.order_id) AS pair_count
    FROM men_order_cats a
    JOIN men_order_cats b ON a.order_id = b.order_id AND a.category < b.category
    GROUP BY a.category, b.category
)
SELECT cat_a, cat_b, pair_count FROM pairs ORDER BY pair_count DESC LIMIT 10
""")

print("\n=== BUSINESS LOGIC SURVEY COMPLETE ===")
