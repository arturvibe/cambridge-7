"""
Core service for handling OAuth 2.0 authorization flows.
"""
from abc import ABC, abstractmethod

class OAuthProvider(ABC):
    """Abstract base class for an OAuth provider."""

    @abstractmethod
    async def authorize_redirect(self, request, redirect_uri: str):
        """Redirect the user to the provider's authorization page."""
        raise NotImplementedError

    @abstractmethod
    async def authorize_access_token(self, request):
        """Exchange the authorization code for an access token."""
        raise NotImplementedError

class OAuthService:
    """
    A service for handling OAuth 2.0 flows with different providers.
    """

    def __init__(self, provider: OAuthProvider):
        self.provider = provider

    async def login(self, request, redirect_uri: str):
        """Initiate the OAuth 2.0 login flow."""
        return await self.provider.authorize_redirect(request, redirect_uri)

    async def auth(self, request):
        """Handle the OAuth 2.0 callback and get the access token."""
        return await self.provider.authorize_access_token(request)
