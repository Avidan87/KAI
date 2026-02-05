"""
JWT Authentication for KAI - Supabase Auth Integration

Uses Supabase Auth for secure password-based authentication.
Tokens issued by Supabase are verified server-side.
"""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from kai.database.db_setup import get_supabase

logger = logging.getLogger(__name__)

security = HTTPBearer()


def sign_up_user(email: str, password: str) -> dict:
    """
    Sign up a new user with Supabase Auth.

    Args:
        email: User's email address
        password: User's password (min 6 characters)

    Returns:
        dict: Contains user info and session tokens

    Raises:
        ValueError: If signup fails (e.g., email already exists, weak password)
    """
    client = get_supabase()

    try:
        response = client.auth.sign_up({
            "email": email,
            "password": password
        })

        if response.user is None:
            raise ValueError("Signup failed - no user returned")

        logger.info(f"✓ User signed up: {email}")

        return {
            "user_id": response.user.id,
            "email": response.user.email,
            "access_token": response.session.access_token if response.session else None,
            "refresh_token": response.session.refresh_token if response.session else None,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"✗ Signup failed for {email}: {error_msg}")

        # Parse common Supabase Auth errors
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            raise ValueError("Email already registered")
        elif "password" in error_msg.lower():
            raise ValueError("Password must be at least 6 characters")
        else:
            raise ValueError(f"Signup failed: {error_msg}")


def sign_in_user(email: str, password: str) -> dict:
    """
    Sign in an existing user with Supabase Auth.

    Args:
        email: User's email address
        password: User's password

    Returns:
        dict: Contains user info and session tokens

    Raises:
        ValueError: If login fails (e.g., invalid credentials)
    """
    client = get_supabase()

    try:
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if response.user is None:
            raise ValueError("Login failed - invalid credentials")

        logger.info(f"✓ User signed in: {email}")

        return {
            "user_id": response.user.id,
            "email": response.user.email,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"✗ Login failed for {email}: {error_msg}")

        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            raise ValueError("Invalid email or password")
        else:
            raise ValueError(f"Login failed: {error_msg}")


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract and verify user_id from Supabase JWT token.

    Verifies the token with Supabase Auth server to ensure it's valid.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        str: The authenticated user's ID

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    client = get_supabase()

    try:
        # Verify token with Supabase Auth
        response = client.auth.get_user(token)

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return response.user.id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
