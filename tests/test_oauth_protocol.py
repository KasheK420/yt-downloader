import base64
import hashlib
import time
from urllib.parse import parse_qs, urlsplit

import httpx2 as httpx
import pytest
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import RSAKey
from pydantic import SecretStr, ValidationError

from app.accounts import LoginError
from app.config import Settings
from app.oauth import SocialLogin


@pytest.fixture
def oauth(settings):
    settings.public_origin = "http://localhost:8080"
    settings.google_client_id = "google-test"
    settings.google_client_secret = SecretStr("google-secret")
    settings.facebook_client_id = "facebook-test"
    settings.facebook_client_secret = SecretStr("facebook-secret")
    return SocialLogin(settings)


@pytest.mark.parametrize("bad", [None, "nonce", "aud", "iss", "exp", "signature", "azp", "none"])
async def test_google_uses_pkce_and_validates_signed_identity(oauth, bad):
    key = RSAKey.generate_key(2048, parameters={"kid": "test-key"})
    client = oauth.client("google")
    claims = {
        "iss": "https://accounts.google.com",
        "sub": "person-1",
        "aud": "google-test",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
        "nonce": "expected",
        "name": "Test user",
    }
    if bad in {"nonce", "aud", "iss", "azp"}:
        claims[bad] = "wrong"
    if bad == "exp":
        claims["exp"] = int(time.time()) - 300
    signing_key = (
        RSAKey.generate_key(2048, parameters={"kid": "test-key"}) if bad == "signature" else key
    )
    encoded = jwt.encode({"alg": "RS256", "kid": "test-key"}, claims, signing_key)
    if bad == "none":
        encoded = "eyJhbGciOiJub25lIn0.e30."
    client.server_metadata.update(
        {
            "_loaded_at": time.time(),
            "issuer": "https://accounts.google.com",
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "jwks": {"keys": [key.as_dict(private=False)]},
            "id_token_signing_alg_values_supported": ["RS256"],
        }
    )

    def handler(request):
        assert str(request.url) == "https://oauth2.googleapis.com/token"
        params = parse_qs(request.content.decode())
        assert params["code_verifier"] == ["v" * 64]
        assert params["redirect_uri"] == ["http://localhost:8080/auth/google/callback"]
        assert params["client_secret"] == ["google-secret"]
        return httpx.Response(
            200,
            json={"access_token": "transient-token", "token_type": "Bearer", "id_token": encoded},
        )

    client.client_kwargs["transport"] = httpx.MockTransport(handler)
    url = await oauth.authorize("google", "state", "v" * 64, "expected")
    params = parse_qs(urlsplit(url).query)
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(("v" * 64).encode()).digest()).rstrip(b"=").decode()
    )
    assert params["code_challenge"] == [expected]
    assert params["code_challenge_method"] == ["S256"]
    assert params["scope"] == ["openid profile"]
    flow = {"verifier": "v" * 64, "nonce": "expected"}
    if bad:
        with pytest.raises((JoseError, LoginError)):
            await oauth.identity("google", "code", flow)
    else:
        assert await oauth.identity("google", "code", flow) == ("person-1", "Test user")


@pytest.mark.parametrize(
    "bad", [None, "app_id", "is_valid", "expires_at", "user_id", "type", "data_access_expires_at"]
)
async def test_facebook_checks_app_token_expiry_and_subject(oauth, monkeypatch, bad):
    debug = {
        "app_id": "facebook-test",
        "is_valid": True,
        "type": "USER",
        "expires_at": time.time() + 300,
        "user_id": "person-1",
        "data_access_expires_at": time.time() + 500,
    }
    if bad:
        debug[bad] = 1 if bad.endswith("expires_at") else False if bad == "is_valid" else "wrong"

    def handler(request):
        if request.url.path.endswith("/debug_token"):
            assert request.headers["authorization"] == "Bearer facebook-test|facebook-secret"
            return httpx.Response(200, json={"data": debug})
        assert request.url.path.endswith("/me")
        assert request.headers["authorization"] == "Bearer transient-token"
        assert "appsecret_proof" in request.url.params
        return httpx.Response(200, json={"id": "person-1", "name": "Test user"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.oauth.httpx.AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    if bad:
        with pytest.raises(LoginError):
            await oauth.facebook_identity("transient-token")
    else:
        assert (await oauth.facebook_identity("transient-token"))["id"] == "person-1"


@pytest.mark.parametrize(
    "options",
    [
        {"public_origin": "http://public.example"},
        {"public_origin": "https://public.example", "allowed_hosts": ["public.example"]},
        {"google_client_id": "partial"},
        {"require_login": True},
        {"public_origin": "http://localhost/path"},
    ],
)
def test_invalid_auth_configuration_fails_closed(tmp_path, options):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, data_dir=tmp_path, **options)
