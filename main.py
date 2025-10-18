import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from database.engine import create_db
from handlers import start_router, menu_router, analysis_router, cabinet_router, admin_router
from middlewares.admin_check import AdminMiddleware

logging.basicConfig(level=logging.INFO)

async def main():
    config = Config()
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.message.middleware(AdminMiddleware())
    
    dp.include_routers(
        start_router,
        analysis_router,
        menu_router,
        cabinet_router,
        admin_router
    )
    
    await create_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())