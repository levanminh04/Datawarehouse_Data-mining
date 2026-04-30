# Backend - DW Dashboard API

## 1) Cai dependencies
```bat
cd D:\Coding\Project\Kho_du_lieu\web-app\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Tao file env
```bat
copy .env.example .env
```

Chinh lai thong tin Oracle trong `.env` neu can.

## 3) Chay API
```bat
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 4) Test nhanh
- Health: `http://localhost:8000/api/health`
- Health DB: `http://localhost:8000/api/health/db`
- Dashboard summary: `http://localhost:8000/api/dashboard/summary`
- ETL run (manual): `POST http://localhost:8000/api/etl/run`
- ETL logs: `GET http://localhost:8000/api/etl/logs?limit=20`
- ETL logs by status: `GET http://localhost:8000/api/etl/logs?status=LOI&limit=20`
- OLAP Q1: `GET http://localhost:8000/api/olap/1?limit=5`
- OLAP Q3 (co tham so): `GET http://localhost:8000/api/olap/3?ma_kh=1&limit=5`
- OLAP Q9: `GET http://localhost:8000/api/olap/9?limit=5`
- Swagger: `http://localhost:8000/docs`
