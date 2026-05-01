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

# Sửa lỗi cast datetime cho Angle 3: Shipping Delay
run("Angle 3: Delivery Time by Distribution Center", """
SELECT 
    p.distribution_center_id,
    COUNT(*) as total_shipped,
    ROUND(AVG(EXTRACT(EPOCH FROM (oi.delivered_at::timestamp - oi.shipped_at::timestamp))/86400)::numeric, 2) as avg_transit_days,
    ROUND(AVG(EXTRACT(EPOCH FROM (oi.shipped_at::timestamp - oi.created_at::timestamp))/86400)::numeric, 2) as avg_processing_days
FROM order_items oi
JOIN products p ON oi.product_id = p.id
WHERE oi.delivered_at IS NOT NULL
GROUP BY 1
ORDER BY avg_transit_days DESC
""")

# Sửa lỗi cast datetime cho Angle 4: Inventory Turn-over
run("Angle 4: Time in Inventory by Category", """
SELECT 
    p.category,
    COUNT(*) as items_sold,
    ROUND(AVG(EXTRACT(EPOCH FROM (ii.sold_at::timestamp - ii.created_at::timestamp))/86400)::numeric, 2) as avg_days_to_sell
FROM inventory_items ii
JOIN products p ON ii.product_id = p.id
WHERE ii.sold_at IS NOT NULL
GROUP BY 1
ORDER BY avg_days_to_sell DESC
""")

# Kiểm tra phân phối của thời gian xử lý (Processing days) - có phải luôn là 0-3 ngày ngẫu nhiên?
run("Angle 3.1: Processing Time Distribution", """
WITH processing_times AS (
    SELECT 
        EXTRACT(EPOCH FROM (shipped_at::timestamp - created_at::timestamp))/86400 as processing_days
    FROM order_items
    WHERE shipped_at IS NOT NULL
)
SELECT 
    CASE 
        WHEN processing_days < 1 THEN 'Under 1 day'
        WHEN processing_days < 2 THEN '1-2 days'
        WHEN processing_days < 3 THEN '2-3 days'
        ELSE 'Over 3 days'
    END as processing_time_bucket,
    COUNT(*) as num_orders
FROM processing_times
GROUP BY 1
ORDER BY 1
""")
