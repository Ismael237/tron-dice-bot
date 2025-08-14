from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import (
    DEPOSIT_BTN,
    HISTORY_BTN, HELP_BTN, MAIN_MENU_BTN, REFERRAL_INFO_BTN,
    SETTINGS_BTN, SUPPORT_BTN, ABOUT_BTN,
    BALANCE_BTN, WITHDRAW_BTN,
    SHARE_EARN_BTN, CANCEL_WITHDRAW_BTN, CONFIRM_WITHDRAW_BTN,
    Q_A_BTN, ALL_TRANSACTIONS_BTN, DEPOSITS_ONLY_BTN,
    WITHDRAWALS_ONLY_BTN,
)

from bot.handlers import withdrawal_handler
from bot.handlers import start_handler, settings_handler, deposit_handler, referral_handler
from utils.logger import logger


async def route_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route free-text menu selections to the appropriate handlers."""
    text = update.message.text

    if text == DEPOSIT_BTN:
        await deposit_handler.handle_deposit(update, context)
    elif text == BALANCE_BTN:
        await start_handler.handle_balance(update, context)
    elif text == WITHDRAW_BTN:
        await withdrawal_handler.handle_withdraw(update, context)
    elif text == CANCEL_WITHDRAW_BTN:
        await withdrawal_handler.cancel_withdraw(update, context)
    elif text == CONFIRM_WITHDRAW_BTN:
        await withdrawal_handler.handle_withdraw_free_text(update, context)
    elif text in {HISTORY_BTN, ALL_TRANSACTIONS_BTN, DEPOSITS_ONLY_BTN, WITHDRAWALS_ONLY_BTN}:
        await start_handler.handle_history(update, context)
    elif text == SETTINGS_BTN:
        await settings_handler.handle_settings(update, context)
    elif text == HELP_BTN:
        await settings_handler.handle_help(update, context)
    elif text == SUPPORT_BTN:
        await settings_handler.handle_support(update, context)
    elif text == ABOUT_BTN:
        await settings_handler.handle_about(update, context)
    elif text == Q_A_BTN:
        await settings_handler.handle_qa(update, context)
    elif text == REFERRAL_INFO_BTN:
        await referral_handler.handle_referral_info(update, context)
    elif text == MAIN_MENU_BTN:
        await settings_handler.back_to_main_menu(update, context)
    elif text == SHARE_EARN_BTN:
        await referral_handler.handle_referral(update, context)
    elif "withdraw" in context.user_data:
        await withdrawal_handler.handle_withdraw_free_text(update, context)
    else:
        await update.message.reply_text("❌ Invalid command")


async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and attempt to notify the user gracefully."""
    logger.warning(f'Update "{update}" caused error "{context.error}"')
    try:
        await update.message.reply_text('An error occurred. Please try again or contact support.')
    except Exception:
        try:
            await update.callback_query.message.reply_text('An error occurred. Please try again or contact support.')
        except Exception:
            pass
