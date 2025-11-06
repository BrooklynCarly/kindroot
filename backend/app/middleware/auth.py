"""
Authentication middleware for protecting API routes
"""
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth import verify_token

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        User information from token
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    return payload


async def verify_auth_header(request: Request):
    """
    Middleware to verify authentication header on protected routes
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If authentication fails
    """
    # Skip auth for public endpoints
    public_paths = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/auth/login",
        "/api/auth/callback",
    ]
    
    if request.url.path in public_paths:
        return
    
    # Check for Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    token = auth_header.split(" ")[1]
    verify_token(token)
