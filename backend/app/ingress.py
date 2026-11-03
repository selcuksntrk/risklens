"""Bound multipart bodies before Starlette writes them to temporary disk."""
from fastapi import HTTPException
from starlette.responses import JSONResponse


class UploadLimits:
    def __init__(self, app, max_bytes: int, max_active: int = 3):
        self.app, self.max_bytes, self.max_active = app, max_bytes, max_active
        self.active = 0

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('method') != 'POST':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        if not headers.get(b'content-type', b'').startswith(b'multipart/form-data'):
            return await self.app(scope, receive, send)
        if self.active >= self.max_active:
            return await JSONResponse({'detail': 'Uploads are busy. Keep your video and retry shortly.'}, 429)(scope, receive, send)
        self.active += 1
        size = 0
        async def bounded():
            nonlocal size
            message = await receive()
            size += len(message.get('body', b''))
            if size > self.max_bytes:
                raise HTTPException(413, 'Video is too large.')
            return message
        try:
            await self.app(scope, bounded, send)
        finally:
            self.active -= 1
