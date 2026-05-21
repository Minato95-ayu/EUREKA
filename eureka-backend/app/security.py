"""
Security module for EUREKA backend.
Handles JWT authentication, rate limiting, CORS, and security middleware.
"""

import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address


# Secret key for JWT
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# HTTP Bearer scheme
security_scheme = HTTPBearer()


class SecurityManager:
    """Manages JWT token creation and verification."""

    def __init__(self, secret_key: str = SECRET_KEY, algorithm: str = ALGORITHM):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(self, user_id: str) -> str:
        """Create a JWT token for a user."""
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user_id,
            "exp": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
            "iat": now,
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_token(self, token: str) -> dict:
        """Verify a JWT token and return the payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
            )


# Global security manager instance
security_manager = SecurityManager()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """FastAPI dependency to get the current authenticated user from JWT."""
    token = credentials.credentials
    payload = security_manager.verify_token(token)
    return payload


# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


def setup_cors(app):
    """Configure CORS middleware for production."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "https://eureka.example.com",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )


def setup_security_middleware(app):
    """Add security middleware including trusted hosts."""
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.example.com"],
    )
