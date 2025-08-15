
from decimal import Decimal, InvalidOperation
from typing import Dict

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from bot.keyboards import (
    MAIN_MENU_BTN,
    withdraw_reply_keyboard,
    main_reply_keyboard,
    cancel_withdraw_keyboard,
    withdrawal_confirm_reply_keyboard,
    CONFIRM_WITHDRAW_BTN,
    CANCEL_WITHDRAW_BTN,
)
from bot.messages import (
    msg_withdraw_start,
    msg_invalid_amount,
    msg_amount_out_of_bounds,
    msg_insufficient_balance,
    msg_ask_address,
    msg_invalid_address,
    msg_confirm_withdraw,
    msg_daily_limit_exceeded,
    msg_withdraw_submitted,
    msg_withdraw_cancelled,
    msg_session_expired,
)
from bot.utils import escape_markdown_v2, format_trx
from config import DAILY_WITHDRAWAL_LIMIT, MIN_WITHDRAWAL_AMOUNT, WITHDRAWAL_FEE_RATE
from services.withdrawal_service import WithdrawalService


# ==============================
# Local state helpers
# ==============================

def _withdraw_state(context: ContextTypes.DEFAULT_TYPE) -> Dict:
    return context.user_data.setdefault("withdraw", {})


def _reset_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("withdraw", None)


# ==============================
# Entry point
# ==============================
async def handle_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    user = WithdrawalService.get_user_by_telegram(telegram_id)
    if not user:
        await update.message.reply_markdown_v2("❌ *You are not registered\.* Use /start to register\.")
        return

    _reset_state(context)
    state = _withdraw_state(context)
    state["step"] = "amount"

    balance_trx = format_trx(user.account_balance)
    min_trx = format_trx(MIN_WITHDRAWAL_AMOUNT)
    max_trx = format_trx(DAILY_WITHDRAWAL_LIMIT)

    await update.message.reply_markdown_v2(
        msg_withdraw_start(balance_trx, min_trx, max_trx, MAIN_MENU_BTN),
        reply_markup=withdraw_reply_keyboard(),
    )


# ==============================
# Text message handler
# ==============================
async def process_withdraw_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "withdraw" not in context.user_data:
        return

    state = _withdraw_state(context)
    step = state.get("step")

    if step == "amount":
        await _handle_amount_input(update, context, state)
    elif step == "address":
        await _handle_address_input(update, context, state)


async def handle_withdraw_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delegate free-text messages to the appropriate withdraw step handler."""
    if "withdraw" not in context.user_data:
        return

    state = _withdraw_state(context)
    step = state.get("step")
    if step in {"amount", "address"}:
        await process_withdraw_message(update, context)
    elif step == "cancel":
        await cancel_withdraw(update, context)
    elif step == "confirm":
        text = (update.message.text or "").strip()
        if text == CONFIRM_WITHDRAW_BTN:
            await _finalize_withdrawal(update, context, state)
        elif text == CANCEL_WITHDRAW_BTN:
            await cancel_withdraw(update, context)


async def _handle_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    raw = update.message.text.strip().replace(" TRX", "").replace(",", "")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        await update.message.reply_markdown_v2(msg_invalid_amount())
        return

    if not WithdrawalService.validate_amount(amount):
        await update.message.reply_markdown_v2(
            msg_amount_out_of_bounds(format_trx(MIN_WITHDRAWAL_AMOUNT), format_trx(DAILY_WITHDRAWAL_LIMIT))
        )
        return

    user = WithdrawalService.get_user_by_telegram(str(update.effective_user.id))
    if not user or Decimal(user.account_balance) < amount:
        await update.message.reply_markdown_v2(msg_insufficient_balance())
        return

    state["amount"] = amount
    state["step"] = "address"

    fee = (amount * Decimal(str(WITHDRAWAL_FEE_RATE))).quantize(Decimal("0.01"))
    net = amount - fee

    await update.message.reply_markdown_v2(
        msg_ask_address(format_trx(amount), format_trx(net), f"{int(WITHDRAWAL_FEE_RATE * 100)}%"),
        reply_markup=cancel_withdraw_keyboard(),
    )


async def _handle_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    address = update.message.text.strip()
    if not WithdrawalService.validate_address(address):
        await update.message.reply_markdown_v2(msg_invalid_address())
        return

    state["address"] = escape_markdown_v2(address)
    state["step"] = "confirm"
    amount = state["amount"]

    await update.message.reply_markdown_v2(
        msg_confirm_withdraw(format_trx(amount), address),
        reply_markup=withdrawal_confirm_reply_keyboard(),
    )


async def _finalize_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    """Finalize the withdrawal after user confirms via reply keyboard.
    Performs balance checks, daily limit enforcement, creates withdrawal and transaction,
    notifies the user, and resets state.
    """
    amount = state.get("amount")
    address = state.get("address")

    user = WithdrawalService.get_user_by_telegram(str(update.effective_user.id))
    if not user or Decimal(user.account_balance) < amount:
        await update.message.reply_markdown_v2(msg_insufficient_balance())
        _reset_state(context)
        await update.message.reply_markdown_v2(MAIN_MENU_BTN, reply_markup=main_reply_keyboard())
        return

    daily_withdrawals = WithdrawalService.get_daily_withdrawals(user.id)
    total_daily_withdrawn = sum(Decimal(str(w.amount_trx)) for w in daily_withdrawals)
    remaining_limit = Decimal(str(DAILY_WITHDRAWAL_LIMIT)) - Decimal(str(total_daily_withdrawn))

    if amount > remaining_limit:
        await update.message.reply_markdown_v2(
            msg_daily_limit_exceeded(
                format_trx(DAILY_WITHDRAWAL_LIMIT),
                format_trx(total_daily_withdrawn),
                format_trx(remaining_limit),
                format_trx(amount),
            )
        )
        _reset_state(context)
        await update.message.reply_markdown_v2(MAIN_MENU_BTN, reply_markup=main_reply_keyboard())
        return

    withdrawal = WithdrawalService.create_withdrawal(user.id, amount, address)
    WithdrawalService.create_withdrawal_transaction(user.id, amount, withdrawal.id)

    msg = msg_withdraw_submitted(format_trx(amount), format_trx(remaining_limit - amount))
    await update.message.reply_markdown_v2(msg)

    _reset_state(context)
    await update.message.reply_markdown_v2(MAIN_MENU_BTN, reply_markup=main_reply_keyboard())


async def cancel_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        _reset_state(context)
        await update.message.reply_markdown_v2(msg_withdraw_cancelled(), reply_markup=main_reply_keyboard())
        await update.message.reply_markdown_v2(MAIN_MENU_BTN, reply_markup=main_reply_keyboard())
        return

    await query.answer()
    _reset_state(context)
    await query.edit_message_text(msg_withdraw_cancelled(), parse_mode=ParseMode.MARKDOWN_V2)
    await query.message.reply_markdown_v2(MAIN_MENU_BTN, reply_markup=main_reply_keyboard())
