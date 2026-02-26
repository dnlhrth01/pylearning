from database import (
    ASSIGNABLE_ROLES,
    clear_login_attempts,
    create_user,
    get_user,
    is_login_locked,
    register_login_failure,
    tx
)
from utils import (
    hash_password,
    normalize_text,
    now_iso,
    validate_email,
    validate_full_name,
    validate_password,
    validate_username,
    verify_password
)


ROLES = ASSIGNABLE_ROLES
DEFAULT_MANAGER_USERNAME = "manager"
DEFAULT_MANAGER_EMAIL = "manager@opslog.com"
DEFAULT_MANAGER_PASSWORD = "Manager@123"


def create_manager():
    existing = get_user(DEFAULT_MANAGER_USERNAME)
    if existing:
        return

    with tx(immediate=True) as conn:
        conn.execute(
            """
            INSERT INTO users(
                full_name, email, username, password_hash, role, is_active, created_at
            ) VALUES (?, ?, ?, ?, 'Manager', 1, ?)
            """,
            (
                "System Manager",
                DEFAULT_MANAGER_EMAIL,
                DEFAULT_MANAGER_USERNAME,
                hash_password(DEFAULT_MANAGER_PASSWORD),
                now_iso()
            )
        )
        conn.execute(
            """
            INSERT INTO audit_logs(actor, action, target_type, target_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_MANAGER_USERNAME,
                "SYSTEM_MANAGER_CREATED",
                "USER",
                DEFAULT_MANAGER_USERNAME,
                "Default manager account created.",
                now_iso()
            )
        )


def register(full_name, email, username, password):
    full_name = normalize_text(full_name)
    email = normalize_text(email).lower()
    username = normalize_text(username)

    ok, msg = validate_full_name(full_name)
    if not ok:
        raise ValueError(msg)
    ok, msg = validate_username(username)
    if not ok:
        raise ValueError(msg)
    if not validate_email(email):
        raise ValueError("Invalid email format.")
    ok, msg = validate_password(password)
    if not ok:
        raise ValueError(msg)

    if get_user(username):
        raise ValueError("Username already exists.")
    with tx() as conn:
        email_exists = conn.execute(
            "SELECT 1 FROM users WHERE lower(email)=lower(?)",
            (email,)
        ).fetchone()
        if email_exists:
            raise ValueError("Email already exists.")

    create_user(
        full_name=full_name,
        email=email,
        username=username,
        password_hash=hash_password(password)
    )


def login(username, password):
    username = normalize_text(username)
    if not username or not password:
        return None, "Username and password are required."

    if is_login_locked(username):
        return None, "Too many failed attempts. Try again in 15 minutes."

    user = get_user(username)
    if not user:
        register_login_failure(username)
        return None, "Invalid credentials."

    if not verify_password(password, user["password_hash"]):
        register_login_failure(username)
        return None, "Invalid credentials."

    if not user["is_active"]:
        return None, "Account suspended. Please contact Manager."

    if not normalize_text(user["role"]):
        return None, "Role not assigned. Please contact Manager."

    clear_login_attempts(username)
    return user, ""
