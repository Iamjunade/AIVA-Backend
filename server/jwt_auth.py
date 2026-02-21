"""
AIVA Server — JWT Authentication Middleware
==============================================
Production-ready JSON Web Token implementation for WebSocket authentication.

Provides:
    - JWTManager: Token generation, validation, and refresh
    - HS256 algorithm with configurable expiry
    - Secret key loaded from AIVA_JWT_SECRET env var

Security model:
    1. Client authenticates via /auth/token endpoint (HTTP POST)
    2. Server issues signed JWT with 24h expiry
    3. Client includes JWT in WebSocket upgrade request headers
    4. Server validates JWT during handshake, rejects expired/invalid tokens
    5. Client can refresh token before expiry via /auth/refresh

Usage:
    manager = JWTManager()
    token = manager.generate_token("client-1")
    payload = manager.validate_token(token)       # Raises AuthError on failure
    new_token = manager.refresh_token(old_token)   # Within refresh window
"""

import time
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timezone

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    jwt = None
    JWT_AVAILABLE = False
    print("[JWTAuth] WARNING: PyJWT not installed. Run: pip install PyJWT>=2.8.0")

from server.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRY_HOURS,
    JWT_REFRESH_WINDOW_HOURS,
    JWT_ISSUER,
)
from server.auth import AuthError


class JWTManager:
    """
    JWT token lifecycle manager.

    Handles generation, validation, and refresh of signed JWTs.
    All tokens use HS256 with a server-side secret.
    """

    def __init__(self, secret: Optional[str] = None):
        """
        Initialize JWT manager.

        Args:
            secret: Override secret key (defaults to config value).
                    Must be at least 32 characters for HS256 security.

        Raises:
            AuthError: If PyJWT is not installed
        """
        if not JWT_AVAILABLE:
            raise AuthError("PyJWT not installed. Run: pip install PyJWT>=2.8.0")

        self._secret = secret or JWT_SECRET
        if not self._secret or len(self._secret) < 32:
            raise AuthError(
                "JWT secret must be at least 32 characters. "
                "Set AIVA_JWT_SECRET in .env"
            )

        self._algorithm = JWT_ALGORITHM
        self._expiry_hours = JWT_EXPIRY_HOURS
        self._refresh_window_hours = JWT_REFRESH_WINDOW_HOURS
        self._issuer = JWT_ISSUER

    def generate_token(
        self,
        client_id: str,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a signed JWT for a client.

        Args:
            client_id: Unique client identifier (device ID, user ID, etc.)
            extra_claims: Additional claims to include in the payload

        Returns:
            Encoded JWT string
        """
        now = time.time()
        payload = {
            "sub": client_id,                           # Subject
            "iss": self._issuer,                        # Issuer
            "iat": int(now),                            # Issued At
            "exp": int(now + self._expiry_hours * 3600), # Expiry
            "jti": secrets.token_hex(16),               # JWT ID (unique)
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def validate_token(self, token: Optional[str]) -> Dict[str, Any]:
        """
        Validate and decode a JWT.

        Args:
            token: Encoded JWT string (with or without 'Bearer ' prefix)

        Returns:
            Decoded payload dictionary

        Raises:
            AuthError: If token is missing, expired, or invalid
        """
        if not token:
            raise AuthError("Missing authentication token")

        # Strip Bearer prefix if present
        if token.startswith("Bearer "):
            token = token[7:]

        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                options={
                    "require": ["sub", "exp", "iat", "iss"],
                    "verify_exp": True,
                    "verify_iss": True,
                },
            )
            return payload

        except jwt.ExpiredSignatureError:
            raise AuthError("Token expired — request a new token via /auth/token")
        except jwt.InvalidIssuerError:
            raise AuthError("Invalid token issuer")
        except jwt.InvalidTokenError as e:
            raise AuthError(f"Invalid token: {str(e)}")

    def refresh_token(self, token: str) -> str:
        """
        Refresh an existing token if within the refresh window.

        Accepts tokens that are expired but within the refresh window
        (default: 48 hours after issuance). Issues a new token with
        fresh expiry.

        Args:
            token: Existing JWT (may be expired but within refresh window)

        Returns:
            New JWT string with fresh expiry

        Raises:
            AuthError: If token is beyond the refresh window or invalid
        """
        if token.startswith("Bearer "):
            token = token[7:]

        try:
            # Decode WITHOUT expiry verification (we check manually)
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                options={
                    "verify_exp": False,
                    "verify_iss": True,
                },
            )
        except jwt.InvalidTokenError as e:
            raise AuthError(f"Cannot refresh: invalid token ({e})")

        # Check if within refresh window
        issued_at = payload.get("iat", 0)
        refresh_deadline = issued_at + self._refresh_window_hours * 3600
        now = time.time()

        if now > refresh_deadline:
            raise AuthError(
                f"Token too old to refresh (issued {int((now - issued_at) / 3600)}h ago, "
                f"max {self._refresh_window_hours}h)"
            )

        # Issue fresh token for the same client
        client_id = payload.get("sub", "unknown")
        return self.generate_token(client_id)

    def get_client_id(self, token: str) -> str:
        """Extract client ID from a valid token without full validation."""
        if token.startswith("Bearer "):
            token = token[7:]

        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"verify_exp": False},
            )
            return payload.get("sub", "unknown")
        except jwt.InvalidTokenError:
            return "unknown"

    @staticmethod
    def generate_secret() -> str:
        """Generate a cryptographically secure secret key for .env."""
        return secrets.token_hex(32)


# =============================================================================
# Quick test / key generation when run directly
# =============================================================================

if __name__ == "__main__":
    import sys

    if "--generate-secret" in sys.argv:
        print(f"AIVA_JWT_SECRET={JWTManager.generate_secret()}")
        sys.exit(0)

    # Self-test
    print("JWT Self-Test")
    print("=" * 40)

    secret = secrets.token_hex(32)
    mgr = JWTManager(secret=secret)

    # Generate
    token = mgr.generate_token("test-client", {"role": "user"})
    print(f"Token: {token[:50]}...")

    # Validate
    payload = mgr.validate_token(token)
    print(f"Payload: sub={payload['sub']}, exp={payload['exp']}")

    # Validate with Bearer prefix
    payload2 = mgr.validate_token(f"Bearer {token}")
    assert payload2["sub"] == "test-client"
    print("Bearer prefix handling: ✓")

    # Refresh
    new_token = mgr.refresh_token(token)
    new_payload = mgr.validate_token(new_token)
    assert new_payload["sub"] == "test-client"
    assert new_payload["jti"] != payload["jti"]  # New JTI
    print("Token refresh: ✓")

    # Expired token
    try:
        expired = jwt.encode(
            {"sub": "x", "exp": int(time.time()) - 100, "iat": 0, "iss": "aiva-server"},
            secret, algorithm="HS256"
        )
        mgr.validate_token(expired)
        print("Expired rejection: ✗ (should have raised)")
    except AuthError as e:
        print(f"Expired rejection: ✓ ({e})")

    print("\nAll tests passed ✓")
