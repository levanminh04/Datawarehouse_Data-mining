# H&M Mining App

Phần code do **một thành viên Nhóm 01 — KDL & KPDL** phụ trách trong bài tập lớn môn _Kho dữ liệu và Khai phá dữ liệu_ (giảng viên: ThS. Nguyễn Quỳnh Chi, năm học 2025–2026).

Module này đáp ứng 2 yêu cầu mở rộng của cô được nêu ở **Chương 5.3** báo cáo nhóm:

1. **Hệ thống thu thập dữ liệu liên tục** — endpoint `POST /ingest/*` nhận khách hàng & giao dịch mới qua HTTP, ghi thẳng vào bảng `transactions`.
2. **Hệ thống học liên tục** — `APScheduler` retrain định kỳ; mỗi phiên bản mô hình được lưu vào bảng `model_registry` với chỉ số đánh giá; phục vụ bằng phiên bản `is_active=TRUE` (zero-downtime swap).

## Phạm vi của module

- ✅ **Trong scope:** FastAPI app + 3 lớp ML (K-Means / Apriori / Random Forest theo Chương 4 báo cáo) + scheduler + dashboard tối giản (Alpine.js + Chart.js).
- ❌ **Ngoài scope (việc của thành viên khác):** notebook EDA H&M (Chương 3), ETL từ CSV `customers.csv` / `articles.csv` / `transactions_train.csv` vào Postgres, slide demo, file Word báo cáo.

## Tiền đề

DB Postgres remote do **levanminh04** set up đã có sẵn 3 bảng H&M (xem [README root](../../README.md) phần "DB connections"):

- `customers` — `customer_id` VARCHAR PK (≈1.37 triệu khách hàng)
- `articles` — `article_id` VARCHAR PK; có `index_group_name`, `product_group_name` (≈105k SKU)
- `transactions(t_dat, customer_id, article_id, price, sales_channel_id)` — có index trên `(customer_id, t_dat)` (≈31.8 triệu giao dịch)

`.env.example` đã set sẵn `DATABASE_URL` trỏ vào DB remote — anh chỉ cần `cp .env.example .env` là chạy được. Không cần dump CSV về local.

App **không** chạm DDL của 3 bảng trên. Khi chạy `python -m scripts.init_db`, app dùng `CREATE TABLE IF NOT EXISTS` cho **3 bảng nội bộ** (idempotent — không ảnh hưởng nếu đã tồn tại):

- `customer_clusters` — output Layer 1 (cluster_id của mỗi khách)
- `model_registry` — version history của các mô hình ML
- `prediction_log` — log mọi response `/predict/*` để đo drift sau này

## Kiến trúc

```text
Client (web/curl) ──► FastAPI ──► PostgreSQL (do thành viên khác load)
                        │
                        ├─► Layer 1 KMeans      (Fashion DNA)
                        ├─► Layer 2 Apriori     (per-cluster rules)
                        └─► Layer 3 RandomForest (will_buy_7d)
                        ▲
                        │ APScheduler cron retrain
```

Tất cả tính toán nặng (JOIN, AGG) đẩy xuống PostgreSQL bằng SQL — đúng tinh thần báo cáo mục 3.3 (chống OOM khi >1 triệu khách hàng).

## Cài đặt local

> **Yêu cầu:** Python **3.11** (hoặc 3.12). Pinning trong `requirements.txt` (numpy 1.26.4, pandas 2.2.3, psycopg2-binary 2.9.9, scikit-learn 1.5.2) không có wheel cho Python 3.13/3.14 — nếu dùng version mới hơn, pip sẽ cố build từ source và fail. Trên macOS: `brew install python@3.11`.

```bash
# 1. Vào thư mục app
cd data-mining/hm_mining_app

# 2. Venv + dependencies (BẮT BUỘC dùng python3.11)
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Config — .env.example đã trỏ sẵn vào DB remote, copy xong là chạy được
cp .env.example .env

# 4. Tạo 3 bảng nội bộ (customer_clusters, model_registry, prediction_log)
python -m scripts.init_db

# 5. Khởi động app
uvicorn app.main:app --reload --port 8000

# 6. (Terminal khác) Train lần đầu — cần khoảng 5–15 phút trên 32M giao dịch
curl -X POST http://localhost:8000/retrain/all
```

App chạy tại <http://localhost:8000> (Dashboard) và <http://localhost:8000/docs> (Swagger). Health check: <http://localhost:8000/health>.

> **Lưu ý:** Phương án trên dùng DB remote `13.239.118.235` của nhóm. Yêu cầu mạng vào được AWS Sydney (ping/TCP 5432). Nếu lỗi connection, kiểm tra VPN/firewall hoặc đổi sang Postgres local theo dòng comment trong `.env.example`.

## API chính

| Method | Path | Mô tả |
|---|---|---|
| POST | `/ingest/customer` | Tạo / update khách hàng |
| POST | `/ingest/transactions` | Nhận lô giao dịch (≤10k) |
| GET  | `/predict/cluster/{customer_id}` | Cụm phong cách |
| GET  | `/predict/recommend/{customer_id}?top_k=5` | Cross-sell theo luật của cụm |
| GET  | `/predict/will-buy/{customer_id}` | Xác suất mua trong 7 ngày |
| POST | `/retrain/layer1` \| `/layer2` \| `/layer3` \| `/all` | Trigger retrain (background) |
| GET  | `/metrics/summary` | Overview + mô hình active |
| GET  | `/metrics/models/{layer}` | Lịch sử các phiên bản |
| GET  | `/metrics/cluster-distribution` | Số KH theo từng cụm |

## Học liên tục — đáp ứng yêu cầu cô

1. **Thu thập:** `POST /ingest/transactions` ghi thẳng vào bảng `transactions`. Mọi giao dịch mới đều hiện diện ở lần huấn luyện kế tiếp.
2. **Versioning:** mỗi lần `train_*` thành công sẽ:
   - Lưu file `models_store/{layer}/v{ts}.joblib`
   - INSERT 1 dòng vào `model_registry` (metrics, n_samples, cutoff_date)
   - Đánh dấu `is_active=TRUE` cho phiên bản mới, FALSE cho các phiên bản cũ
3. **Cron retrain:** `APScheduler` chạy ngầm trong process `uvicorn`. Mặc định:
   - L1 KMeans: Chủ nhật 02:00 UTC
   - L2 Apriori: Chủ nhật 03:00 UTC (sau L1)
   - L3 Random Forest: Hằng ngày 01:00 UTC
4. **Logging dự đoán:** mọi response `/predict/*` đều được ghi vào `prediction_log` — sau N ngày có thể join với `transactions` thực tế để tính accuracy drift, từ đó trigger retrain ngoài lịch nếu cần.
5. **Zero-downtime:** predict luôn nạp `is_active=TRUE`. Train mới không gián đoạn traffic.

## Diễn giải mô hình

- **Layer 1** dùng đúng 7 đặc trưng của báo cáo (mục 4.1.1) — KHÔNG đưa `age` và `total_items` vào K-Means.
- **Layer 2** chạy theo mô hình **Segment-then-Mine**: mỗi cụm có bộ luật riêng, tránh sinh luật chung chung vô giá trị.
- **Layer 3** dùng `class_weight='balanced'`, `max_samples=0.4`, `max_depth=8` — khớp đúng tham số trong báo cáo (mục 4.3.2.b). Mục tiêu là Recall cao ở lớp 1 (như báo cáo mục 4.3.2: "Tại sao Recall cao 0.75 là chiến thắng").

## Test nhanh

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Predict cho 1 khách hàng (sau khi đã train)
curl http://localhost:8000/predict/cluster/cust_000001
curl http://localhost:8000/predict/recommend/cust_000001?top_k=5
curl http://localhost:8000/predict/will-buy/cust_000001

# 3. Xem chỉ số
curl http://localhost:8000/metrics/summary | jq

# 4. Nạp giao dịch mới
curl -X POST http://localhost:8000/ingest/transactions \
     -H 'Content-Type: application/json' \
     -d '{"transactions":[
            {"t_dat":"2024-01-15","customer_id":"cust_000001",
             "article_id":"0000000001","price":0.025,"sales_channel_id":2}
         ]}'
```

## Hạn chế & hướng phát triển

- Hiện chưa lập lịch tự động "đối chiếu" `prediction_log.actual_value` từ `transactions` — có thể bổ sung 1 cron job nữa.
- Drift detection (PSI / KS test trên feature distribution) chưa có — đây là next step nếu muốn retrain "có điều kiện" thay vì cố định lịch.
- Frontend tối giản — đủ để demo. Production nên thay bằng React + thư viện chart đầy đủ.
