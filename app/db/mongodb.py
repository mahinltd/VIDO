# ©2026 VIDO Mahin Ltd develop by (Tanvir)

from motor.motor_asyncio import AsyncIOMotorClient
import logging
from app.core.config import settings

# Configure logging to see connection status in the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    """
    Creates an asynchronous connection to MongoDB Atlas.
    """
    logger.info("Attempting to connect to MongoDB Atlas...")
    try:
        db.client = AsyncIOMotorClient(settings.MONGODB_URL)
        db.db = db.client[settings.DATABASE_NAME]
        logger.info("Successfully connected to MongoDB!")
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")

async def close_mongo_connection():
    """
    Closes the database connection gracefully.
    """
    logger.info("Closing MongoDB connection...")
    if db.client is not None:
        db.client.close()
        logger.info("MongoDB connection successfully closed.")

def get_database():
    """
    Utility function to retrieve the active database instance.
    """
    return db.db