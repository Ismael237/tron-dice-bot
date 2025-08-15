import asyncio
import datetime
from telegram import Bot, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from decimal import Decimal
from utils.helpers import escape_markdown_v2
from config import TELEGRAM_BOT_TOKEN


def format_trx(amount: float | Decimal, decimals: int = 2) -> str:
    """Format TRX amount for display"""
    return f"{float(amount):.{decimals}f} TRX"


def format_trx_escaped(amount: float | Decimal) -> str:
    """Format a TRX amount with escaping for Telegram Markdown V2"""
    return escape_markdown_v2(format_trx(amount))


def format_date(dt: datetime.datetime | None) -> str:
    """Format a date"""
    return dt.strftime('%Y-%m-%d') if dt else '-'


def format_time(dt: datetime.datetime | None) -> str:
    """Format a time"""
    return dt.strftime('%H:%M:%S') if dt else '-'


def format_datetime(dt: datetime.datetime | None) -> str:
    """Format a datetime"""
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else '-'


async def notify_user(telegram_id: str, message: str, reply_markup: ReplyKeyboardMarkup = None) -> None:
    """Send a Markdown-v2 formatted message to the given Telegram user, if possible."""
    # Initialize Telegram Bot for notifications
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    if not telegram_id:
        return
    try:
        await bot.send_message(chat_id=telegram_id, text=(message), parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"[Notify] Failed to send message to {telegram_id}: {e}")

def safe_notify_user(telegram_id: int, message: str, reply_markup: ReplyKeyboardMarkup = None):
    """Send a Markdown-v2 formatted message to the given Telegram user, if possible."""
    try:
        # Python ≥3.7: create a new loop if none exists (e.g. in thread)
        loop = asyncio.get_event_loop()
    except RuntimeError as e:
        if "There is no current event loop" in str(e):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            raise

    try:
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                notify_user(telegram_id, message, reply_markup), loop
            )
        else:
            loop.run_until_complete(notify_user(telegram_id, message, reply_markup))
    except Exception as e:
        # log this error instead of retrying recursively
        logger.error(f"[Notify] Failed to notify {telegram_id}: {e}")