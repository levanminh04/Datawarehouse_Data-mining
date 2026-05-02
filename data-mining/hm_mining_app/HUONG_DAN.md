# H&M Mining App — Hướng dẫn sử dụng

Module này là phần code do **một thành viên Nhóm 01** phụ trách trong bài tập lớn môn _Kho dữ liệu và Khai phá dữ liệu_ (PTIT, năm học 2025–2026, giảng viên: ThS. Nguyễn Quỳnh Chi).

Tài liệu này dành cho **các thành viên khác trong nhóm** muốn cài đặt + chạy + demo app trên máy mình. Đọc theo thứ tự từ trên xuống.

---

## 1. App này làm gì?

Đáp ứng **2 yêu cầu mở rộng của cô** ở Chương 5.3 báo cáo nhóm:

1. **Thu thập dữ liệu liên tục** — cô có thể `POST /ingest/transactions` để gửi giao dịch mới qua HTTP, app ghi thẳng vào bảng `transactions`. Lần huấn luyện kế tiếp sẽ tự động học từ giao dịch mới.

2. **Học liên tục** — `APScheduler` retrain định kỳ (Sunday 02:00 UTC cho L1+L2, daily 01:00 UTC cho L3). Mỗi phiên bản mô hình lưu vào bảng `model_registry` với chỉ số đánh giá. App predict luôn dùng version `is_active=TRUE`, train mới không gián đoạn traffic.

Cài 3 lớp đúng theo Chương 4:

| Lớp | Thuật toán | Đặc trưng | Output |
|---|---|---|---|
| **L1** | K-Means (k=5) | 5 tỉ trọng ngành hàng + pct_online + avg_price | cluster_id mỗi khách |
| **L2** | Apriori per cluster | Giỏ hàng theo product_group_name | luật kết hợp riêng từng cụm |
| **L3** | Random Forest | RFM + Fashion DNA | xác suất mua trong 7 ngày |

---

## 2. Yêu cầu cài đặt

- **Python 3.11** bắt buộc (3.13/3.14 chưa có wheel cho `numpy 1.26.4`, `psycopg2-binary 2.9.9`, `scikit-learn 1.5.2`)
- macOS / Linux (Windows chưa test)
- Mạng vào được Postgres `13.239.118.235:5432` (AWS Sydney của nhóm)
- ~500 MB ổ cứng cho venv + model artifacts

Nếu chưa có Python 3.11:
```bash
brew install python@3.11
```

---

## 3. Cài đặt — 6 bước copy-paste

```bash
# Bước 1: Vào thư mục app
cd Datawarehouse_Data-mining/data-mining/hm_mining_app

# Bước 2: Tạo virtualenv (BẮT BUỘC python3.11)
python3.11 -m venv .venv
source .venv/bin/activate
python --version    # phải hiện "Python 3.11.x"

# Bước 3: Cài thư viện
pip install -r requirements.txt

# Bước 4: Config — file .env.example đã trỏ sẵn vào DB nhóm,
# copy là chạy được
cp .env.example .env

# Bước 5: Tạo 3 bảng nội bộ trên DB (idempotent — chạy lại không sao)
# Lần đầu sẽ build index trên 32M giao dịch, mất ~10-15 phút
python -m scripts.init_db

# Bước 6: Khởi động server
uvicorn app.main:app --reload --port 8000
```

Mở **http://localhost:8000** → thấy dashboard.

> ⚠️ Bước 5 mỗi statement commit độc lập (autocommit) — nếu mạng rớt giữa chừng, chạy lại sẽ tiếp từ chỗ dở (`CREATE … IF NOT EXISTS` skip cái đã có).

---

## 4. Lần đầu — train 3 mô hình

Sau khi server khởi động, **bắt buộc train** trước khi gọi predict. 2 cách:

**Cách 1 — Click nút trên dashboard:**
- Mở http://localhost:8000 → tab Tổng quan → nút "Retrain toàn bộ ngay"

**Cách 2 — curl:**
```bash
curl -X POST http://localhost:8000/retrain/all
# Response: {"status":"scheduled","layers":["L1","L2","L3"]}
```

Train chạy **background** trong process uvicorn. Theo log uvicorn, sẽ thấy:

```
[INFO] Bắt đầu retrain L1_KMEANS
... (10-15 phút)
[INFO] Hoàn tất L1: {n_clusters: 5, ..., n_total_assigned: 1362281, ...}
[INFO] Bắt đầu retrain L2_APRIORI
... (5-10 phút)
[INFO] Hoàn tất L2: {total_rules: 90, ...}
[INFO] Bắt đầu retrain L3_RANDOMFOREST
... (5 phút)
[INFO] Hoàn tất L3: {auc: 0.82, recall_class1: 0.76, ...}
```

Tổng **~25-30 phút** trên DB remote. Lần sau retrain nhanh hơn nhờ index đã có.

---

## 5. Sử dụng dashboard

### Tab "Tổng quan"
- 4 chỉ số tổng: số khách hàng, số sản phẩm, số giao dịch, số đã phân cụm
- Biểu đồ phân bố khách theo 5 cụm phong cách
- Bảng 3 mô hình đang `is_active=TRUE`
- Nút "Retrain toàn bộ ngay"

### Tab "Suy luận"
Nhập **customer_id** thật → xem 3 thông tin:
- **Cụm phong cách** (Layer 1) — 1 trong 5 nhóm
- **Top-5 sản phẩm gợi ý** (Layer 2) — Apriori riêng theo cụm
- **Xác suất mua 7 ngày tới** (Layer 3) — kèm interpret thấp/cao

Lấy customer_id thật bằng SQL:
```sql
SELECT customer_id FROM customer_clusters LIMIT 5;
```

Hoặc click nút "Lấy ID mẫu" trên tab Suy luận, app tự fetch.

### Tab "Mô hình"
Lịch sử các version theo từng layer — đáp ứng "học liên tục":
- Bảng version: timestamp, số mẫu train, cutoff_date, ACTIVE flag
- Biểu đồ feature importance của Layer 3 (verify với Chương 4.3.3 báo cáo)
- Pie chart số luật Apriori theo từng cụm

### Tab "Nạp dữ liệu"
2 form tương ứng 2 endpoint:
- `POST /ingest/customer` — tạo / update 1 khách hàng
- `POST /ingest/transactions` — gửi batch giao dịch (≤10k / lần)

Demo cô: nhập 1 giao dịch giả → click POST → quay lại tab Tổng quan → số giao dịch tăng → click Retrain → mô hình mới học được giao dịch đó.

### Tab "Hướng dẫn"
Chính là tài liệu này, render sẵn trong app.

---

## 6. Demo cho cô — trình tự đề xuất

1. **Tab Tổng quan** — show 1.37M khách + 31.8M giao dịch thật từ H&M dataset. Khớp với báo cáo Chương 3.
2. **Biểu đồ phân bố cụm** — chỉ ra Classic Ladieswear chiếm ~65%, GenZ Trend ~23%, đúng tinh thần Chương 4.1.3 ("nữ giới là trụ cột doanh thu").
3. **Tab Mô hình** — show AUC=0.82, recall=0.76 trên L3. Nhấn mạnh chỉ số này khớp với "Recall 0.75 là chiến thắng" trong Chương 4.3.2.
4. **Tab Suy luận** — gõ customer_id, demo cả 3 endpoint trả lời trong 1-2 giây.
5. **Tab Nạp dữ liệu** — POST 1 giao dịch → vào DB ngay → cô thấy "thu thập liên tục".
6. **Click Retrain** → giải thích `model_registry` versioning + cron schedule → cô thấy "học liên tục".

---

## 7. API endpoints (curl examples)

```bash
HOST=http://localhost:8000

# Health check
curl $HOST/health

# Predict (cần customer_id thật)
CID=d9793b30ac8a88a161cb8d690bab119fb9285007a222dedde49b63e9088b660e
curl $HOST/predict/cluster/$CID
curl "$HOST/predict/recommend/$CID?top_k=5"
curl $HOST/predict/will-buy/$CID

# Metrics
curl $HOST/metrics/summary
curl $HOST/metrics/cluster-distribution
curl $HOST/metrics/models/L3_RANDOMFOREST

# Retrain
curl -X POST $HOST/retrain/all
curl -X POST $HOST/retrain/layer1     # chỉ L1
curl -X POST $HOST/retrain/layer3     # chỉ L3 (nhanh nhất)

# Ingest
curl -X POST $HOST/ingest/customer \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"new_user_001","age":28,"club_member_status":"ACTIVE"}'

curl -X POST $HOST/ingest/transactions \
  -H 'Content-Type: application/json' \
  -d '{"transactions":[{"t_dat":"2024-01-15","customer_id":"new_user_001","article_id":"0108775015","price":0.025,"sales_channel_id":2}]}'
```

Doc chi tiết: **http://localhost:8000/docs** (Swagger UI auto-generated).

---

## 8. Troubleshooting

| Triệu chứng | Nguyên nhân | Cách fix |
|---|---|---|
| `pip install` fail ở `psycopg2-binary` | Python 3.13/3.14 thiếu wheel | Bước 2 phải dùng `python3.11`, xoá `.venv` cũ |
| `connection refused` khi `init_db` | DATABASE_URL sai hoặc mất mạng | Mở `.env` kiểm tra `DATABASE_URL`. Test: `nc -zv 13.239.118.235 5432` |
| `init_db` chạy rất lâu (10+ phút) | Lần đầu build index trên 32M rows | Bình thường — đừng tắt giữa chừng |
| Predict trả `404 Khách hàng chưa có dữ liệu` | customer_id không có trong DB | Lấy ID hợp lệ từ `SELECT customer_id FROM customer_clusters LIMIT 5;` |
| Predict trả `404 Layer X chưa được huấn luyện` | Chưa retrain | Click "Retrain toàn bộ" hoặc `curl -X POST /retrain/all` |
| Retrain "scheduled" nhưng không thấy progress | Background task — log ở terminal uvicorn, không phải curl | Check log uvicorn |
| Dashboard hiện 0 khách / 0 giao dịch | App connect sai DB | Kiểm tra `.env`, restart uvicorn |
| Retrain quá lâu (1+ giờ) | Network sang Sydney chậm | Đợi tiếp, hoặc dùng VPN gần Singapore |
| `python: command not found` (macOS) | Không có alias | Luôn dùng `python3.11` (hoặc `python3` sau khi activate venv) |
| `ImportError psycopg2` khi `python -m scripts.init_db` | Chưa activate venv | `source .venv/bin/activate` trước |

Có lỗi khác không có trong bảng → paste log uvicorn lên group chat.

---

## 9. File đáng quan tâm trong repo

```
data-mining/hm_mining_app/
├── app/
│   ├── main.py              FastAPI entry point
│   ├── config.py            Đọc .env (12 biến)
│   ├── db.py                SQLAlchemy engine + session
│   ├── api/                 4 router: ingest, predict, retrain, metrics
│   ├── ml/                  3 layer + features + registry
│   └── sql/                 schema.sql + feature_queries.sql
├── frontend/index.html      Dashboard (Tailwind + Alpine + Chart.js, 1 file)
├── scripts/init_db.py       Tạo bảng nội bộ (autocommit, idempotent)
├── requirements.txt         Pinned versions (Python 3.11)
├── .env.example             Config mẫu — copy thành .env
├── HUONG_DAN.md             File này
└── README.md                Tóm tắt ngắn cho người đọc lần đầu
```

---

## 10. Liên hệ

Có thắc mắc hoặc lỗi không tự xử lý được → ping `tychicus04` trong group chat nhóm.
