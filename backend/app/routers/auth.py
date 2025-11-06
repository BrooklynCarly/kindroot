"""
Authentication endpoints for Google OAuth 2.0
"""
import os
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from starlette.config import Config
from app.services.auth import oauth, create_user_session, GOOGLE_CLIENT_ID
from app.middleware.auth import get_current_user, security

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Frontend URL for OAuth redirect (configurable for production)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.get("/login")
async def login(request: Request):
    """
    Initiate Google OAuth login flow
    
    Returns:
        Redirect to Google OAuth consent screen
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )
    
    # Generate redirect URI for OAuth callback
    redirect_uri = request.url_for('auth_callback')
    logger.info(f"Initiating OAuth login with redirect_uri: {redirect_uri}")
    
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request):
    """
    Handle Google OAuth callback
    
    Returns:
        Redirect to frontend with access token
    """
    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info:
            # Fallback: fetch user info if not in token
            resp = await oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
            user_info = resp.json()
        
        logger.info(f"User authenticated: {user_info.get('email')}")
        
        # Create session with JWT token
        session_data = create_user_session(user_info)
        
        # Redirect to frontend with token
        redirect_url = f"{FRONTEND_URL}?token={session_data['access_token']}"
        
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information
    
    Returns:
        Current user details
    """
    return {
        "email": current_user.get("sub"),
        "name": current_user.get("name"),
        "picture": current_user.get("picture"),
    }


@router.post("/logout")
async def logout():
    """
    Logout endpoint (client-side token deletion)
    
    Returns:
        Success message
    """
    return {"message": "Logged out successfully"}


@router.get("/status")
async def auth_status(request: Request):
    """
    Check authentication configuration status
    
    Returns:
        OAuth configuration status
    """
    return {
        "oauth_configured": bool(GOOGLE_CLIENT_ID),
        "google_client_id": GOOGLE_CLIENT_ID[:20] + "..." if GOOGLE_CLIENT_ID else None,
    }
