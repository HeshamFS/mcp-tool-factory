"""OAuth2/PKCE Authentication module for MCP Tool Factory.

This module provides OAuth2 authentication support per the MCP June 2025 spec,
including PKCE (Proof Key for Code Exchange) for public clients and
Resource Indicators per RFC 8707.
"""

from tool_factory.auth.oauth2 import (
    OAuth2Config,
    OAuth2Flow,
    OAuth2Token,
)
from tool_factory.auth.pkce import (
    PKCECodeVerifier,
    generate_code_verifier,
    generate_code_challenge,
)
from tool_factory.auth.providers import (
    OAuth2Provider,
    GitHubOAuth2Provider,
    GoogleOAuth2Provider,
    AzureADOAuth2Provider,
    CustomOAuth2Provider,
)

__all__ = [
    "OAuth2Config",
    "OAuth2Flow",
    "OAuth2Token",
    "PKCECodeVerifier",
    "generate_code_verifier",
    "generate_code_challenge",
    "OAuth2Provider",
    "GitHubOAuth2Provider",
    "GoogleOAuth2Provider",
    "AzureADOAuth2Provider",
    "CustomOAuth2Provider",
]
