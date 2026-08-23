"""Practical starter bots. Every template reads the token from BOT_TOKEN."""


def _item(name, description, category, language, framework, code, badge=""):
    return {"name": name, "description": description, "category": category,
            "language": language, "framework": framework, "badge": badge,
            "code": code.strip() + "\n"}


TEMPLATES = {
    "command-bot": _item(
        "Command bot", "A clean /start and /help foundation.", "Basics",
        "python", "python-telegram-bot", '''
# requirements: python-telegram-bot==21.4
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am online. Send /help to begin.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commands:\\n/start — start the bot\\n/help — show help")

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.run_polling()
''', "Popular"),

    "aiogram-echo": _item(
        "Aiogram echo", "Replies with the same text a user sends.", "Basics",
        "python", "aiogram", '''
# requirements: aiogram==3.13.1
import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

@dp.message(F.text)
async def echo(message: Message):
    await message.answer(message.text)

async def main():
    await dp.start_polling(bot)

asyncio.run(main())
''', "Simple"),

    "telebot-menu": _item(
        "Reply menu", "A simple keyboard with Help, About, and Contact buttons.", "Menus",
        "python", "pyTelegramBotAPI", '''
# requirements: pyTelegramBotAPI==4.23.0
import os
import telebot
from telebot import types

bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

@bot.message_handler(commands=["start"])
def start(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Help", "About", "Contact")
    bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)

@bot.message_handler(func=lambda m: True)
def menu(message):
    replies = {"Help": "How can I help?", "About": "Hosted on CodeNest.", "Contact": "Send your message here."}
    bot.reply_to(message, replies.get(message.text, "Use the menu below."))

bot.infinity_polling(skip_pending=True)
''', "Popular"),

    "inline-buttons": _item(
        "Inline buttons", "Clickable buttons with callback responses.", "Menus",
        "python", "python-telegram-bot", '''
# requirements: python-telegram-bot==21.4
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Status", callback_data="status"), InlineKeyboardButton("Help", callback_data="help")]]
    await update.message.reply_text("Choose an action:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Bot is running." if query.data == "status" else "Send /start to open the menu.")

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.run_polling()
'''),

    "welcome-bot": _item(
        "Group welcome", "Welcomes new group members and shows /rules.", "Groups",
        "python", "python-telegram-bot", '''
# requirements: python-telegram-bot==21.4
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

RULES = "1. Be respectful\\n2. No spam\\n3. Stay on topic"

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(f"Welcome, {member.first_name}!\\n\\n{RULES}")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES)

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
app.add_handler(CommandHandler("rules", rules))
app.run_polling()
''', "Groups"),

    "file-info": _item(
        "File ID helper", "Returns Telegram file IDs for photos and documents.", "Utilities",
        "python", "python-telegram-bot", '''
# requirements: python-telegram-bot==21.4
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

async def file_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        item = update.message.document
        text = f"Document: {item.file_name}\\nFile ID: {item.file_id}"
    else:
        item = update.message.photo[-1]
        text = f"Photo size: {item.width}×{item.height}\\nFile ID: {item.file_id}"
    await update.message.reply_text(text)

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, file_info))
app.run_polling()
'''),

    "poll-bot": _item(
        "Quick poll", "Creates a Telegram poll from one command.", "Utilities",
        "python", "python-telegram-bot", '''
# requirements: python-telegram-bot==21.4
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = " ".join(context.args)
    parts = [part.strip() for part in raw.split("|") if part.strip()]
    if len(parts) < 3:
        await update.message.reply_text("Use: /poll Question | Option one | Option two")
        return
    await update.message.reply_poll(parts[0], parts[1:11], is_anonymous=False)

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(CommandHandler("poll", poll))
app.run_polling()
'''),

    "reminder-bot": _item(
        "Simple reminder", "Sends a reminder after a number of seconds.", "Utilities",
        "python", "python-telegram-bot", '''
# requirements: python-telegram-bot==21.4
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def send_later(chat_id, seconds, text, context):
    await asyncio.sleep(seconds)
    await context.bot.send_message(chat_id, f"⏰ {text}")

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text("Use: /remind 60 Drink water")
        return
    seconds = min(int(context.args[0]), 86400)
    text = " ".join(context.args[1:])
    context.application.create_task(send_later(update.effective_chat.id, seconds, text, context))
    await update.message.reply_text(f"Reminder set for {seconds} seconds.")

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(CommandHandler("remind", remind))
app.run_polling()
'''),

    "notes-bot": _item(
        "Personal notes", "Saves small notes in SQLite and retrieves them by key.", "Storage",
        "python", "python-telegram-bot", '''
# requirements: python-telegram-bot==21.4
import os
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

DB = sqlite3.connect("notes.db", check_same_thread=False)
DB.execute("CREATE TABLE IF NOT EXISTS notes (chat_id INTEGER, name TEXT, value TEXT, PRIMARY KEY(chat_id, name))")

async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /save name your note")
        return
    name, value = context.args[0].lower(), " ".join(context.args[1:])
    DB.execute("INSERT OR REPLACE INTO notes VALUES (?, ?, ?)", (update.effective_chat.id, name, value))
    DB.commit()
    await update.message.reply_text(f"Saved: {name}")

async def note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.args[0].lower() if context.args else ""
    row = DB.execute("SELECT value FROM notes WHERE chat_id=? AND name=?", (update.effective_chat.id, name)).fetchone()
    await update.message.reply_text(row[0] if row else "Note not found. Use /save first.")

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(CommandHandler("save", save))
app.add_handler(CommandHandler("note", note))
app.run_polling()
''', "Storage"),

    "url-checker": _item(
        "Website checker", "Checks a public URL and reports its HTTP status.", "Utilities",
        "python", "python-telegram-bot", '''
# requirements: python-telegram-bot==21.4 requests==2.32.3
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].startswith(("http://", "https://")):
        await update.message.reply_text("Use: /check https://example.com")
        return
    try:
        response = requests.get(context.args[0], timeout=8, allow_redirects=True)
        await update.message.reply_text(f"Status: {response.status_code}\\nFinal URL: {response.url}")
    except requests.RequestException:
        await update.message.reply_text("The website did not respond in time.")

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(CommandHandler("check", check))
app.run_polling()
'''),

    "telegraf-echo": _item(
        "Telegraf echo", "A minimal Node.js bot with /start and text replies.", "Node.js",
        "javascript", "Telegraf", '''
// requirements: telegraf
const { Telegraf } = require("telegraf");
const bot = new Telegraf(process.env.BOT_TOKEN);

bot.start((ctx) => ctx.reply("Your bot is online."));
bot.on("text", (ctx) => ctx.reply(ctx.message.text));
bot.launch();
''', "Node.js"),
}


def list_templates():
    return [{"id": key, "name": value["name"],
             "description": value["description"], "category": value["category"],
             "language": value["language"], "framework": value["framework"],
             "badge": value.get("badge", "")} for key, value in TEMPLATES.items()]


def get_template(template_id):
    value = TEMPLATES.get(template_id)
    return dict(value) if value else None
