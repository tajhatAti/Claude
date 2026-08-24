# Telegram bot product research

Research updated: 2026-08-24

There is no trustworthy official global installation ranking. Repeated categories across current Telegram directories and mature open-source products were used instead:

- group moderation/captcha/anti-spam;
- file storage, conversion, OCR and security;
- AI assistants and business support;
- shops, carts, payments and order tracking;
- channel publishing, referrals and paid membership.

References:

- Telegram Bot API: https://core.telegram.org/bots/api
- Telegram Bot FAQ/rate limits: https://core.telegram.org/bots/faq
- python-telegram-bot examples: https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples
- current Telegram bot category directory: https://www.itechguides.com/70-best-telegram-bots-list/
- business workflow research: https://blog.bothero.ai/the-telegram-bot-list-that-actually-matters-27-bots-organized-by-what-they-do-for-small-businesses-and-what-you-can-steal-for-your-own
- shop architecture: https://github.com/ilyarolf/AiogramShopBot
- support architecture: https://github.com/bostrot/telegram-support-bot

## Decision

The previous 101-entry catalog reused a few engines across many names. It was removed. The public catalog now has five integrated products; each groups related features users expect to work together.

## Validation

Automated tests require every public product to:

- be standalone Python;
- read `BOT_TOKEN` from the environment;
- contain no token-shaped literal;
- compile successfully;
- use polling correctly;
- execute its embedded SQLite schema;
- contain the advertised integrated controls for its category.
