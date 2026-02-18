import hashlib
import re
from datetime import datetime


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def validate_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True


def now():
    return datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")


def format_datetime(date_obj, time_obj):
    dt = datetime.combine(date_obj, time_obj)
    return dt.strftime("%d/%m/%Y %I:%M %p"), dt


def calculate_minutes(start, end):
    return int((end - start).total_seconds() / 60)
