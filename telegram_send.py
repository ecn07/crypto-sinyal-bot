import asyncio
from telegram import Bot

TOKEN = "8107305284:AAHpE6C6wS8JuzW_4Hd-HJMuGqVPI0q45XI"
bot = Bot(token=TOKEN)
chat_id = 1542821447

async def main():
    await bot.send_message(chat_id=chat_id, text="Merhaba, bu Telegram botundan test mesajıdır!")
    print("Mesaj gönderildi.")

asyncio.run(main())
