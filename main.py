from bot import bot, dp
from handlers import *
import asyncio
from database import reset_db
from utils.update import scheduler

async def main():
    scheduler.start()
    dp.include_router(start_router)
    dp.include_router(game_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    reset_db()
    
    asyncio.run(main())