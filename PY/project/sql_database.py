import sqlite3
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_name="database.db"):
        self.db_name = db_name
        self.initialize_database()

    def initialize_database(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT UNIQUE,
                age INTEGER,
                created_at TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                content TEXT,
                created_at TEXT
            )
            """)

    # USER CRUD
    def create_user(self, name, email, age):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO users(name,email,age,created_at)
                VALUES(?,?,?,?)
                """, (name, email, age, datetime.now().isoformat()))
                return cursor.lastrowid
        except:
            return None

    def get_all_users(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            return cursor.fetchall()

    def delete_user(self, user_id):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
            return cursor.rowcount > 0

    # POSTS
    def create_post(self, user_id, title, content):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO posts(user_id,title,content,created_at)
            VALUES(?,?,?,?)
            """, (user_id, title, content, datetime.now().isoformat()))
            return cursor.lastrowid

    def get_all_posts(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts ORDER BY created_at DESC")
            return cursor.fetchall()

    def delete_post(self, post_id):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM posts WHERE id=?", (post_id,))
            return cursor.rowcount > 0
