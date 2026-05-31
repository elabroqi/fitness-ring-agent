import os
import logging
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Import your storage layer to use its production index configurations
from colmi_r02_client import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def initialize_production_database():
    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB")

    if not mongo_uri or not db_name:
        logger.error("❌ Missing MONGODB_URI or MONGODB_DB in your .env file!")
        return

    logger.info(f"🔌 Connecting to Atlas Cluster... Target DB: {db_name}")
    client = MongoClient(mongo_uri, server_api=ServerApi('1'))
    db = client[db_name]

    # Initialize the strict, idempotent structural indexes for your live telemetry
    logger.info("🛠️ Building production collection structures and indexes...")
    storage.ensure_indexes(db)
    
    logger.info("✅ Database infrastructure is locked and optimized!")
    logger.info(f"Active Active Collections: {db.list_collection_names()}")
    
    client.close()

if __name__ == "__main__":
    initialize_production_database()