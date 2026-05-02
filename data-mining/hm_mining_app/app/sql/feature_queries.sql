-- =====================================================================
--  Truy vấn trích xuất đặc trưng — chạy trực tiếp trong PostgreSQL
--  để tránh OOM khi dataset hơn 1 triệu khách hàng.
-- =====================================================================

-- ----- Q1: Fashion DNA + RFM cho mỗi khách hàng (Layer 1 input) -----
-- :cutoff_date    => DATE, mọi giao dịch t_dat <= cutoff được tính
-- Lưu ý: trên DB hiện tại t_dat là VARCHAR (do load CSV không cast type),
-- nên cần t_dat::date ở các chỗ làm số học. Khi ALTER COLUMN sang DATE
-- thì có thể bỏ các cast này để truy vấn dùng được index.
WITH joined AS (
    SELECT  t.customer_id,
            t.t_dat,
            t.price,
            t.sales_channel_id,
            a.index_group_name,
            a.product_group_name
    FROM    transactions t
    JOIN    articles a USING (article_id)
    WHERE   t.t_dat::date <= CAST(:cutoff_date AS date)
),
agg AS (
    SELECT
        customer_id,
        COUNT(*)                                                 AS total_items,
        AVG(price)                                               AS avg_price,
        SUM(price)                                               AS monetary,
        COUNT(DISTINCT t_dat)                                    AS frequency,
        MAX(t_dat::date)                                         AS last_purchase,
        AVG(CASE WHEN sales_channel_id = 2 THEN 1.0 ELSE 0.0 END) AS pct_online,
        AVG(CASE WHEN index_group_name = 'Ladieswear'    THEN 1.0 ELSE 0.0 END) AS pct_ladieswear,
        AVG(CASE WHEN index_group_name = 'Divided'       THEN 1.0 ELSE 0.0 END) AS pct_divided,
        AVG(CASE WHEN index_group_name = 'Menswear'      THEN 1.0 ELSE 0.0 END) AS pct_menswear,
        AVG(CASE WHEN index_group_name = 'Baby/Children' THEN 1.0 ELSE 0.0 END) AS pct_baby,
        AVG(CASE WHEN index_group_name = 'Sport'         THEN 1.0 ELSE 0.0 END) AS pct_sport
    FROM joined
    GROUP BY customer_id
)
SELECT
    a.customer_id,
    c.age,
    a.total_items,
    a.frequency,
    a.monetary,
    a.avg_price,
    a.pct_online,
    a.pct_ladieswear,
    a.pct_divided,
    a.pct_menswear,
    a.pct_baby,
    a.pct_sport,
    (CAST(:cutoff_date AS date) - a.last_purchase)::int AS recency_days
FROM agg a
LEFT JOIN customers c ON c.customer_id = a.customer_id;


-- ----- Q2: Giỏ hàng cho Apriori (Layer 2) ----------------------------
-- Mỗi (customer, ngày) là một giỏ hàng, sản phẩm gom theo product_group_name
-- :cluster_id => SMALLINT (chạy Apriori riêng cho từng cụm)
SELECT
    t.customer_id,
    t.t_dat,
    ARRAY_AGG(DISTINCT a.product_group_name ORDER BY a.product_group_name) AS items
FROM transactions t
JOIN articles a   USING (article_id)
JOIN customer_clusters cc ON cc.customer_id = t.customer_id
WHERE cc.cluster_id = :cluster_id
GROUP BY t.customer_id, t.t_dat
HAVING COUNT(DISTINCT a.product_group_name) >= 2;


-- ----- Q3: Nhãn will_buy (Layer 3) -----------------------------------
-- :cutoff_date    => DATE
-- :window_days    => INT (mặc định 7)
SELECT DISTINCT customer_id
FROM   transactions
WHERE  t_dat::date >  CAST(:cutoff_date AS date)
  AND  t_dat::date <= CAST(:cutoff_date AS date) + (:window_days || ' days')::interval;
