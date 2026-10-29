"""Muse Voice Transcribe realtime proxy: browser mic (PCM s16le 24 kHz) -> our server -> Meta, events back.

The key is added server-side in the handshake frame, so it never reaches the browser.
Protocol: Meta Model API reference, realtime voice (muse-voice-transcribe-1.0).
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from urllib.parse import urlparse

import websockets
from fastapi import WebSocket, WebSocketDisconnect

ASR_URL = "wss://api.meta.ai/v1/asr/realtime"
KEYWORDS = ["yatak odası", "çocuk odası", "salon", "kitaplık", "dolap", "gardırop", "ayna", "tablo", "televizyon",
            "kapı", "bookshelf", "wardrobe", "mirror", "bedroom", "kids sleep here", "exit"]


MAX_SESSION_SECONDS = 90          # same cap as a recording; transcription bills by audio time
MAX_SESSIONS = 3                  # concurrent narrations across all users
MAX_FRAME_BYTES = 64 * 1024       # the browser sends 80 ms frames (3,840 bytes)
CLOSE_MESSAGES = {1008: "Narration stopped: the audio stream was rejected.",
                  1011: "Narration stopped: the transcription service had a problem.",
                  1013: "Narration is busy right now. Please try again in a minute."}
ACTIVE = {"sessions": 0}


def same_origin(client: WebSocket) -> bool:
    """Browsers always send Origin on WebSockets: only our own page may open a narration (and spend our key)."""
    origin, host = client.headers.get("origin"), client.headers.get("host")
    return bool(origin and host) and urlparse(origin).netloc == host


async def proxy(client: WebSocket) -> None:
    if not same_origin(client):
        await client.close(code=1008)
        return
    await client.accept()
    if ACTIVE["sessions"] >= MAX_SESSIONS:
        await client.send_json({"type": "error", "message": CLOSE_MESSAGES[1013]})
        await client.close()
        return
    ACTIVE["sessions"] += 1
    session = f"risklens-{uuid.uuid4().hex[:8]}"
    try:
        async with websockets.connect(f"{ASR_URL}?sessionId={session}", open_timeout=30) as upstream:
            await upstream.send(json.dumps({
                "authorization": {"accessToken": f"Bearer {os.environ['MODEL_API_KEY']}"},
                "audioEncoding": "PCM_24KHZ",
                "model": "muse-voice-transcribe-1.0",
                "mode": "ENDPOINTING",
                "languageBias": ["Turkish", "English"],
                "keywords": KEYWORDS,
            }))
            ack = json.loads(await upstream.recv())
            if "sessionId" not in ack:
                await client.send_json({"type": "error", "message": "Narration could not start."})
                return
            await client.send_json({"type": "ready"})

            async def uplink() -> None:
                deadline = time.monotonic() + MAX_SESSION_SECONDS
                try:
                    while time.monotonic() < deadline:
                        message = await client.receive()
                        data = message.get("bytes")
                        if data:
                            if len(data) > MAX_FRAME_BYTES:
                                break
                            await upstream.send(data)
                        elif message.get("text") == "end" or message["type"] == "websocket.disconnect":
                            break
                finally:
                    await upstream.send(json.dumps({"type": "endStream"}))   # half-close: final results still flush

            async def downlink() -> None:
                async for message in upstream:
                    if isinstance(message, str):
                        await client.send_text(message)

            up = asyncio.create_task(uplink())
            try:
                await asyncio.wait_for(downlink(), MAX_SESSION_SECONDS + 15)   # ends when Meta closes after endStream
            except websockets.ConnectionClosedError as exc:
                code = exc.rcvd.code if exc.rcvd else None
                await client.send_json({"type": "error", "message": CLOSE_MESSAGES.get(code, "Narration stopped.")})
            finally:
                up.cancel()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print(f"voice proxy: {exc!r}")
        try:
            await client.send_json({"type": "error", "message": "Narration stopped."})
        except Exception:
            pass
    finally:
        ACTIVE["sessions"] -= 1
        try:
            await client.close()
        except Exception:
            pass
