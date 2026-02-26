from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=3)
    email: EmailStr
    username: str = Field(min_length=3)
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    username: str
    full_name: str
    role: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class IncidentCreateRequest(BaseModel):
    incident_id: Optional[str] = ""
    error_name: str
    component: str
    root_cause: str
    remark: str
    action_taken: str
    start_date: str
    start_time: str
    end_date: str
    end_time: str


class IncidentUpdateRequest(BaseModel):
    root_cause: Optional[str] = None
    remark: Optional[str] = None
    action_taken: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None


class DeleteRequestPayload(BaseModel):
    incident_id: str


class UserRoleUpdatePayload(BaseModel):
    username: str
    role: str


class UserStatusUpdatePayload(BaseModel):
    username: str
    is_active: bool


class SearchResponse(BaseModel):
    total: int
    rows: List[dict]


class DashboardResponse(BaseModel):
    total_incidents: int
    open_cases: int
    monitoring_cases: int
    resolved_closed_cases: int
    avg_duration_minutes: float
    incidents_last_7_days: int
    top_components: List[dict]
    status_breakdown: List[dict]
