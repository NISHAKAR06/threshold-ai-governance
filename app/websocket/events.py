"""
events.py — WebSocket endpoint handlers for THRESHOLD AI.

Channels
--------
/ws              — Global (all events)
/ws/dashboard    — Dashboard stats updates
/ws/review       — Review queue events
/ws/audit        — Audit log events
/ws/notifications— Notification events (global alias)
"""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from app.core.websocket_manager import ws_manager
from app.core.security import decode_access_token, extract_token
from app.core.enums import WSEventType
from app.core.logger import ws_logger

router = APIRouter()


async def _authenticate_ws(websocket: WebSocket) -> Optional[dict[str, Any]]:
    """Return validated JWT claims from the WebSocket query token."""
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        return payload if payload.get("sub") and payload.get("role") else None
    except Exception:
        return None


async def _require_ws_user(websocket: WebSocket, required_roles: Optional[set[str]] = None) -> Optional[dict[str, Any]]:
    claims = await _authenticate_ws(websocket)
    if not claims or (required_roles and str(claims.get("role", "")).lower() not in required_roles):
        await websocket.close(code=1008, reason="Authentication or authorization required")
        return None
    return claims


@router.websocket("/ws")
async def ws_global(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    """Global WebSocket — receives all platform events."""
    claims = await _require_ws_user(websocket)
    if claims is None:
        return
    user_id = claims["sub"]
    await ws_manager.connect(websocket, channel="global", user_id=user_id)
    ws_logger.info("Global WS connected", extra={"user": user_id})
    try:
        while True:
            raw = await websocket.receive_text()
            await _handle_client_message(websocket, raw, "global")
    except WebSocketDisconnect:
        ws_logger.info("Global WS disconnected", extra={"user": user_id})
    except Exception as exc:
        ws_logger.warning("Global WS error", extra={"error": str(exc)})
    finally:
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    """Dashboard channel — receives dashboard stat update events."""
    claims = await _require_ws_user(websocket)
    if claims is None:
        return
    user_id = claims["sub"]
    await ws_manager.connect(websocket, channel="dashboard", user_id=user_id)
    try:
        while True:
            await websocket.receive_text()   # keep alive
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/review")
async def ws_review(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    """Review channel — receives new review and status update events."""
    claims = await _require_ws_user(websocket, {"admin", "superadmin", "reviewer"})
    if claims is None:
        return
    user_id = claims["sub"]
    await ws_manager.connect(websocket, channel="review", user_id=user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/audit")
async def ws_audit(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    """Audit channel — receives new audit log events."""
    claims = await _require_ws_user(websocket, {"admin", "superadmin"})
    if claims is None:
        return
    user_id = claims["sub"]
    await ws_manager.connect(websocket, channel="audit", user_id=user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    """Notifications channel (alias for global notification events)."""
    claims = await _require_ws_user(websocket)
    if claims is None:
        return
    user_id = claims["sub"]
    await ws_manager.connect(websocket, channel="global", user_id=user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


# ── Client message handler ────────────────────────────────────
async def _handle_client_message(websocket: WebSocket, raw: str, channel: str) -> None:
    """
    Handle messages FROM the client (e.g. ping, subscribe).
    Clients should send: {"type": "ping"} or {"type": "subscribe", "channel": "dashboard"}
    """
    try:
        msg = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return

    msg_type = msg.get("type", "")

    if msg_type == WSEventType.PING:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_text(
                json.dumps({"type": WSEventType.PONG, "ts": _now()})
            )

    elif msg_type == "subscribe":
        # Do not allow a client to subscribe to a channel with a different
        # authorization policy than the endpoint that authenticated it.
        new_channel = msg.get("channel", "global")
        if new_channel == channel:
            ws_manager._channels[new_channel].add(websocket)

    elif msg_type == "unsubscribe":
        rm_channel = msg.get("channel", "")
        ws_manager._channels.get(rm_channel, set()).discard(websocket)


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
