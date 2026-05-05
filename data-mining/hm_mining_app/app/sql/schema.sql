-- =====================================================================
--  H&M Mining App — schema PostgreSQL
--  Khớp với mô tả trong báo cáo: bảng customers, articles, transactions
--  Bổ sung 3 bảng phục vụ vận hành: customer_clusters, model_registry,
--  prediction_log (để hệ thống "học liên tục" có dữ liệu phản hồi).
-- =====================================================================

-- 1. Khách hàng -------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    customer_id          VARCHAR(64) PRIMARY KEY,
    fn                   SMALLINT,
    active               SMALLINT,
    club_member_status   VARCHAR(20),
    fashion_news_frequency VARCHAR(20),
    age                  SMALLINT,
    postal_code          VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_customers_age ON customers(age);

-- 2. Sản phẩm ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS articles (
    article_id           VARCHAR(20) PRIMARY KEY,
    product_code         VARCHAR(20),
    prod_name            VARCHAR(255),
    product_type_no      INT,
    product_type_name    VARCHAR(120),
    product_group_name   VARCHAR(120),
    graphical_appearance_no INT,
    graphical_appearance_name VARCHAR(120),
    colour_group_code    INT,
    colour_group_name    VARCHAR(120),
    department_no        INT,
    department_name      VARCHAR(120),
    index_code           VARCHAR(8),
    index_name           VARCHAR(120),
    index_group_no       INT,
    index_group_name     VARCHAR(120),  -- 5 giá trị: Ladieswear, Divided, Menswear, Baby/Children, Sport
    section_no           INT,
    section_name         VARCHAR(120),
    garment_group_no     INT,
    garment_group_name   VARCHAR(120),
    detail_desc          TEXT
);
CREATE INDEX IF NOT EXISTS idx_articles_index_group ON articles(index_group_name);
CREATE INDEX IF NOT EXISTS idx_articles_product_group ON articles(product_group_name);

-- 3. Giao dịch --------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id                   BIGSERIAL PRIMARY KEY,
    t_dat                DATE NOT NULL,
    customer_id          VARCHAR(64) NOT NULL REFERENCES customers(customer_id),
    article_id           VARCHAR(20) NOT NULL REFERENCES articles(article_id),
    price                DOUBLE PRECISION,
    sales_channel_id     SMALLINT  -- 1=offline, 2=online
);
CREATE INDEX IF NOT EXISTS idx_tx_customer ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_tx_article  ON transactions(article_id);
CREATE INDEX IF NOT EXISTS idx_tx_date     ON transactions(t_dat);
CREATE INDEX IF NOT EXISTS idx_tx_cust_date ON transactions(customer_id, t_dat);

-- 4. Kết quả phân cụm (Layer 1 output) --------------------------------
-- Note: KHÔNG dùng FK REFERENCES customers(customer_id) vì 3 bảng nguồn
-- (customers/articles/transactions) đã được load sẵn KHÔNG có PRIMARY KEY,
-- nên FK sẽ raise InvalidForeignKey. App tự đảm bảo customer_id valid khi
-- INSERT (Layer 1 đọc trực tiếp từ customers nên không có ID lạ).
CREATE TABLE IF NOT EXISTS customer_clusters (
    customer_id          VARCHAR(64) PRIMARY KEY,
    cluster_id           SMALLINT NOT NULL,
    cluster_label        VARCHAR(40),     -- ví dụ "Classic Ladieswear"
    model_version        VARCHAR(40) NOT NULL,
    assigned_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cc_cluster ON customer_clusters(cluster_id);

-- 5. Sổ đăng ký mô hình ---------------------------------------------
-- Mỗi lần retrain ghi 1 dòng để frontend xem được lịch sử + chỉ số
CREATE TABLE IF NOT EXISTS model_registry (
    id                   BIGSERIAL PRIMARY KEY,
    layer                VARCHAR(20) NOT NULL,    -- 'L1_KMEANS' | 'L2_APRIORI' | 'L3_RANDOMFOREST'
    version              VARCHAR(40) NOT NULL,    -- timestamp string YYYYMMDD_HHMMSS
    artifact_path        TEXT NOT NULL,           -- đường dẫn file joblib
    metrics              JSONB,                   -- AUC, recall, n_rules, inertia, ...
    n_samples_train      BIGINT,
    cutoff_date          DATE,                    -- với L3: ngày chốt sổ
    is_active            BOOLEAN DEFAULT FALSE,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mr_layer_active ON model_registry(layer, is_active);
CREATE INDEX IF NOT EXISTS idx_mr_layer_created ON model_registry(layer, created_at DESC);

-- Bổ sung 2 cột phục vụ "học tiếp" (incremental learning):
--   parent_version  — version của model gốc nếu phiên bản này dẫn xuất từ model cũ
--   is_incremental — TRUE nếu dùng partial_fit / warm_start (giữ state cũ),
--                    FALSE nếu fit từ đầu (học lại / batch retrain)
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS parent_version VARCHAR(40);
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS is_incremental BOOLEAN DEFAULT FALSE;

-- 6. Nhật ký dự đoán (continuous learning feedback) ----------------
-- Khi BE trả 1 dự đoán, ghi vào đây. Sau N ngày so với t_dat thực tế
-- để tính accuracy "drift" của mô hình → trigger retrain nếu giảm.
CREATE TABLE IF NOT EXISTS prediction_log (
    id                   BIGSERIAL PRIMARY KEY,
    customer_id          VARCHAR(64) NOT NULL,
    layer                VARCHAR(20) NOT NULL,
    model_version        VARCHAR(40) NOT NULL,
    predicted_value      JSONB,                   -- {will_buy:1, proba:0.83} hoặc {cluster:2}
    actual_value         JSONB,                   -- điền sau khi quan sát thực tế
    predicted_at         TIMESTAMPTZ DEFAULT NOW(),
    resolved_at          TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_pl_layer_pred ON prediction_log(layer, predicted_at DESC);
