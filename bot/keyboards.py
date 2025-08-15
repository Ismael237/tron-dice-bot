from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from config import TRON_EXPLORER_URL

# ==================== CONSTANTS ====================
# Main Menu Buttons
PLAY_BTN = "🎲 Play"
DEPOSIT_BTN = "💰 Deposit"
BALANCE_BTN = "💳 Balance"
WITHDRAW_BTN = "🏧 Withdraw"
SHARE_EARN_BTN = "👥 Share & Earn"
HISTORY_BTN = "📜 History"
SETTINGS_BTN = "⚙️ Settings"

# Navigation Buttons
MAIN_MENU_BTN = "🏠 Main Menu"
BACK_BTN = "🔙 Back"
CANCEL_BTN = "❌ Cancel"
CANCEL_WITHDRAW_BTN = "❌ Cancel Withdrawal"
CONFIRM_WITHDRAW_BTN = "✅ Confirm Withdrawal"

# Balance Submenu Buttons
VIEW_BALANCE_BTN = "💰 View Balance"
RECENT_ACTIVITY_BTN = "📊 Recent Activity"

# Withdraw Buttons
WITHDRAW_50_BTN = "50 TRX"
WITHDRAW_100_BTN = "100 TRX"
WITHDRAW_500_BTN = "500 TRX"
WITHDRAW_1000_BTN = "1,000 TRX"
WITHDRAW_5000_BTN = "5,000 TRX"

# History Buttons
ALL_TRANSACTIONS_BTN = "📋 All Transactions"
DEPOSITS_ONLY_BTN = "📥 Deposits Only"
WITHDRAWALS_ONLY_BTN = "📤 Withdrawals Only"

# Settings Buttons
HELP_BTN = "❓ Help"
SUPPORT_BTN = "🆘 Support"
ABOUT_BTN = "ℹ️ About"
Q_A_BTN = "🤔 Q&A"
REFERRAL_INFO_BTN = "👥 Referral Info"

# ==================== REPLY KEYBOARDS ====================

def main_reply_keyboard():
    """Main menu keyboard with primary bot functions"""
    keyboard = [
        [PLAY_BTN, BALANCE_BTN],
        [DEPOSIT_BTN, WITHDRAW_BTN],
        [SHARE_EARN_BTN, HISTORY_BTN],
        [SETTINGS_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def withdraw_reply_keyboard():
    """Withdraw submenu with predefined amounts"""
    keyboard = [
        [WITHDRAW_50_BTN],
        [WITHDRAW_100_BTN, WITHDRAW_500_BTN],
        [WITHDRAW_1000_BTN, WITHDRAW_5000_BTN],
        [MAIN_MENU_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def cancel_withdraw_keyboard():
    """Cancel withdrawal keyboard"""
    keyboard = [
        [CANCEL_WITHDRAW_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def history_reply_keyboard():
    """History submenu keyboard"""
    keyboard = [
        [ALL_TRANSACTIONS_BTN],
        [DEPOSITS_ONLY_BTN, WITHDRAWALS_ONLY_BTN],
        [MAIN_MENU_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def settings_reply_keyboard():
    """Settings submenu keyboard"""
    keyboard = [
        [HELP_BTN, SUPPORT_BTN],
        [ABOUT_BTN, Q_A_BTN],
        [REFERRAL_INFO_BTN],
        [MAIN_MENU_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def withdrawal_confirm_reply_keyboard():
    """Reply keyboard for confirming or cancelling a withdrawal"""
    keyboard = [
        [CONFIRM_WITHDRAW_BTN],
        [CANCEL_WITHDRAW_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def withdrawal_confirm_inline_keyboard(amount):
    """Confirmation keyboard for withdrawal"""
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Withdrawal", callback_data=f"confirm_withdraw_{amount}")],
        [InlineKeyboardButton("❌ Cancel Withdrawal", callback_data="cancel_withdraw")]
    ]
    return InlineKeyboardMarkup(keyboard)


def transaction_details_inline_keyboard(tx_hash=None):
    """Inline keyboard for transaction details"""
    keyboard = []
    
    if tx_hash:
        keyboard.append([InlineKeyboardButton("🔍 View on Blockchain", url=f"{TRON_EXPLORER_URL}/#/transaction/{tx_hash}")])
    
    return InlineKeyboardMarkup(keyboard)


def pagination_inline_keyboard(current_page, total_pages, callback_prefix):
    """Generic pagination keyboard"""
    keyboard = []
    
    # Navigation row
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"{callback_prefix}_page_{current_page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="current_page"))
    
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"{callback_prefix}_page_{current_page+1}"))
    
    keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard)


def withdraw_button():
    return InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")


def referral_info_inline_keyboard():
    """Creates an inline keyboard with a button to show referral system info"""
    keyboard = [
        [
            InlineKeyboardButton(
                "❓ How It Works",
                callback_data="referral_info"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== GAME INLINE KEYBOARDS ====================


def game_bet_amounts_inline_keyboard():
    """Inline keyboard for selecting a bet amount quickly."""
    keyboard = [
        [
            InlineKeyboardButton("1 TRX", callback_data="play_amt_1"),
            InlineKeyboardButton("5 TRX", callback_data="play_amt_5"),
            InlineKeyboardButton("10 TRX", callback_data="play_amt_10"),
        ],
        [
            InlineKeyboardButton("50 TRX", callback_data="play_amt_50"),
            InlineKeyboardButton("100 TRX", callback_data="play_amt_100"),
            InlineKeyboardButton("MAX", callback_data="play_amt_max"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="play_cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def game_confirm_inline_keyboard(target: int | None = None):
    """Inline keyboard for confirming bet and adjusting target with +/-."""
    row_ctrl = []
    if target is not None:
        row_ctrl = [
            InlineKeyboardButton("➖", callback_data="play_dec"),
            InlineKeyboardButton(f"🎯 {target}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="play_inc"),
        ]
    keyboard = []
    if row_ctrl:
        keyboard.append(row_ctrl)
    keyboard.append([InlineKeyboardButton("✅ Confirm", callback_data="play_confirm")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="play_cancel")])
    return InlineKeyboardMarkup(keyboard)


def game_post_result_inline_keyboard(game_id: int):
    """Inline keyboard after a game result: replay or go back to menu."""
    keyboard = [
        [InlineKeyboardButton("🔄 Replay", callback_data="play_replay")],
        [InlineKeyboardButton("🏠 Menu", callback_data="play_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== REFERRAL INLINE KEYBOARDS ====================

def referral_overview_inline_keyboard(share_link: str):
    """Inline keyboard for referral overview with share link, history and leaderboard."""
    keyboard = [
        [InlineKeyboardButton("🔗 Share Link", url=share_link)],
        [InlineKeyboardButton("📜 History", callback_data="ref_hist_page_1")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="ref_lb_page_1")],
        [InlineKeyboardButton("❓ Info", callback_data="referral_info")],
    ]
    return InlineKeyboardMarkup(keyboard)