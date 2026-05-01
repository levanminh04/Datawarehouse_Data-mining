# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'datamining-version3'))
from database import query_db

def run(label, sql):
    print(f"\n{'='*65}\n  {label}\n{'='*65}")
    r = query_db(sql)
    if r is not None:
        print(r.to_string())
    return r

# Kiểm tra schema của bảng products
run("Schema of 'products' table", """
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'products'
""")

# Kiểm tra schema của bảng order_items
run("Schema of 'order_items' table", """
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'order_items'
""")

# Lấy 3 mẫu dữ liệu thực tế để xem chính xác nó có gì
run("Sample data from 'products'", """
SELECT id, category, retail_price, cost 
FROM products 
LIMIT 3
""")

run("Sample data from 'order_items'", """
SELECT id, order_id, product_id, sale_price, status 
FROM order_items 
LIMIT 3
""")
