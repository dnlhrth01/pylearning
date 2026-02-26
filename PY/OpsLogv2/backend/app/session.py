import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Optional

from database import get_user


SESSION_TTL_MINUTES = 30


@dataclass
class SessionData:
    username: str
    created_at: datetime
    expires_at: datetime


class SessionStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: Dict[str, SessionData] = {}

    def create(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now()
        with self._lock:
            self._sessions[token] = SessionData(
                username=username,
                created_at=now,
                expires_at=now + timedelta(minutes=SESSION_TTL_MINUTES),
            )
        return token

    def get_user(self, token: str) -> Optional[dict]:
        now = datetime.now()
        with self._lock:
            data = self._sessions.get(token)
            if not data:
                return None
            if data.expires_at <= now:
                self._sessions.pop(token, None)
                return None
            data.expires_at = now + timedelta(minutes=SESSION_TTL_MINUTES)
            user = get_user(data.username)
            if not user or not user.get("is_active"):
                self._sessions.pop(token, None)
                return None
            return {
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
            }

    def revoke(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)


session_store = SessionStore()

