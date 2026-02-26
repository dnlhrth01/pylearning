# OpsLog v2 FastAPI + React Migration

This migration keeps your existing business logic (`database.py`, `auth.py`, `utils.py`) and exposes it through:
- `backend`: FastAPI API
- `frontend`: React (Vite) UI with minimalist red/white theme

## Backend setup

From `PY/OpsLogv2/backend`:

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend setup

From `PY/OpsLogv2/frontend`:

```powershell
npm install
npm run dev
```

Frontend runs at `http://127.0.0.1:5173` and calls backend at `http://127.0.0.1:8000`.

## Preserved functions

- Login/register with lockout and role checks
- Incident create/update/search/get
- Delete request workflow + approval
- Manager user role/status controls
- Incident change logs

## Dashboard statistics included

- Total incidents
- Open case count
- Monitoring count
- Resolved/closed count
- Average incident duration
- Incidents in last 7 days
- Top 5 components by incident count
- Status breakdown
