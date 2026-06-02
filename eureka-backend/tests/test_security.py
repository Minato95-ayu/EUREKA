"""
Security tests for EUREKA — generated via ECC tdd-guide agent.
Covers JWT create/verify/expiry/tampering and config validation.
"""

import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from app.security import SecurityManager, validate_security_config


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def manager():
    return SecurityManager(
        secret_key="a-very-secure-test-key-at-least-32-chars!!",
        algorithm="HS256",
    )


# ─── Token Creation ───────────────────────────────────────────────────────────

class TestCreateToken:
    def test_valid_admin_role(self, manager):
        token = manager.create_token("user_abc", "admin")
        payload = manager.verify_token(token)
        assert payload["user_id"] == "user_abc"
        assert payload["role"] == "admin"

    def test_valid_viewer_role(self, manager):
        token = manager.create_token("user_xyz", "viewer")
        payload = manager.verify_token(token)
        assert payload["role"] == "viewer"

    def test_invalid_role_defaults_to_viewer(self, manager):
        """Unknown roles must fall back to 'viewer', not escalate."""
        token = manager.create_token("user123", "superuser")
        payload = manager.verify_token(token)
        assert payload["role"] == "viewer"

    def test_token_has_expiry(self, manager):
        token = manager.create_token("user123", "viewer")
        payload = pyjwt.decode(
            token,
            "a-very-secure-test-key-at-least-32-chars!!",
            algorithms=["HS256"],
        )
        assert "exp" in payload
        assert "iat" in payload

    def test_token_is_string(self, manager):
        token = manager.create_token("user123", "editor")
        assert isinstance(token, str)
        assert len(token) > 20


# ─── Token Verification ───────────────────────────────────────────────────────

class TestVerifyToken:
    def test_expired_token_raises(self, manager):
        """Expired tokens must be rejected."""
        payload = {
            "user_id": "user123",
            "role": "viewer",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = pyjwt.encode(
            payload,
            "a-very-secure-test-key-at-least-32-chars!!",
            algorithm="HS256",
        )
        with pytest.raises(Exception) as exc_info:
            manager.verify_token(expired_token)
        # HTTPException stores message in .detail, not in str() repr
        err = exc_info.value
        err_text = getattr(err, "detail", str(err)).lower()
        assert "expired" in err_text

    def test_tampered_token_raises(self, manager):
        """Tampered tokens must be rejected."""
        token = manager.create_token("user123", "admin")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(Exception):
            manager.verify_token(tampered)

    def test_wrong_secret_raises(self, manager):
        """Token signed with wrong secret must be rejected."""
        other_manager = SecurityManager(
            secret_key="completely-different-secret-key-32chars",
            algorithm="HS256",
        )
        token = other_manager.create_token("user123", "admin")
        with pytest.raises(Exception):
            manager.verify_token(token)

    def test_empty_token_raises(self, manager):
        with pytest.raises(Exception):
            manager.verify_token("")

    def test_malformed_token_raises(self, manager):
        with pytest.raises(Exception):
            manager.verify_token("not.a.jwt")


# ─── Security Config Validation ──────────────────────────────────────────────

class TestValidateSecurityConfig:
    def _mock_settings(self, env, auth_required, secret_key):
        mock = MagicMock()
        mock.ENVIRONMENT = env
        mock.AUTH_REQUIRED = auth_required
        mock.SECRET_KEY = secret_key
        return mock

    def test_production_with_weak_key_raises(self):
        with patch("app.security.get_settings") as mock_get:
            mock_get.return_value = self._mock_settings(
                env="production",
                auth_required=True,
                secret_key="short",
            )
            with pytest.raises(RuntimeError, match="SECRET_KEY"):
                validate_security_config()

    def test_production_with_default_key_raises(self):
        with patch("app.security.get_settings") as mock_get:
            mock_get.return_value = self._mock_settings(
                env="production",
                auth_required=True,
                secret_key="your-secret-key-change-in-production",
            )
            with pytest.raises(RuntimeError, match="SECRET_KEY"):
                validate_security_config()

    def test_production_auth_disabled_raises(self):
        with patch("app.security.get_settings") as mock_get:
            mock_get.return_value = self._mock_settings(
                env="production",
                auth_required=False,
                secret_key="a-very-long-and-secure-production-key-that-is-good",
            )
            with pytest.raises(RuntimeError, match="AUTH_REQUIRED"):
                validate_security_config()

    def test_development_passes_without_error(self):
        with patch("app.security.get_settings") as mock_get:
            mock_get.return_value = self._mock_settings(
                env="development",
                auth_required=False,
                secret_key="any-key",  # dev mode — no strict check
            )
            # Should not raise
            validate_security_config()

    def test_production_valid_config_passes(self):
        with patch("app.security.get_settings") as mock_get:
            mock_get.return_value = self._mock_settings(
                env="production",
                auth_required=True,
                secret_key="a-very-long-and-secure-production-key-that-is-good",
            )
            # Should not raise
            validate_security_config()
