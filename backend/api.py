from fastapi import FastAPI
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGODB_DB", "fitness_agent")]


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/dashboard/{user_id}")
def get_dashboard(user_id: str):

    summary = db.daily_summaries.find_one(
        {"user_id": user_id},
        sort=[("date", -1)]
    )

    if not summary:
        return {"error": "No data found"}

    return {
        "user_id": user_id,
        "date": str(summary.get("date")),
        "steps": summary.get("steps", 0),
        "distance_meters": summary.get("distance_meters", 0),
        "active_minutes": summary.get("active_minutes", 0),
        "calories": summary.get("calories", 0)
    }