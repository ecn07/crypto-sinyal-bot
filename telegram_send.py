import os
from telegram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
bot = Bot(token=TOKEN)

async def send_telegram_message(message):
    await bot.send_message(chat_id=CHAT_ID, text=message)
