"""Tests for OAuth2/PKCE authentication module."""

import base64
import hashlib
import time

import pytest

from tool_factory.auth import (
    OAuth2Config,
    OAuth2Flow,
    OAuth2Token,
    PKCECodeVerifier,
    generate_code_challenge,
    generate_code_verifier,
    OAuth2Provider,
    GitHubOAuth2Provider,
    GoogleOAuth2Provider,
    AzureADOAuth2Provider,
    CustomOAuth2Provider,
)
from tool_factory.auth.providers import get_provider, OAUTH2_PROVIDERS


class TestPKCE:
    """Tests for PKCE implementation."""

    def test_generate_code_verifier_default_length(self):
        """Test code verifier generation with default length."""
        verifier = generate_code_verifier()
        assert len(verifier) == 64
        # Verify it's base64url safe characters
        assert all(c.isalnum() or c in "-_" for c in verifier)

    def test_generate_code_verifier_custom_length(self):
        """Test code verifier generation with custom length."""
        verifier = generate_code_verifier(length=43)
        assert len(verifier) == 43

        verifier = generate_code_verifier(length=128)
        assert len(verifier) == 128

    def test_generate_code_verifier_invalid_length(self):
        """Test code verifier with invalid length raises error."""
        with pytest.raises(ValueError, match="between 43 and 128"):
            generate_code_verifier(length=42)

        with pytest.raises(ValueError, match="between 43 and 128"):
            generate_code_verifier(length=129)

    def test_generate_code_challenge_s256(self):
        """Test S256 code challenge generation."""
        verifier = "test_verifier_string_123456789012345678901234"
        challenge = generate_code_challenge(verifier, method="S256")

        # Verify by recreating the challenge
        expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected_challenge = (
            base64.urlsafe_b64encode(expected_digest).decode("ascii").rstrip("=")
        )

        assert challenge == expected_challenge

    def test_generate_code_challenge_plain(self):
        """Test plain code challenge (returns verifier as-is)."""
        verifier = "test_verifier_string_123456789012345678901234"
        challenge = generate_code_challenge(verifier, method="plain")
        assert challenge == verifier

    def test_generate_code_challenge_invalid_method(self):
        """Test invalid challenge method raises error."""
        with pytest.raises(ValueError, match="Unsupported code challenge method"):
            generate_code_challenge("test", method="invalid")

    def test_pkce_code_verifier_generate(self):
        """Test PKCECodeVerifier.generate() class method."""
        pkce = PKCECodeVerifier.generate()

        assert len(pkce.verifier) == 64
        assert pkce.method == "S256"
        assert pkce.challenge != pkce.verifier  # S256 should transform

        # Verify challenge matches expected
        expected_challenge = generate_code_challenge(pkce.verifier, "S256")
        assert pkce.challenge == expected_challenge

    def test_pkce_code_verifier_to_auth_params(self):
        """Test PKCECodeVerifier.to_auth_params() method."""
        pkce = PKCECodeVerifier.generate()
        params = pkce.to_auth_params()

        assert params["code_challenge"] == pkce.challenge
        assert params["code_challenge_method"] == "S256"

    def test_pkce_code_verifier_to_token_params(self):
        """Test PKCECodeVerifier.to_token_params() method."""
        pkce = PKCECodeVerifier.generate()
        params = pkce.to_token_params()

        assert params["code_verifier"] == pkce.verifier


class TestOAuth2Token:
    """Tests for OAuth2Token class."""

    def test_token_creation(self):
        """Test basic token creation."""
        token = OAuth2Token(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test_refresh_token",
            scope="read write",
        )

        assert token.access_token == "test_access_token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.refresh_token == "test_refresh_token"
        assert token.scope == "read write"

    def test_token_is_expired_false(self):
        """Test token expiration check when not expired."""
        token = OAuth2Token(
            access_token="test",
            expires_in=3600,
            issued_at=time.time(),
        )
        assert not token.is_expired

    def test_token_is_expired_true(self):
        """Test token expiration check when expired."""
        token = OAuth2Token(
            access_token="test",
            expires_in=60,
            issued_at=time.time() - 120,  # Issued 2 minutes ago, expires in 1 minute
        )
        assert token.is_expired

    def test_token_no_expiry(self):
        """Test token with no expiry is never expired."""
        token = OAuth2Token(
            access_token="test",
            expires_in=None,
        )
        assert not token.is_expired

    def test_token_authorization_header(self):
        """Test authorization header generation."""
        token = OAuth2Token(access_token="abc123", token_type="Bearer")
        assert token.authorization_header == "Bearer abc123"

        token2 = OAuth2Token(access_token="xyz789", token_type="MAC")
        assert token2.authorization_header == "MAC xyz789"

    def test_token_to_dict(self):
        """Test token serialization to dict."""
        issued_at = time.time()
        token = OAuth2Token(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="refresh",
            scope="read",
            issued_at=issued_at,
        )

        data = token.to_dict()

        assert data["access_token"] == "test_token"
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 3600
        assert data["refresh_token"] == "refresh"
        assert data["scope"] == "read"
        assert data["issued_at"] == issued_at

    def test_token_from_dict(self):
        """Test token deserialization from dict."""
        data = {
            "access_token": "test_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "refresh",
            "scope": "read",
            "issued_at": 1234567890.0,
        }

        token = OAuth2Token.from_dict(data)

        assert token.access_token == "test_token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.refresh_token == "refresh"
        assert token.scope == "read"
        assert token.issued_at == 1234567890.0

    def test_token_to_json_and_back(self):
        """Test JSON serialization round-trip."""
        original = OAuth2Token(
            access_token="test",
            expires_in=3600,
            refresh_token="refresh",
        )

        json_str = original.to_json()
        restored = OAuth2Token.from_json(json_str)

        assert restored.access_token == original.access_token
        assert restored.expires_in == original.expires_in
        assert restored.refresh_token == original.refresh_token


class TestOAuth2Config:
    """Tests for OAuth2Config class."""

    def test_config_creation(self):
        """Test basic config creation."""
        config = OAuth2Config(
            provider_name="test",
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="test_client",
            scopes=["read", "write"],
        )

        assert config.provider_name == "test"
        assert config.authorization_url == "https://auth.example.com/authorize"
        assert config.token_url == "https://auth.example.com/token"
        assert config.client_id == "test_client"
        assert config.scopes == ["read", "write"]
        assert config.use_pkce is True  # Default

    def test_get_authorization_url_basic(self):
        """Test authorization URL generation."""
        config = OAuth2Config(
            provider_name="test",
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="my_client",
            scopes=["read", "write"],
            redirect_uri="http://localhost:8080/callback",
        )

        url = config.get_authorization_url(state="random_state")

        assert "https://auth.example.com/authorize?" in url
        assert "client_id=my_client" in url
        assert "response_type=code" in url
        assert "state=random_state" in url
        assert "scope=read+write" in url
        assert "redirect_uri=http" in url

    def test_get_authorization_url_with_pkce(self):
        """Test authorization URL with PKCE parameters."""
        config = OAuth2Config(
            provider_name="test",
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="my_client",
            use_pkce=True,
        )

        url = config.get_authorization_url(
            state="state123",
            code_challenge="challenge_abc",
            code_challenge_method="S256",
        )

        assert "code_challenge=challenge_abc" in url
        assert "code_challenge_method=S256" in url

    def test_get_authorization_url_with_resource(self):
        """Test authorization URL with resource indicator (RFC 8707)."""
        config = OAuth2Config(
            provider_name="test",
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="my_client",
            resource="https://api.example.com",
        )

        url = config.get_authorization_url(state="state")
        assert "resource=https" in url

    def test_get_token_request_data(self):
        """Test token request data generation."""
        config = OAuth2Config(
            provider_name="test",
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="my_client",
            client_secret="my_secret",
            redirect_uri="http://localhost:8080/callback",
        )

        data = config.get_token_request_data(code="auth_code_123")

        assert data["grant_type"] == "authorization_code"
        assert data["client_id"] == "my_client"
        assert data["client_secret"] == "my_secret"
        assert data["redirect_uri"] == "http://localhost:8080/callback"
        assert data["code"] == "auth_code_123"

    def test_get_token_request_data_with_pkce(self):
        """Test token request data with PKCE verifier."""
        config = OAuth2Config(
            provider_name="test",
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="my_client",
            use_pkce=True,
        )

        data = config.get_token_request_data(
            code="auth_code",
            code_verifier="verifier_string",
        )

        assert data["code_verifier"] == "verifier_string"

    def test_get_refresh_token_data(self):
        """Test refresh token request data generation."""
        config = OAuth2Config(
            provider_name="test",
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="my_client",
            client_secret="my_secret",
        )

        data = config.get_refresh_token_data(refresh_token="refresh_abc")

        assert data["grant_type"] == "refresh_token"
        assert data["client_id"] == "my_client"
        assert data["client_secret"] == "my_secret"
        assert data["refresh_token"] == "refresh_abc"


class TestOAuth2Providers:
    """Tests for OAuth2 provider implementations."""

    def test_github_provider_name(self):
        """Test GitHub provider name property."""
        provider = GitHubOAuth2Provider()
        assert provider.name == "github"

    def test_github_provider_config(self):
        """Test GitHub provider configuration."""
        provider = GitHubOAuth2Provider()
        config = provider.get_config(
            client_id="gh_client_123",
            scopes=["read:user", "repo"],
        )

        assert config.provider_name == "github"
        assert config.authorization_url == "https://github.com/login/oauth/authorize"
        assert config.token_url == "https://github.com/login/oauth/access_token"
        assert config.userinfo_url == "https://api.github.com/user"
        assert config.client_id == "gh_client_123"
        assert config.scopes == ["read:user", "repo"]
        assert config.use_pkce is True  # No secret = PKCE

    def test_github_provider_with_secret(self):
        """Test GitHub provider with client secret disables PKCE."""
        provider = GitHubOAuth2Provider()
        config = provider.get_config(
            client_id="gh_client",
            client_secret="gh_secret",
        )
        assert config.use_pkce is False

    def test_google_provider_name(self):
        """Test Google provider name property."""
        provider = GoogleOAuth2Provider()
        assert provider.name == "google"

    def test_google_provider_config(self):
        """Test Google provider configuration."""
        provider = GoogleOAuth2Provider()
        config = provider.get_config(client_id="google_client_123")

        assert config.provider_name == "google"
        assert (
            config.authorization_url == "https://accounts.google.com/o/oauth2/v2/auth"
        )
        assert config.token_url == "https://oauth2.googleapis.com/token"
        assert config.revoke_url == "https://oauth2.googleapis.com/revoke"
        assert "openid" in config.scopes
        assert config.use_pkce is True
        assert config.extra_auth_params.get("access_type") == "offline"

    def test_azure_provider_name(self):
        """Test Azure AD provider name property."""
        provider = AzureADOAuth2Provider()
        assert provider.name == "azure"

    def test_azure_provider_config_common_tenant(self):
        """Test Azure AD provider with common tenant."""
        provider = AzureADOAuth2Provider()
        config = provider.get_config(client_id="azure_client_123")

        assert config.provider_name == "azure"
        assert "login.microsoftonline.com/common" in config.authorization_url
        assert config.userinfo_url == "https://graph.microsoft.com/v1.0/me"
        assert "offline_access" in config.scopes

    def test_azure_provider_config_specific_tenant(self):
        """Test Azure AD provider with specific tenant."""
        provider = AzureADOAuth2Provider(tenant_id="my-tenant-id")
        config = provider.get_config(client_id="azure_client")

        assert "my-tenant-id" in config.authorization_url
        assert "my-tenant-id" in config.token_url

    def test_azure_provider_tenant_override(self):
        """Test Azure AD provider tenant override in get_config."""
        provider = AzureADOAuth2Provider(tenant_id="default-tenant")
        config = provider.get_config(
            client_id="azure_client",
            tenant_id="override-tenant",
        )

        assert "override-tenant" in config.authorization_url

    def test_custom_provider_name(self):
        """Test custom provider name property."""
        provider = CustomOAuth2Provider(provider_name="my_idp")
        assert provider.name == "my_idp"

    def test_custom_provider_config(self):
        """Test custom provider configuration."""
        provider = CustomOAuth2Provider(
            provider_name="my_idp",
            authorization_url="https://idp.example.com/authorize",
            token_url="https://idp.example.com/token",
            revoke_url="https://idp.example.com/revoke",
            userinfo_url="https://idp.example.com/userinfo",
        )

        config = provider.get_config(
            client_id="custom_client",
            scopes=["api:read"],
            use_pkce=False,
        )

        assert config.provider_name == "my_idp"
        assert config.authorization_url == "https://idp.example.com/authorize"
        assert config.token_url == "https://idp.example.com/token"
        assert config.revoke_url == "https://idp.example.com/revoke"
        assert config.scopes == ["api:read"]
        assert config.use_pkce is False


class TestProviderRegistry:
    """Tests for provider registry functions."""

    def test_oauth2_providers_registry(self):
        """Test OAUTH2_PROVIDERS registry contains expected providers."""
        assert "github" in OAUTH2_PROVIDERS
        assert "google" in OAUTH2_PROVIDERS
        assert "azure" in OAUTH2_PROVIDERS
        assert "custom" in OAUTH2_PROVIDERS

    def test_get_provider_github(self):
        """Test get_provider for GitHub."""
        provider = get_provider("github")
        assert isinstance(provider, GitHubOAuth2Provider)
        assert provider.name == "github"

    def test_get_provider_google(self):
        """Test get_provider for Google."""
        provider = get_provider("google")
        assert isinstance(provider, GoogleOAuth2Provider)

    def test_get_provider_azure(self):
        """Test get_provider for Azure."""
        provider = get_provider("azure")
        assert isinstance(provider, AzureADOAuth2Provider)

    def test_get_provider_case_insensitive(self):
        """Test get_provider is case insensitive."""
        provider = get_provider("GitHub")
        assert provider.name == "github"

        provider = get_provider("GOOGLE")
        assert provider.name == "google"

    def test_get_provider_unknown(self):
        """Test get_provider with unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown OAuth2 provider"):
            get_provider("unknown_provider")


class TestOAuth2Flow:
    """Tests for OAuth2Flow enum."""

    def test_oauth2_flow_values(self):
        """Test OAuth2Flow enum values."""
        assert OAuth2Flow.AUTHORIZATION_CODE.value == "authorization_code"
        assert OAuth2Flow.CLIENT_CREDENTIALS.value == "client_credentials"
        assert OAuth2Flow.DEVICE_CODE.value == "device_code"
