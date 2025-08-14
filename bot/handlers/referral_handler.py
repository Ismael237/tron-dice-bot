from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import main_reply_keyboard
from bot.messages import (
    msg_referral_overview,
    msg_referral_info_single_level,
    msg_not_registered_prompt_start,
)
from bot.utils import format_trx
from config import REFERRAL_RATE
from services.referral_service import ReferralService
from utils.helpers import generate_share_link


async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a concise single-level referral overview (UI only)."""
    service = ReferralService()
    user = service.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await update.message.reply_markdown_v2(
            msg_not_registered_prompt_start(),
            reply_markup=main_reply_keyboard(),
        )
        return

    # Single-level: direct referrals only
    direct_refs = service.get_direct_referrals(user.id)
    total_referrals = str(len(direct_refs))

    summary = service.summarize_commissions(user.id)
    total_paid_trx = format_trx(summary.get("total_paid", 0.0))
    total_pending_trx = format_trx(summary.get("total_pending", 0.0))

    # Share link constructed from bot username + referral code
    bot_username = context.bot.username
    share_link = generate_share_link(bot_username, user.referral_code)

    msg = msg_referral_overview(
        referral_code=user.referral_code,
        share_link=share_link,
        total_referrals=total_referrals,
        total_paid_trx=total_paid_trx,
        total_pending_trx=total_pending_trx,
    )
    await update.message.reply_markdown_v2(msg, reply_markup=main_reply_keyboard())


async def handle_referral_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rate_percent = str(int(REFERRAL_RATE * 100))
    msg = msg_referral_info_single_level(rate_percent)
    if update.message:
        await update.message.reply_markdown_v2(msg, reply_markup=main_reply_keyboard())
    else:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_markdown_v2(msg, reply_markup=main_reply_keyboard())