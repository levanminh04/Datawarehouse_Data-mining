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

run("Q3: Category comparison: China vs Brasil vs France", """
WITH country_cat AS (
    SELECT 
        u.country,
        p.category,
        COUNT(*) AS cnt
    FROM users u
    JOIN order_items oi ON u.id = oi.user_id
    JOIN products p ON oi.product_id = p.id
    WHERE u.country IN ('China', 'Brasil', 'France')
    GROUP BY 1, 2
),
country_total AS (
    SELECT country, SUM(cnt) as total FROM country_cat GROUP BY country
)
SELECT 
    cc.category,
    ROUND(100.0 * MAX(CASE WHEN cc.country = 'China' THEN cc.cnt ELSE 0 END) / ct_china.total, 2) as china_pct,
    ROUND(100.0 * MAX(CASE WHEN cc.country = 'Brasil' THEN cc.cnt ELSE 0 END) / ct_brasil.total, 2) as brasil_pct,
    ROUND(100.0 * MAX(CASE WHEN cc.country = 'France' THEN cc.cnt ELSE 0 END) / ct_france.total, 2) as france_pct
FROM country_cat cc
JOIN country_total ct_china ON ct_china.country = 'China'
JOIN country_total ct_brasil ON ct_brasil.country = 'Brasil'
JOIN country_total ct_france ON ct_france.country = 'France'
GROUP BY 1
ORDER BY 2 DESC
""")
