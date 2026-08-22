"""Safe starter bots. Tokens are always read from BOT_TOKEN."""
TEMPLATES = {
    "python-telegram-bot": {
        "name": "Python command bot",
        "language": "python",
        "framework": "python-telegram-bot",
        "code": '''# requirements: python-telegram-bot==21.4
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Your CodeNest bot is running.")

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
''',
    },
    "aiogram": {
        "name": "Aiogram echo bot",
        "language": "python",
        "framework": "aiogram",
        "code": '''# requirements: aiogram==3.13.1
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
''',
    },
    "telebot": {
        "name": "TeleBot menu bot",
        "language": "python",
        "framework": "pyTelegramBotAPI",
        "code": '''# requirements: pyTelegramBotAPI==4.23.0
import os
import telebot

bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Your bot is online.")

bot.infinity_polling()
''',
    },
    "telegraf": {
        "name": "Node.js Telegraf bot",
        "language": "javascript",
        "framework": "Telegraf",
        "code": '''// requirements: telegraf
const { Telegraf } = require("telegraf");
const bot = new Telegraf(process.env.BOT_TOKEN);

bot.start((ctx) => ctx.reply("Your bot is online."));
bot.on("text", (ctx) => ctx.reply(ctx.message.text));
bot.launch();
''',
    },
}


def list_templates():
    return [{"id": key, "name": value["name"], "language": value["language"],
             "framework": value["framework"]} for key, value in TEMPLATES.items()]


def get_template(template_id):
    value = TEMPLATES.get(template_id)
    return dict(value) if value else None
