"""OAuth2 core implementation.

Provides OAuth2 Authorization Code flow with PKCE support,
token management, and refresh handling per the MCP June 2025 spec.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class OAuth2Flow(Enum):
    """Supported OAuth2 flows."""

    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    DEVICE_CODE = "device_code"


@dataclass
class OAuth2Token:
    """OAuth2 access token with optional refresh token.

    Handles token storage, expiration checking, and serialization.
    """

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    issued_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired.

        Returns:
            True if token has expired (with 60s buffer), False otherwise
        """
        if self.expires_in is None:
            return False
        expiry_time = self.issued_at + self.expires_in - 60  # 60s buffer
        return time.time() > expiry_time

    @property
    def authorization_header(self) -> str:
        """Get the Authorization header value.

        Returns:
            Header value like "Bearer <token>"
        """
        return f"{self.token_type} {self.access_token}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize token to dictionary.

        Returns:
            Dict representation of the token
        """
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
            "issued_at": self.issued_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OAuth2Token":
        """Deserialize token from dictionary.

        Args:
            data: Dict with token data

        Returns:
            OAuth2Token instance
        """
        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in"),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            issued_at=data.get("issued_at", time.time()),
        )

    def to_json(self) -> str:
        """Serialize token to JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "OAuth2Token":
        """Deserialize token from JSON string.

        Args:
            json_str: JSON string

        Returns:
            OAuth2Token instance
        """
        return cls.from_dict(json.loads(json_str))


@dataclass
class OAuth2Config:
    """OAuth2 configuration for a provider.

    Contains all settings needed for OAuth2 authentication including
    endpoints, client credentials, and PKCE settings.
    """

    # Provider identification
    provider_name: str

    # OAuth2 endpoints
    authorization_url: str
    token_url: str
    revoke_url: str | None = None
    userinfo_url: str | None = None

    # Client credentials
    client_id: str = ""
    client_secret: str | None = None  # None for public clients using PKCE

    # OAuth2 settings
    scopes: list[str] = field(default_factory=list)
    redirect_uri: str = "http://localhost:8080/callback"

    # PKCE settings (required for public clients per MCP spec)
    use_pkce: bool = True
    pkce_method: str = "S256"

    # Resource Indicators (RFC 8707)
    resource: str | None = None

    # Additional settings
    extra_auth_params: dict[str, str] = field(default_factory=dict)
    extra_token_params: dict[str, str] = field(default_factory=dict)

    def get_authorization_url(
        self,
        state: str,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        """Build the authorization URL.

        Args:
            state: Random state for CSRF protection
            code_challenge: PKCE code challenge (if using PKCE)
            code_challenge_method: PKCE method ("S256" or "plain")

        Returns:
            Full authorization URL with query parameters
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
        }

        if self.scopes:
            params["scope"] = " ".join(self.scopes)

        if self.use_pkce and code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method or self.pkce_method

        if self.resource:
            params["resource"] = self.resource

        params.update(self.extra_auth_params)

        return f"{self.authorization_url}?{urlencode(params)}"

    def get_token_request_data(
        self,
        code: str,
        code_verifier: str | None = None,
    ) -> dict[str, str]:
        """Build token request data.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier (if using PKCE)

        Returns:
            Dict of form data for token request
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "code": code,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        if self.use_pkce and code_verifier:
            data["code_verifier"] = code_verifier

        if self.resource:
            data["resource"] = self.resource

        data.update(self.extra_token_params)

        return data

    def get_refresh_token_data(self, refresh_token: str) -> dict[str, str]:
        """Build refresh token request data.

        Args:
            refresh_token: The refresh token

        Returns:
            Dict of form data for refresh request
        """
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        if self.resource:
            data["resource"] = self.resource

        return data
