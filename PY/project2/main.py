from fastapi import FastAPI
from pydantic import BaseModel, EmailStr
from mongo_database import DatabaseManager

app = FastAPI(title="MongoDB API")
db = DatabaseManager()


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: int


@app.post("/users/")
def create_user(user: UserCreate):
    return {"id": db.create_user(user.name, user.email, user.age)}


@app.get("/users/")
def get_users():
    users = db.get_all_users()
    for u in users:
        u["_id"] = str(u["_id"])
    return users
