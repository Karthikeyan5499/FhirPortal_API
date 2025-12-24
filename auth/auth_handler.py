# auth/auth_handler.py
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from config import settings
from .auth_bearer import JWTBearer

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============ REFRESH TOKEN SETTINGS ============

class Token(BaseModel):
    access_token: str
    refresh_token: str  # NEW
    token_type: str


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class LoginRequest(BaseModel):
    username: str
    password: str


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create access token (short-lived: 15 minutes)"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    """Create refresh token (long-lived: configured days)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_jwt(token: str):
    """Decode and validate JWT token"""
    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Check expiration
        if decoded["exp"] < datetime.utcnow().timestamp():
            return None
            
        return decoded
    except JWTError:
        return None


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """
    Login endpoint - Returns both access token and refresh token
    
    - Access Token: Valid for 15 minutes (for API calls)
    - Refresh Token: Valid for 7 days (to get new access tokens)
    """
    # TODO: Replace with database user verification
    if request.username == "admin" and request.password == "admin123":
        token_data = {"sub": request.username, "role": "admin"}
        
        # Generate both tokens
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password"
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    
    When the access token expires (after 15 minutes), the frontend can use
    this endpoint with the refresh token to get a new access token without
    requiring the user to log in again.
    
    Request Body:
```json
    {
      "refresh_token": "your-refresh-token-here"
    }
```
    
    Returns:
        New access token and refresh token
    """
    try:
        # Decode refresh token
        payload = decode_jwt(request.refresh_token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Refresh token required."
            )
        
        # Extract user data
        username = payload.get("sub")
        role = payload.get("role")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Generate new tokens
        token_data = {"sub": username, "role": role}
        new_access_token = create_access_token(data=token_data)
        new_refresh_token = create_refresh_token(data=token_data)
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token"
        )


@router.post("/register")
async def register(request: LoginRequest):
    """Register new user (TODO: Implement database storage)"""
    hashed_password = get_password_hash(request.password)
    # TODO: Save to database
    return {"message": "User registered successfully"}


@router.get("/verify-token")
async def verify_token(token: str = Depends(JWTBearer())):
    """
    Verify if the current access token is valid
    
    Useful for frontend to check if user is still authenticated
    """
    payload = decode_jwt(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return {
        "valid": True,
        "user": payload.get("sub"),
        "role": payload.get("role"),
        "expires_at": payload.get("exp")
    }