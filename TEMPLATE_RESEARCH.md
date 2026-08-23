# CodeNest Telegram product research

Research updated: 2026-08-23

## Correction made

The previous catalog optimized for the number “101” and produced variations of generic workflow and tracker engines. That was the wrong product decision. Appointment variants, expense/habit/water trackers, reminders, notes, generic command bots, URL checkers, and echo demos have been removed from the public catalog.

The replacement catalog still contains **101 Python bots**, but 91 are ranked products based on observed Telegram demand and 10 are existing specialized Telegram-native products (support, referrals, channels, groups, broadcasting, orders, and file storage).

## How demand was evaluated

No trustworthy official global Telegram installation ranking exists. We therefore used repeated appearance across current bot directories, mature open-source projects, and Bangladesh-specific API availability rather than pretending an exact popularity table exists.

Repeated high-demand product groups:

1. AI assistants and AI business support
2. Shops, payments, order status, and digital products
3. Group moderation, anti-spam, reports, and analytics
4. Channel publishing, force-join, paid access, and referral growth
5. File conversion, PDF/image tools, OCR, and malware scanning
6. RSS/news/content automation
7. Live cricket/football and market data
8. GitHub/developer notifications
9. Quran/Hadith Bangla access
10. Bangladesh jobs, laws, location, courier, payment, and ecommerce workflows

Sources used to identify those groups:

- Current Telegram bot category comparison: https://www.itechguides.com/70-best-telegram-bots-list/
- Popular product categories and reported usage: https://controlhippo.com/blog/telegram/telegram-bot-list/
- Business bot patterns: https://blog.bothero.ai/the-telegram-bot-list-that-actually-matters-27-bots-organized-by-what-they-do-for-small-businesses-and-what-you-can-steal-for-your-own
- Group/channel products including ControllerBot, Combot, Rose, InviteMember and Feed Reader: https://techcult.com/best-telegram-bots/
- AI, moderation and analytics product comparison: https://teleclaw.bot/blog/best-telegram-bots-2026

Directory-provided user counts were treated as unverified indicators, not facts. Product categories repeated across independent lists were given more weight than claimed counts.

## API research

### Primary specifications

- Telegram Bot API: https://core.telegram.org/bots/api
- Telegram Bot FAQ and rate limits: https://core.telegram.org/bots/faq
- python-telegram-bot official examples: https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples
- ConversationHandler reference: https://docs.python-telegram-bot.org/en/stable/telegram.ext.conversationhandler.html

### Public API directories

- Public APIs: https://github.com/public-apis/public-apis
- Bangladesh API directory: https://github.com/rdnasim/bangla-apis

The Bangladesh directory was used to verify that real integrations exist for:

- bKash, Nagad, aamarPay, SSLCOMMERZ, ShurjoPay;
- RedX, eCourier, PandaGo and other courier workflows;
- Bangla Quran and Hadith;
- Bangladesh news;
- Barikoi/Dingi and Bangladesh administrative locations;
- Bangladesh laws and identity verification.

Merchant APIs require contracts and credentials. Templates never include fake keys and never claim that a payment is verified when only a transaction reference was submitted.

### Open-source architecture reviewed

- Production shop architecture: https://github.com/ilyarolf/AiogramShopBot
- Digital/physical shop patterns: https://github.com/interlumpen/Telegram-shop
- Support ticket architecture: https://github.com/bostrot/telegram-support-bot
- Bangladesh multi-courier tracking model: https://github.com/mdminhazulhaque/bangladeshi-parcel-tracker
- Advanced moderation patterns: https://github.com/DevyRuxpin/telegram-moderator-bot
- Official PTB examples are CC0. Third-party project source was not copied.

## Catalog architecture

### 17 AI products

OpenAI-compatible provider integration supports OpenAI, OpenRouter, Groq, DeepSeek, Mistral, or a self-hosted compatible endpoint. Templates include:

- encrypted API setup fields;
- owner-editable system policy;
- per-user contextual memory with retention limits;
- daily quota and provider-spend controls;
- usage analytics;
- ban/unban and paced broadcasts;
- explicit boundaries for health, legal, travel, ecommerce, and educational use.

The top result is a Bangladesh business assistant that understands Bangla, English, and Banglish and is instructed not to invent price, stock, discounts, or policy.

### 25 live API products

Provider-specific request and response handling exists for:

- Bangla and English Wikipedia;
- dictionary, Open Library, Jikan anime, REST Countries, and IP intelligence;
- GitHub repositories, releases, and Actions;
- PyPI and npm;
- CoinGecko USD/BDT prices and Frankfurter remittance conversion;
- AlQuran Cloud Bangla ayah and alQuranBD Bangla Hadith book/chapter data;
- TMDB, NewsAPI, CricAPI, API-Football, Aviationstack, and VirusTotal;
- configurable Bangladesh jobs/location endpoints and Bangladesh laws.

They include bounded input, timeout handling, HTTP status reporting, five-minute response cache, user quotas, and admin analytics.

### 24 commerce products

Each commerce bot includes:

- owner-managed product catalog;
- stock and quantity enforcement;
- persistent cart;
- cryptographically random order reference;
- transactional stock reduction at checkout;
- payment URL or payment-proof review flow;
- user order history;
- owner status transitions and buyer notification;
- gross sales and user/order analytics.

Products cover Bangladesh online shops, Facebook sellers, COD courier orders, food, fashion, books, courses, software licenses, electronics, pharmacy review, printing, wholesale, subscriptions, tickets, and reseller services.

### 15 channel/growth products

Channel-admin verification, join checks, referral attribution after verified membership, scheduled publishing, optional auto-delete, broadcasts, and member/post analytics. Product names target paid access, course/VIP access, jobs/news/deal channels, giveaways, affiliate growth, and creator communities.

### 10 file/security products

Files are bounded to 20 MB and processed in memory. Products include image-to-PDF, compression, resizing, PDF extraction/splitting, QR generation, OCR.Space, VirusTotal scanning, checksum/metadata foundations, and private processing. The bot states that files are not retained.

### Existing specialized products

The existing full master referral, live support inbox, admin broadcast, file store, order bot, channel poster, channel gate, group helper, reward referral, and basic referral implementations remain because they solve Telegram-native demand directly.

## Ranking

The gallery no longer follows source-file insertion order. It is explicitly ranked:

1. Bangla AI business/support/sales/study products
2. Live API products
3. Commerce products
4. Channel/growth products
5. File/security products
6. Existing specialized products

This prevents compatibility templates from occupying the first screen.

## Validation gate

Automated checks require:

1. exactly 101 unique catalog IDs;
2. Python-only source;
3. environment-based `BOT_TOKEN` with no token-shaped literals;
4. Telegram detection and polling mode;
5. successful Python compilation for every template;
6. required API credentials declared as encrypted setup fields;
7. top-ranked Bangladesh AI products in the first results;
8. removed filler IDs to be unavailable;
9. family-specific storage, quota, cache, cart/stock/order, channel membership, and file-security controls.
