import sqlite3

DB = "opslog.db"


def connect():
    return sqlite3.connect(DB, check_same_thread=False)


def create_tables():
    with connect() as conn:

        conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            is_active INTEGER DEFAULT 1
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents(
            id INTEGER PRIMARY KEY,
            error TEXT,
            component TEXT,
            root_cause TEXT,
            action_taken TEXT,
            start_time TEXT,
            end_time TEXT,
            downtime INTEGER,
            status TEXT,
            created_by TEXT,
            modified TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS delete_requests(
            id INTEGER PRIMARY KEY,
            incident_id INTEGER,
            requested_by TEXT
        )
        """)
