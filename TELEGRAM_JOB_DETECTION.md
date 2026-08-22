# Telegram bot detection in RunSpace

RunSpace uses a bot-first **Add Bot 🤖** flow. For a new bot, the code editor stays locked until the owner pastes a BotFather token and presses **Verify bot**. The server asks Telegram `getMe`, then returns the verified `@username`, a clickable link, and a 15-minute single-use verification proof. The database stores only the token's SHA-256 digest in that proof—not the token.

After verification, the owner pastes or uploads the bot code and presses **Save & Run**. The browser submits the token as the bot's `BOT_TOKEN` environment variable together with the proof. The server checks that the authenticated user, proof, token digest and expiry all match before sending anything to the runner.

## One authoritative token

The verified token overrides token material already in the pasted code:

- old real Telegram token strings;
- example `BOT_TOKEN`, `TELEGRAM_BOT_TOKEN`, or `TOKEN` assignments;
- `TeleBot(...)`, `telegram.Bot(token=...)`, `Bot(...)`, and `ApplicationBuilder().token(...)` arguments;
- Telegram-token values in environment variables.

The canonical token is also forced into `BOT_TOKEN`. This happens server-side, so editing the browser request cannot bypass it. The proof is consumed only after successful bot creation. Each account can run at most three bots; the fourth is rejected server-side.

## What is stored and shown

Only safe identity metadata is retained: bot username, bot id, verification status and verification time. The token is never copied into metadata, API responses, deployment history or the admin console. Request exception text is not retained because it may contain the token-bearing URL.

The RunSpace workspace displays:

- the detected bot username;
- whether the RunSpace process is running;
- whether Telegram accepted the token;
- **Go to your bot**, linking to `https://t.me/<username>`.

These are deliberately separate signals. “RunSpace process running” and “Telegram identity verified” do not falsely claim that every command handler inside user code is working.

The admin console has a **Telegram bots on RunSpace** section with current detected bots, owner, bot job, process status, token-check status, uptime and a safe direct link. It also stores immutable run/update/restart history in `job_deploy_events`, recording who ran what without duplicating source or tokens.

Existing pre-migration jobs that have no verified bot metadata must use the verification section before their next update.
