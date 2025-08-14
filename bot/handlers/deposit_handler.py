from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import main_reply_keyboard
from bot.messages import (
    msg_deposit_not_registered,
    msg_deposit_wallet_not_found,
    msg_deposit_panel,
)
from services.deposit_service import DepositService


async def handle_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)

    user = DepositService.get_user_by_telegram(telegram_id)
    if not user:
        await update.message.reply_markdown_v2(
            msg_deposit_not_registered(),
            reply_markup=main_reply_keyboard(),
        )
        return

    wallet = DepositService.get_wallet_for_user(user.id)
    if not wallet:
        await update.message.reply_markdown_v2(
            msg_deposit_wallet_not_found(),
            reply_markup=main_reply_keyboard(),
        )
        return

    await update.message.reply_markdown_v2(
        msg_deposit_panel(wallet.address),
        reply_markup=main_reply_keyboard(),
    )
