from database import connect
from utils import hash_password

ROLES = [
    "SO Engineer",
    "Service Field Engineer",
    "CS Leader"
]


def create_developer():
    with connect() as conn:

        cur = conn.execute(
            "SELECT * FROM users WHERE role='Developer'"
        )

        if not cur.fetchone():

            conn.execute("""
            INSERT INTO users(
                full_name,email,username,password,role
            )
            VALUES(?,?,?,?,?)
            """, (
                "System Developer",
                "dev@opslog.com",
                "developer",
                hash_password("Dev12345"),
                "Developer"
            ))


def register(full, email, username, password, role):

    with connect() as conn:
        conn.execute("""
        INSERT INTO users(
            full_name,email,username,password,role
        )
        VALUES(?,?,?,?,?)
        """, (full, email, username, hash_password(password), role))


def login(username, password):

    with connect() as conn:

        cur = conn.execute("""
        SELECT username,role,is_active
        FROM users
        WHERE username=? AND password=?
        """, (username, hash_password(password)))

        return cur.fetchone()
