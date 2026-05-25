"""
Security module for EUREKA backend.
Handles JWT authentication, rate limiting, CORS, and security middleware.
"""

import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends, WebSocket, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import get_settings


# Secret key for JWT
settings = get_settings()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_HOURS = settings.ACCESS_TOKEN_EXPIRE_HOURS
ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3}

# HTTP Bearer scheme. auto_error=False lets local/dev mode bypass auth cleanly.
security_scheme = HTTPBearer(auto_error=False)


class SecurityManager:
    """Manages JWT token creation and verification."""

    def __init__(self, secret_key: str = SECRET_KEY, algorithm: str = ALGORITHM):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(self, user_id: str, role: str = "viewer") -> str:
        """Create a JWT token for a user."""
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user_id,
            "role": role if role in ROLE_RANK else "viewer",
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


def validate_security_config() -> None:
    """Fail fast for unsafe production auth settings."""
    cfg = get_settings()
    if cfg.ENVIRONMENT.lower() == "production":
        if not cfg.AUTH_REQUIRED:
            raise RuntimeError("AUTH_REQUIRED must be true in production.")
        if cfg.SECRET_KEY == "your-secret-key-change-in-production" or len(cfg.SECRET_KEY) < 32:
            raise RuntimeError("SECRET_KEY must be a strong non-default value in production.")


# Global security manager instance
security_manager = SecurityManager()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict:
    """FastAPI dependency to get the current authenticated user from JWT."""
    cfg = get_settings()
    if not cfg.AUTH_REQUIRED:
        return {"user_id": "dev-user", "role": "admin", "auth_bypass": True}
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = credentials.credentials
    payload = security_manager.verify_token(token)
    return payload


def require_role(required_role: str):
    """FastAPI dependency factory for simple RBAC checks."""
    async def dependency(user: dict = Depends(get_current_user)) -> dict:
        user_role = user.get("role", "viewer")
        if ROLE_RANK.get(user_role, 0) < ROLE_RANK.get(required_role, 99):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role",
            )
        return user
    return dependency


def verify_websocket_token(websocket: WebSocket, required_role: str = "viewer") -> dict:
    """Validate WebSocket auth before accepting a connection."""
    cfg = get_settings()
    if not cfg.AUTH_REQUIRED:
        return {"user_id": "dev-user", "role": "admin", "auth_bypass": True}

    auth_header = websocket.headers.get("authorization", "")
    token = websocket.query_params.get("token")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing WebSocket auth token")

    payload = security_manager.verify_token(token)
    user_role = payload.get("role", "viewer")
    if ROLE_RANK.get(user_role, 0) < ROLE_RANK.get(required_role, 99):
        raise HTTPException(status_code=403, detail=f"Requires {required_role} role")
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
