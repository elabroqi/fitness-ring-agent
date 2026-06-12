from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os
from datetime import datetime, timezone

load_dotenv()

app = FastAPI(title="Fitness Agent Telemetry Aggregator")

# Initialize database connections
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGODB_DB", "fitness_agent")]

# Initialize the official Google GenAI SDK (Reads GEMINI_API_KEY from environment)
ai_client = genai.Client()

# =============================================================================
# 📋 AGENT CHAT REQUEST/RESPONSE SCHEMAS
# =============================================================================
class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str

# =============================================================================
# 🛠️ MODEL CONTEXT PROTOCOL (MCP) TOOLS FOR GEMINI
# =============================================================================

def query_user_fitness_summary(user_id: str) -> dict:
    """MCP Tool: Retrieves the absolute latest daily summary (steps, calories, active minutes) for a user."""
    summary = db.daily_summaries.find_one({"user_id": user_id}, sort=[("date", -1)])
    if not summary:
        return {"error": "No fitness summary metrics found."}
    return {
        "steps": summary.get("steps", 0),
        "calories": summary.get("calories", 0),
        "distance_meters": summary.get("distance_meters", 0),
        "active_minutes": summary.get("active_minutes", 0),
        "date": str(summary.get("date"))
    }

def query_latest_biometrics(user_id: str) -> dict:
    """MCP Tool: Retrieves the newest granular heart rate (bpm) and stress samples for a user."""
    hr = db.heart_rate_samples.find_one({"user_id": user_id}, sort=[("timestamp", -1)])
    stress = db.stress_samples.find_one({"user_id": user_id}, sort=[("timestamp", -1)])
    return {
        "latest_heart_rate_bpm": hr.get("bpm", 0) if hr else "No Data",
        "latest_stress_score": stress.get("score", 0) if stress else "No Data"
    }

def query_user_rewards(user_id: str) -> dict:
    """MCP Tool: Retrieves all loyalty, gamification, and unlocked brand milestones for a user."""
    rewards = list(db.rewards.find({"user_id": user_id}).sort("unlocked_at", -1).limit(3))
    if not rewards:
        return {"message": "User hasn't unlocked any rewards yet."}
    return [
        {
            "brand": r.get("brand"),
            "tier": r.get("tier"),
            "description": r.get("description"),
            "used": r.get("used", False)
        } for r in rewards
    ]

# =============================================================================
# 📋 EQUIPMENT HARDWARE PROVISIONING SCHEMAS
# =============================================================================

class DeviceBindingPayload(BaseModel):
    user_id: str
    device_name: str
    ios_peripheral_uuid: str
    device_family: str
    bound_at: Optional[datetime] = None

class UnbindDevicePayload(BaseModel):
    user_id: str

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
    device_bound: bool = False

    steps: int = 0
    distance_meters: int = 0
    active_minutes: int = 0
    calories: float = 0

    bpm: int = 0
    spo2: int = 0
    stress_score: int = 0

    latest_reward: Optional[RewardItem] = None

# =============================================================================
# 🚀 CORE AI AGENT ENDPOINT ROUTE
# =============================================================================

@app.post("/agent/chat", response_model=ChatResponse)
def execute_agent_chat_loop(request: ChatRequest):
    """
    Handles live conversational strings from the iOS App. Fires a Gemini session 
    with functional routing tools acting as a lightweight MongoDB MCP server container.
    """
    try:
        # Define the system identity and context constraints for Google Agent Builder rules
        system_instruction = """
        You are the intelligence core of the Fitness Agent Ring iOS application. 
        You are connected directly to the user's secure MongoDB Atlas cluster via MCP tools.

        When a user asks a question, always invoke the appropriate database tools to inspect their real-time telemetry (bpm, steps, rewards). 
        Translate the data into natural, encouraging human insights. 

        CRITICAL: Never mention technical phrases like 'database', 'MCP', 'rows', 'collections', or 'tools' to the user. 
        Speak directly about their health, progress, and unlocked badges as an invisible assistant.
        """
        
        # Bundle our functional read handlers as available tools
        mcp_tools = [query_user_fitness_summary, query_latest_biometrics, query_user_rewards]
        
        # Configure the execution agent state parameters
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=mcp_tools,
            temperature=0.3,
        )
        
        # Format execution context prompt explicitly mapping the session target
        prompt_with_context = f"Context User ID: {request.user_id}\nUser Question: {request.message}"
        
        # FIX: Point to verified stable model identifier node matching the current SDK specification
        response = ai_client.models.generate_content(
            model='gemini-3-flash',
            contents=prompt_with_context,
            config=config
        )
        
        # Fallback safeguard in case text parsing block is returned empty
        reply_text = response.text if response.text else "I looked into your profile metrics, but couldn't compile a clear update right now."
        return ChatResponse(reply=reply_text)
        
    except Exception as agent_error:
        # Prints output details directly to the running python console block to trace bugs
        print(f"❌ Backend Agent Process Fault: {str(agent_error)}")
        raise HTTPException(
            status_code=500, 
            detail=f"AI Agent runtime engine execution failure: {str(agent_error)}"
        )
    

@app.post("/devices/bind")
def bind_device(payload: DeviceBindingPayload):
    now = datetime.now(timezone.utc)

    # Only allow one active bound device per user.
    db.devices.update_many(
        {"user_id": payload.user_id, "bound": True},
        {
            "$set": {
                "bound": False,
                "updated_at": now,
            }
        },
    )

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

    return {
        "status": "bound",
        "matched_count": result.matched_count,
        "upserted_id": str(result.upserted_id) if result.upserted_id else None,
    }


@app.post("/devices/unbind")
def unbind_device(payload: UnbindDevicePayload):
    now = datetime.now(timezone.utc)

    result = db.devices.update_one(
        {"user_id": payload.user_id, "bound": True},
        {
            "$set": {
                "bound": False,
                "updated_at": now,
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No bound device found for this user.",
        )

    return {
        "status": "success",
        "message": "Device unbound successfully.",
    }


@app.get("/dashboard/{user_id}", response_model=UnifiedDashboardPayload)
def get_dashboard(user_id: str):
    device_doc = db.devices.find_one(
        {"user_id": user_id, "bound": True},
        sort=[("updated_at", -1)],
    )

    summary = db.daily_summaries.find_one(
        {"user_id": user_id},
        sort=[("date", -1)],
    )

    latest_hr = db.heart_rate_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)],
    )

    latest_spo2 = db.spo2_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)],
    )

    latest_stress = db.stress_samples.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)],
    )

    reward_doc = db.rewards.find_one(
        {"user_id": user_id},
        sort=[("unlocked_at", -1)],
    )

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
        device_bound=device_doc.get("bound", False) if device_doc else False,

        steps=summary.get("steps", 0) if summary else 0,
        distance_meters=summary.get("distance_meters", 0) if summary else 0,
        active_minutes=summary.get("active_minutes", 0) if summary else 0,
        calories=summary.get("calories", 0) if summary else 0,

        bpm=latest_hr.get("bpm", 0) if latest_hr else 0,
        spo2=latest_spo2.get("value", latest_spo2.get("spo2", 0)) if latest_spo2 else 0,
        stress_score=latest_stress.get("score", latest_stress.get("stress_score", 0)) if latest_stress else 0,

        latest_reward=formatted_reward,
    )