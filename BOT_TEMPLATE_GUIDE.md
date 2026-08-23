# Practical bot template guide

## Admin identity without numeric IDs

Templates that need a private owner use a generated `ADMIN_CLAIM_CODE`. After deployment, the owner sends `/claim CODE` from their own Telegram account. Telegram supplies `effective_user.id`; the bot stores it in its SQLite settings table and refuses later claims. The claim code is an encrypted job secret and is shown in Review before deployment.

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
