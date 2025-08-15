from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import (
    settings_reply_keyboard,
    main_reply_keyboard,
    MAIN_MENU_BTN,
)
from bot.messages import (
    msg_settings_menu,
    msg_help_panel,
    msg_support_panel,
    msg_about_panel,
    msg_faq_panel,
)
from bot.utils import format_trx_escaped
from config import DAILY_WITHDRAWAL_LIMIT, MIN_WITHDRAWAL_AMOUNT, TELEGRAM_ADMIN_USERNAME, WITHDRAWAL_FEE_RATE


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown_v2(
        msg_settings_menu(),
        reply_markup=settings_reply_keyboard(),
    )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown_v2(
        msg_help_panel(),
        reply_markup=settings_reply_keyboard(),
    )


async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown_v2(
        msg_support_panel(TELEGRAM_ADMIN_USERNAME),
        reply_markup=settings_reply_keyboard(),
    )


async def handle_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown_v2(
        msg_about_panel(),
        reply_markup=settings_reply_keyboard(),
    )


async def handle_qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    daily = format_trx_escaped(DAILY_WITHDRAWAL_LIMIT)
    minimum = format_trx_escaped(MIN_WITHDRAWAL_AMOUNT)
    fee_percent = f"{int(WITHDRAWAL_FEE_RATE * 100)}%"

    await update.message.reply_markdown_v2(
        msg_faq_panel(daily, minimum, fee_percent),
        reply_markup=settings_reply_keyboard(),
    )


async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown_v2(
        MAIN_MENU_BTN,
        reply_markup=main_reply_keyboard(),
    )
