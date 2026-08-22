# Telegram bot detection in RunSpace

When a job is run or updated, CodeNest scans its source and environment values for a Telegram bot token, a `t.me/<username>` link, or a `BOT_USERNAME`/`TELEGRAM_BOT_USERNAME` declaration.

If a token is found, the server makes a short Telegram `getMe` request. Only safe identity metadata is retained: bot username, bot id, verification status and verification time. The token is never copied into metadata, API responses, deployment history or the admin console. Request exception text is not retained because it may contain the token-bearing URL.

RunSpace also has a dedicated **Telegram bot** setup section. The owner pastes a BotFather token, presses **Verify bot**, receives the verified `@username` and a clickable bot link, then presses **Save & Run**. The verified token is included as that job's `BOT_TOKEN` environment variable. Uploaded files containing a token automatically open this verification section; direct Run still performs authoritative server-side detection.

The RunSpace workspace displays:

- the detected bot username;
- whether the RunSpace process is running;
- whether Telegram accepted the token;
- **Go to your bot**, linking to `https://t.me/<username>`.

These are deliberately separate signals. “RunSpace process running” and “Telegram identity verified” do not falsely claim that every command handler inside user code is working.

The admin console has a **Telegram bots on RunSpace** section with current detected bots, owner, job, process status, token-check status, uptime and a safe direct link. It also stores an immutable run/update/restart history in `job_deploy_events`, recording who ran what without duplicating source or tokens.

Existing jobs receive metadata on their next run/update. New jobs are detected immediately.
