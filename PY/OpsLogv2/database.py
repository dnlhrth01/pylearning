import sqlite3
from contextlib import contextmanager
from datetime import datetime
import re

from utils import (
    calculate_duration_minutes,
    contains_script_like_text,
    normalize_text,
    now_iso
)


DB_NAME = "opslog.db"
ROLE_OPTIONS = ["SO Engineer", "Service Field Engineer", "CS Leader", "Manager"]
ASSIGNABLE_ROLES = ["SO Engineer", "Service Field Engineer", "CS Leader"]
INCIDENT_STATUSES = ["Open Case", "Monitoring", "Resolved", "Closed"]


def connect():
    conn = sqlite3.connect(DB_NAME, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def tx(immediate=False):
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_tables():
    with tx() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL UNIQUE COLLATE BINARY,
                error_name TEXT NOT NULL,
                component TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                remark TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                start_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_date TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open Case',
                modified_by TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS incident_registry(
                incident_id TEXT PRIMARY KEY COLLATE BINARY,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS incident_change_logs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                modified_by TEXT NOT NULL,
                modified_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS delete_requests(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                approver TEXT,
                requested_at TEXT NOT NULL,
                approved_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS login_attempts(
                username TEXT PRIMARY KEY,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                last_attempt TEXT
            )
            """
        )
        _migrate_legacy_schema(conn)
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_pending_delete_request
            ON delete_requests(incident_id)
            WHERE status='Pending'
            """
        )


def _has_column(conn, table_name, column_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(r["name"] == column_name for r in rows)


def _table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row is not None


def _migrate_legacy_schema(conn):
    if _table_exists(conn, "users") and _has_column(conn, "users", "password"):
        conn.execute("ALTER TABLE users RENAME TO users_legacy")
        conn.execute(
            """
            CREATE TABLE users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        rows = conn.execute(
            """
            SELECT full_name, email, username, password, role, is_active
            FROM users_legacy
            """
        ).fetchall()
        for row in rows:
            role = row["role"] if row["role"] in ROLE_OPTIONS else ""
            conn.execute(
                """
                INSERT INTO users(full_name, email, username, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["full_name"],
                    row["email"],
                    row["username"],
                    row["password"],
                    role,
                    1 if row["is_active"] else 0,
                    now_iso()
                )
            )
        conn.execute("DROP TABLE users_legacy")

    if _table_exists(conn, "incidents") and not _has_column(conn, "incidents", "incident_id"):
        conn.execute("ALTER TABLE incidents RENAME TO incidents_legacy")
        conn.execute(
            """
            CREATE TABLE incidents(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL UNIQUE COLLATE BINARY,
                error_name TEXT NOT NULL,
                component TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                remark TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                start_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_date TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open Case',
                modified_by TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        rows = conn.execute(
            """
            SELECT id, error, component, root_cause, action_taken, start_time, end_time, downtime, status, created_by, modified
            FROM incidents_legacy
            """
        ).fetchall()
        for row in rows:
            incident_id = f"LEGACY-{row['id']}"
            conn.execute(
                """
                INSERT INTO incidents(
                    incident_id, error_name, component, root_cause, remark, action_taken,
                    start_date, start_time, end_date, end_time, duration_minutes, status,
                    modified_by, modified_at, is_deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    incident_id,
                    normalize_text(row["error"]),
                    normalize_text(row["component"]),
                    normalize_text(row["root_cause"]),
                    "",
                    normalize_text(row["action_taken"]),
                    "",
                    "",
                    "",
                    "",
                    int(row["downtime"] or 0),
                    row["status"] if row["status"] in INCIDENT_STATUSES else "Open Case",
                    normalize_text(row["created_by"]) or "legacy",
                    normalize_text(row["modified"]) or now_iso()
                )
            )
            conn.execute(
                "INSERT OR IGNORE INTO incident_registry(incident_id, created_at) VALUES (?, ?)",
                (incident_id, now_iso())
            )
        conn.execute("DROP TABLE incidents_legacy")

    if _table_exists(conn, "delete_requests") and not _has_column(conn, "delete_requests", "status"):
        conn.execute("ALTER TABLE delete_requests RENAME TO delete_requests_legacy")
        conn.execute(
            """
            CREATE TABLE delete_requests(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                approver TEXT,
                requested_at TEXT NOT NULL,
                approved_at TEXT
            )
            """
        )
        rows = conn.execute(
            "SELECT incident_id, requested_by FROM delete_requests_legacy"
        ).fetchall()
        for row in rows:
            conn.execute(
                """
                INSERT INTO delete_requests(incident_id, requested_by, status, requested_at)
                VALUES (?, ?, 'Pending', ?)
                """,
                (str(row["incident_id"]), row["requested_by"], now_iso())
            )
        conn.execute("DROP TABLE delete_requests_legacy")


def log_audit(conn, actor, action, target_type, target_id="", details=""):
    conn.execute(
        """
        INSERT INTO audit_logs(actor, action, target_type, target_id, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (actor, action, target_type, target_id, details, now_iso())
    )


def get_user(username):
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, full_name, email, username, password_hash, role, is_active
            FROM users
            WHERE username=?
            """,
            (normalize_text(username),)
        ).fetchone()
        return dict(row) if row else None


def create_user(full_name, email, username, password_hash):
    with tx(immediate=True) as conn:
        conn.execute(
            """
            INSERT INTO users(full_name, email, username, password_hash, role, is_active, created_at)
            VALUES (?, ?, ?, ?, '', 1, ?)
            """,
            (normalize_text(full_name), normalize_text(email).lower(), normalize_text(username), password_hash, now_iso())
        )
        log_audit(conn, normalize_text(username), "REGISTER", "USER", normalize_text(username), "User registered with no role.")


def list_users():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT full_name, email, username, role, is_active
            FROM users
            ORDER BY username
            """
        ).fetchall()
        return [dict(r) for r in rows]


def assign_role(actor_username, target_username, new_role):
    if new_role not in ASSIGNABLE_ROLES:
        raise ValueError("Invalid role assignment.")
    with tx(immediate=True) as conn:
        actor = conn.execute("SELECT role FROM users WHERE username=?", (actor_username,)).fetchone()
        if not actor or actor["role"] != "Manager":
            raise ValueError("Only Manager can assign roles.")

        target = conn.execute(
            "SELECT username, role FROM users WHERE username=?",
            (target_username,)
        ).fetchone()
        if not target:
            raise ValueError("User does not exist.")
        if target["username"] == actor_username:
            raise ValueError("Manager cannot modify own role.")

        old_role = target["role"]
        conn.execute(
            "UPDATE users SET role=? WHERE username=?",
            (new_role, target_username)
        )
        log_audit(
            conn,
            actor_username,
            "ROLE_CHANGE",
            "USER",
            target_username,
            f"{old_role} -> {new_role}"
        )


def set_user_active(actor_username, target_username, is_active):
    with tx(immediate=True) as conn:
        actor = conn.execute("SELECT role FROM users WHERE username=?", (actor_username,)).fetchone()
        if not actor or actor["role"] != "Manager":
            raise ValueError("Only Manager can manage account status.")

        target = conn.execute(
            "SELECT username, is_active FROM users WHERE username=?",
            (target_username,)
        ).fetchone()
        if not target:
            raise ValueError("User does not exist.")
        if target["username"] == actor_username:
            raise ValueError("Manager cannot modify own account status.")

        conn.execute(
            "UPDATE users SET is_active=? WHERE username=?",
            (1 if is_active else 0, target_username)
        )
        log_audit(
            conn,
            actor_username,
            "ACCOUNT_STATUS_CHANGE",
            "USER",
            target_username,
            f"is_active -> {1 if is_active else 0}"
        )


def get_login_attempt(username):
    with connect() as conn:
        row = conn.execute(
            "SELECT failed_attempts, locked_until FROM login_attempts WHERE username=?",
            (normalize_text(username),)
        ).fetchone()
        return dict(row) if row else {"failed_attempts": 0, "locked_until": None}


def register_login_failure(username, lock_after=5, lock_minutes=15):
    with tx(immediate=True) as conn:
        row = conn.execute(
            "SELECT failed_attempts FROM login_attempts WHERE username=?",
            (normalize_text(username),)
        ).fetchone()
        attempts = (row["failed_attempts"] if row else 0) + 1
        locked_until = None
        if attempts >= lock_after:
            locked_until = f"datetime('now', '+{lock_minutes} minutes')"
            conn.execute(
                """
                INSERT INTO login_attempts(username, failed_attempts, locked_until, last_attempt)
                VALUES (?, ?, datetime('now', '+15 minutes'), ?)
                ON CONFLICT(username) DO UPDATE SET
                    failed_attempts=excluded.failed_attempts,
                    locked_until=excluded.locked_until,
                    last_attempt=excluded.last_attempt
                """,
                (normalize_text(username), attempts, now_iso())
            )
        else:
            conn.execute(
                """
                INSERT INTO login_attempts(username, failed_attempts, locked_until, last_attempt)
                VALUES (?, ?, NULL, ?)
                ON CONFLICT(username) DO UPDATE SET
                    failed_attempts=excluded.failed_attempts,
                    last_attempt=excluded.last_attempt
                """,
                (normalize_text(username), attempts, now_iso())
            )


def clear_login_attempts(username):
    with tx() as conn:
        conn.execute("DELETE FROM login_attempts WHERE username=?", (normalize_text(username),))


def is_login_locked(username):
    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM login_attempts
            WHERE username=?
              AND locked_until IS NOT NULL
              AND datetime(locked_until) > datetime('now')
            """,
            (normalize_text(username),)
        ).fetchone()
        return row is not None


def _validate_incident_payload(payload, allow_status=False):
    fields = [
        "incident_id", "error_name", "component", "root_cause", "remark",
        "action_taken", "start_date", "start_time", "end_date", "end_time"
    ]
    for field in fields:
        if not normalize_text(payload.get(field)):
            raise ValueError(f"{field.replace('_', ' ').title()} is required.")
        if contains_script_like_text(payload.get(field)):
            raise ValueError(f"{field.replace('_', ' ').title()} contains blocked script text.")

    incident_id = normalize_text(payload["incident_id"])
    if " " in incident_id:
        raise ValueError("Incident ID must not contain spaces.")

    start_dt, end_dt, calculated = calculate_duration_minutes(
        payload["start_date"],
        payload["start_time"],
        payload["end_date"],
        payload["end_time"]
    )
    if end_dt <= start_dt:
        raise ValueError("Start datetime must be before End datetime.")
    if calculated <= 0:
        raise ValueError("Duration must be a positive integer.")

    provided_duration = int(calculated)

    status = "Open Case"
    if allow_status:
        status = normalize_text(payload.get("status"))
        if status not in INCIDENT_STATUSES:
            raise ValueError("Invalid incident status.")

    return {
        "incident_id": incident_id,
        "error_name": normalize_text(payload["error_name"]),
        "component": normalize_text(payload["component"]),
        "root_cause": normalize_text(payload["root_cause"]),
        "remark": normalize_text(payload["remark"]),
        "action_taken": normalize_text(payload["action_taken"]),
        "start_date": normalize_text(payload["start_date"]),
        "start_time": normalize_text(payload["start_time"]),
        "end_date": normalize_text(payload["end_date"]),
        "end_time": normalize_text(payload["end_time"]),
        "duration_minutes": provided_duration,
        "status": status
    }


def _normalize_incident_id_input(value):
    incident_id = normalize_text(value)
    if re.fullmatch(r"\d{4}-\d{1,8}", incident_id):
        return f"INC-{incident_id}"
    return incident_id


def _generate_incident_id(conn):
    year = datetime.now().strftime("%Y")
    prefix = f"INC-{year}-"
    rows = conn.execute(
        "SELECT incident_id FROM incident_registry WHERE incident_id LIKE ?",
        (f"{prefix}%",)
    ).fetchall()

    max_seq = 0
    for row in rows:
        value = row["incident_id"]
        if not value.startswith(prefix):
            continue
        tail = value[len(prefix):]
        if tail.isdigit():
            max_seq = max(max_seq, int(tail))

    return f"{prefix}{max_seq + 1:04d}"


def _build_modified_by(actor_full_name):
    return f"{normalize_text(actor_full_name)} @ {datetime.now().strftime('%d/%m/%Y %I:%M %p')}"


def create_incident(payload, actor_username, actor_full_name):
    try:
        with tx(immediate=True) as conn:
            prepared_payload = dict(payload or {})
            prepared_payload["incident_id"] = normalize_text(prepared_payload.get("incident_id"))
            if not prepared_payload["incident_id"]:
                prepared_payload["incident_id"] = _generate_incident_id(conn)

            clean = _validate_incident_payload(prepared_payload, allow_status=False)

            exists = conn.execute(
                "SELECT 1 FROM incident_registry WHERE incident_id=?",
                (clean["incident_id"],)
            ).fetchone()
            if exists:
                raise ValueError("Incident ID already exists and cannot be reused.")

            conn.execute(
                "INSERT INTO incident_registry(incident_id, created_at) VALUES (?, ?)",
                (clean["incident_id"], now_iso())
            )
            conn.execute(
                """
                INSERT INTO incidents(
                    incident_id, error_name, component, root_cause, remark, action_taken,
                    start_date, start_time, end_date, end_time, duration_minutes,
                    status, modified_by, modified_at, is_deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Open Case', ?, ?, 0)
                """,
                (
                    clean["incident_id"], clean["error_name"], clean["component"],
                    clean["root_cause"], clean["remark"], clean["action_taken"],
                    clean["start_date"], clean["start_time"], clean["end_date"], clean["end_time"],
                    clean["duration_minutes"], _build_modified_by(actor_full_name), now_iso()
                )
            )
            log_audit(conn, actor_username, "INCIDENT_CREATE", "INCIDENT", clean["incident_id"], "Created incident.")
            return clean["incident_id"]
    except sqlite3.IntegrityError:
        raise ValueError("Incident ID already exists and cannot be reused.")


def get_incident(incident_id):
    incident_id = _normalize_incident_id_input(incident_id)
    with connect() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM incidents
            WHERE incident_id=? AND is_deleted=0
            """,
            (normalize_text(incident_id),)
        ).fetchone()
        return dict(row) if row else None


def search_incidents(keyword, page, page_size):
    key = normalize_text(keyword).lower()
    like = f"%{key}%"
    page = max(1, int(page))
    page_size = max(1, int(page_size))
    offset = (page - 1) * page_size

    where_sql = "is_deleted=0"
    params = []
    if key:
        where_sql += """
            AND (
                lower(incident_id) LIKE ?
                OR lower(error_name) LIKE ?
                OR lower(component) LIKE ?
                OR lower(root_cause) LIKE ?
                OR lower(remark) LIKE ?
                OR lower(action_taken) LIKE ?
                OR lower(start_date) LIKE ?
                OR lower(start_time) LIKE ?
                OR lower(end_date) LIKE ?
                OR lower(end_time) LIKE ?
                OR lower(status) LIKE ?
                OR lower(modified_by) LIKE ?
            )
        """
        params.extend([like] * 12)

    with connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM incidents WHERE {where_sql}",
            params
        ).fetchone()["n"]
        rows = conn.execute(
            f"""
            SELECT incident_id, error_name, component, root_cause, remark, action_taken,
                   start_date, start_time, end_date, end_time, duration_minutes, status,
                   modified_by, modified_at
            FROM incidents
            WHERE {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset]
        ).fetchall()
        return total, [dict(r) for r in rows]


def update_incident(incident_id, updates, actor_username, actor_full_name):
    incident_id = _normalize_incident_id_input(incident_id)
    with tx(immediate=True) as conn:
        pending = conn.execute(
            "SELECT 1 FROM delete_requests WHERE incident_id=? AND status='Pending'",
            (normalize_text(incident_id),)
        ).fetchone()
        if pending:
            raise ValueError("Cannot update incident while delete request is pending.")

        row = conn.execute(
            "SELECT * FROM incidents WHERE incident_id=? AND is_deleted=0",
            (normalize_text(incident_id),)
        ).fetchone()
        if not row:
            raise ValueError("Incident not found or already deleted.")

        current = dict(row)
        allowed_updates = {
            "root_cause",
            "remark",
            "action_taken",
            "start_time",
            "end_time",
            "status"
        }
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_updates}
        merged = {
            "incident_id": current["incident_id"],
            "error_name": current["error_name"],
            "component": current["component"],
            "root_cause": filtered_updates.get("root_cause", current["root_cause"]),
            "remark": filtered_updates.get("remark", current["remark"]),
            "action_taken": filtered_updates.get("action_taken", current["action_taken"]),
            "start_date": current["start_date"],
            "start_time": filtered_updates.get("start_time", current["start_time"]),
            "end_date": current["end_date"],
            "end_time": filtered_updates.get("end_time", current["end_time"]),
            "duration_minutes": filtered_updates.get("duration_minutes", current["duration_minutes"]),
            "status": filtered_updates.get("status", current["status"])
        }
        clean = _validate_incident_payload(merged, allow_status=True)

        editable_fields = [
            "root_cause", "remark", "action_taken",
            "start_time", "end_time", "duration_minutes", "status"
        ]
        for field in editable_fields:
            old_value = str(current[field]) if current[field] is not None else ""
            new_value = str(clean[field]) if clean[field] is not None else ""
            if old_value != new_value:
                conn.execute(
                    """
                    INSERT INTO incident_change_logs(
                        incident_id, field_name, old_value, new_value, modified_by, modified_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        clean["incident_id"],
                        field,
                        old_value,
                        new_value,
                        _build_modified_by(actor_full_name),
                        now_iso()
                    )
                )

        conn.execute(
            """
            UPDATE incidents
            SET root_cause=?,
                remark=?,
                action_taken=?,
                start_date=?,
                start_time=?,
                end_date=?,
                end_time=?,
                duration_minutes=?,
                status=?,
                modified_by=?,
                modified_at=?
            WHERE incident_id=? AND is_deleted=0
            """,
            (
                clean["root_cause"], clean["remark"], clean["action_taken"],
                clean["start_date"], clean["start_time"], clean["end_date"],
                clean["end_time"], clean["duration_minutes"], clean["status"],
                _build_modified_by(actor_full_name), now_iso(), clean["incident_id"]
            )
        )
        log_audit(conn, actor_username, "INCIDENT_UPDATE", "INCIDENT", clean["incident_id"], "Updated incident fields.")


def request_delete_incident(incident_id, actor_username, actor_role):
    incident_id = _normalize_incident_id_input(incident_id)
    if actor_role != "CS Leader":
        raise ValueError("Only CS Leader can submit delete requests.")
    with tx(immediate=True) as conn:
        row = conn.execute(
            "SELECT 1 FROM incidents WHERE incident_id=? AND is_deleted=0",
            (incident_id,)
        ).fetchone()
        if not row:
            raise ValueError("Incident not found or already deleted.")

        pending = conn.execute(
            "SELECT 1 FROM delete_requests WHERE incident_id=? AND status='Pending'",
            (incident_id,)
        ).fetchone()
        if pending:
            raise ValueError("A pending delete request already exists for this incident.")

        conn.execute(
            """
            INSERT INTO delete_requests(incident_id, requested_by, status, requested_at)
            VALUES (?, ?, 'Pending', ?)
            """,
            (incident_id, actor_username, now_iso())
        )
        log_audit(conn, actor_username, "DELETE_REQUEST_CREATE", "INCIDENT", incident_id, "Delete request submitted.")


def list_delete_requests():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT incident_id, requested_by, status, approver, requested_at, approved_at
            FROM delete_requests
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def approve_delete_request(incident_id, actor_username, actor_role):
    incident_id = _normalize_incident_id_input(incident_id)
    if actor_role not in ["CS Leader", "Manager"]:
        raise ValueError("Only CS Leader and Manager can approve delete requests.")

    with tx(immediate=True) as conn:
        req = conn.execute(
            """
            SELECT id, status
            FROM delete_requests
            WHERE incident_id=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (incident_id,)
        ).fetchone()
        if not req:
            raise ValueError("Delete request not found.")
        if req["status"] != "Pending":
            raise ValueError("Delete request already processed.")

        inc = conn.execute(
            "SELECT 1 FROM incidents WHERE incident_id=? AND is_deleted=0",
            (incident_id,)
        ).fetchone()
        if not inc:
            raise ValueError("Incident already deleted.")

        conn.execute(
            """
            UPDATE delete_requests
            SET status='Approved', approver=?, approved_at=?
            WHERE id=?
            """,
            (actor_username, now_iso(), req["id"])
        )
        conn.execute(
            "DELETE FROM incident_change_logs WHERE incident_id=?",
            (incident_id,)
        )
        conn.execute(
            "DELETE FROM incidents WHERE incident_id=?",
            (incident_id,)
        )
        conn.execute(
            "DELETE FROM audit_logs WHERE target_type='INCIDENT' AND target_id=?",
            (incident_id,)
        )
        log_audit(conn, actor_username, "INCIDENT_DELETE_FINAL", "INCIDENT", incident_id, "Incident permanently deleted.")


def get_change_logs(incident_id):
    incident_id = _normalize_incident_id_input(incident_id)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT field_name, old_value, new_value, modified_by, modified_at
            FROM incident_change_logs
            WHERE incident_id=?
            ORDER BY id DESC
            """,
            (incident_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_incidents():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT incident_id, error_name, component, root_cause, action_taken,
                   start_date, start_time, end_date, end_time,
                   duration_minutes, status, modified_by, modified_at
            FROM incidents
            WHERE is_deleted=0
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
