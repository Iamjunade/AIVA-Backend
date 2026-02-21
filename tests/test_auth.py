"""
Tests for AIVA Server Authentication & Rate Limiting
"""

import time
import pytest
from unittest.mock import patch

from server.auth import Authenticator, RateLimiter, AuthError


# Check if RateLimitError exists
try:
    from server.auth import RateLimitError
except ImportError:
    RateLimitError = Exception


# =============================================================================
# AUTHENTICATOR
# =============================================================================

class TestAuthenticator:
    """Tests for bearer token validation."""

    @patch("server.auth.AUTH_TOKEN", "test-secret-token")
    def test_valid_token_passes(self):
        auth = Authenticator()
        result = auth.validate_token("test-secret-token")
        assert result is True

    @patch("server.auth.AUTH_TOKEN", "test-secret-token")
    def test_invalid_token_raises(self):
        auth = Authenticator()
        with pytest.raises(AuthError):
            auth.validate_token("wrong-token")

    @patch("server.auth.AUTH_TOKEN", "test-secret-token")
    def test_empty_token_raises(self):
        auth = Authenticator()
        with pytest.raises(AuthError):
            auth.validate_token("")

    @patch("server.auth.AUTH_TOKEN", "test-secret-token")
    def test_none_token_raises(self):
        auth = Authenticator()
        with pytest.raises(AuthError):
            auth.validate_token(None)

    @patch("server.auth.AUTH_TOKEN", "test-secret-token")
    def test_bearer_prefix_stripped_by_validate(self):
        """validate_token should strip 'Bearer ' prefix."""
        auth = Authenticator()
        result = auth.validate_token("Bearer test-secret-token")
        assert result is True

    @patch("server.auth.AUTH_TOKEN", "test-secret-token")
    def test_extract_bearer_from_headers(self):
        auth = Authenticator()
        headers = {"Authorization": "Bearer test-secret-token"}
        token = auth.extract_token(headers)
        assert token == "test-secret-token"

    @patch("server.auth.AUTH_TOKEN", "test-secret-token")
    def test_extract_token_no_bearer_prefix(self):
        auth = Authenticator()
        headers = {"Authorization": "test-secret-token"}
        token = auth.extract_token(headers)
        assert token == "test-secret-token"

    @patch("server.auth.AUTH_TOKEN", "test-secret-token")
    def test_extract_token_missing_header(self):
        auth = Authenticator()
        headers = {}
        token = auth.extract_token(headers)
        assert token is None

    @patch("server.auth.AUTH_TOKEN", "test-secret-token")
    def test_extract_token_empty_header(self):
        auth = Authenticator()
        headers = {"Authorization": ""}
        token = auth.extract_token(headers)
        assert token is None


# =============================================================================
# RATE LIMITER
# =============================================================================

class TestRateLimiter:
    """Tests for per-client rate limiting."""

    def test_first_request_allowed(self):
        """First request should always succeed (no exception)."""
        limiter = RateLimiter(max_fps=30)
        limiter.check("client-1")  # Should not raise

    def test_rapid_requests_limited(self):
        """Exceeding max_fps in 1 second should raise RateLimitError."""
        limiter = RateLimiter(max_fps=1)
        limiter.check("client-1")  # First allowed
        with pytest.raises(RateLimitError):
            limiter.check("client-1")  # Second immediately → over limit

    def test_different_clients_independent(self):
        """Each client has an independent rate limit."""
        limiter = RateLimiter(max_fps=1)
        limiter.check("client-1")
        limiter.check("client-2")  # Should not raise

    def test_after_window_reset(self):
        """After 1 second window, limit resets."""
        limiter = RateLimiter(max_fps=1)
        limiter.check("client-1")
        time.sleep(1.1)  # Wait for window to expire
        limiter.check("client-1")  # Should not raise

    def test_remove_client(self):
        """After removal, client's frame history is cleared."""
        limiter = RateLimiter(max_fps=1)
        limiter.check("client-1")
        limiter.remove_client("client-1")
        # After removal, should be able to send again
        limiter.check("client-1")  # Should not raise

    def test_max_fps_property(self):
        limiter = RateLimiter(max_fps=15)
        assert limiter.max_fps == 15
