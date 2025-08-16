from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import (
    DEPOSIT_BTN,
    HISTORY_BTN, HELP_BTN, MAIN_MENU_BTN,
    PLAY_CANCEL_BTN, PLAY_CONFIRM_BTN,
    PLAY_NEW_BET_BTN, PLAY_REPLAY_BTN,
    REFERRAL_INFO_BTN,
    SETTINGS_BTN, SUPPORT_BTN, ABOUT_BTN,
    BALANCE_BTN, WITHDRAW_BTN,
    SHARE_EARN_BTN, CANCEL_WITHDRAW_BTN, CONFIRM_WITHDRAW_BTN,
    Q_A_BTN, ALL_TRANSACTIONS_BTN, DEPOSITS_ONLY_BTN,
    WITHDRAWALS_ONLY_BTN, BETS_ONLY_BTN, PAYOUTS_ONLY_BTN, BONUSES_ONLY_BTN, COMMISSIONS_ONLY_BTN,
    PLAY_BTN,
    ADMIN_BTN,
    PLAY_CHANGE_TARGET_BTN,
    STATS_BTN, CHALLENGES_BTN,
    REF_SHARE_LINK_BTN, REF_HISTORY_BTN, REF_LEADERBOARD_BTN,
    ADMIN_STATS_BTN, ADMIN_USERS_BTN, ADMIN_GAMES_BTN, ADMIN_ALERTS_BTN,
)

from bot.handlers import withdrawal_handler
from bot.handlers import start_handler, settings_handler, deposit_handler, referral_handlers as referral_handler
from bot.handlers import game_handlers
from bot.handlers import admin_handlers
from bot.handlers import challenge_handlers
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
    elif text in {HISTORY_BTN, ALL_TRANSACTIONS_BTN, DEPOSITS_ONLY_BTN, WITHDRAWALS_ONLY_BTN, BETS_ONLY_BTN, PAYOUTS_ONLY_BTN, BONUSES_ONLY_BTN, COMMISSIONS_ONLY_BTN}:
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
    elif text == REF_SHARE_LINK_BTN:
        await referral_handler.handle_referral_share_link(update, context)
    elif text == REF_HISTORY_BTN:
        await referral_handler.handle_referral_history(update, context)
    elif text == REF_LEADERBOARD_BTN:
        await referral_handler.handle_referral_leaderboard(update, context)
    elif text == PLAY_BTN:
        await game_handlers.handle_play(update, context)
    elif text == PLAY_CANCEL_BTN:
        await game_handlers.handle_play_cancel(update, context)
    elif text == PLAY_CONFIRM_BTN:
        await game_handlers.handle_play_confirm(update, context)
    elif text == PLAY_CHANGE_TARGET_BTN:
        await game_handlers.handle_play_change_target(update, context)
    elif text == PLAY_REPLAY_BTN:
        await game_handlers.handle_play_replay(update, context)
    elif text == PLAY_NEW_BET_BTN:
        await game_handlers.handle_play(update, context)
    elif text == STATS_BTN:
        await game_handlers.handle_stats(update, context)
    elif text == CHALLENGES_BTN:
        await challenge_handlers.handle_challenges(update, context)
    elif text == ADMIN_BTN:
        await admin_handlers.handle_admin_main(update, context)
    elif text == ADMIN_STATS_BTN:
        await admin_handlers.handle_admin_stats(update, context)
    elif text == ADMIN_USERS_BTN:
        await admin_handlers.handle_admin_users(update, context)
    elif text == ADMIN_GAMES_BTN:
        await admin_handlers.handle_admin_games(update, context)
    elif text == ADMIN_ALERTS_BTN:
        await admin_handlers.handle_admin_alerts(update, context)
    elif "withdraw" in context.user_data:
        await withdrawal_handler.handle_withdraw_free_text(update, context)
    elif "play" in context.user_data:
        await game_handlers.handle_play_free_text(update, context)
    else:
        msg = "❌ Invalid command\."
        msg += "\n\n"
        msg += "Type /start to see the main menu\."
        await update.message.reply_markdown_v2(msg)


async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and attempt to notify the user gracefully."""
    logger.warning(f'Update "{update}" caused error "{context.error}"')
    msg = "❌ An error occurred\."
    msg += "\n\n"
    msg += "Please try again or contact support\."
    msg += "\n\n"
    msg += "Type /start to see the main menu\."
    try:
        await update.message.reply_markdown_v2(msg)
    except Exception:
        try:
            await update.callback_query.message.reply_markdown_v2(msg)
        except Exception:
            pass
