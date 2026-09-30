import secrets
from pathlib import Path

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def signing_secret(data_dir: Path) -> str:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "session.key"
    try:
        with path.open("x", encoding="ascii") as handle:
            handle.write(secrets.token_hex(32))
        path.chmod(0o600)
    except FileExistsError:
        pass
    return path.read_text(encoding="ascii").strip()


class BodyLimitMiddleware:
    """Bound requests before JSON parsing, including chunked bodies."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH", "DELETE"}:
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 4096:
                await JSONResponse({"detail": "request_too_large"}, status_code=413)(
                    scope, receive, send
                )
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
