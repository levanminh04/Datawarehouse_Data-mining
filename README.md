# Datawarehouse_Data-mining — Bài tập lớn Nhóm 01

Repo môn **Kho dữ liệu và Khai phá dữ liệu** (PTIT, năm học 2025–2026, giảng viên: ThS. Nguyễn Quỳnh Chi).

Nội dung repo gồm **2 mảng độc lập**: phần Kho dữ liệu (Data Warehouse) trên dataset Olist, và phần Khai phá dữ liệu (Data Mining) trên dataset H&M. Mỗi mảng có dataset riêng, kho lưu trữ riêng, và quy trình làm việc riêng.

## Cấu trúc

```text
.
├── data-warehouse/            ← Mảng 1: Kho dữ liệu (Olist → Oracle)
│   ├── etl_olist_to_sql.py    Script ETL từ CSV Olist sang câu INSERT SQL
│   ├── data/                  9 file CSV gốc của Olist (~129 MB)
│   ├── output/                9 file SQL DDL+INSERT cho 9 thực thể DW
│   │                          (VanPhongDaiDien, KhachHang, MatHang...)
│   ├── web/                   Dashboard demo (FastAPI backend + Vite/TS frontend),
│   │                          kết nối Oracle DW (xem web/backend/.env.example)
│   └── surveys/               16 script khảo sát/verify schema, geo, return-rate...
│
├── data-mining/               ← Mảng 2: Khai phá dữ liệu (H&M + Olist → Postgres)
│   ├── hm_mining_app/         FastAPI app phục vụ "thu thập + học liên tục"
│   │                          (3 lớp: K-Means / Apriori / Random Forest theo
│   │                          Chương 4 báo cáo, dataset H&M)
│   ├── notebooks/
│   │   ├── lop123-original/   Bài tập đầu tiên của lớp (Lop1/2/3 .ipynb)
│   │   ├── olist-rfm-v2/      Iteration v2: RFM clustering trên Olist
│   │   ├── olist-product-v3/  Iteration v3: Product clustering, AUC verify
│   │   ├── olist-lookalike-v4/ Iteration v4: Lookalike, Returns, Rules
│   │   └── hm-survey/         Survey + 3 notebook chính trên H&M (Ch.3-4)
│   └── generate_notebook.py   Helper chuyển .py → .ipynb
│
└── docs/superpowers/          Spec + plan cho các đợt refactor (workflow nội bộ)
    ├── specs/
    └── plans/
```

## DB connections

| Mảng | DB | Host | DB info |
|---|---|---|---|
| Data Warehouse | Oracle | (Oracle XE local mỗi thành viên) | xem `data-warehouse/web/backend/.env.example` |
| Data Mining | Postgres | `13.239.118.235:5432/data-mining` (remote AWS, do levanminh04 set up) | user `user2`, pass `datamining` — xem các `database.py` trong `data-mining/notebooks/*/` |

App `hm_mining_app/` có thể chạy với DB remote trên hoặc Docker Postgres local — xem `data-mining/hm_mining_app/README.md`.

## Phân công

| Thành viên | Phụ trách |
|---|---|
| levanminh04 | DW (ETL, schema, web), Mining notebooks (v1-v4), survey, H&M survey notebook, load data |
| tychicus04 | `data-mining/hm_mining_app/` — FastAPI continuous-learning app |

## Đáp ứng yêu cầu mở rộng của cô

Cô yêu cầu **hệ thống thu thập dữ liệu liên tục** + **học liên tục** — được triển khai trong [data-mining/hm_mining_app/](data-mining/hm_mining_app/) (xem README riêng của app). Các phần khác là cơ sở dữ liệu và phân tích offline.
