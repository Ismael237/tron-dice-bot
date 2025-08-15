from __future__ import annotations

from math import ceil
from typing import List

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.keyboards import (
    main_reply_keyboard,
    referral_overview_inline_keyboard,
    pagination_inline_keyboard,
)
from bot.messages import (
    msg_referral_overview,
    msg_referral_info_single_level,
    msg_not_registered_prompt_start,
    msg_referral_history_page,
    msg_referral_leaderboard_page,
)
from bot.utils import format_trx
from config import REFERRAL_RATE, BOT_USERNAME
from services.referral_service import ReferralService


_PAGE_SIZE = 5


async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a single-level referral overview with actions (share, history, leaderboard)."""
    service = ReferralService()
    user = service.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await update.message.reply_markdown_v2(
            msg_not_registered_prompt_start(),
            reply_markup=main_reply_keyboard(),
        )
        return

    # Ensure code and share link
    code = service.ensure_referral_code(user.id)
    share_link = service.generate_share_link(user.id, BOT_USERNAME)

    # Direct refs count and commissions summary
    direct_refs = service.get_direct_referrals(user.id)
    summary = service.summarize_commissions(user.id)
    total_paid_trx = format_trx(summary.get("total_paid", 0.0))
    total_pending_trx = format_trx(summary.get("total_pending", 0.0))

    text = msg_referral_overview(
        referral_code=code,
        share_link=share_link,
        total_referrals=str(len(direct_refs)),
        total_paid_trx=total_paid_trx,
        total_pending_trx=total_pending_trx,
    )

    await update.message.reply_markdown_v2(
        text,
        reply_markup=referral_overview_inline_keyboard(share_link),
    )


async def handle_referral_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explain the referral program briefly."""
    rate_percent = str(int(REFERRAL_RATE * 100))
    msg = msg_referral_info_single_level(rate_percent)
    if update.message:
        await update.message.reply_markdown_v2(msg, reply_markup=main_reply_keyboard())
    else:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_markdown_v2(msg, reply_markup=main_reply_keyboard())


async def handle_referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline callback actions for referral pages (history, leaderboard)."""
    query = update.callback_query
    if not query:
        return
    data = (query.data or "").strip()

    service = ReferralService()
    user = service.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await query.answer()
        await query.message.reply_markdown_v2(msg_not_registered_prompt_start(), reply_markup=main_reply_keyboard())
        return

    async def _edit(text: str, reply_markup=None):
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
        except Exception:
            await query.message.reply_markdown_v2(text, reply_markup=reply_markup)

    try:
        # Referral commissions history pagination: ref_hist_page_{n}
        if data.startswith("ref_hist_page_"):
            page_str = data.split("ref_hist_page_")[-1]
            try:
                page = max(1, int(page_str))
            except Exception:
                page = 1

            comms = service.get_commissions(user.id)
            total = len(comms)
            total_pages = max(1, ceil(total / _PAGE_SIZE))
            start = (page - 1) * _PAGE_SIZE
            end = start + _PAGE_SIZE
            slice_rows = comms[start:end]

            text = msg_referral_history_page(slice_rows, page, total_pages)
            await _edit(text, reply_markup=pagination_inline_keyboard(page, total_pages, "ref_hist"))
            await query.answer()
            return

        # Referral leaderboard pagination: ref_lb_page_{n}
        if data.startswith("ref_lb_page_"):
            page_str = data.split("ref_lb_page_")[-1]
            try:
                page = max(1, int(page_str))
            except Exception:
                page = 1

            # Leaderboard by total referral earnings (all-time), descending
            lb = service.get_referral_leaderboard(limit=100)  # type: ignore[attr-defined]
            total = len(lb)
            total_pages = max(1, ceil(total / _PAGE_SIZE))
            start = (page - 1) * _PAGE_SIZE
            end = start + _PAGE_SIZE
            slice_rows = lb[start:end]

            text = msg_referral_leaderboard_page(slice_rows, page, total_pages)
            await _edit(text, reply_markup=pagination_inline_keyboard(page, total_pages, "ref_lb"))
            await query.answer()
            return

        if data == "referral_info":
            await query.answer()
            await handle_referral_info(update, context)
            return

    finally:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
