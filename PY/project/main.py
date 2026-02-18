from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List
from sql_database import DatabaseManager

app = FastAPI(title="SQLite Database API", version="1.0.0")
db = DatabaseManager()


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: int


class PostCreate(BaseModel):
    user_id: int
    title: str
    content: str


@app.get("/")
def root():
    return {"message": "SQLite Database API"}


@app.post("/users/", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    user_id = db.create_user(user.name, user.email, user.age)
    if not user_id:
        raise HTTPException(400, "Failed to create user")
    return {"user_id": user_id}


@app.get("/users/")
def get_users():
    return db.get_all_users()


@app.post("/posts/")
def create_post(post: PostCreate):
    post_id = db.create_post(post.user_id, post.title, post.content)
    return {"post_id": post_id}


@app.get("/posts/")
def get_posts():
    return db.get_all_posts()


@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    if not db.delete_user(user_id):
        raise HTTPException(404, "User not found")
    return {"message": "User deleted"}


@app.delete("/posts/{post_id}")
def delete_post(post_id: int):
    if not db.delete_post(post_id):
        raise HTTPException(404, "Post not found")
    return {"message": "Post deleted"}
