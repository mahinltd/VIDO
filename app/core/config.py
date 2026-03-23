# ©2026 VIDO Mahin Ltd develop by (Tanvir)

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "VIDO Backend API"
    DATABASE_NAME: str = "vido_db"
    
    # These variables MUST be provided in the .env file or environment
    MONGODB_URL: str
    SECRET_KEY: str
    
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    # PayPal Configurations
    PAYPAL_MODE: str = "sandbox"
    PAYPAL_CLIENT_ID: str
    PAYPAL_SECRET: str
    PAYPAL_WEBHOOK_ID: str

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()