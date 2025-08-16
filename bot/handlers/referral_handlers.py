from __future__ import annotations

from math import ceil

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.keyboards import (
    main_reply_keyboard,
    referral_reply_keyboard,
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
    bot_username = context.bot.username
    if not bot_username or bot_username == "":
        bot_username = BOT_USERNAME
    share_link = service.generate_share_link(user.id, bot_username)

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
        reply_markup=referral_reply_keyboard(),
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


async def handle_referral_share_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send user's personal share link as a plain message with submenu."""
    service = ReferralService()
    user = service.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await update.message.reply_markdown_v2(
            msg_not_registered_prompt_start(), reply_markup=main_reply_keyboard()
        )
        return
    bot_username = context.bot.username or BOT_USERNAME
    share_link = service.generate_share_link(user.id, bot_username)
    await update.message.reply_text(share_link, reply_markup=referral_reply_keyboard())


async def handle_referral_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show referral commissions history (first page) with ReplyKeyboard submenu."""
    service = ReferralService()
    user = service.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await update.message.reply_markdown_v2(
            msg_not_registered_prompt_start(), reply_markup=main_reply_keyboard()
        )
        return
    comms = service.get_commissions(user.id)
    total = len(comms)
    total_pages = max(1, ceil(total / _PAGE_SIZE))
    page = 1
    start = 0
    end = start + _PAGE_SIZE
    slice_rows = comms[start:end]
    text = msg_referral_history_page(slice_rows, page, total_pages)
    await update.message.reply_markdown_v2(text, reply_markup=referral_reply_keyboard())


async def handle_referral_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show referral leaderboard (first page) with ReplyKeyboard submenu."""
    service = ReferralService()
    user = service.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await update.message.reply_markdown_v2(
            msg_not_registered_prompt_start(), reply_markup=main_reply_keyboard()
        )
        return
    lb = service.get_referral_leaderboard(limit=100)  # type: ignore[attr-defined]
    total = len(lb)
    total_pages = max(1, ceil(total / _PAGE_SIZE))
    page = 1
    start = 0
    end = start + _PAGE_SIZE
    slice_rows = lb[start:end]
    text = msg_referral_leaderboard_page(slice_rows, page, total_pages)
    await update.message.reply_markdown_v2(text, reply_markup=referral_reply_keyboard())
