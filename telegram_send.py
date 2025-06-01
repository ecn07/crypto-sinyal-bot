import os
import asyncio
from telegram import Bot

# Token ve Chat ID environment variables'dan okunuyor
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

bot = Bot(token=TOKEN)

async def send_telegram_message(message):
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
