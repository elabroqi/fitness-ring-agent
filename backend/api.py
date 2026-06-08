from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

client = MongoClient(os.getenv("MONGO_URI"))
# Make sure this DB name matches what this script writes to (e.g., "fitness_agent")
db = client[os.getenv("MONGODB_DB", "fitness_agent")] 

@app.get("/dashboard/{user_id}")
def get_dashboard(user_id: str):
    # 1. Pulls the pre-aggregated daily data created by recompute_daily_summary()
    summary = db.daily_summaries.find_one(
        {"user_id": user_id},
        sort=[("date", -1)]
    )

    # 2. Pulls the latest single minute metric processed by upsert_heart_rate_log()
    latest_hr = db.heart_rate_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )

    # 3. Pulls from your custom stress metrics logs
    latest_stress = db.stress_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )

    # 4. Pulls your gamification badge logs
    latest_reward = db.rewards.find_one(
        {"user_id": user_id},
        sort=[("unlocked_at", -1)]
    )

    if not summary and not latest_hr:
        raise HTTPException(status_code=404, detail="No sync records found for this user.")

    return {
        "user_id": user_id,
        "date": str(summary.get("date")) if summary else None,
        
        # Activity Metrics (Matches fields in your file's _daily_id summary block)
        "steps": summary.get("steps", 0) if summary else 0,
        "distance_meters": summary.get("distance_meters", 0) if summary else 0,
        "active_minutes": summary.get("active_minutes", 0) if summary else 0,
        "calories": summary.get("calories", 0) if summary else 0,
        
        # Biometrics (Matches keys used in upsert_heart_rate_log)
        "bpm": latest_hr.get("bpm", 0) if latest_hr else 0,
        "stress_score": latest_stress.get("stress_score", 0) if latest_stress else 0,
        
        # Rewards Object block
        "latest_reward": {
            "brand": latest_reward.get("brand", "None"),
            "tier": latest_reward.get("tier", "None"),
            "description": latest_reward.get("description", "")
        } if latest_reward else None
    }