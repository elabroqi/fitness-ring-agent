from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGODB_DB", "fitness_agent")]

# ==========================================
# API RESPONSE MODELS
# Defines the data returned to the mobile app
# ==========================================

class RewardSchema(BaseModel):
    brand: str
    tier: str
    description: str
    unlocked_at: Optional[str] = None
    used: bool

class DashboardResponse(BaseModel):
    user_id: str
    date: Optional[str] = None

    # Daily activity summary
    steps: int
    distance_meters: int
    active_minutes: int
    calories: int

    # Latest biometric measurements
    bpm: int
    spo2: int
    stress_score: int

    # Most recently unlocked reward
    latest_reward: Optional[RewardSchema] = None

# ==========================================
# DASHBOARD ENDPOINT
# Aggregates activity, biometrics, and rewards
# into a single payload for the app dashboard
# ==========================================

@app.get("/dashboard/{user_id}", response_model=DashboardResponse)
def get_dashboard(user_id: str):

    # Retrieve the most recent daily activity summary
    summary = db.daily_summaries.find_one(
        {"user_id": user_id},
        sort=[("date", -1)]
    )

    # Retrieve the latest heart rate measurement
    latest_hr = db.heart_rate_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )

    # Retrieve the latest blood oxygen measurement
    latest_spo2 = db.spo2_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )

    # Retrieve the latest stress measurement
    latest_stress = db.stress_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )

    # Retrieve the most recently unlocked reward
    reward_doc = db.rewards.find_one(
        {"user_id": user_id},
        sort=[("unlocked_at", -1)]
    )

    # Return a 404 if no dashboard data exists yet
    if not any([summary, latest_hr, latest_spo2, latest_stress, reward_doc]):
        raise HTTPException(
            status_code=404,
            detail="No metric tracking data found."
        )

    # Convert reward document into API response format
    formatted_reward = None
    if reward_doc:
        formatted_reward = RewardSchema(
            brand=reward_doc.get("brand", "Unknown"),
            tier=reward_doc.get("tier", "Unknown"),
            description=reward_doc.get("description", ""),
            unlocked_at=str(reward_doc.get("unlocked_at")) if reward_doc.get("unlocked_at") else None,
            used=reward_doc.get("used", False)
        )

    # Build dashboard response using the latest available data
    return DashboardResponse(
        user_id=user_id,
        date=str(summary.get("date")) if summary else None,

        steps=summary.get("steps", 0) if summary else 0,
        distance_meters=summary.get("distance_meters", 0) if summary else 0,
        active_minutes=summary.get("active_minutes", 0) if summary else 0,
        calories=summary.get("calories", 0) if summary else 0,

        bpm=latest_hr.get("bpm", 0) if latest_hr else 0,
        spo2=latest_spo2.get("value", latest_spo2.get("spo2", 0)) if latest_spo2 else 0,
        stress_score=latest_stress.get("score", latest_stress.get("stress_score", 0)) if latest_stress else 0,

        latest_reward=formatted_reward
    )