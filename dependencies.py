#dependencies.py
from fastapi import Depends, HTTPException, status
from auth.auth_bearer import JWTBearer
from auth.auth_handler import decode_jwt

def get_current_user(token: str = Depends(JWTBearer())):
    """Dependency to get current authenticated user"""
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return payload

def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to require admin role"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def get_user_id(current_user: dict = Depends(get_current_user)) -> int:
    """Extract user ID from token"""
    try:
        return int(current_user.get("sub", 0))
    except:
        return 0