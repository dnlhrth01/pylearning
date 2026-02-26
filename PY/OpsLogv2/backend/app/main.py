from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[2]
import sys

if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from auth import ROLES, create_manager, login, register
from database import (
    INCIDENT_STATUSES,
    approve_delete_request,
    assign_role,
    create_incident,
    create_tables,
    get_incident,
    get_change_logs,
    list_delete_requests,
    list_users,
    request_delete_incident,
    search_incidents,
    set_user_active,
    update_incident,
)

from .dashboard import get_dashboard_stats
from .schemas import (
    AuthResponse,
    DashboardResponse,
    DeleteRequestPayload,
    IncidentCreateRequest,
    IncidentUpdateRequest,
    LoginRequest,
    RegisterRequest,
    SearchResponse,
    UserRoleUpdatePayload,
    UserStatusUpdatePayload,
)
from .session import session_store


app = FastAPI(title="OpsLog API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    create_tables()
    create_manager()


def get_current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    user = session_store.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid token.")
    return user, token


def require_role(user: dict, roles: list[str]):
    if user.get("role") not in roles:
        raise HTTPException(status_code=403, detail="You do not have permission for this action.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/meta")
def get_meta():
    return {"roles": ROLES, "incident_statuses": INCIDENT_STATUSES}


@app.post("/auth/register")
def auth_register(payload: RegisterRequest):
    try:
        register(payload.full_name, payload.email, payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "Account created. Please wait for Manager role assignment."}


@app.post("/auth/login", response_model=AuthResponse)
def auth_login(payload: LoginRequest):
    user, message = login(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail=message)
    token = session_store.create(user["username"])
    return {
        "token": token,
        "user": {
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
    }


@app.post("/auth/logout")
def auth_logout(auth=Depends(get_current_user)):
    _, token = auth
    session_store.revoke(token)
    return {"message": "Logged out"}


@app.get("/auth/me")
def auth_me(auth=Depends(get_current_user)):
    user, _ = auth
    return user


@app.get("/dashboard", response_model=DashboardResponse)
def dashboard(auth=Depends(get_current_user)):
    _user, _ = auth
    return get_dashboard_stats()


@app.post("/incidents")
def incidents_create(payload: IncidentCreateRequest, auth=Depends(get_current_user)):
    user, _ = auth
    if user["role"] not in ["SO Engineer", "Service Field Engineer", "CS Leader"]:
        raise HTTPException(status_code=403, detail="Role not allowed to create incidents.")
    try:
        incident_id = create_incident(
            payload.model_dump(),
            actor_username=user["username"],
            actor_full_name=user["full_name"],
        )
        return {"incident_id": incident_id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/incidents/{incident_id}")
def incidents_get(incident_id: str, auth=Depends(get_current_user)):
    _user, _ = auth
    row = get_incident(incident_id)
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return row


@app.patch("/incidents/{incident_id}")
def incidents_update(incident_id: str, payload: IncidentUpdateRequest, auth=Depends(get_current_user)):
    user, _ = auth
    if user["role"] not in ["SO Engineer", "Service Field Engineer", "CS Leader"]:
        raise HTTPException(status_code=403, detail="Role not allowed to update incidents.")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    try:
        update_incident(incident_id, updates, user["username"], user["full_name"])
        return {"message": "Incident updated."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/incidents", response_model=SearchResponse)
def incidents_search(
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    auth=Depends(get_current_user),
):
    _user, _ = auth
    total, rows = search_incidents(keyword, page, page_size)
    return {"total": total, "rows": rows}


@app.get("/incidents/{incident_id}/changes")
def incidents_changes(incident_id: str, auth=Depends(get_current_user)):
    _user, _ = auth
    return get_change_logs(incident_id)


@app.post("/delete-requests")
def delete_request_create(payload: DeleteRequestPayload, auth=Depends(get_current_user)):
    user, _ = auth
    try:
        request_delete_incident(payload.incident_id, user["username"], user["role"])
        return {"message": "Delete request submitted."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/delete-requests")
def delete_requests_list(auth=Depends(get_current_user)):
    user, _ = auth
    require_role(user, ["Manager", "CS Leader"])
    return list_delete_requests()


@app.post("/delete-requests/approve")
def delete_request_approve(payload: DeleteRequestPayload, auth=Depends(get_current_user)):
    user, _ = auth
    try:
        approve_delete_request(payload.incident_id, user["username"], user["role"])
        return {"message": "Incident deleted permanently."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/users")
def users_list(auth=Depends(get_current_user)):
    user, _ = auth
    require_role(user, ["Manager"])
    return list_users()


@app.post("/users/role")
def users_assign_role(payload: UserRoleUpdatePayload, auth=Depends(get_current_user)):
    user, _ = auth
    require_role(user, ["Manager"])
    try:
        assign_role(user["username"], payload.username, payload.role)
        return {"message": "Role updated."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/users/status")
def users_update_status(payload: UserStatusUpdatePayload, auth=Depends(get_current_user)):
    user, _ = auth
    require_role(user, ["Manager"])
    try:
        set_user_active(user["username"], payload.username, payload.is_active)
        return {"message": "Account status updated."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
