"""
Shared HTTP Basic authentication for every browser-facing route.

One set of credentials for the whole demo, taken from the environment
(NORDFLOW_AUTH_USER / NORDFLOW_AUTH_PASSWORD). This keeps a private deployment
private; it is not a user system, and there are no accounts, sessions or roles.
"""
import base64
import binascii
from secrets import compare_digest

REALM = "NordFlow demo"
OPEN_PATHS = ("/healthz",)  # liveness probe for the proxy; returns no configuration or data


class BasicAuthMiddleware:
    """ASGI middleware: 401 unless the request carries the shared credentials."""

    def __init__(self, app, user, password, open_paths=OPEN_PATHS):
        if not user or not password:
            raise ValueError("BasicAuthMiddleware requires a user and a password")
        self.app = app
        self._user = user.encode()
        self._password = password.encode()
        self.open_paths = tuple(open_paths)

    def authorized(self, header):
        if not header:
            return False
        scheme, _, encoded = header.partition(" ")
        if scheme.lower() != "basic":
            return False
        try:
            user, _, password = base64.b64decode(encoded.strip(), validate=True).partition(b":")
        except (binascii.Error, ValueError):
            return False
        # both comparisons always run, so the response time does not reveal which half matched
        return compare_digest(user, self._user) & compare_digest(password, self._password)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") in self.open_paths:
            return await self.app(scope, receive, send)
        header = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"authorization"), None)
        if self.authorized(header):
            return await self.app(scope, receive, send)
        body = b'{"error":"authentication required"}'
        await send({"type": "http.response.start", "status": 401, "headers": [
            (b"www-authenticate", f'Basic realm="{REALM}", charset="UTF-8"'.encode()),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"cache-control", b"no-store"),
        ]})
        await send({"type": "http.response.body", "body": body})
