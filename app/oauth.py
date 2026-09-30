"""Provider protocol boundary; access and ID tokens exist only during the callback."""

import hashlib
import hmac
import time
from typing import Any

import httpx2 as httpx
from authlib.integrations.starlette_client import OAuth

from app.accounts import LoginError
from app.config import Settings


class SocialLogin:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry = OAuth()
        if settings.google_client_id and settings.google_client_secret:
            self.registry.register(
                "google",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret.get_secret_value(),
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={
                    "scope": "openid profile",
                    "code_challenge_method": "S256",
                    "token_endpoint_auth_method": "client_secret_post",
                    "timeout": 10,
                },
            )
        if settings.facebook_client_id and settings.facebook_client_secret:
            base = f"https://graph.facebook.com/{settings.facebook_api_version}"
            self.registry.register(
                "facebook",
                client_id=settings.facebook_client_id,
                client_secret=settings.facebook_client_secret.get_secret_value(),
                authorize_url=f"https://www.facebook.com/{settings.facebook_api_version}/dialog/oauth",
                access_token_url=f"{base}/oauth/access_token",
                client_kwargs={
                    "scope": "public_profile",
                    "token_endpoint_auth_method": "client_secret_post",
                    "timeout": 10,
                },
            )

    def providers(self) -> list[str]:
        return [
            name for name in ("google", "facebook") if getattr(self.settings, f"{name}_client_id")
        ]

    def client(self, provider: str) -> Any:
        if provider not in self.providers():
            raise LoginError("login_unavailable")
        return self.registry.create_client(provider)

    def callback(self, provider: str) -> str:
        return f"{self.settings.public_origin}/auth/{provider}/callback"

    async def authorize(self, provider: str, state: str, verifier: str, nonce: str) -> str:
        params = {"state": state}
        if provider == "google":
            params.update(code_verifier=verifier, nonce=nonce, prompt="select_account")
        result = await self.client(provider).create_authorization_url(
            self.callback(provider), **params
        )
        return str(result["url"])

    async def identity(self, provider: str, code: str, flow: dict[str, Any]) -> tuple[str, str]:
        client = self.client(provider)
        params = {"code": code}
        if provider == "google":
            params["code_verifier"] = flow["verifier"]
        token = await client.fetch_access_token(redirect_uri=self.callback(provider), **params)
        if provider == "google":
            info = await client.parse_id_token(token, nonce=flow["nonce"], leeway=30)
            # Require nonce explicitly even if a provider claims nonce_supported=false.
            if (
                not info
                or info.get("nonce") != flow["nonce"]
                or info.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}
            ):
                raise LoginError("login_failed")
            subject = info.get("sub")
        else:
            info = await self.facebook_identity(str(token["access_token"]))
            subject = info.get("id")
        if not isinstance(subject, str) or not subject or len(subject) > 255:
            raise LoginError("login_failed")
        name = info.get("name")
        return subject, name[:100] if isinstance(name, str) and name.strip() else provider.title()

    async def facebook_identity(self, access_token: str) -> dict[str, Any]:
        assert self.settings.facebook_client_secret
        secret = self.settings.facebook_client_secret.get_secret_value()
        app_id = self.settings.facebook_client_id
        base = f"https://graph.facebook.com/{self.settings.facebook_api_version}"
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            debug = await client.get(
                f"{base}/debug_token",
                params={"input_token": access_token},
                headers={"Authorization": f"Bearer {app_id}|{secret}"},
            )
            debug.raise_for_status()
            data = debug.json().get("data", {})
            if (
                data.get("is_valid") is not True
                or str(data.get("app_id")) != app_id
                or data.get("type") != "USER"
                or not data.get("user_id")
                or not isinstance(data.get("expires_at"), (int, float))
                or data["expires_at"] <= time.time()
                or (
                    data.get("data_access_expires_at")
                    and data["data_access_expires_at"] <= time.time()
                )
            ):
                raise LoginError("login_failed")
            proof = hmac.new(secret.encode(), access_token.encode(), hashlib.sha256).hexdigest()
            response = await client.get(
                f"{base}/me",
                params={"fields": "id,name", "appsecret_proof": proof},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            info: dict[str, Any] = response.json()
            if info.get("id") != data["user_id"]:
                raise LoginError("login_failed")
            return info
