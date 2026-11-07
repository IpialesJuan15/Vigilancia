"""Bound incoming bodies before multipart uploads can exhaust temporary storage."""

from fastapi import HTTPException
from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            size = int(headers.get(b"content-length", b"0"))
        except ValueError:
            size = self.max_bytes + 1
        if size > self.max_bytes:
            response = JSONResponse(
                {
                    "code": "upload_too_large",
                    "message": "El archivo supera el tamaño permitido",
                    "details": None,
                },
                status_code=413,
            )
            return await response(scope, receive, send)
        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise HTTPException(413, "El archivo supera el tamaño permitido")
            return message

        await self.app(scope, bounded_receive, send)
