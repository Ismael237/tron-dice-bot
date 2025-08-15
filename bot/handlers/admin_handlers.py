from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import ITEMS_PER_PAGE, EMERGENCY_STOP
from services.admin_service import AdminService
from bot.messages import (
    msg_admin_unauthorized,
    msg_admin_main,
    msg_admin_stats,
    msg_admin_users_page,
    msg_admin_games_page,
    msg_admin_alerts_page,
    msg_admin_controls_hint,
)
from bot.keyboards import (
    admin_main_inline_keyboard,
    admin_pagination_inline_keyboard,
    admin_controls_inline_keyboard,
)


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    return AdminService.is_admin(str(user.id) if user else None, user.username if user else None)


async def _require_admin(update: Update) -> bool:
    if not _is_admin(update):
        if update.message:
            await update.message.reply_text(msg_admin_unauthorized())
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg_admin_unauthorized())
        return False
    return True


# ============== Commands and main entry ==============

async def handle_admin_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    if update.message:
        await update.message.reply_markdown_v2(
            msg_admin_main(), reply_markup=admin_main_inline_keyboard()
        )
    else:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(
            msg_admin_main(), parse_mode=ParseMode.MARKDOWN_V2, reply_markup=admin_main_inline_keyboard()
        )


async def handle_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    overall = AdminService.get_overall_stats()
    text = msg_admin_stats(overall, EMERGENCY_STOP)
    if update.message:
        await update.message.reply_markdown_v2(text, reply_markup=admin_controls_inline_keyboard(EMERGENCY_STOP))
    else:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=admin_controls_inline_keyboard(EMERGENCY_STOP))


async def handle_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    # Determine page
    page = 1
    if update.callback_query:
        try:
            # pattern: admin_users_page_{n}
            _, section, _, page_str = update.callback_query.data.split("_")
            page = int(page_str)
        except Exception:
            page = 1
    rows, total_pages = AdminService.list_users(page, ITEMS_PER_PAGE)
    text = msg_admin_users_page(rows, page, total_pages)
    kb = admin_pagination_inline_keyboard(page, total_pages, "users")
    if update.message:
        await update.message.reply_markdown_v2(text, reply_markup=kb)
    else:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)


async def handle_admin_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    page = 1
    if update.callback_query:
        try:
            _, section, _, page_str = update.callback_query.data.split("_")
            page = int(page_str)
        except Exception:
            page = 1
    rows, total_pages = AdminService.list_games(page, ITEMS_PER_PAGE)
    text = msg_admin_games_page(rows, page, total_pages)
    kb = admin_pagination_inline_keyboard(page, total_pages, "games")
    if update.message:
        await update.message.reply_markdown_v2(text, reply_markup=kb)
    else:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)


async def handle_admin_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    page = 1
    if update.callback_query:
        try:
            _, section, _, page_str = update.callback_query.data.split("_")
            page = int(page_str)
        except Exception:
            page = 1
    rows, total_pages = AdminService.list_alerts(page, ITEMS_PER_PAGE)
    text = msg_admin_alerts_page(rows, page, total_pages)
    kb = admin_pagination_inline_keyboard(page, total_pages, "alerts")
    if update.message:
        await update.message.reply_markdown_v2(text, reply_markup=kb)
    else:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)


async def handle_admin_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    q = update.callback_query
    await q.answer()
    new_val = AdminService.toggle_emergency()
    overall = AdminService.get_overall_stats()
    text = msg_admin_stats(overall, new_val)
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=admin_controls_inline_keyboard(new_val))
