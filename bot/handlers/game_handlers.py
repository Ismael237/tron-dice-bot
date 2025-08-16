from __future__ import annotations

from decimal import ROUND_DOWN, Decimal, InvalidOperation
from typing import Dict
from time import monotonic
import asyncio
from sqlalchemy import func

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.keyboards import (
    main_reply_keyboard,
    game_bet_amounts_reply_keyboard,
    game_confirm_reply_keyboard,
    game_post_result_reply_keyboard,
    game_target_presets_reply_keyboard,
    deposit_prompt_reply_keyboard,
    BET_1_TRX_BTN, BET_5_TRX_BTN, BET_10_TRX_BTN, BET_50_TRX_BTN, BET_100_TRX_BTN, BET_MAX_BTN,
    PLAY_CONFIRM_BTN, PLAY_CANCEL_BTN, PLAY_REPLAY_BTN, PLAY_MENU_BTN, PLAY_CHANGE_TARGET_BTN,
)
from bot.messages import (
    msg_play_intro,
    msg_invalid_bet_amount_play,
    msg_invalid_target_number,
    msg_confirm_bet,
    msg_bet_in_progress,
    msg_game_result,
    msg_enter_target_number,
    msg_play_cancelled,
    msg_insufficient_balance_play,
    msg_user_stats,
)
from bot.utils import format_trx
from config import MIN_BET_AMOUNT, MAX_BET_AMOUNT
from services.game_service import GameService
from services.user_service import UserService
from utils.logger import logger
from database.database import get_db_session
from database.models import Game

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

    house_edge = Decimal(str(GameService.HOUSE_EDGE))

    chance = (Decimal(101) - Decimal(target)) / Decimal(100)

    if chance <= 0:
        chance = Decimal(1) / Decimal(100)  # min chance

    multiplier = (Decimal(1) / chance) * (Decimal(1) - house_edge)
    return multiplier.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    

def _potential_win(bet: Decimal, multiplier: Decimal) -> Decimal:
    return (bet * multiplier).quantize(GameService.TRX_PRECISION, rounding=ROUND_DOWN)


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
        msg_play_intro(balance_trx, min_bet, max_bet),
        reply_markup=game_bet_amounts_reply_keyboard(),
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


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all-time user stats with win rate and aggregates."""
    user = UserService.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await update.message.reply_markdown_v2("❌ *You are not registered\!* Use /start to register.", reply_markup=main_reply_keyboard())
        return
    # Aggregate totals from Game table
    with get_db_session() as session:
        totals = session.query(
            func.coalesce(func.sum(Game.bet_amount), 0),
            func.coalesce(func.sum(Game.win_amount), 0),
        ).filter(Game.user_id == user.id).one()
        total_wagered = Decimal(str(totals[0] or 0))
        total_won = Decimal(str(totals[1] or 0))

    text = msg_user_stats(
        balance=Decimal(str(user.account_balance or 0)),
        games_played=int(user.total_games_played or 0),
        games_won=int(user.total_games_won or 0),
        biggest_win=Decimal(str(user.biggest_win or 0)),
        biggest_loss=Decimal(str(user.biggest_loss or 0)),
        total_wagered=total_wagered,
        total_won=total_won,
    )
    await update.message.reply_markdown_v2(text, reply_markup=main_reply_keyboard())


# =============================
# Text input routing
# =============================
async def handle_play_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "play" not in context.user_data:
        return
    state = _play_state(context)
    step = state.get("step")

    # Global cancel available in any step
    if (update.message.text or "").strip() == PLAY_CANCEL_BTN:
        _reset_state(context)
        await update.message.reply_markdown_v2(
            msg_play_cancelled(), reply_markup=main_reply_keyboard()
        )
        return

    if step == "amount":
        await _handle_amount_input(update, context, state)
    elif step == "target":
        await _handle_target_input(update, context, state)
    elif step == "confirm":
        await _handle_confirm_input(update, context, state)
    elif step == "post":
        await _handle_post_input(update, context, state)


async def _resolve_amount_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Decimal | None:
    """Map reply buttons or custom numeric text to a Decimal amount.
    Returns None if cannot parse.
    """
    text = (update.message.text or "").strip()
    # Button shortcuts
    preset_map = {
        BET_1_TRX_BTN: Decimal(1),
        BET_5_TRX_BTN: Decimal(5),
        BET_10_TRX_BTN: Decimal(10),
        BET_50_TRX_BTN: Decimal(50),
        BET_100_TRX_BTN: Decimal(100),
    }
    if text in preset_map:
        return preset_map[text]
    if text == BET_MAX_BTN:
        user = UserService.get_user_by_telegram(str(update.effective_user.id))
        bal = Decimal(str(getattr(user, "account_balance", 0) or 0)) if user else Decimal(0)
        return min(bal, Decimal(str(MAX_BET_AMOUNT)))

    # Custom numeric (accepts forms like "10", "10 TRX", "1,000 TRX")
    raw = text.replace(" TRX", "").replace(",", "")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


async def _handle_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    amount = await _resolve_amount_from_text(update, context)
    if amount is None:
        await update.message.reply_markdown_v2(
            msg_invalid_bet_amount_play(), reply_markup=game_bet_amounts_reply_keyboard()
        )
        return

    # Bounds check using GameService validation semantics
    try:
        amount = GameService._validate_bet_amount(amount)  # type: ignore[attr-defined]
    except Exception:
        await update.message.reply_markdown_v2(
            msg_invalid_bet_amount_play(), reply_markup=game_bet_amounts_reply_keyboard()
        )
        return

    # Balance check
    user = UserService.get_user_by_telegram(str(update.effective_user.id))
    balance = Decimal(str(getattr(user, "account_balance", 0) or 0)) if user else Decimal(0)
    if balance < amount:
        await update.message.reply_markdown_v2(
            msg_insufficient_balance_play(format_trx(balance), format_trx(amount)),
            reply_markup=deposit_prompt_reply_keyboard(),
        )
        # Keep step as 'amount' so user can pick a smaller bet or deposit
        state["step"] = "amount"
        return

    state["amount"] = amount
    state["step"] = "target"

    await update.message.reply_markdown_v2(
        msg_enter_target_number(format_trx(amount)),
        reply_markup=game_target_presets_reply_keyboard(),
    )


async def _handle_target_input(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    text = (update.message.text or "").strip()
    try:
        target = int(text)
    except (ValueError, TypeError):
        await update.message.reply_markdown_v2(msg_invalid_target_number(), reply_markup=game_target_presets_reply_keyboard())
        return
    if target < 1 or target > 100:
        await update.message.reply_markdown_v2(msg_invalid_target_number(), reply_markup=game_target_presets_reply_keyboard())
        return

    state["target"] = target
    state["step"] = "confirm"

    amount = Decimal(state.get("amount") or 0)
    mult = _compute_multiplier(target)
    pot = _potential_win(amount, mult)

    await update.message.reply_markdown_v2(
        msg_confirm_bet(format_trx(amount), target, f"{mult}", format_trx(pot)),
        reply_markup=game_confirm_reply_keyboard(),
    )


async def _handle_confirm_input(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    text = (update.message.text or "").strip()
    if text == PLAY_CHANGE_TARGET_BTN:
        # Go back to target selection
        state["step"] = "target"
        amount = Decimal(state.get("amount") or 0)
        await update.message.reply_markdown_v2(
            msg_enter_target_number(format_trx(amount)),
            reply_markup=game_target_presets_reply_keyboard(),
        )
        return
    if text != PLAY_CONFIRM_BTN:
        # re-render confirm
        amount = Decimal(state.get("amount") or 0)
        target = int(state.get("target") or 50)
        mult = _compute_multiplier(target)
        pot = _potential_win(amount, mult)
        await update.message.reply_markdown_v2(
            msg_confirm_bet(format_trx(amount), target, f"{mult}", format_trx(pot)),
            reply_markup=game_confirm_reply_keyboard(),
        )
        return

    # Cooldown check
    now = monotonic()
    last = state.get("last_confirm_ts")
    if last is not None and (now - float(last)) < _COOLDOWN_SECONDS:
        await update.message.reply_markdown_v2(msg_bet_in_progress())
        return
    state["last_confirm_ts"] = now

    amount = Decimal(state.get("amount") or 0)
    target = int(state.get("target") or 50)

    # Attempt to play via GameService
    user = UserService.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("Not registered")
        return
    try:
        outcome = GameService.play(user.id, amount, target)
    except RuntimeError:
        await update.message.reply_markdown_v2(msg_bet_in_progress())
        return
    except ValueError as e:
        await update.message.reply_text(str(e))
        return
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
        return

    # Send dice animation for UX before showing actual result
    try:
        dice = await update.message.reply_dice(emoji="🎲", reply_markup=game_post_result_reply_keyboard())
        # Also send a placeholder text we will edit into the result
        placeholder = await update.message.reply_markdown_v2("_🎲 Rolling dice\.\.\._")
        # Short pause to let the animation play a bit
        await asyncio.sleep(3.5)
    except Exception as e:
        logger.info(f"Failed to send dice animation: {e}")
        dice = None
        placeholder = None

    # Show result
    result_msg = msg_game_result(
        outcome.game_id,
        outcome.is_winner,
        outcome.bet_amount,
        outcome.win_amount,
        outcome.target_number,
        outcome.result_number,
        outcome.multiplier,
        outcome.balance_after,
    )
    try:
        if placeholder:
            await placeholder.edit_text(result_msg, parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await update.message.reply_markdown_v2(result_msg, reply_markup=game_post_result_reply_keyboard())
    except Exception as e:
        logger.info(f"Failed to send result message: {e}")
        await update.message.reply_markdown_v2(result_msg, reply_markup=game_post_result_reply_keyboard())

    # Prepare for replay
    state["step"] = "post"
    state["amount"] = outcome.bet_amount
    state["target"] = outcome.target_number


async def _handle_post_input(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    text = (update.message.text or "").strip()
    if text == PLAY_REPLAY_BTN:
        # Reuse same amount/target
        amount = Decimal(state.get("amount") or 0)
        target = int(state.get("target") or 50)
        if amount <= 0:
            state["step"] = "amount"
            await _send_intro(update, context)
            return
        state["step"] = "confirm"
        mult = _compute_multiplier(target)
        pot = _potential_win(amount, mult)
        await update.message.reply_markdown_v2(
            msg_confirm_bet(format_trx(amount), target, f"{mult}", format_trx(pot)),
            reply_markup=game_confirm_reply_keyboard(),
        )
        return
    if text == PLAY_MENU_BTN:
        _reset_state(context)
        await update.message.reply_markdown_v2("🏠 Back to main menu", reply_markup=main_reply_keyboard())
        return

    # Default: keep post keyboard
    await update.message.reply_text("Choose an option:", reply_markup=game_post_result_reply_keyboard())


# =============================
# Dedicated button handlers (mirror withdrawal flow)
# =============================
async def handle_play_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explicit cancel handler triggered by PLAY_CANCEL_BTN."""
    _reset_state(context)
    await update.message.reply_markdown_v2(
        msg_play_cancelled(), reply_markup=main_reply_keyboard()
    )


async def handle_play_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explicit confirm handler triggered by PLAY_CONFIRM_BTN."""
    if "play" not in context.user_data:
        return
    state = _play_state(context)
    # Delegate to confirm step logic (reads the message text which equals PLAY_CONFIRM_BTN)
    await _handle_confirm_input(update, context, state)


async def handle_play_change_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explicit handler triggered by PLAY_CHANGE_TARGET_BTN to go back to target selection."""
    if "play" not in context.user_data:
        return
    state = _play_state(context)
    state["step"] = "target"
    amount = Decimal(state.get("amount") or 0)
    await update.message.reply_markdown_v2(
        msg_enter_target_number(format_trx(amount)),
        reply_markup=game_target_presets_reply_keyboard(),
    )


async def handle_play_replay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explicit replay handler triggered by PLAY_REPLAY_BTN."""
    state = _play_state(context)
    # Delegate to post step logic (reads the message text which equals PLAY_REPLAY_BTN)
    await _handle_post_input(update, context, state)


# =============================
# Callback handler (legacy, kept for compatibility if referenced elsewhere)
# =============================
async def handle_play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # No longer used: flow is now based on ReplyKeyboard and free-text handling.
    query = update.callback_query
    if query:
        try:
            await query.answer("Use the menu buttons below.")
        except Exception:
            pass
