"""
AIVA Server — Authentication & Rate Limiting
================================================
Dual-mode authentication: static bearer token (dev) or JWT (production).

Mode is set via AIVA_AUTH_MODE env var:
    - "static" (default): Uses AIVA_AUTH_TOKEN for simple dev testing
    - "jwt": Uses AIVA_JWT_SECRET for signed JWT validation

Rate limiting is mode-independent.
"""

import time
import logging
import threading
from collections import defaultdict
from typing import Optional

from server.config import AUTH_TOKEN, AUTH_MODE, MAX_FPS_PER_CLIENT

logger = logging.getLogger("aiva.auth")


class AuthError(Exception):
    """Raised when authentication fails."""
    pass


class RateLimitError(Exception):
    """Raised when client exceeds frame rate limit."""
    pass


class Authenticator:
    """
    Dual-mode authenticator: static bearer token or JWT.

    Automatically selects mode based on AIVA_AUTH_MODE config.
    JWT mode requires AIVA_JWT_SECRET to be set.
    """

    def __init__(self):
        self._jwt_manager = None
        self._mode = AUTH_MODE  # "static" or "jwt"

        if self._mode == "jwt":
            try:
                from server.jwt_auth import JWTManager
                self._jwt_manager = JWTManager()
                logger.info("Auth mode: JWT (HS256)")
            except (ImportError, AuthError) as e:
                logger.warning(f"JWT init failed ({e}), falling back to static token")
                self._mode = "static"
        else:
            logger.info("Auth mode: static bearer token")

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def jwt_manager(self):
        """Access JWT manager for token generation/refresh (JWT mode only)."""
        return self._jwt_manager

    def validate_token(self, token: Optional[str]) -> bool:
        """
        Validate a bearer token or JWT.

        Args:
            token: Token string from Authorization header

        Returns:
            True if valid

        Raises:
            AuthError: If token is missing or invalid
        """
        if not token:
            raise AuthError("Missing authentication token")

        # Strip "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]

        if self._mode == "jwt" and self._jwt_manager:
            # JWT validation (returns payload dict, raises AuthError on failure)
            self._jwt_manager.validate_token(token)
            return True

        # Static token validation (development mode)
        if not AUTH_TOKEN:
            raise AuthError("Server auth token not configured")

        if token != AUTH_TOKEN:
            raise AuthError("Invalid authentication token")

        return True

    def extract_token(self, headers: dict) -> Optional[str]:
        """
        Extract bearer token from WebSocket headers.

        Args:
            headers: Request headers dict

        Returns:
            Token string or None
        """
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return auth_header if auth_header else None

    def get_client_id(self, token: Optional[str]) -> str:
        """
        Extract client identifier from token.

        JWT mode: returns 'sub' claim.
        Static mode: returns 'static-client'.
        """
        if self._mode == "jwt" and self._jwt_manager and token:
            clean = token[7:] if token.startswith("Bearer ") else token
            return self._jwt_manager.get_client_id(clean)
        return "static-client"


class RateLimiter:
    """
    Per-client frame rate limiter.

    Enforces MAX_FPS_PER_CLIENT to prevent abuse and server overload.
    Uses a sliding window of 1 second.
    """

    def __init__(self, max_fps: int = MAX_FPS_PER_CLIENT):
        self._max_fps = max_fps
        self._min_interval = 1.0 / max_fps if max_fps > 0 else 0
        # Track frame timestamps per client: client_id → [timestamps]
        self._client_frames: dict = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, client_id: str) -> None:
        """
        Check if client is within rate limit.

        Args:
            client_id: Unique client identifier (IP:port or connection ID)

        Raises:
            RateLimitError: If client exceeds max FPS
        """
        now = time.time()
        window_start = now - 1.0  # 1-second sliding window

        with self._lock:
            # Remove timestamps outside window
            self._client_frames[client_id] = [
                t for t in self._client_frames[client_id]
                if t > window_start
            ]

            if len(self._client_frames[client_id]) >= self._max_fps:
                raise RateLimitError(
                    f"Rate limit exceeded: {len(self._client_frames[client_id])} "
                    f"frames in last second (max {self._max_fps})"
                )

            self._client_frames[client_id].append(now)

    def remove_client(self, client_id: str) -> None:
        """Remove tracking for a disconnected client."""
        with self._lock:
            self._client_frames.pop(client_id, None)

    @property
    def max_fps(self) -> int:
        return self._max_fps
