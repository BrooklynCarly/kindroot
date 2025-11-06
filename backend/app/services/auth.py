"""
Authentication service for Google OAuth 2.0
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/callback")

# Optional: Restrict to specific domain (e.g., your organization's Google Workspace)
ALLOWED_DOMAIN = os.getenv("ALLOWED_EMAIL_DOMAIN")  # e.g., "yourcompany.com"

# Optional: Whitelist specific email addresses (comma-separated)
ALLOWED_EMAILS = os.getenv("ALLOWED_EMAILS", "").split(",") if os.getenv("ALLOWED_EMAILS") else []

# Initialize OAuth
oauth = OAuth()

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def validate_user_email(email: str) -> bool:
    """
    Validate if user email is allowed to access the system
    
    Args:
        email: User's email address
        
    Returns:
        True if email is allowed, False otherwise
    """
    # Check if email is in whitelist
    if ALLOWED_EMAILS and email.strip() in [e.strip() for e in ALLOWED_EMAILS]:
        return True
    
    # Check domain restriction
    if not ALLOWED_DOMAIN:
        # If no domain restriction and not in whitelist, allow all emails
        return True
    
    return email.endswith(f"@{ALLOWED_DOMAIN}")


def create_user_session(user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a user session with access token
    
    Args:
        user_info: User information from Google OAuth
        
    Returns:
        Session data including access token
        
    Raises:
        HTTPException: If user email is not allowed
    """
    email = user_info.get("email")
    
    if not validate_user_email(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Only {ALLOWED_DOMAIN} email addresses are allowed."
        )
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": email,
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": email,
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
        }
    }
