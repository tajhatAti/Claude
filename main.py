import telebot
from telebot import types
import requests

# আপনার নতুন বট টোকেন বসান
BOT_TOKEN = "8850127960:AAG9hM2eaNUwOn-U1sRmlRElVTqhhAX3S1Y"
                                               bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])       def send_welcome(message):
    bot.reply_to(
        message,
        "👋 আমাকে যেকোনো গানের নাম লিখে পাঠান, আমি লিরিক্স খুঁজে দেব।"
    )

@bot.message_handler(func=lambda message: True)
def fetch_lyrics(message):
    song_query = message.text.strip()
    bot.send_chat_action(message.chat.id, 'typing')

    api_url = f"https://lrclib.net/api/search?q={requests.utils.quote(song_query)}"

    try:
        response = requests.get(api_url, timeout=10)
        results = response.json()

        lyrics_found = False

        if response.status_code == 200 and isinstance(results, list) and len(results) > 0:
            for item in results:
                lyrics = item.get("plainLyrics")
                if lyrics:
                    track_name = item.get("trackName", song_query)
                    artist_name = item.get("artistName", "Unknown Artist")

                    # স্ক্রিনশটের মতো ফরম্যাট: 🎵 Track - Artist
                    reply_text = f"🎵 *{track_name}* - {artist_name}\n\n{lyrics}"

                    # টেলিগ্রামের মেসেজ সাইজ লিমিট (4000 chars) হ্যান্ডেল করা
                    if len(reply_text) > 4000:
                        reply_text = reply_text[:3900] + "\n\n...(লিরিক্স বড় হওয়ায় বাকি অংশ বাদ দেওয়া হয়েছে)"

                    bot.reply_to(message, reply_text, parse_mode="Markdown")
                    lyrics_found = True
                    break

        # লিরিক্স না পাওয়া গেলে Inline Button এবং Hidden Link দেখাবে
        if not lyrics_found:
            encoded_query = requests.utils.quote(f"{song_query} lyrics")
            google_url = f"https://www.google.com/search?q={encoded_query}"

            # 1. Inline Button তৈরি
            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton(text="🔍 Google-এ লিরিক্স দেখুন", url=google_url)
            markup.add(btn)

            # 2. Hidden Link সহ মেসেজ
            msg_text = (
                f"❌ *{song_query}* গানটির লিরিক্স ডাটাবেজে পাওয়া যায়নি।\n\n"
                f"আপনি [এখানে ক্লিক করে]({google_url}) অথবা নিচের বাটনে চাপ দিয়ে সরাসরি গুগলে লিরিক্স দেখে নিতে পারেন।"
            )

            bot.reply_to(
                message,
                msg_text,
                parse_mode="Markdown",
                reply_markup=markup,
                disable_web_page_preview=True # ওয়েবসাইটের বড় প্রিভিউ বন্ধ রাখার জন্য
            )

    except Exception:
        encoded_query = requests.utils.quote(f"{song_query} lyrics")
        google_url = f"https://www.google.com/search?q={encoded_query}"

        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton(text="🔍 Google-এ খুঁজুন", url=google_url)
        markup.add(btn)

        bot.reply_to(
            message,
            "⚠️ লিরিক্স সার্ভারে সংযোগ করা যায়নি। নিচের বাটনে ক্লিক করে গুগলে দেখুন:",
            reply_markup=markup
        )

if __name__ == "__main__":
    bot.infinity_polling()
