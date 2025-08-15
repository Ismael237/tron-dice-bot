from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict
from time import monotonic

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.keyboards import (
    main_reply_keyboard,
    game_bet_amounts_inline_keyboard,
    game_confirm_inline_keyboard,
    game_post_result_inline_keyboard,
)
from bot.messages import (
    msg_game_intro,
    msg_invalid_bet_amount,
    msg_enter_target,
    msg_invalid_target_number,
    msg_confirm_bet,
    msg_game_in_progress,
    msg_game_result,
)
from bot.utils import format_trx
from config import MIN_BET_AMOUNT, MAX_BET_AMOUNT
from services.game_service import GameService
from services.user_service import UserService

# Cooldown seconds between confirms to avoid spamming
_COOLDOWN_SECONDS = 2.0


# =============================
# Local state helpers
# =============================

def _play_state(context: ContextTypes.DEFAULT_TYPE) -> Dict:
    return context.user_data.setdefault("play", {})


def _reset_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("play", None)


# =============================
# Helpers
# =============================

def _compute_multiplier(target: int) -> Decimal:
    # Approx multiplier: (1 - house_edge) / chance, where chance = target/100
    if target < 1:
        target = 1
    if target > 100:
        target = 100
    he = Decimal(str(GameService.HOUSE_EDGE))
    chance = Decimal(target) / Decimal(100)
    if chance <= 0:
        chance = Decimal(1) / Decimal(100)
    mult = (Decimal(1) - he) / chance
    return mult.quantize(Decimal("0.01"))


def _potential_win(bet: Decimal, multiplier: Decimal) -> Decimal:
    return (Decimal(bet) * Decimal(multiplier)).quantize(GameService.TRX_PRECISION)


async def _send_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    user = UserService.get_user_by_telegram(telegram_id)
    if not user:
        await update.message.reply_markdown_v2("❌ *You are not registered\\!* Use /start to register\.")
        return
    balance_trx = format_trx(user.account_balance)
    min_bet = format_trx(MIN_BET_AMOUNT)
    max_bet = format_trx(MAX_BET_AMOUNT)
    await update.message.reply_markdown_v2(
        msg_game_intro(balance_trx, min_bet, max_bet),
        reply_markup=game_bet_amounts_inline_keyboard(),
    )


# =============================
# Entry points
# =============================
async def handle_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _reset_state(context)
    state = _play_state(context)
    state["step"] = "amount"
    # intro + amount presets
    await _send_intro(update, context)


# =============================
# Text input routing
# =============================
async def handle_play_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "play" not in context.user_data:
        return
    state = _play_state(context)
    step = state.get("step")
    if step == "amount":
        await _handle_amount_input(update, context, state)
    elif step == "target":
        await _handle_target_input(update, context, state)


async def _handle_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    raw = (update.message.text or "").strip().replace(" TRX", "").replace(",", "")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        await update.message.reply_markdown_v2(
            msg_invalid_bet_amount(format_trx(MIN_BET_AMOUNT), format_trx(MAX_BET_AMOUNT))
        )
        return
    # Bounds check using GameService validation semantics
    try:
        amount = GameService._validate_bet_amount(amount)  # type: ignore[attr-defined]
    except Exception:
        await update.message.reply_markdown_v2(
            msg_invalid_bet_amount(format_trx(MIN_BET_AMOUNT), format_trx(MAX_BET_AMOUNT))
        )
        return

    state["amount"] = amount
    state["target"] = 50  # default
    state["step"] = "target"

    mult = _compute_multiplier(state["target"])
    pot = _potential_win(amount, mult)

    await update.message.reply_markdown_v2(
        msg_confirm_bet(format_trx(amount), state["target"], f"{mult}", format_trx(pot)),
        reply_markup=game_confirm_inline_keyboard(state["target"]),
    )


async def _handle_target_input(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    text = (update.message.text or "").strip()
    try:
        target = int(text)
    except (ValueError, TypeError):
        await update.message.reply_markdown_v2(msg_invalid_target_number())
        return
    if target < 1 or target > 100:
        await update.message.reply_markdown_v2(msg_invalid_target_number())
        return

    state["target"] = target
    amount = Decimal(state.get("amount") or 0)
    mult = _compute_multiplier(target)
    pot = _potential_win(amount, mult)

    await update.message.reply_markdown_v2(
        msg_confirm_bet(format_trx(amount), target, f"{mult}", format_trx(pot)),
        reply_markup=game_confirm_inline_keyboard(target),
    )


# =============================
# Callback handler
# =============================
async def handle_play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    data = query.data or ""

    state = _play_state(context)

    async def _edit(text: str, reply_markup=None):
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
        except Exception:
            # Fallback: send a new message
            await query.message.reply_markdown_v2(text, reply_markup=reply_markup)

    try:
        if data.startswith("play_amt_"):
            # Amount presets: 1,5,10,50,100 or max
            choice = data.split("play_amt_")[-1]
            amt_map = {
                "1": Decimal(1),
                "5": Decimal(5),
                "10": Decimal(10),
                "50": Decimal(50),
                "100": Decimal(100),
            }
            amount: Decimal
            if choice == "max":
                # min(user balance, MAX_BET_AMOUNT)
                user = UserService.get_user_by_telegram(str(update.effective_user.id))
                bal = Decimal(str(getattr(user, "account_balance", 0) or 0)) if user else Decimal(0)
                amount = min(bal, Decimal(str(MAX_BET_AMOUNT)))
                if amount <= 0:
                    await query.answer("Insufficient balance", show_alert=True)
                    return
            else:
                amount = amt_map.get(choice, Decimal(0))

            try:
                amount = GameService._validate_bet_amount(amount)  # type: ignore[attr-defined]
            except Exception:
                await query.answer("Invalid bet amount", show_alert=True)
                return

            state["amount"] = amount
            state["target"] = state.get("target", 50)
            state["step"] = "target"

            mult = _compute_multiplier(state["target"])
            pot = _potential_win(amount, mult)
            await _edit(
                msg_confirm_bet(format_trx(amount), state["target"], f"{mult}", format_trx(pot)),
                reply_markup=game_confirm_inline_keyboard(state["target"]),
            )
            await query.answer()
            return

        if data == "play_inc" or data == "play_dec":
            if state.get("step") != "target":
                await query.answer()
                return
            target = int(state.get("target", 50))
            target = target + (1 if data == "play_inc" else -1)
            if target < 1:
                target = 1
            if target > 100:
                target = 100
            state["target"] = target
            amount = Decimal(state.get("amount") or 0)
            mult = _compute_multiplier(target)
            pot = _potential_win(amount, mult)
            await _edit(
                msg_confirm_bet(format_trx(amount), target, f"{mult}", format_trx(pot)),
                reply_markup=game_confirm_inline_keyboard(target),
            )
            await query.answer()
            return

        if data == "play_confirm":
            # Cooldown check
            now = monotonic()
            last = state.get("last_confirm_ts")
            if last is not None and (now - float(last)) < _COOLDOWN_SECONDS:
                await query.answer("Please wait a moment before betting again", show_alert=True)
                return
            state["last_confirm_ts"] = now

            amount = Decimal(state.get("amount") or 0)
            target = int(state.get("target") or 50)

            # Attempt to play via GameService
            user = UserService.get_user_by_telegram(str(update.effective_user.id))
            if not user:
                await query.answer("Not registered", show_alert=True)
                return

            try:
                outcome = GameService.play(user.id, amount, target)
            except RuntimeError:
                await query.answer("Bet in progress. Please wait.", show_alert=True)
                await query.message.reply_markdown_v2(msg_game_in_progress())
                return
            except ValueError as e:
                await query.answer(str(e)[:120], show_alert=True)
                return
            except Exception as e:
                await query.answer("Unexpected error", show_alert=True)
                # Also tell user in chat
                await query.message.reply_text(f"Error: {e}")
                return

            # Show result
            bet_trx = format_trx(outcome.bet_amount)
            win_trx = format_trx(outcome.win_amount)
            bal_trx = format_trx(outcome.balance_after)
            mult_str = f"{outcome.multiplier}"
            result_msg = msg_game_result(
                outcome.is_winner,
                bet_trx,
                outcome.target_number,
                outcome.result_number,
                mult_str,
                win_trx,
                bal_trx,
            )
            await _edit(result_msg, reply_markup=game_post_result_inline_keyboard())
            # Prepare for replay
            state["step"] = "post"
            state["amount"] = outcome.bet_amount
            state["target"] = outcome.target_number
            await query.answer()
            return

        if data == "play_replay":
            amount = Decimal(state.get("amount") or 0)
            target = int(state.get("target") or 50)
            if amount <= 0:
                await query.answer()
                return
            state["step"] = "target"
            mult = _compute_multiplier(target)
            pot = _potential_win(amount, mult)
            await _edit(
                msg_confirm_bet(format_trx(amount), target, f"{mult}", format_trx(pot)),
                reply_markup=game_confirm_inline_keyboard(target),
            )
            await query.answer()
            return

        if data in {"play_menu", "play_cancel"}:
            _reset_state(context)
            await _edit("🏠 Back to main menu", reply_markup=None)
            # Send main menu keyboard
            await query.message.reply_markdown_v2("Select an option:", reply_markup=main_reply_keyboard())
            await query.answer()
            return

        if data == "noop":
            await query.answer()
            return

    finally:
        # Ensure callback answered in any path not explicitly handled
        try:
            await update.callback_query.answer()
        except Exception:
            pass
