from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.keyboards import (
    main_reply_keyboard,
    history_reply_keyboard,
    pagination_inline_keyboard,
    HISTORY_BTN,
    ALL_TRANSACTIONS_BTN,
    DEPOSITS_ONLY_BTN,
    WITHDRAWALS_ONLY_BTN,
)
from bot.messages import (
    msg_already_registered,
    msg_new_referral,
    msg_welcome_registration,
    msg_not_registered_prompt_start,
    msg_balance,
    msg_select_history_filter,
    msg_no_transactions_for_filter,
    msg_history_page,
    msg_user_not_found,
)
from services.user_service import UserService
from config import ITEMS_PER_PAGE, TELEGRAM_ADMIN_USERNAME
from utils.helpers import escape_markdown_v2


# Exported handlers (registration is done elsewhere)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or "User"
    last_name = update.effective_user.last_name or None

    # if already registered, show main menu
    user = UserService.get_user_by_telegram(telegram_id)
    if user:
        await update.message.reply_markdown_v2(
            msg_already_registered(),
            reply_markup=main_reply_keyboard(),
        )
        return

    # referral from deep-link args
    referral_code = None
    if context.args:
        referral_code = context.args[0]

    # generate unique code for the new user
    code = UserService.generate_unique_referral_code()

    sponsor_id = None
    sponsor_line = ""
    if referral_code and referral_code.lower() != code.lower():
        sponsor = UserService.find_sponsor_by_code(referral_code)
        if sponsor:
            sponsor_id = sponsor.id
            sponsor_line = f"👤 Referred by : {escape_markdown_v2('@' + (sponsor.username or 'User'))}\n"
            # notify sponsor
            await context.bot.send_message(
                sponsor.telegram_id,
                msg_new_referral(
                    sponsor_username='@' + (sponsor.username or 'User'),
                    friend_username='@' + (username or 'this user'),
                ),
                parse_mode=ParseMode.MARKDOWN_V2,
            )

    # create user and wallet
    user = UserService.create_user(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        referral_code=code,
        sponsor_id=sponsor_id,
    )
    wallet = UserService.get_or_create_wallet_for_user(user.id)

    # share link
    share_link = UserService.build_share_link(context.bot.username, code)

    await update.message.reply_markdown_v2(
        msg_welcome_registration(
            username='@' + (username or 'New User'),
            address=wallet.address,
            share_link=share_link,
            support_username='@' + TELEGRAM_ADMIN_USERNAME,
            sponsor_line=sponsor_line,
        ),
        reply_markup=main_reply_keyboard(),
    )


async def handle_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    user = UserService.get_user_by_telegram(telegram_id)
    if not user:
        await update.message.reply_markdown_v2(
            msg_not_registered_prompt_start(),
            reply_markup=main_reply_keyboard(),
        )
        return

    await update.message.reply_markdown_v2(
        msg_balance(
            balance_trx=user.account_balance,
            total_deposited_trx=user.total_deposited,
            total_withdrawn_trx=user.total_withdrawn,
        ),
        reply_markup=main_reply_keyboard(),
    )


async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    user = UserService.get_user_by_telegram(telegram_id)
    if not user:
        await update.message.reply_markdown_v2(
            msg_not_registered_prompt_start(),
            reply_markup=main_reply_keyboard(),
        )
        return

    # Resolve filter
    filter_key = None
    if update.message:
        text = update.message.text
        if text in {HISTORY_BTN, "/history"}:
            await update.message.reply_markdown_v2(
                msg_select_history_filter(),
                reply_markup=history_reply_keyboard(),
            )
            return
        elif text == ALL_TRANSACTIONS_BTN:
            filter_key = "all"
        elif text == DEPOSITS_ONLY_BTN:
            filter_key = "deposits"
        elif text == WITHDRAWALS_ONLY_BTN:
            filter_key = "withdrawals"

    elif "history_filter" in context.user_data:
        filter_key = context.user_data["history_filter"]

    if not filter_key:
        filter_key = "all"
    context.user_data["history_filter"] = filter_key

    # Fetch and display first page
    txs = UserService.list_transactions(user.id, None if filter_key == "all" else filter_key)
    if not txs:
        if update.message:
            await update.message.reply_markdown_v2(
                msg_no_transactions_for_filter(),
                reply_markup=history_reply_keyboard(),
            )
        else:
            await update.callback_query.edit_message_text(
                msg_no_transactions_for_filter(), parse_mode=ParseMode.MARKDOWN_V2
            )
        return

    await _send_transactions_page(update, txs, 1, filter_key)


async def handle_history_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        _, filter_key, _, page_str = query.data.split("_")
        page = int(page_str)
    except (ValueError, IndexError):
        filter_key = "all"
        page = 1

    telegram_id = str(query.from_user.id)
    user = UserService.get_user_by_telegram(telegram_id)
    if not user:
        await query.edit_message_text(msg_user_not_found())
        return

    txs = UserService.list_transactions(user.id, None if filter_key == "all" else filter_key)
    await _send_transactions_page(update, txs, page, filter_key)


# Internal helper for paginated rendering
async def _send_transactions_page(update: Update, transactions, page: int, filter_key: str):
    from math import ceil

    total_pages = max(1, ceil(len(transactions) / ITEMS_PER_PAGE))
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_txs = transactions[start_idx:end_idx]

    text = msg_history_page(page_txs, page, total_pages)
    keyboard = pagination_inline_keyboard(page, total_pages, f"history_{filter_key}")

    if update.message:
        await update.message.reply_markdown_v2(text, reply_markup=keyboard)
    else:
        query = update.callback_query
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)