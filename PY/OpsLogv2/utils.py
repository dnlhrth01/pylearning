import hashlib
import hmac
import re
import secrets
from datetime import datetime


DATE_FMT = "%d/%m/%Y"
TIME_FMT = "%I:%M %p"
DATETIME_FMT = "%d/%m/%Y %I:%M:%S %p"


def now_display():
    return datetime.now().strftime(DATETIME_FMT)


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def normalize_text(value):
    return (value or "").strip()


def contains_script_like_text(value):
    text = normalize_text(value).lower()
    blocked = ["<script", "</script", "javascript:", "onerror=", "onload="]
    return any(token in text for token in blocked)


def validate_full_name(full_name):
    value = normalize_text(full_name)
    if len(value) < 3:
        return False, "Full Name must be at least 3 characters."
    if not re.fullmatch(r"[A-Za-z,\s]+", value):
        return False, "Full Name must contain letters, spaces, and commas only."
    return True, ""


def validate_username(username):
    value = normalize_text(username)
    if len(value) < 3:
        return False, "Username must be at least 3 characters."
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        return False, "Username may contain only letters, numbers, _, ., -."
    return True, ""


def validate_email(email):
    value = normalize_text(email)
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, value) is not None


def validate_password(password):
    value = password or ""
    if len(value) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", value):
        return False, "Password must include at least 1 uppercase letter."
    if not re.search(r"[a-z]", value):
        return False, "Password must include at least 1 lowercase letter."
    if not re.search(r"[0-9]", value):
        return False, "Password must include at least 1 number."
    if not re.search(r"[^A-Za-z0-9]", value):
        return False, "Password must include at least 1 special character."
    return True, ""


def hash_password(password):
    salt = secrets.token_hex(16)
    iterations = 390000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password, stored_hash):
    # Backward compatibility for legacy SHA256 hashes.
    if "$" not in (stored_hash or ""):
        legacy = hashlib.sha256((password or "").encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy, stored_hash or "")

    try:
        algo, iter_str, salt, stored_digest = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
    except Exception:
        return False

    computed = hashlib.pbkdf2_hmac(
        "sha256",
        (password or "").encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    ).hex()
    return hmac.compare_digest(computed, stored_digest)


def parse_date(date_text):
    value = normalize_text(date_text)
    if not re.fullmatch(r"(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/[0-9]{4}", value):
        raise ValueError("Date must be in DD/MM/YYYY format.")
    return datetime.strptime(value, DATE_FMT)


def parse_time(time_text):
    value = normalize_text(time_text)
    if not re.fullmatch(r"(0[1-9]|1[0-2]):[0-5][0-9] (AM|PM)", value):
        raise ValueError("Time must be in HH:MM AM/PM format.")
    return datetime.strptime(value, TIME_FMT)


def calculate_duration_minutes(start_date, start_time, end_date, end_time):
    start_d = parse_date(start_date)
    start_t = parse_time(start_time)
    end_d = parse_date(end_date)
    end_t = parse_time(end_time)
    start_dt = datetime.combine(start_d.date(), start_t.time())
    end_dt = datetime.combine(end_d.date(), end_t.time())
    minutes = int((end_dt - start_dt).total_seconds() // 60)
    return start_dt, end_dt, minutes
