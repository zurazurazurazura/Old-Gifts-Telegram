import os
import asyncio
import logging
from config import API_ID, API_HASH, BOT_TOKEN, SESSIONS_DIR
from db import init_db
from auth import check_timeouts
from bot_handlers import register_handlers
from telethon import TelegramClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    init_db()
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    
    bot = TelegramClient("bot", API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    await register_handlers(bot)
    asyncio.create_task(check_timeouts(bot))
    
    logger.info("Bot is running...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
