# Practical bot template guide

CodeNest includes **101 ready-to-deploy templates, all written in Python**. The ranked catalog focuses on AI, Bangladesh commerce, live public APIs, channel growth, moderation, files/security, referrals, and support. Generic reminders, notes, habit/water trackers, URL checkers, and echo/command demos are not included. See `TEMPLATE_RESEARCH.md` for demand research, API sources, architecture decisions, and validation rules.

## Admin identity without numeric IDs

Templates that need a private owner use a generated, encrypted `ADMIN_CLAIM_CODE`. After token verification CodeNest deploys immediately and builds the **Go to bot** URL with `start=claim_CODE`. The owner taps it and presses Start; Telegram supplies `effective_user.id`, the bot stores that ID in SQLite, and later claim attempts are refused. The user never discovers or types a numeric Telegram ID or claim command.

The **Master referral rewards** template intentionally follows a different requested rule: the first Telegram user to send `/start` becomes master admin. Open it immediately after deployment.

## Master referral flow

1. First `/start` user becomes master admin.
2. Admin adds the bot as administrator in a public channel.
3. Admin sends `/setchannel @channel`.
4. Users start the bot and must join that channel.
5. A referred user is pending until `getChatMember` confirms membership.
6. Only then is the referral activated and the inviter rewarded.
7. Users can view balance, referral link, leaderboard, and request withdrawal.
8. Admin controls reward, minimum withdrawal, currency, broadcasts, bans, balances, and withdrawal approval from bot commands.

Telegram only guarantees membership lookup for other users when the bot is an administrator in the target channel. A Bot API bot cannot silently add arbitrary users; it can present join links, verify voluntary membership, create/approve invite flows when permitted, and reward verified users.

## Other configured templates

- **Live support inbox:** claim admin, receive copied user messages, reply to users, ban, and view stats.
- **Channel poster:** claim admin, add bot as channel admin, set channel, publish text or replied media.
- **Channel join gate:** claim admin, set channel, show Join/Check buttons, verify membership.
- **Group helper:** Telegram group administrators control rules, warnings, cleanup, and welcome messages.
- **Referral rewards:** claim admin, award points, show leaderboard, and adjust points.
- **Admin broadcast / Order bot:** claim admin before using protected controls.

All state is stored in per-bot SQLite files and included in CodeNest workspace snapshots.
