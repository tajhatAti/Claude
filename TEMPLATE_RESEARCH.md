# Telegram template research and engineering notes

Research date: 2026-08-23

## Sources reviewed

### Primary specifications

- Telegram Bot API: https://core.telegram.org/bots/api
  - Verified polling, callback queries, membership/admin operations, chat permissions, files, polls, payments, deep links, and update types.
  - `getChatMember` checks for other users are reliable when the bot is an administrator.
- Telegram Bot FAQ: https://core.telegram.org/bots/faq
  - Free broadcasts should stay below roughly 30 messages/second; one chat should normally receive at most one message/second.
  - Generated broadcast engines pace delivery and handle `RetryAfter`; unreachable users are disabled after `Forbidden`.
- python-telegram-bot official examples: https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples
  - Reviewed ConversationHandler, persistent conversation, deep linking, inline keyboard, poll, timer, payment, chat-member, and error handling patterns.
  - The official examples are CC0. No third-party project source was copied into CodeNest.
- ConversationHandler reference: https://docs.python-telegram-bot.org/en/stable/telegram.ext.conversationhandler.html
  - Multi-step intake templates use explicit states, `/cancel` fallbacks, bounded input, and restart-safe final records in SQLite.

### Open-source product research

These projects were reviewed for feature and workflow ideas only:

- AiogramShopBot: https://github.com/ilyarolf/AiogramShopBot
  - Catalog, cart/order state, inventory, purchase history, admin controls, analytics, referrals, and localization.
- Telegram Shop: https://github.com/interlumpen/Telegram-shop
  - Search, categories, stock notifications, idempotent payments, reviews, promos, audit logs, and exports.
- Telegram Support Bot: https://github.com/bostrot/telegram-support-bot
  - Open/close/reopen ticket lifecycle, staff replies, media, restrictions, anti-spam, routing, and FAQ handoff.
- Telegram Booking Bot: https://github.com/yuri586/telegram-booking-bot
  - Services, slots, active bookings, cancellation, reminders, status/payment state, exports, and admin scheduling.
- Telegram Moderator Bot: https://github.com/DevyRuxpin/telegram-moderator-bot
  - Flood control, warning thresholds, temporary mutes, bans, per-chat settings, rules, and moderation statistics.
- Samurai moderator: https://github.com/Priler/samurai
  - Reports, logs, reputation, anti-spam, announcements, and configurable moderation actions.
- Money Bot: https://github.com/cenoff/Money-Bot
  - Categories, recurring records, summaries, reports, exports, and private SQLite storage.
- python-telegram-bot examples are used as the API-behavior baseline; open projects above are not vendored or copied.

## Resulting architecture

The catalog has **101 templates, all Python**.

### Existing specialized templates (21)

The original referral, live support, channel gate/poster, group helper, broadcast, storage, order, poll, notes, and utility templates remain standalone. The former JavaScript echo starter was replaced with Python.

### Workflow engine (40 templates)

Used for bookings, CRM, support, applications, operations, rentals, education, hospitality, travel, workplace, and commerce.

Every emitted bot includes:

- secure one-tap administrator claim;
- multi-step `ConversationHandler` intake with cancellation;
- bounded and normalized input;
- per-user request ownership;
- configurable domain-specific states;
- user request list, detail view, and pending cancellation;
- admin queue, status transitions, private notes, and user notification;
- immutable status/action history;
- SQLite WAL storage;
- UTF-8 CSV export;
- paced broadcasts with Telegram flood-wait handling;
- ban/unban controls.

### Ledger/tracker engine (20 templates)

Used for finance, inventory, habits, goals, tasks, study, lifestyle, workplace, travel, developer, and CRM tracking.

Every emitted bot includes:

- per-user isolated records;
- numeric range validation and bounded labels;
- completion and deletion by owner only;
- totals, averages, completion count, and top-label summaries;
- CSV export;
- admin aggregate counts;
- paced broadcast and access restriction controls;
- SQLite WAL storage.

### Searchable catalog engine (10 templates)

Used for FAQ, company knowledge, products, services, prices, courses, recipes, resources, offers, and announcements.

Every emitted bot includes:

- admin publishing/editing/visibility controls;
- category browsing and SQL-backed search;
- pagination;
- per-user favorites;
- item view analytics;
- private admin claim and durable SQLite state.

### Group moderation engine (10 templates)

Used for flood, links, words, forwards, reports, newcomer safety, classroom, marketplace, discussion, and support groups.

Every emitted bot includes:

- actual Telegram group-admin authorization instead of a private numeric owner ID;
- configurable filter words and flood thresholds;
- escalating warnings;
- automatic one-hour mute after three warnings;
- manual timed mute and ban;
- member reports to administrators;
- persistent audit history;
- admin bypass and safe permission failure handling.

## Validation gate

The automated catalog gate verifies every template:

1. has a unique ID and complete metadata;
2. is Python-only;
3. reads `BOT_TOKEN` from the environment;
4. contains no token-shaped secret;
5. is detected as a Telegram bot using polling;
6. compiles as Python;
7. includes the expected state, storage, admin, export, moderation, or analytics controls for its family.

Templates intentionally avoid claiming that a Telegram bot can silently add users to channels, bypass group permissions, or process an external payment without a configured provider.
