# ©2026 VIDO Mahin Ltd develop by (Tanvir)

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# Model for User Registration request
class UserCreate(BaseModel):
    email: str = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long")

# Model for User Login request
class UserLogin(BaseModel):
    email: str
    password: str

# Model for sending User data back to the client (Android App)
class UserResponse(BaseModel):
    id: str
    email: str
    is_premium: bool
    daily_downloads: int
    premium_expiry: Optional[datetime] = None
    created_at: datetime

# Model for JWT Token response
class Token(BaseModel):
    access_token: str
    token_type: str

# Model for extracting Token data
class TokenData(BaseModel):
    email: Optional[str] = None