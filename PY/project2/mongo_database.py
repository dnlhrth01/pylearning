from pymongo import MongoClient
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        client = MongoClient("mongodb://localhost:27017")
        db = client["bootcamp"]
        self.users = db["users"]
        self.posts = db["posts"]

    def create_user(self, name, email, age):
        result = self.users.insert_one({
            "name": name,
            "email": email,
            "age": age,
            "created_at": datetime.utcnow()
        })
        return str(result.inserted_id)

    def get_all_users(self):
        return list(self.users.find())

    def create_post(self, user_id, title, content):
        result = self.posts.insert_one({
            "user_id": user_id,
            "title": title,
            "content": content,
            "created_at": datetime.utcnow()
        })
        return str(result.inserted_id)
