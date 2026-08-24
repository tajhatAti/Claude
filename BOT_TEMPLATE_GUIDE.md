# Complete bot product guide

CodeNest intentionally exposes **five complete Python bot products**, not a padded gallery of tiny feature variations:

1. **Complete group manager** — captcha, anti-flood, links, blocked words, rules, warnings, mute, ban/unban, lock/unlock, reports, stats, and audit history.
2. **Complete file & AI toolbox** — Telegram file sharing/deep links, expiry/download limits, image/PDF conversion, compression, PDF text, OCR, VirusTotal, hashes, QR, voice transcription, and text-to-speech.
3. **Complete AI business assistant** — OpenAI-compatible provider, Bangla/Banglish policy prompt, memory, quota, analytics, ban controls, and broadcast.
4. **Complete Telegram store** — catalog, stock, cart, checkout, payment review, order history, buyer notifications, support, and sales analytics.
5. **Complete channel growth & membership** — force-join, verified referrals, paid plans, payment approval, private invites, expiry removal, scheduled/auto-delete posts, broadcast, and analytics.

Templates are optional. **Own code** accepts pasted Python directly and **Upload file** accepts a `.py` file.

## Admin identity

Products that need a private owner receive an encrypted generated `ADMIN_CLAIM_CODE`. The post-deploy **Go to bot** link claims the first owner without asking for a numeric Telegram ID.

## Telegram limitations

Membership checks require the bot to be an administrator. Bots cannot silently add arbitrary users. Payment-reference flows require owner/provider verification unless an actual merchant checkout URL is configured.
