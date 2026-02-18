from database import connect
from utils import hash_password

ROLES = [
    "SO Engineer",
    "Service Field Engineer",
    "CS Leader"
]


def create_manager():

    with connect() as conn:

        cur = conn.execute(
            "SELECT * FROM users WHERE role='Manager'"
        )

        if not cur.fetchone():

            conn.execute("""
            INSERT INTO users(
                full_name,email,username,password,role
            )
            VALUES(?,?,?,?,?)
            """, (
                "System Manager",
                "manager@opslog.com",
                "manager",
                hash_password("Manager123"),
                "Manager"
            ))


def register(full, email, username, password, role):

    with connect() as conn:

        cur = conn.execute(
            "SELECT 1 FROM users WHERE username=? OR email=?",
            (username, email)
        )

        if cur.fetchone():
            raise ValueError("Username or email already exists.")

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
