from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

load_dotenv()

app = FastAPI(title="Fitness Agent Telemetry Aggregator")

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGODB_DB", "fitness_agent")]


class DeviceBindingPayload(BaseModel):
    user_id: str
    device_name: str
    ios_peripheral_uuid: str
    device_family: str
    bound_at: Optional[datetime] = None


class RewardItem(BaseModel):
    brand: str
    tier: str
    description: str
    unlocked_at: Optional[str] = None
    used: bool


class UnifiedDashboardPayload(BaseModel):
    user_id: str
    date: Optional[str] = None

    connected_device_name: str = "No Device Bound"
    battery_level: int = 0
    device_type: Optional[str] = None

    steps: int
    distance_meters: int
    active_minutes: int
    calories: float

    bpm: int
    spo2: int
    stress_score: int

    latest_reward: Optional[RewardItem] = None


@app.post("/devices/bind")
def bind_device(payload: DeviceBindingPayload):
    now = datetime.now(timezone.utc)

    document = {
        "user_id": payload.user_id,
        "name": payload.device_name,
        "ios_peripheral_uuid": payload.ios_peripheral_uuid,
        "device_type": payload.device_family,
        "bound": True,
        "bound_at": payload.bound_at or now,
        "updated_at": now,
    }

    result = db.devices.update_one(
        {
            "user_id": payload.user_id,
            "ios_peripheral_uuid": payload.ios_peripheral_uuid,
        },
        {
            "$set": document,
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    return {"status": "bound", "matched_count": result.matched_count}


@app.get("/dashboard/{user_id}", response_model=UnifiedDashboardPayload)
def get_dashboard(user_id: str):
    device_doc = db.devices.find_one(
        {"user_id": user_id, "bound": True},
        sort=[("updated_at", -1)]
    )

    summary = db.daily_summaries.find_one(
        {"user_id": user_id},
        sort=[("date", -1)]
    )

    latest_hr = db.heart_rate_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )

    latest_spo2 = db.spo2_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )

    latest_stress = db.stress_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )

    reward_doc = db.rewards.find_one(
        {"user_id": user_id},
        sort=[("unlocked_at", -1)]
    )

    if not any([device_doc, summary, latest_hr, latest_spo2, latest_stress, reward_doc]):
        raise HTTPException(status_code=404, detail="No user data found.")

    formatted_reward = None
    if reward_doc:
        formatted_reward = RewardItem(
            brand=reward_doc.get("brand", "Unknown"),
            tier=reward_doc.get("tier", "Unknown"),
            description=reward_doc.get("description", ""),
            unlocked_at=str(reward_doc.get("unlocked_at")) if reward_doc.get("unlocked_at") else None,
            used=reward_doc.get("used", False),
        )

    return UnifiedDashboardPayload(
        user_id=user_id,
        date=str(summary.get("date")) if summary else None,

        connected_device_name=device_doc.get("name", "Unknown Ring") if device_doc else "No Device Bound",
        battery_level=device_doc.get("battery_level", 0) if device_doc else 0,
        device_type=device_doc.get("device_type") if device_doc else None,

        steps=summary.get("steps", 0) if summary else 0,
        distance_meters=summary.get("distance_meters", 0) if summary else 0,
        active_minutes=summary.get("active_minutes", 0) if summary else 0,
        calories=summary.get("calories", 0) if summary else 0,

        bpm=latest_hr.get("bpm", 0) if latest_hr else 0,
        spo2=latest_spo2.get("value", latest_spo2.get("spo2", 0)) if latest_spo2 else 0,
        stress_score=latest_stress.get("score", latest_stress.get("stress_score", 0)) if latest_stress else 0,

        latest_reward=formatted_reward,
    )