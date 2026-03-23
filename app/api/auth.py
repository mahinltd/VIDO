# ©2026 VIDO Mahin Ltd develop by (Tanvir)

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime
import jwt

from app.models.user import UserCreate, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.db.mongodb import get_database

router = APIRouter()

# OAuth2 scheme for dependency injection in secure routes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """
    Register a new user, hash their password, save to MongoDB, and return a JWT token.
    """
    db = get_database()
    users_collection = db.get_collection("users")

    # Check if the user already exists
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Hash the password and prepare user document
    hashed_password = get_password_hash(user.password)
    new_user = {
        "email": user.email,
        "password_hash": hashed_password,
        "is_premium": False,
        "daily_downloads": 0,
        "premium_expiry": None,
        "created_at": datetime.utcnow()
    }

    # Insert into database
    await users_collection.insert_one(new_user)

    # Generate JWT Token
    access_token = create_access_token(data={"sub": user.email, "is_premium": False})
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate a user using Form Data (compatible with Swagger Authorize button).
    """
    db = get_database()
    users_collection = db.get_collection("users")

    # Find user using form_data.username (which is the email)
    db_user = await users_collection.find_one({"email": form_data.username})

    if not db_user or not verify_password(form_data.password, db_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": db_user["email"], "is_premium": db_user.get("is_premium", False)}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Dependency function to extract and verify the current user from the JWT token.
    This will be used to protect other API routes (like the extraction API).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    db = get_database()
    user = await db.get_collection("users").find_one({"email": email})
    
    if user is None:
        raise credentials_exception
        
    return user