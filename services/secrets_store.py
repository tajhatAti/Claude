"""Encryption-at-rest for per-bot environment secrets.

Values are encrypted as one authenticated JSON envelope. Legacy plaintext JSON
is readable and migrated on startup when a key is configured.
"""
import base64
import hashlib
import json
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("codenest.secrets")
PREFIX = "enc:v1:"


def _material():
    return (os.getenv("JOB_SECRETS_KEY", "").strip()
            or os.getenv("RUNNER_SERVICE_SECRET", "").strip())


def configured():
    return bool(_material())


def _fernet():
    material = _material()
    if not material:
        return None
    key = base64.urlsafe_b64encode(hashlib.sha256(material.encode()).digest())
    return Fernet(key)


def pack_env(values):
    values = dict(values or {})
    if not values:
        return None
    raw = json.dumps(values, separators=(",", ":"), ensure_ascii=False)
    cipher = _fernet()
    if not cipher:
        # Local SQLite remains zero-config. /health reports this explicitly;
        # production blueprints generate JOB_SECRETS_KEY automatically.
        return raw
    return PREFIX + cipher.encrypt(raw.encode()).decode()


def unpack_env(value):
    if not value:
        return {}
    text = str(value)
    if text.startswith(PREFIX):
        cipher = _fernet()
        if not cipher:
            logger.error("Encrypted bot secrets exist but JOB_SECRETS_KEY is missing")
            return {}
        try:
            text = cipher.decrypt(text[len(PREFIX):].encode()).decode()
        except (InvalidToken, ValueError):
            logger.error("Could not decrypt bot environment (wrong key or corrupt value)")
            return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def migrate_job_envs():
    """Encrypt legacy plaintext env rows in place. Idempotent."""
    if not configured():
        logger.warning("JOB_SECRETS_KEY is not configured; bot env secrets are not encrypted at rest")
        return {"migrated": 0, "configured": False}
    from database import get_db_connection
    conn = get_db_connection()
    migrated = 0
    changed = 0
    try:
        rows = conn.execute("SELECT id,env,telegram_token_fingerprint FROM jobs WHERE env IS NOT NULL AND env != ''").fetchall()
        for row in rows:
            item = dict(row)
            values = unpack_env(item.get("env"))
            updates = []
            params = []
            if values and not str(item.get("env") or "").startswith(PREFIX):
                updates.append("env=?")
                params.append(pack_env(values))
                migrated += 1
            token = str(values.get("BOT_TOKEN") or "") if values else ""
            if token and not item.get("telegram_token_fingerprint"):
                from services import telegram_detector
                updates.append("telegram_token_fingerprint=?")
                params.append(telegram_detector.token_fingerprint(token))
            if updates:
                params.append(item["id"])
                conn.execute(f"UPDATE jobs SET {','.join(updates)} WHERE id=?", tuple(params))
                changed += 1
        if changed:
            conn.commit()
            if migrated:
                logger.info("Encrypted %d legacy bot environment(s)", migrated)
    finally:
        conn.close()
    return {"migrated": migrated, "configured": True}
