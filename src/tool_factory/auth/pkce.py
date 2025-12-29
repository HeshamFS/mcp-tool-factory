"""PKCE (Proof Key for Code Exchange) implementation.

PKCE is an extension to the OAuth 2.0 Authorization Code flow that
prevents authorization code interception attacks. It's required for
public clients (like CLI tools) per the MCP June 2025 spec.

See: RFC 7636 - Proof Key for Code Exchange
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass


def generate_code_verifier(length: int = 64) -> str:
    """Generate a cryptographically random code verifier.

    The code verifier is a high-entropy cryptographic random string
    using unreserved characters [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"

    Args:
        length: Length of the verifier (43-128 characters per RFC 7636)

    Returns:
        Base64url-encoded random string

    Raises:
        ValueError: If length is not between 43 and 128
    """
    if not 43 <= length <= 128:
        raise ValueError("Code verifier length must be between 43 and 128 characters")

    # Generate random bytes and encode as base64url
    random_bytes = secrets.token_bytes(length)
    verifier = base64.urlsafe_b64encode(random_bytes).decode("ascii")

    # Remove padding and trim to exact length
    verifier = verifier.rstrip("=")[:length]

    return verifier


def generate_code_challenge(verifier: str, method: str = "S256") -> str:
    """Generate a code challenge from the code verifier.

    Args:
        verifier: The code verifier string
        method: Challenge method - "S256" (recommended) or "plain"

    Returns:
        The code challenge string

    Raises:
        ValueError: If method is not supported
    """
    if method == "plain":
        return verifier
    elif method == "S256":
        # SHA-256 hash of the verifier
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        # Base64url encode without padding
        challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return challenge
    else:
        raise ValueError(f"Unsupported code challenge method: {method}")


@dataclass
class PKCECodeVerifier:
    """PKCE code verifier and challenge pair.

    This class holds both the verifier (kept secret) and the challenge
    (sent to the authorization server).
    """

    verifier: str
    challenge: str
    method: str = "S256"

    @classmethod
    def generate(cls, length: int = 64, method: str = "S256") -> "PKCECodeVerifier":
        """Generate a new PKCE code verifier and challenge pair.

        Args:
            length: Length of the code verifier
            method: Challenge method ("S256" or "plain")

        Returns:
            New PKCECodeVerifier instance
        """
        verifier = generate_code_verifier(length)
        challenge = generate_code_challenge(verifier, method)
        return cls(verifier=verifier, challenge=challenge, method=method)

    def to_auth_params(self) -> dict[str, str]:
        """Get authorization request parameters.

        Returns:
            Dict with code_challenge and code_challenge_method
        """
        return {
            "code_challenge": self.challenge,
            "code_challenge_method": self.method,
        }

    def to_token_params(self) -> dict[str, str]:
        """Get token request parameters.

        Returns:
            Dict with code_verifier
        """
        return {
            "code_verifier": self.verifier,
        }
