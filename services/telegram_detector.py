"""Detect Telegram bots in RunSpace source without exposing their tokens.

The raw token is used only for a short Telegram getMe check. It is never
returned, logged, or copied into analytics/admin metadata; the jobs table
already holds the user's source/env as required to restart their app.
"""
from datetime import datetime, timezone
import json
import re
import requests

TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_-])(\d{6,12}:[A-Za-z0-9_-]{30,})(?![A-Za-z0-9_-])")
LINK_RE = re.compile(r"(?:https?://)?(?:t|telegram)\.me/([A-Za-z][A-Za-z0-9_]{3,31})", re.I)
USER_RE = re.compile(r"(?:BOT_USERNAME|TELEGRAM_BOT_USERNAME)\s*[=:]\s*['\"]?@?([A-Za-z][A-Za-z0-9_]{3,31})", re.I)
VALID_USERNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _text(code, env):
    values = [str(code or "")[:1_000_000]]
    if isinstance(env, dict):
        values.extend(str(v)[:5000] for v in env.values())
    elif env:
        try:
            parsed = json.loads(env)
            if isinstance(parsed, dict):
                values.extend(str(v)[:5000] for v in parsed.values())
        except Exception:
            pass
    return "\n".join(values)


def inspect_bot(code, env=None, timeout=4):
    """Return safe bot metadata. Never includes the token."""
    text = _text(code, env)
    token_match = TOKEN_RE.search(text)
    usernames = LINK_RE.findall(text) + USER_RE.findall(text)
    username = next((u for u in usernames if VALID_USERNAME.match(u)), None)
    if not token_match and not username:
        return {"detected": False, "username": None, "bot_id": None,
                "check_status": "not_detected", "verified_at": None}
    result = {"detected": True, "username": username, "bot_id": None,
              "check_status": "username_only" if not token_match else "unverified",
              "verified_at": None}
    if not token_match:
        return result
    token = token_match.group(1)
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/getMe", json={}, timeout=timeout)
        payload = response.json() if response is not None else {}
        bot = payload.get("result") or {}
        if payload.get("ok") and bot.get("is_bot"):
            safe_username = str(bot.get("username") or "")
            result.update(username=safe_username if VALID_USERNAME.match(safe_username) else username,
                          bot_id=str(bot.get("id") or "") or None,
                          check_status="verified", verified_at=_now())
        elif response is not None and response.status_code in (401, 404):
            result["check_status"] = "invalid_token"
        else:
            result["check_status"] = "telegram_unreachable"
    except Exception:
        # Exception text from requests can contain the URL (and therefore the
        # token), so deliberately retain only this fixed status.
        result["check_status"] = "telegram_unreachable"
    return result


def public_fields(meta):
    username = meta.get("username") if meta else None
    return {
        "telegram_bot_detected": bool(meta and meta.get("detected")),
        "telegram_bot_username": username,
        "telegram_bot_id": meta.get("bot_id") if meta else None,
        "telegram_check_status": meta.get("check_status") if meta else "not_detected",
        "telegram_verified_at": meta.get("verified_at") if meta else None,
        "telegram_bot_url": f"https://t.me/{username}" if username else None,
    }
