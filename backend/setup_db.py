from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.server_api import ServerApi
import os
from datetime import datetime

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"), server_api=ServerApi('1'))
db = client[os.getenv("MONGODB_DB")]

# Users collection
db.users.insert_one({
    "username": "aurela",
    "max_heart_rate": 190,
    "preferred_brands": ["Starbucks", "Nike", "Spotify"],
    "risk_tolerance": "medium",
    "created_at": datetime.utcnow()
})

# Workouts collection
db.workouts.create_index([("user_id", ASCENDING), ("started_at", ASCENDING)])
db.workouts.insert_one({
    "user_id": "aurela",
    "started_at": datetime.utcnow(),
    "duration_minutes": 25,
    "avg_heart_rate": 145,
    "max_heart_rate": 167,
    "hr_zone": 3,
    "reward_tier": "silver",
    "xapi_sent": False
})

# Portfolio collection
db.portfolio.insert_one({
    "user_id": "aurela",
    "asset": "BTC",
    "amount_usd": 0.10,
    "quantity": 0.0000015,
    "purchased_at": datetime.utcnow(),
    "workout_id": None,
    "price_at_purchase": 67000.00
})

# Rewards collection
db.rewards.insert_one({
    "user_id": "aurela",
    "tier": "silver",
    "brand": "Starbucks",
    "description": "Free drink up to $7",
    "unlocked_at": datetime.utcnow(),
    "used": False,
    "expires_at": None
})

print("Collections created and sample data inserted!")
print("Collections:", db.list_collection_names())