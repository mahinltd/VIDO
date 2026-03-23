# ©2026 VIDO Mahin Ltd develop by (Tanvir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.api import auth, extract, webhooks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown events.
    It ensures the database connection is opened when the server starts
    and closed gracefully when the server stops.
    """
    # Startup event
    await connect_to_mongo()
    yield
    # Shutdown event
    await close_mongo_connection()

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Universal Video Downloader Backend API for Android App",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS (Cross-Origin Resource Sharing)
# Since the Android app will make requests, allowing all origins during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific domains if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(extract.router, prefix="/api", tags=["Media Extraction"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Monetization Webhooks"])

@app.get("/", tags=["Health Check"])
async def root():
    """
    Root endpoint to verify the server is running.
    """
    return {
        "status": "online",
        "message": f"Welcome to the {settings.PROJECT_NAME}",
        "docs_url": "/docs"
    }