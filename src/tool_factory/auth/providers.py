"""OAuth2 provider implementations.

Pre-configured OAuth2 providers for common services.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from tool_factory.auth.oauth2 import OAuth2Config


class OAuth2Provider(ABC):
    """Base class for OAuth2 providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    def get_config(self, client_id: str, **kwargs: Any) -> OAuth2Config:
        """Get OAuth2 configuration for this provider.

        Args:
            client_id: OAuth2 client ID
            **kwargs: Additional provider-specific options

        Returns:
            OAuth2Config instance
        """
        pass


@dataclass
class GitHubOAuth2Provider(OAuth2Provider):
    """GitHub OAuth2 provider.

    GitHub OAuth supports PKCE for public clients.
    See: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
    """

    @property
    def name(self) -> str:
        return "github"

    def get_config(
        self,
        client_id: str,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
        redirect_uri: str = "http://localhost:8080/callback",
        **kwargs: Any,
    ) -> OAuth2Config:
        """Get GitHub OAuth2 configuration.

        Args:
            client_id: GitHub OAuth App client ID
            client_secret: Client secret (optional for PKCE)
            scopes: Requested scopes (e.g., ["read:user", "repo"])
            redirect_uri: Callback URL

        Returns:
            OAuth2Config for GitHub
        """
        return OAuth2Config(
            provider_name="github",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            revoke_url=None,  # GitHub doesn't have a standard revoke endpoint
            userinfo_url="https://api.github.com/user",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes or ["read:user"],
            redirect_uri=redirect_uri,
            use_pkce=client_secret is None,  # Use PKCE if no secret
            extra_token_params={"Accept": "application/json"},
        )


@dataclass
class GoogleOAuth2Provider(OAuth2Provider):
    """Google OAuth2 provider.

    Google OAuth with PKCE support.
    See: https://developers.google.com/identity/protocols/oauth2
    """

    @property
    def name(self) -> str:
        return "google"

    def get_config(
        self,
        client_id: str,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
        redirect_uri: str = "http://localhost:8080/callback",
        **kwargs: Any,
    ) -> OAuth2Config:
        """Get Google OAuth2 configuration.

        Args:
            client_id: Google OAuth client ID
            client_secret: Client secret (optional for PKCE)
            scopes: Requested scopes
            redirect_uri: Callback URL

        Returns:
            OAuth2Config for Google
        """
        return OAuth2Config(
            provider_name="google",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            revoke_url="https://oauth2.googleapis.com/revoke",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes or ["openid", "profile", "email"],
            redirect_uri=redirect_uri,
            use_pkce=True,  # Google always supports PKCE
            extra_auth_params={"access_type": "offline", "prompt": "consent"},
        )


@dataclass
class AzureADOAuth2Provider(OAuth2Provider):
    """Azure AD / Microsoft Entra ID OAuth2 provider.

    Azure AD OAuth with PKCE support.
    See: https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow
    """

    tenant_id: str = "common"  # "common", "organizations", "consumers", or tenant ID

    @property
    def name(self) -> str:
        return "azure"

    def get_config(
        self,
        client_id: str,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
        redirect_uri: str = "http://localhost:8080/callback",
        tenant_id: str | None = None,
        **kwargs: Any,
    ) -> OAuth2Config:
        """Get Azure AD OAuth2 configuration.

        Args:
            client_id: Azure AD application client ID
            client_secret: Client secret (optional for PKCE)
            scopes: Requested scopes
            redirect_uri: Callback URL
            tenant_id: Azure tenant ID or "common"/"organizations"/"consumers"

        Returns:
            OAuth2Config for Azure AD
        """
        tenant = tenant_id or self.tenant_id
        base_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"

        return OAuth2Config(
            provider_name="azure",
            authorization_url=f"{base_url}/authorize",
            token_url=f"{base_url}/token",
            revoke_url=None,  # Azure uses logout endpoint instead
            userinfo_url="https://graph.microsoft.com/v1.0/me",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes or ["openid", "profile", "email", "offline_access"],
            redirect_uri=redirect_uri,
            use_pkce=True,  # Azure always supports PKCE
        )


@dataclass
class CustomOAuth2Provider(OAuth2Provider):
    """Custom OAuth2 provider for any OAuth2-compliant server.

    Use this for self-hosted or custom OAuth2 servers.
    """

    provider_name: str = "custom"
    authorization_url: str = ""
    token_url: str = ""
    revoke_url: str | None = None
    userinfo_url: str | None = None

    @property
    def name(self) -> str:
        return self.provider_name

    def get_config(
        self,
        client_id: str,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
        redirect_uri: str = "http://localhost:8080/callback",
        use_pkce: bool = True,
        **kwargs: Any,
    ) -> OAuth2Config:
        """Get custom OAuth2 configuration.

        Args:
            client_id: OAuth2 client ID
            client_secret: Client secret (optional)
            scopes: Requested scopes
            redirect_uri: Callback URL
            use_pkce: Whether to use PKCE

        Returns:
            OAuth2Config for custom provider
        """
        return OAuth2Config(
            provider_name=self.provider_name,
            authorization_url=self.authorization_url,
            token_url=self.token_url,
            revoke_url=self.revoke_url,
            userinfo_url=self.userinfo_url,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes or [],
            redirect_uri=redirect_uri,
            use_pkce=use_pkce,
        )


# Provider registry for easy lookup
OAUTH2_PROVIDERS: dict[str, type[OAuth2Provider]] = {
    "github": GitHubOAuth2Provider,
    "google": GoogleOAuth2Provider,
    "azure": AzureADOAuth2Provider,
    "custom": CustomOAuth2Provider,
}


def get_provider(name: str) -> OAuth2Provider:
    """Get an OAuth2 provider by name.

    Args:
        name: Provider name (github, google, azure, custom)

    Returns:
        OAuth2Provider instance

    Raises:
        ValueError: If provider is not found
    """
    provider_class = OAUTH2_PROVIDERS.get(name.lower())
    if provider_class is None:
        available = ", ".join(OAUTH2_PROVIDERS.keys())
        raise ValueError(f"Unknown OAuth2 provider: {name}. Available: {available}")
    return provider_class()
