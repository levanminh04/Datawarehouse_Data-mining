# Frontend (React + Vite + Ant Design)

## 1) Cai dat

```powershell
cd D:\Coding\Project\Kho_du_lieu\web-app\frontend
copy .env.example .env
npm install
```

## 2) Chay local

```powershell
npm run dev
```

Mo trinh duyet:
- `http://localhost:5173`

## 3) Man hinh hien co

- Dashboard
- ETL Control
- OLAP Explorer
- Health

## 4) Yeu cau backend

Frontend goi den `VITE_API_BASE_URL` (mac dinh: `http://localhost:8000`) voi cac endpoint:
- `GET /api/health`
- `GET /api/health/db`
- `GET /api/dashboard/summary`
- `POST /api/etl/run`
- `GET /api/etl/logs`
- `GET /api/olap/{1..9}`
