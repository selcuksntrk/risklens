"""Muse Voice Transcribe realtime proxy: browser mic (PCM s16le 24 kHz) -> our server -> Meta, events back.

The key is added server-side in the handshake frame, so it never reaches the browser.
Protocol: Meta Model API reference, realtime voice (muse-voice-transcribe-1.0).
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid

import websockets
from fastapi import WebSocket, WebSocketDisconnect

ASR_URL = "wss://api.meta.ai/v1/asr/realtime"
KEYWORDS = ["yatak odası", "çocuk odası", "salon", "kitaplık", "dolap", "gardırop", "ayna", "tablo", "televizyon",
            "kapı", "bookshelf", "wardrobe", "mirror", "bedroom", "kids sleep here", "exit"]


async def proxy(client: WebSocket) -> None:
    await client.accept()
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
                await client.send_json({"type": "error", "message": f"handshake failed: {ack}"})
                return
            await client.send_json({"type": "ready"})

            async def uplink() -> None:
                try:
                    while True:
                        message = await client.receive()
                        if message.get("bytes"):
                            await upstream.send(message["bytes"])
                        elif message.get("text") == "end" or message["type"] == "websocket.disconnect":
                            break
                finally:
                    await upstream.send(json.dumps({"type": "endStream"}))

            async def downlink() -> None:
                async for message in upstream:
                    if isinstance(message, str):
                        await client.send_text(message)

            up = asyncio.create_task(uplink())
            await downlink()                    # ends when Meta closes (1000 after endStream)
            up.cancel()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await client.send_json({"type": "error", "message": str(exc)[:300]})
        except Exception:
            pass
    finally:
        try:
            await client.close()
        except Exception:
            pass
