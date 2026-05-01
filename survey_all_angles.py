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

# Angle 1: Age vs Category
# Có sự khác biệt về độ tuổi khi mua các Category khác nhau không?
run("Angle 1: Average Age by Category", """
SELECT 
    p.category,
    COUNT(*) as total_orders,
    ROUND(AVG(u.age)::numeric, 1) as avg_age,
    ROUND(STDDEV(u.age)::numeric, 1) as std_age
FROM users u
JOIN order_items oi ON u.id = oi.user_id
JOIN products p ON oi.product_id = p.id
GROUP BY 1
ORDER BY avg_age DESC
""")

# Angle 2: Traffic Source vs Price Tier
# Nguồn traffic khác nhau (Ad, Organic) có mua đồ giá trị khác nhau không?
run("Angle 2: Traffic Source vs Avg Spend", """
SELECT 
    u.traffic_source,
    COUNT(DISTINCT oi.order_id) as total_orders,
    ROUND(AVG(oi.sale_price)::numeric, 2) as avg_item_price,
    ROUND(AVG(o.num_of_item)::numeric, 2) as avg_items_per_order
FROM users u
JOIN orders o ON u.id = o.user_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY 1
ORDER BY total_orders DESC
""")

# Angle 3: Shipping Delay (Delivery Time) by Distribution Center
# Có dự đoán được thời gian giao hàng dựa vào kho không?
run("Angle 3: Delivery Time by Distribution Center", """
SELECT 
    p.distribution_center_id,
    COUNT(*) as total_shipped,
    ROUND(AVG(EXTRACT(EPOCH FROM (oi.delivered_at - oi.shipped_at))/86400)::numeric, 2) as avg_transit_days,
    ROUND(AVG(EXTRACT(EPOCH FROM (oi.shipped_at - oi.created_at))/86400)::numeric, 2) as avg_processing_days
FROM order_items oi
JOIN products p ON oi.product_id = p.id
WHERE oi.delivered_at IS NOT NULL
GROUP BY 1
ORDER BY avg_transit_days DESC
LIMIT 10
""")

# Angle 4: Inventory Turn-over (Time to sell)
# Khoảng thời gian từ lúc tạo item trong kho đến lúc bán được
run("Angle 4: Time in Inventory by Category", """
SELECT 
    p.category,
    COUNT(*) as items_sold,
    ROUND(AVG(EXTRACT(EPOCH FROM (ii.sold_at - ii.created_at))/86400)::numeric, 2) as avg_days_to_sell
FROM inventory_items ii
JOIN products p ON ii.product_id = p.id
WHERE ii.sold_at IS NOT NULL
GROUP BY 1
ORDER BY avg_days_to_sell DESC
""")

# Angle 5: Event Browsing depth vs Purchase probability
# Số lượng event trong 1 session có ảnh hưởng tỉ lệ mua không? (check kỹ lại event sequence)
run("Angle 5: Events per Session vs Purchase", """
WITH session_stats AS (
    SELECT 
        session_id,
        COUNT(*) as total_events,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as has_purchase
    FROM events
    GROUP BY 1
)
SELECT 
    CASE 
        WHEN total_events = 1 THEN '1 event'
        WHEN total_events BETWEEN 2 AND 5 THEN '2-5 events'
        WHEN total_events BETWEEN 6 AND 10 THEN '6-10 events'
        ELSE '11+ events'
    END AS event_count_bucket,
    COUNT(*) as total_sessions,
    ROUND(100.0 * SUM(has_purchase) / COUNT(*), 2) as purchase_rate
FROM session_stats
GROUP BY 1
ORDER BY 1
""")
