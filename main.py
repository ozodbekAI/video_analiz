import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from database.engine import create_db
from handlers import start_router, menu_router, analysis_router, cabinet_router, admin_router, verification_router, evolution_router, shorts_router
from middlewares.admin_check import AdminMiddleware
from handlers.strategic_hub import router as strategic_router
from services.multi_analysis_optimizer import run_multi_analysis_optimizer_scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    config = Config()
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required in .env to run the Telegram bot")
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required in .env")

    
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(AdminMiddleware())
    dp.callback_query.middleware(AdminMiddleware())
    

    dp.include_router(start_router)
    dp.include_router(analysis_router)
    dp.include_router(menu_router)
    dp.include_router(cabinet_router)
    dp.include_router(admin_router)
    dp.include_router(verification_router)
    dp.include_router(evolution_router)
    dp.include_router(shorts_router)
    dp.include_router(strategic_router)

    await create_db()

    # TZ-2: background optimizer (Advanced-only), runs every 30 minutes
    asyncio.create_task(run_multi_analysis_optimizer_scheduler(interval_seconds=1800))
    
    logging.info("🚀 Bot ishga tushdi...")
    
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("❌ Bot to'xtatildi")