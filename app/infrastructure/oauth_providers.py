"""
OAuth 2.0 provider implementations.
"""

import os
from authlib.integrations.starlette_client import OAuth
from app.core.oauth_service import OAuthProvider

oauth = OAuth()


class AdobeOAuthProvider(OAuthProvider):
    """OAuth provider for Adobe."""

    def __init__(self):
        self.provider_name = "adobe"
        ADOBE_AUTHORIZE_URL = "https://ims-na1.adobelogin.com/ims/authorize"
        ADOBE_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token"

        oauth.register(
            name=self.provider_name,
            client_id=os.environ.get("ADOBE_CLIENT_ID"),
            client_secret=os.environ.get("ADOBE_CLIENT_SECRET"),
            authorize_url=ADOBE_AUTHORIZE_URL,
            access_token_url=ADOBE_TOKEN_URL,
            client_kwargs={"scope": "files offline_access"},
        )
        self.provider = oauth.create_client(self.provider_name)

    async def authorize_redirect(self, request, redirect_uri: str):
        return await self.provider.authorize_redirect(request, redirect_uri)

    async def authorize_access_token(self, request):
        return await self.provider.authorize_access_token(request)
