"""Browser ownership, with explicit public examples. IDs are locators, never credentials."""
import hashlib
import hmac
import json
import re
import secrets
import time
from pathlib import Path
from urllib.parse import urlparse
from fastapi import HTTPException, Request, Response
from app import config
from app.storage import write_json

COOKIE = 'risklens_session'
TOKEN = re.compile(r'^[a-f0-9]{64}$')


def owner(request) -> str | None:
    token = request.cookies.get(COOKIE, '')
    return hashlib.sha256(token.encode()).hexdigest() if TOKEN.fullmatch(token) else None


def require_owner(request) -> str:
    value = owner(request)
    if value is None:
        raise HTTPException(401, 'Open a private browser session before uploading.')
    return value


def same_origin(request):
    origin = request.headers.get('origin')
    if origin and urlparse(origin).netloc != request.headers.get('host'):
        raise HTTPException(403, 'Cross-origin requests are not accepted.')


def session(request: Request, response: Response):
    same_origin(request)
    token = request.cookies.get(COOKIE, '')
    if not TOKEN.fullmatch(token):
        token = secrets.token_hex(32)
    response.set_cookie(COOKIE, token, max_age=30*86400, httponly=True,
                        secure=config.COOKIE_SECURE or request.url.scheme == 'https', samesite='lax', path='/')
    return {'status': 'ready', 'access': 'this_browser', 'report_retention_days': 30}


def metadata(root: Path) -> dict:
    try:
        return json.loads((root / 'meta.json').read_text())
    except (OSError, ValueError):
        return {}


def new_metadata(root: Path, owner_id: str, **extra):
    write_json(root / 'meta.json', {'owner_sha256': owner_id, 'created_at_unix': time.time(), **extra})


def authorized(root: Path, request) -> bool:
    own = owner(request)
    expected = metadata(root).get('owner_sha256')
    return bool(own and expected and hmac.compare_digest(own, expected))


def check_private(root: Path, request):
    from app.retention import report_expired
    if not authorized(root, request) or not root.is_dir() or (root / '.deleted').exists():
        raise HTTPException(404, 'Scan not found in this browser.')
    if report_expired(root):
        raise HTTPException(410, 'This report has expired.')
