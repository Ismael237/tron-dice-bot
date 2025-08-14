import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor as APSchedulerThreadPoolExecutor
import atexit
from config import (
    TELEGRAM_BOT_TOKEN, DATABASE_URL,
    DEPOSIT_CHECK_INTERVAL, WITHDRAWAL_PROCESS_INTERVAL,
    AP_SCHEDULER_THREAD_POOL_SIZE
)
from database.database import init_database
from utils.logger import logger
from bot.handlers.start_handler import (
    handle_start,
    handle_balance,
    handle_history,
    handle_history_pagination,
)
from bot.handlers.deposit_handler import handle_deposit
from bot.handlers.withdrawal_handler import handle_withdraw
from bot.handlers.referral_handler import handle_referral, handle_referral_info
from bot.handlers.message_router import route_text_message, handle_error
from bot.handlers.settings_handler import handle_settings, back_to_main_menu, handle_help, handle_about, handle_support, handle_qa
from workers.deposit_monitor import run_deposit_monitor
from workers.withdrawal_processor import run_withdrawal_processor

def start_scheduler():
    jobstores = {'default': SQLAlchemyJobStore(url=DATABASE_URL)}
    executors = {'default': APSchedulerThreadPoolExecutor(AP_SCHEDULER_THREAD_POOL_SIZE)}
    scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, timezone='UTC')
    
    # cron job
    scheduler.add_job(run_deposit_monitor, 'interval', minutes=DEPOSIT_CHECK_INTERVAL, id='monitor_deposits', replace_existing=True)
    scheduler.add_job(run_withdrawal_processor, 'interval', minutes=WITHDRAWAL_PROCESS_INTERVAL, id='process_withdrawals', replace_existing=True)
    
    scheduler.start()
    logger.info("[Scheduler] APScheduler started with persistent jobs.")
    atexit.register(lambda: scheduler.shutdown())
    return scheduler

async def setup_bot():
    """Configure and setup the bot with all handlers"""
    # Create bot application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers (explicit)
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("deposit", handle_deposit))
    app.add_handler(CommandHandler("balance", handle_balance))
    app.add_handler(CommandHandler("withdraw", handle_withdraw))
    app.add_handler(CommandHandler("referral", handle_referral))
    app.add_handler(CommandHandler("history", handle_history))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("settings", handle_settings))
    app.add_handler(CommandHandler("about", handle_about))
    app.add_handler(CommandHandler("support", handle_support))
    app.add_handler(CommandHandler("qa", handle_qa))
    app.add_handler(CommandHandler("main", back_to_main_menu))
    
    # Register free-text message router
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text_message))
    
    # Register callback query handlers
    app.add_handler(CallbackQueryHandler(handle_history_pagination, pattern=r"^history_(?:all|deposits|withdrawals)_page_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_referral_info, pattern=r"^referral_info$"))
    
    # Error handler
    app.add_error_handler(handle_error)
    
    return app

async def main():
    # Initialize DB
    init_database()
    
    # Start scheduler
    start_scheduler()
    
    # Setup bot
    app = await setup_bot()
    
    # Use context manager for proper initialization
    async with app:
        logger.info("[Main] Bot is running...")
        await app.start()
        await app.updater.start_polling()
        
        # Keep the bot running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("[Main] Received interrupt signal, shutting down...")
        finally:
            logger.info("[Main] Bot stopped.")

def run_bot():
    """Entry point to run the bot"""
    logger.info("[Main] Starting bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[Main] Bot interrupted by user.")
    except Exception as e:
        logger.error(f"[Main] Unexpected error: {e}")
        raise

if __name__ == "__main__":
    logger.info("[Main] Running main...")
    run_bot()