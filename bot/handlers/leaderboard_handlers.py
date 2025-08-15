from __future__ import annotations

from math import ceil
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.keyboards import leaderboard_nav_inline_keyboard, main_reply_keyboard
from bot.messages import msg_game_leaderboard_page, msg_not_registered_prompt_start
from services.user_service import UserService
from services.leaderboard_service import LeaderboardService

_DEFAULT_PERIOD = "daily"  # daily | weekly | monthly
_DEFAULT_METRIC = "won"     # won | wagered
_PAGE_SIZE = 10


def _get_state(context: ContextTypes.DEFAULT_TYPE) -> tuple[str, str]:
    period = context.user_data.get("lb_period", _DEFAULT_PERIOD)
    metric = context.user_data.get("lb_metric", _DEFAULT_METRIC)
    return period, metric


def _set_state(context: ContextTypes.DEFAULT_TYPE, period: str | None = None, metric: str | None = None):
    if period:
        context.user_data["lb_period"] = period
    if metric:
        context.user_data["lb_metric"] = metric


async def handle_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry command to show leaderboard with default state and page 1."""
    user = UserService.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await update.message.reply_markdown_v2(
            msg_not_registered_prompt_start(), reply_markup=main_reply_keyboard()
        )
        return

    period, metric = _get_state(context)

    svc = LeaderboardService()
    rows = svc.list_by_period(period, metric, limit=500)
    total = len(rows)
    total_pages = max(1, ceil(total / _PAGE_SIZE))
    page = 1
    slice_rows = rows[0:_PAGE_SIZE]

    pos, my_val = svc.get_user_position(user.id, period, metric)
    text = msg_game_leaderboard_page(slice_rows, page, total_pages, period, metric, pos, my_val)
    await update.message.reply_markdown_v2(
        text, reply_markup=leaderboard_nav_inline_keyboard(period, metric, page, total_pages)
    )


async def handle_leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks for leaderboard: period/metric toggle and pagination."""
    query = update.callback_query
    if not query:
        return
    data = (query.data or "").strip()

    user = UserService.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await query.answer()
        await query.message.reply_markdown_v2(
            msg_not_registered_prompt_start(), reply_markup=main_reply_keyboard()
        )
        return

    async def _edit(text: str, reply_markup=None):
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
        except Exception:
            await query.message.reply_markdown_v2(text, reply_markup=reply_markup)

    # Toggle period
    if data.startswith("lb_period_"):
        period = data.split("lb_period_")[-1]
        if period not in {"daily", "weekly", "monthly"}:
            await query.answer()
            return
        _set_state(context, period=period)
        metric = _get_state(context)[1]
    # Toggle metric
    elif data.startswith("lb_metric_"):
        metric = data.split("lb_metric_")[-1]
        if metric not in {"won", "wagered"}:
            await query.answer()
            return
        _set_state(context, metric=metric)
        period = _get_state(context)[0]
    # Pagination explicit
    elif data.startswith("lb_") and "_page_" in data:
        # lb_{period}_{metric}_page_{n}
        try:
            _, period, metric, _, page_str = data.split("_", 4)
            page = max(1, int(page_str))
        except Exception:
            period, metric, page = _get_state(context)[0], _get_state(context)[1], 1
        _set_state(context, period=period, metric=metric)
    else:
        await query.answer()
        return

    # Render page 1 for toggles, or the selected page for pagination
    if not (data.startswith("lb_") and "_page_" in data):
        page = 1
    period, metric = _get_state(context)

    svc = LeaderboardService()
    rows = svc.list_by_period(period, metric, limit=500)
    total = len(rows)
    total_pages = max(1, ceil(total / _PAGE_SIZE))
    start = (page - 1) * _PAGE_SIZE
    end = start + _PAGE_SIZE
    slice_rows = rows[start:end]

    pos, my_val = svc.get_user_position(user.id, period, metric)
    text = msg_game_leaderboard_page(slice_rows, page, total_pages, period, metric, pos, my_val)
    await _edit(text, reply_markup=leaderboard_nav_inline_keyboard(period, metric, page, total_pages))
    await query.answer()
