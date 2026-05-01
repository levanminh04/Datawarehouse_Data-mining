# -*- coding: utf-8 -*-
"""
FRESH DIRECTION VALIDATION QUERIES
Checking product-level analysis viability BEFORE any code is written.
Goal: Find a direction that doesn't hit the documented flaws.
"""
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

# ====================================================
# DIRECTION A: PRODUCT-LEVEL ANALYSIS
# products table has: brand, category, department, retail_price, cost
# ====================================================

# A1: Is there real margin variation? (retail_price - cost)
run("A1: Profit margin distribution across products", """
SELECT
    CASE
        WHEN margin_pct < 0.3  THEN '1. Low (<30%)'
        WHEN margin_pct < 0.5  THEN '2. Mid (30-50%)'
        WHEN margin_pct < 0.7  THEN '3. High (50-70%)'
        ELSE                        '4. Premium (>70%)'
    END AS margin_band,
    COUNT(*) AS num_products,
    ROUND(MIN(retail_price)::numeric, 2) AS min_price,
    ROUND(MAX(retail_price)::numeric, 2) AS max_price,
    ROUND(AVG(retail_price)::numeric, 2) AS avg_price
FROM (
    SELECT id, retail_price, cost,
           (retail_price - cost) / NULLIF(retail_price, 0) AS margin_pct
    FROM products WHERE cost > 0 AND retail_price > 0
) t
GROUP BY 1 ORDER BY 1
""")

# A2: Does BRAND predict price tier? (Key signal check for Layer 2)
run("A2: Top 20 brands by avg retail_price (brand vs price tier)", """
SELECT brand, COUNT(*) AS num_products,
       ROUND(AVG(retail_price)::numeric, 2) AS avg_price,
       ROUND(MIN(retail_price)::numeric, 2) AS min_price,
       ROUND(MAX(retail_price)::numeric, 2) AS max_price,
       ROUND(STDDEV(retail_price)::numeric, 2) AS std_price
FROM products
WHERE brand IS NOT NULL
GROUP BY brand
HAVING COUNT(*) >= 5
ORDER BY avg_price DESC
LIMIT 20
""")

# A3: Does category predict margin? (Is margin random or structured?)
run("A3: Margin by category", """
SELECT p.category,
       COUNT(*) AS num_products,
       ROUND(AVG((retail_price - cost) / NULLIF(retail_price, 0))::numeric * 100, 2) AS avg_margin_pct,
       ROUND(STDDEV((retail_price - cost) / NULLIF(retail_price, 0))::numeric * 100, 2) AS std_margin_pct
FROM products p
WHERE cost > 0 AND retail_price > 0
GROUP BY p.category
ORDER BY avg_margin_pct DESC
""")

# A4: How many unique brands? Too few = boring rules
run("A4: Brand count and multi-brand order potential", """
SELECT
    (SELECT COUNT(DISTINCT brand) FROM products WHERE brand IS NOT NULL) AS unique_brands,
    (SELECT COUNT(DISTINCT brand) FROM products 
     WHERE brand IS NOT NULL AND brand != '') AS non_empty_brands,
    (SELECT COUNT(DISTINCT p.brand)
     FROM order_items oi
     JOIN products p ON oi.product_id = p.id
     WHERE oi.status != 'Cancelled') AS brands_actually_purchased
""")

# A5: PRODUCT-LEVEL return rate — is it still flat at product level?
run("A5: Product return rate distribution (is it still 10% flat?)", """
WITH product_stats AS (
    SELECT p.id AS product_id, p.brand, p.category,
           COUNT(*) AS total_sold,
           SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END) AS total_returned,
           ROUND(100.0 * SUM(CASE WHEN oi.status = 'Returned' THEN 1 ELSE 0 END)
                 / NULLIF(COUNT(*), 0)::numeric, 1) AS return_pct
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    GROUP BY p.id, p.brand, p.category
    HAVING COUNT(*) >= 10
)
SELECT
    CASE
        WHEN return_pct = 0   THEN '0%'
        WHEN return_pct <= 5  THEN '1-5%'
        WHEN return_pct <= 10 THEN '6-10%'
        WHEN return_pct <= 15 THEN '11-15%'
        WHEN return_pct <= 20 THEN '16-20%'
        ELSE '>20%'
    END AS return_band,
    COUNT(*) AS num_products,
    ROUND(AVG(return_pct)::numeric, 2) AS avg_return_pct
FROM product_stats
GROUP BY 1 ORDER BY 1
""")

# A6: Multi-brand orders — enough for brand association rules?
run("A6: Multi-brand order stats", """
WITH order_brands AS (
    SELECT oi.order_id, COUNT(DISTINCT p.brand) AS num_brands
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE oi.status != 'Cancelled' AND p.brand IS NOT NULL AND p.brand != ''
    GROUP BY oi.order_id
)
SELECT num_brands,
       COUNT(*) AS num_orders,
       ROUND(100.0 * COUNT(*)::numeric / SUM(COUNT(*)) OVER(), 2) AS pct
FROM order_brands
GROUP BY num_brands
ORDER BY num_brands
""")

# ====================================================
# DIRECTION B: SESSION FUNNEL ANALYSIS (events table)
# Can we segment sessions by BROWSING DEPTH before purchase?
# ====================================================

# B1: Do anonymous sessions (user_id NULL) show different funnel behavior?
run("B1: Funnel depth by event type for anonymous vs logged", """
SELECT
    CASE WHEN user_id IS NULL THEN 'Anonymous' ELSE 'Logged-in' END AS user_type,
    event_type,
    COUNT(*) AS total_events,
    COUNT(DISTINCT session_id) AS sessions_with_this_event
FROM events
GROUP BY 1, 2
ORDER BY 1, total_events DESC
""")

# B2: Within a session for logged users - how many UNIQUE product URIs?
# Products browsed - measures consideration set size
run("B2: Products in URI per session (browsing depth)", """
SELECT
    CASE
        WHEN unique_products <= 1 THEN '1 product'
        WHEN unique_products <= 3 THEN '2-3 products'
        WHEN unique_products <= 5 THEN '4-5 products'
        ELSE '6+ products'
    END AS browse_depth,
    COUNT(*) AS num_sessions,
    ROUND(100.0 * COUNT(*)::numeric / SUM(COUNT(*)) OVER(), 2) AS pct
FROM (
    SELECT session_id, COUNT(DISTINCT uri) AS unique_products
    FROM events
    WHERE event_type = 'product' AND user_id IS NOT NULL
    GROUP BY session_id
) t
GROUP BY 1 ORDER BY 1
""")

# B3: Can we extract product_id from product URIs?
run("B3: Product URI pattern sample", """
SELECT uri, COUNT(*) AS cnt
FROM events
WHERE event_type = 'product' AND user_id IS NOT NULL
GROUP BY uri
ORDER BY cnt DESC
LIMIT 10
""")

# ====================================================
# DIRECTION C: BRAND CO-PURCHASE RULES
# More granular than category (26 cats vs many brands)
# ====================================================

# C1: Top brand pairs in same order
run("C1: Top brand co-purchase pairs", """
WITH order_brands AS (
    SELECT DISTINCT oi.order_id, p.brand
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE oi.status != 'Cancelled'
    AND p.brand IS NOT NULL AND p.brand != ''
),
pairs AS (
    SELECT a.brand AS brand_a, b.brand AS brand_b,
           COUNT(DISTINCT a.order_id) AS pair_count
    FROM order_brands a
    JOIN order_brands b ON a.order_id = b.order_id AND a.brand < b.brand
    GROUP BY a.brand, b.brand
)
SELECT brand_a, brand_b, pair_count,
       ROUND(100.0 * pair_count::numeric /
             (SELECT COUNT(DISTINCT order_id) FROM order_items WHERE status != 'Cancelled'), 3) AS support_pct
FROM pairs
WHERE pair_count >= 50
ORDER BY pair_count DESC
LIMIT 20
""")

print("\n\n=== FRESH DIRECTION VALIDATION COMPLETE ===")
