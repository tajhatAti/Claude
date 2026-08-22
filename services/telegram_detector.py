"""Detect Telegram bots in RunSpace source without exposing their tokens.

The raw token is used only for a short Telegram getMe check. It is never
returned, logged, or copied into analytics/admin metadata; the jobs table
already holds the user's source/env as required to restart their app.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import secrets
import requests

from database import get_db_connection

# Telegram has changed token lengths over time. Keep the structural boundary
# broad and let getMe be the authority instead of rejecting a valid old/new
# token before Telegram sees it.
TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_-])(\d{5,15}:[A-Za-z0-9_-]{20,80})(?![A-Za-z0-9_-])")
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


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_verification(user_id, token, meta, ttl_minutes=15):
    """Create a short-lived, single-use proof without storing the token."""
    verification_id = secrets.token_urlsafe(24)
    created = datetime.now(timezone.utc)
    expires = created + timedelta(minutes=ttl_minutes)
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM telegram_token_verifications WHERE expires_at < ? OR consumed_at IS NOT NULL",
                     (created.strftime("%Y-%m-%d %H:%M:%S"),))
        conn.execute(
            "INSERT INTO telegram_token_verifications "
            "(id,user_id,token_hash,bot_username,bot_id,created_at,expires_at) VALUES (?,?,?,?,?,?,?)",
            (verification_id, user_id, _token_hash(token), meta["username"], meta.get("bot_id"),
             created.strftime("%Y-%m-%d %H:%M:%S"), expires.strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    finally:
        conn.close()
    return verification_id


def validate_verification(user_id, verification_id, token):
    if not verification_id or not token:
        return None
    now = _now()
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id,bot_username,bot_id,expires_at,consumed_at,token_hash "
            "FROM telegram_token_verifications WHERE id=? AND user_id=?",
            (verification_id, user_id),
        ).fetchone()
        if not row:
            return None
        row = dict(row)
        if row.get("consumed_at") or row.get("expires_at", "") <= now:
            return None
        if not secrets.compare_digest(row.get("token_hash") or "", _token_hash(token)):
            return None
        return {"detected": True, "username": row["bot_username"],
                "bot_id": row.get("bot_id"), "check_status": "verified",
                "verified_at": now}
    finally:
        conn.close()


def consume_verification(verification_id):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE telegram_token_verifications SET consumed_at=? WHERE id=?",
                     (_now(), verification_id))
        conn.commit()
    finally:
        conn.close()


_ASSIGN_RE = re.compile(
    r"((?:(?:TELEGRAM_)?BOT_TOKEN|TOKEN)\s*=\s*(?:[rubfRUBF]*)[\"'])(.*?)([\"'])",
    re.S,
)
_DICT_RE = re.compile(
    r"([\"'](?:TELEGRAM_)?BOT_TOKEN[\"']\s*:\s*[\"'])(.*?)([\"'])",
    re.S,
)
_BOT_CTOR_RE = re.compile(
    r"((?:(?:TeleBot|telegram\.Bot|Bot)\s*\(\s*(?:token\s*=\s*)?|"
    r"ApplicationBuilder\(\)\.token\s*\()[\"'])(.*?)([\"'])",
    re.S,
)


def apply_verified_token(code, env, token):
    """Make the verified token authoritative over examples/old bot tokens."""
    source = str(code or "")
    source = TOKEN_RE.sub(token, source)
    source = _ASSIGN_RE.sub(lambda m: m.group(1) + token + m.group(3), source)
    source = _DICT_RE.sub(lambda m: m.group(1) + token + m.group(3), source)
    source = _BOT_CTOR_RE.sub(lambda m: m.group(1) + token + m.group(3), source)
    clean_env = dict(env or {})
    for key, value in list(clean_env.items()):
        text = str(value)
        clean_env[key] = TOKEN_RE.sub(token, text)
    clean_env["BOT_TOKEN"] = token
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN"):
        if key in clean_env:
            clean_env[key] = token
    return source, clean_env


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
