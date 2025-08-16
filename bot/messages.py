from decimal import Decimal
from config import TELEGRAM_ADMIN_USERNAME
from utils.helpers import escape_markdown_v2, get_separator
from bot.utils import format_trx, format_date, format_trx_escaped

# Types for hints (light typing)
try:
    from database.models import ReferralCommission
except Exception:  # pragma: no cover
    ReferralCommission = object  # fallback for typing in isolated context

# Message builders (return MarkdownV2 strings)

def msg_already_registered() -> str:
    sep = get_separator()
    return (
        "⚠️ *You are already registered\\!* ⚠️\n"
        f"{sep}\n\n"
        "🎯 *Available actions \\:*\n\n"
        "💰 Use /balance to check your balance\n"
        "🏦 Type /deposit to see your deposit address\n"
        "👥 Use /referral for your referral code\n\n"
        f"{sep}\n"
        "🚀 *Ready\\?* Start now \\!"
    )

# ============================ WITHDRAWAL MESSAGES ============================

def msg_withdraw_start(balance_trx: str, min_withdrawal: str, daily_limit: str, main_menu_btn: str) -> str:
    return (
        f"💸 *Your current balance\\:* \n"
        f"\\({escape_markdown_v2(balance_trx)}\\)\n\n"
        f"💳 *How much do you want to withdraw?*\n"
        f"• Choose an option below\n"
        f"• Or enter a custom amount \\(min {escape_markdown_v2(min_withdrawal)}, max {escape_markdown_v2(daily_limit)}\\)\n"
        f"• Type {escape_markdown_v2(main_menu_btn)} to cancel the operation\n\n"
    )


def msg_invalid_amount() -> str:
    return r"❌ *Invalid amount\.* Please enter a numeric value\."


def msg_amount_out_of_bounds(min_withdrawal: str, daily_limit: str) -> str:
    return (
        "❗ Amount must be between "
        f"{escape_markdown_v2(min_withdrawal)} and {escape_markdown_v2(daily_limit)}\\."
    )


def msg_insufficient_balance() -> str:
    return r"❌ *Insufficient balance\.*"


def msg_ask_address(amount_trx: str, net_amount_trx: str, fee_percent: str) -> str:
    return (
        f"✉️ *Enter your TRON address*\n\n"
        f"• Amount\\: {escape_markdown_v2(amount_trx)}\n"
        f"• Fee\\: {escape_markdown_v2(fee_percent)}\n"
        f"• Net\\: {escape_markdown_v2(net_amount_trx)}\n"
    )


def msg_invalid_address() -> str:
    return r"❌ *Invalid TRON address\.* Please enter a valid address\."


def msg_confirm_withdraw(amount_trx: str, address: str) -> str:
    addr = escape_markdown_v2(address)
    return (
        "⚠️ *Confirm withdrawal*\n\n"
        f"💸 *Withdraw {escape_markdown_v2(amount_trx)} to\\:*\n"
        f"`{addr}`"
    )


def msg_daily_limit_exceeded(daily_limit: str, withdrawn: str, remaining: str, requested: str) -> str:
    return (
        "❌ *Daily withdrawal limit exceeded\\!*\n\n"
        f"• Daily limit\\: {escape_markdown_v2(daily_limit)}\n"
        f"• Already withdrawn today\\: {escape_markdown_v2(withdrawn)}\n"
        f"• Remaining limit\\: {escape_markdown_v2(remaining)}\n"
        f"• Requested amount\\: {escape_markdown_v2(requested)}\n\n"
    )


def msg_withdraw_submitted(amount_trx: str, remaining_limit_trx: str) -> str:
    return (
        "✅ *Withdrawal request submitted successfully\\!*\n\n"
        f"• Amount\\: {escape_markdown_v2(amount_trx)}\n"
        f"• Daily limit remaining\\: {escape_markdown_v2(remaining_limit_trx)}\n\n"
        "Please wait for the funds to be sent to your TRON address\\."
    )


def msg_withdraw_cancelled() -> str:
    return "❌ *Withdrawal cancelled\\.*"


def msg_session_expired() -> str:
    return "❌ *Withdrawal session expired\\.*"

# Worker notifications for withdrawal processing
def msg_withdrawal_processed(amount_trx: Decimal, tx_id: str) -> str:
    amount_trx = format_trx_escaped(amount_trx)
    return (
        f"✅ *Withdrawal of {amount_trx} processed successfully\\.*\n"
        f"TX\\: `{escape_markdown_v2(tx_id)}`"
    )


def msg_withdrawal_failed(amount_trx: Decimal, error: str, tx_id: str | None = None) -> str:
    amount_trx = format_trx_escaped(amount_trx)
    msg = f"❌ *Withdrawal of {amount_trx} failed\\.*\n"
    if tx_id:
        msg += f"TX\\: `{escape_markdown_v2(tx_id)}`\n"
    msg += f"Error\\: {escape_markdown_v2(error)}\n"
    return msg


def msg_withdrawal_failed_insufficient_balance(amount_trx: Decimal) -> str:
    amount_trx = format_trx_escaped(amount_trx)
    return (
        f"❌ *Withdrawal of {amount_trx} failed\\.*\n"
        f"Insufficient balance\\.\n"
    )

# ============================ DEPOSIT MESSAGES ============================

def msg_deposit_not_registered() -> str:
    return (
        "❌ *You are not registered yet\\!*\n\n"
        "Please use /start to register and get your deposit address\\."
    )


def msg_deposit_wallet_not_found() -> str:
    return (
        "⚠️ *Wallet not found\\!*\n\n"
        "Please contact support to get your deposit address\\.\n"
        "Use /support for assistance\\."
    )


def msg_deposit_panel(address: str) -> str:
    sep = get_separator()
    addr = escape_markdown_v2(address)
    return (
        "🏦 *DEPOSIT TRX*\n"
        f"{sep}\n\n"
        "Send TRX to your personal address below\\:\n\n"
        f"`{addr}`\n\n"
        "• Only send TRX to this address\n"
        "• Minimum deposit: 1 TRX\n"
        "• Funds are credited after confirmations\n"
    )


def msg_deposit_confirmed(amount_trx: Decimal, tx_id: str) -> str:
    amount_trx = format_trx_escaped(amount_trx)
    return (
        f"💰 *Deposit of {amount_trx} confirmed*\\.\n"
        f"TX\\: `{escape_markdown_v2(tx_id)}`"
    )


def msg_deposit_failed(amount_trx: Decimal, error: str) -> str:
    amount_trx = format_trx_escaped(amount_trx)
    return (
        f"❌ *Deposit of {amount_trx} failed*\\.\n"
        f"Error\\: {escape_markdown_v2(error)}"
    )


def msg_deposit_forwarded(amount_trx: Decimal, deposit_tx_id: str, tx_id: str) -> str:
    amount_trx = format_trx_escaped(amount_trx)
    return (
        f"✅ *Forwarded {amount_trx}\\.*\n"
        f"From deposit\\:\n\n"
        f"`{escape_markdown_v2(deposit_tx_id)}`\n\n"
        f"to main wallet\\.\n\n"
        f"TX\\: `{escape_markdown_v2(tx_id)}`"
    )


def msg_deposit_forward_failed(amount_trx: Decimal, deposit_tx_id: str, error: str) -> str:
    amount_trx = format_trx_escaped(amount_trx)
    return (
        f"❌ *{amount_trx} from deposit {escape_markdown_v2(deposit_tx_id)} to main wallet failed*\\.\n"
        f"Error\\: {escape_markdown_v2(error)}"
    )


def msg_new_referral(sponsor_username: str, friend_username: str) -> str:
    friend_username_esc = escape_markdown_v2(friend_username)
    return (
        "🎉 *You got a new referral\\!* 🎉\n"
        f"Your friend, {friend_username_esc}, has joined the bot \\!\n"
    )


def msg_welcome_registration(
    username: str,
    address: str,
    share_link: str,
    support_username: str | None = None,
    sponsor_line: str | None = None,
) -> str:
    sep = get_separator()
    escaped_address = escape_markdown_v2(address)
    escaped_username = escape_markdown_v2(username)
    support_username = support_username or f"@{TELEGRAM_ADMIN_USERNAME}"
    escaped_support_username = escape_markdown_v2(support_username)
    escaped_share_link = escape_markdown_v2(share_link)

    return (
        "🎉 *WELCOME TO THE TRON BOT \\!* 🎉\n"
        f"{sep}\n\n"
        f"👋 Hi {escaped_username} \\!\n"
        f"✅ Registration successful \\!\n\n"
        "🏦 *YOUR WALLET*\n"
        f"{sep}\n\n"
        "💰 *TRON Deposit Address \\:*\n"
        f"`{escaped_address}`\n\n"
        "👥 *REFERRAL LINK*\n"
        f"{sep}\n\n"
        f"📤 *Your referral link\\(click to copy\\)\\:*\n\n"
        f"`{escaped_share_link}`\n\n"
        "💡 Share it to earn commissions \\!\n"
        f"{sponsor_line or ''}\n"
        "🚀 *START*\n"
        f"{sep}\n\n"
        "📋 *Next Steps \\:*\n\n"
        "1️⃣ Deposit TRON \\(TRX\\) to your address\n"
        "2️⃣ Use /balance to check your balance\n"
        "4️⃣ Start earning profits \\!\n"
        f"{sep}\n"
        "💬 *Useful Commands :*\n\n"
        "• /deposit \\- See your deposit address\n"
        "• /balance \\- Check your balance\n"
        "• /referral \\- Referral system\n"
        "• /help \\- Help and support\n\n"
        "🎯 *Ready to start \\?*\n"
        f"📞 Support \\: {escaped_support_username}"
    )


def msg_not_registered_prompt_start() -> str:
    return "\u2757 *You are not registered\\.* Use /start to register\\."


def msg_user_not_found() -> str:
    return "User not found\\."


def msg_balance(
    balance_trx: Decimal,
    total_deposited_trx: Decimal,
    total_withdrawn_trx: Decimal,
) -> str:
    balance_trx_esc = format_trx_escaped(balance_trx)
    total_deposited_trx_esc = format_trx_escaped(total_deposited_trx)
    total_withdrawn_trx_esc = format_trx_escaped(total_withdrawn_trx)
    sep = get_separator()
    return (
        "💰 *Your TRX Balance*\n"
        f"{sep}\n"
        f"💵 *Balance*\\: `{balance_trx_esc}`\n"
        f"{sep}\n"
        f"💳 *Total Deposited*\\: `{total_deposited_trx_esc}`\n"
        f"🏧 *Total Withdrawn*\\: `{total_withdrawn_trx_esc}`\n"
    )


def msg_select_history_filter() -> str:
    return escape_markdown_v2("Select a transaction filter:")


def msg_no_transactions_for_filter() -> str:
    return "\u2139 _No transactions found for this filter\\._"


def msg_history_page(transactions, page: int, total_pages: int) -> str:
    sep = get_separator()
    lines = [
        f"📝 *Transaction History* \\(Page {page}/{total_pages}\\)\n",
        f"{sep}\n",
    ]

    emoji_map = {
        "deposit": "➕",
        "withdrawal": "➖",
        "bet": "🎲",
        "payout": "🏆",
        "bonus": "✨",
        "referral_commission": "🎁",
    }
    type_name_map = {
        "deposit": "Deposit",
        "withdrawal": "Withdrawal",
        "bet": "Bet",
        "payout": "Payout",
        "bonus": "Bonus",
        "referral_commission": "Commission",
    }
    status_emoji = {
        "pending": "⏳",
        "completed": "✅",
        "failed": "❌",
        "paid": "💰",
    }

    for tx in transactions:
        type_key = getattr(getattr(tx, 'type', None), 'value', str(getattr(tx, 'type', ''))).lower()
        status_key = getattr(getattr(tx, 'status', None), 'value', str(getattr(tx, 'status', ''))).lower()
        type_emoji = emoji_map.get(type_key, "🔹")
        type_label = type_name_map.get(type_key, getattr(getattr(tx, 'type', None), 'value', ''))
        stat_emoji = status_emoji.get(status_key, "🔸")
        lines.extend([
            f"  {type_emoji} *Type*\: {escape_markdown_v2(type_label)}\n",
            f"  📅 *Date*\: `{escape_markdown_v2(format_date(tx.created_at))}`\n",
            f"  💵 *Amount*\: {format_trx_escaped(tx.amount_trx)}\n",
            f"  {stat_emoji} *Status*\: _{escape_markdown_v2(getattr(getattr(tx, 'status', None), 'value', ''))}_\n",
            f"{sep}\n",
        ])

    return "".join(lines)

# ============================ SETTINGS / HELP MESSAGES ============================

def msg_settings_menu() -> str:
    sep = get_separator()
    return (
        "⚙️ *BOT SETTINGS*\n"
        f"{sep}\n\n"
        "🤖 *Need help?*\n"
        "• 🗒️ Guide & Commands\n"
        "• 🆘 Support\n"
        "• ℹ️ About the Bot\n"
        "• ❓ FAQ\n\n"
        "👇 _Select an option from the menu below:_\n"
    )


def msg_help_panel() -> str:
    sep = get_separator()
    return (
        "🤖 *TRON Investment Bot — Help Center*\n"
        f"{sep}\n\n"
        "📋 *Commands Overview*\n\n"
        "• /start — Register\n"
        "• /deposit — Show your personal TRX deposit address\n"
        "• /balance — Check your wallet balance\n"
        "• /withdraw — Request a withdrawal\n"
        "• /referral — View referral stats & link\n"
        "• /history — See transaction history\n"
        "• /help — Display this help panel\n\n"
        "💡 *Tip\\:* You can always tap the menu buttons if you prefer the graphical interface\\.\n"
    )


def msg_support_panel(admin_username: str | None) -> str:
    sep = get_separator()
    u = admin_username or TELEGRAM_ADMIN_USERNAME or "admin"
    
    return (
        "🆘 *SUPPORT DESK*\n"
        f"{sep}\n\n"
        "Got stuck or spotted a bug ? Our team is here to help\\!\n\n"
        f"📞 *Contact\\:* @{escape_markdown_v2(u)}\n"
        f"⏱️ We reply within *24h* \\({escape_markdown_v2('usually faster')}\\)\n\n"
        "When messaging, please include your *Telegram ID* and a short description of the issue 🙏\n"
    )


def msg_about_panel() -> str:
    sep = get_separator()
    return (
        "ℹ️ *ABOUT THIS BOT*\n"
        f"{sep}\n\n"
        "Welcome to this Telegram bot \\- a powerful tool for interacting with the TRON blockchain\\!\n\n"
        "🔍 *Transparent* — Every transaction is visible on the blockchain\\.\n"
        "💻 *Feature\\-rich* — Enjoy a growing set of features and commands\\.\n"
        "👥 *Share & Earn* — Refer friends and earn rewards\\.\n"
    )


def msg_faq_panel(daily_withdrawal_limit: str, min_withdrawal: str, withdrawal_fee_rate_percent: str) -> str:
    sep = get_separator()
    min_withdrawal = escape_markdown_v2(min_withdrawal)
    daily_withdrawal_limit = escape_markdown_v2(daily_withdrawal_limit)
    withdrawal_fee_rate_percent = escape_markdown_v2(withdrawal_fee_rate_percent)
    return (
        "❓ *FREQUENTLY ASKED QUESTIONS*\n"
        f"{sep}\n\n"
        "*Q\\:* How do I deposit TRX\\?\n"
        "*A\\:* Use the /deposit command to get your personal TRX address\\.\n"
        "• Minimum deposit\\: 1 TRX\n"
        "• Processing time\\: 1\\-3 minutes\n"
        "• Only send TRX to this address\n"
        "• Double\\-check the address before sending\n\n"

        "*Q\\:* What are the fees\\?\n"
        "*A\\:*\n"
        "• Deposits: Free\n"
        f"• Withdrawals: {withdrawal_fee_rate_percent} network fee and platform commission\n"
        f"• Minimum withdrawal\\: {min_withdrawal}\n"
        f"• Daily withdrawal limit\\: {daily_withdrawal_limit}\n\n"

        "*Q\\:* How do I withdraw my funds\\?\n"
        "*A\\:* Use the /withdraw command to\\:\n"
        f"• Enter amount \\({min_withdrawal}, max {daily_withdrawal_limit}\\)\n"
        "• Provide your TRX address\n"
        "• Confirm withdrawal\n"
        "• Processing time\\: 1\\-3 minutes\n\n"

        "*Q\\:* How do I check my balance\\?\n"
        "*A\\:* Use the /balance command to view\\:\n"
        "• Current account balance\n"
        "• Total earned\n"
        "• Investment status\n\n"

        "*Q\\:* How do I get my referral code\\?\n"
        "*A\\:* Use the /referral command to\\:\n"
        "• Get your unique referral code\n"
        "• Share your referral link\n"
        "• Track your referrals\n\n"

        "*Q\\:* How do I check my transaction history\\?\n"
        "*A\\:* Use the /history command to view\\:\n"
        "• All transactions\n"
        "• Deposits\n"
        "• Withdrawals\n\n"

        "*Q\\:* What should I do if I need help\\?\n"
        "*A\\:* Use the /support command to\\:\n"
        "• Contact support team\n"
        "• Report issues\n"
        "• Get assistance\n\n"
    )

# ============================ REFERRAL MESSAGES ============================

def msg_referral_overview(
    referral_code: str,
    share_link: str,
    total_referrals: str,
    total_paid_trx: str,
    total_pending_trx: str,
) -> str:
    sep = get_separator()
    return (
        "👥 *REFERRAL OVERVIEW*\n"
        f"{sep}\n\n"
        "🔗 *Your Code*\n"
        f"`{escape_markdown_v2(referral_code)}`\n\n"
        "📤 *Share Link*\n"
        f"`{escape_markdown_v2(share_link)}`\n\n"
        "📈 *Stats*\n"
        f"• Referrals\\: {escape_markdown_v2(total_referrals)}\n"
        f"• Earned\\: {escape_markdown_v2(total_paid_trx)}\n"
        f"• Pending\\: {escape_markdown_v2(total_pending_trx)}\n"
    )


def msg_referral_info_single_level(rate_percent: str) -> str:
    sep = get_separator()
    return (
        "🌟 *REFERRAL PROGRAM*\n"
        f"{sep}\n\n"
        "You earn a commission from direct referrals\\!\n\n"
        "📊 *Commission*\n"
        f"• Direct referrals\\: `{escape_markdown_v2(rate_percent)}%`\n\n"
        "💡 Share your code and link to start earning\\!"
    )


def msg_referral_history_page(rows: list[ReferralCommission], page: int, total_pages: int) -> str:
    """Render a page of referral commissions history."""
    sep = get_separator()
    lines = [
        f"👥 *Referral Commissions* \\(Page {page}/{total_pages}\\)\n",
        f"{sep}\n",
    ]
    if not rows:
        lines.append("_No commissions yet\._\n")
        return "".join(lines)
    for c in rows:
        status = getattr(getattr(c, 'status', None), 'value', str(getattr(c, 'status', '')))
        lines.extend([
            f"• 👤 From user\: `{escape_markdown_v2(str(getattr(c, 'referred_user_id', '-')))}" + "`\n",
            f"  💵 Amount\: {format_trx_escaped(getattr(c, 'amount_trx', Decimal(0)))}\n",
            f"  📅 Date\: `{escape_markdown_v2(format_date(getattr(c, 'created_at', None)))}`\n",
            f"  🏷️ Status\: _{escape_markdown_v2(status)}_\n",
            f"{sep}\n",
        ])
    return "".join(lines)


def msg_referral_leaderboard_page(rows: list[dict], page: int, total_pages: int) -> str:
    """Render a leaderboard page for referral earnings."""
    sep = get_separator()
    lines = [
        f"🏆 *Referral Leaderboard* \\(Page {page}/{total_pages}\\)\n",
        f"{sep}\n",
    ]
    if not rows:
        lines.append("_No entries yet\._\n")
        return "".join(lines)
    rank = (page - 1) * 5 + 1
    for r in rows:
        username = f"@{r.get('username')}" if r.get('username') else r.get('first_name') or f"User {r.get('user_id')}"
        total = r.get('total', 0.0)
        lines.append(
            f"\\#{rank}\\. {escape_markdown_v2(str(username))} — {format_trx_escaped(Decimal(str(total)))}\n"
        )
        rank += 1
    return "".join(lines)

# ============================ GAME MESSAGES ============================

def msg_play_intro(balance_trx: str, min_bet: str, max_bet: str) -> str:
    sep = get_separator()
    return (
        "🎲 *DICE GAME*\n"
        f"{sep}\n\n"
        "Place your bet and pick a target number between 1 and 100\!\n\n"
        f"💳 Balance\: {escape_markdown_v2(balance_trx)}\n"
        f"🔻 Min bet\: {escape_markdown_v2(min_bet)}\n"
        f"🔺 Max bet\: {escape_markdown_v2(max_bet)}\n\n"
        "Select a preset amount below or type a custom amount, then send your target number\."
    )


def msg_invalid_bet_amount_play() -> str:
    return "❌ *Invalid bet amount\\.* Please enter a numeric value within limits\\."


def msg_enter_target_number(amount_trx: str) -> str:
    return (
        "🎯 *Enter your target number*\n\n"
        f"Bet\: {escape_markdown_v2(amount_trx)}\n"
        "Range\: 1\-100\n"
        "Tip\: Higher target \= bigger multiplier but lower win chance\."
    )


def msg_invalid_target_number() -> str:
    return "❌ *Invalid target\\.* Please type an integer between 1 and 100\\."


def msg_confirm_bet(bet_amount: str, target_number: str, multiplier: str, potential_win: str) -> str:
    sep = get_separator()
    return (
        "⚠️ *CONFIRM YOUR BET*\n"
        f"{sep}\n\n"
        f"💰 Bet\: {escape_markdown_v2(str(bet_amount))}\n"
        f"🎯 Target\: {escape_markdown_v2(str(target_number))}\n"
        f"📈 Multiplier\: {escape_markdown_v2(str(multiplier))}\n"
        f"🏆 Potential win\: {escape_markdown_v2(str(potential_win))}\n\n"
        "Use the buttons to adjust target or confirm/cancel\."
    )


def msg_game_result(
    game_id: int,
    is_winner: bool,
    bet_amount: Decimal,
    win_amount: Decimal,
    target_number: int,
    result_number: int,
    multiplier: Decimal,
    balance_after: Decimal,
) -> str:
    sep = get_separator()
    outcome = "✅✅✅ *YOU WON\!*" if is_winner else "❌❌❌ *YOU LOST\.*"
    header = "🏆 *WIN*" if is_winner else "💥 *LOSS*"
    return (
        f"{header}\n"
        f"{sep}\n\n"
        f"{outcome}\n\n"
        f"🎯 Target\: `{escape_markdown_v2(str(target_number))}`\n"
        f"🎲 Result\: `{escape_markdown_v2(str(result_number))}`\n"
        f"💰 Bet\: {format_trx_escaped(bet_amount)}\n"
        f"🏆 Win\: {format_trx_escaped(win_amount)}\n"
        f"📈 Multiplier\: `{escape_markdown_v2(f'{multiplier:.2f}x')}`\n\n"
        f"🏦 New balance\: {format_trx_escaped(balance_after)}\n"
        f"🆔 Game ID\: `{escape_markdown_v2(str(game_id))}`\n"
    )


def msg_bet_in_progress() -> str:
    return r"⏳ *A bet is already in progress\\.* Please finish it before starting a new one\."


def msg_play_cancelled() -> str:
    sep = get_separator()
    return (
        "❌ *Bet cancelled*\n"
        f"{sep}\n\n"
        "You have been returned to the main menu\.\n"
        "Tap a button below to continue\."
    )


def msg_insufficient_balance_play(balance_trx: str, needed_trx: str) -> str:
    sep = get_separator()
    b = escape_markdown_v2(balance_trx)
    n = escape_markdown_v2(needed_trx)
    return (
        "❌ *INSUFFICIENT BALANCE*\n"
        f"{sep}\n\n"
        f"Your current balance is `{b}` but you attempted to bet `{n}`\.\n"
        "You need to deposit more TRX to continue\!\n\n"
        "🏦 Use /deposit to get your personal address, then send TRX\.\n"
        "After confirmations, your balance will be updated automatically\."
    )

# ============================ CHALLENGES MESSAGES ============================

def msg_challenges_page(items: list[dict], page: int, total_pages: int) -> str:
    """Render a page of active challenges with user progress.

    Each item dict keys:
      - id: int
      - name: str
      - description: str
      - type: str (bet_count | wagered_amount | win_streak)
      - target: Decimal | float | int
      - progress: Decimal | float | int
      - is_completed: bool
      - reward_amount: Decimal
      - reward_claimed: bool
    """
    sep = get_separator()
    lines = [
        f"🎁 *Daily Challenges* \\(Page {page}/{total_pages}\\)\n",
        f"{sep}\n",
    ]
    if not items:
        lines.append("_No active challenges right now\._\n")
        return "".join(lines)

    def _fmt_bar(curr: float, target: float, width: int = 10) -> str:
        try:
            ratio = max(0.0, min(1.0, float(curr) / float(target) if float(target) > 0 else 0.0))
        except Exception:
            ratio = 0.0
        filled = int(round(ratio * width))
        return "█" * filled + "░" * (width - filled)

    for it in items:
        name = escape_markdown_v2(str(it.get("name", "Challenge")))
        desc = escape_markdown_v2(str(it.get("description", "")))
        t = escape_markdown_v2(str(it.get("type", "-")))
        target = escape_markdown_v2(str(it.get("target", 0)))
        prog_val = it.get("progress", 0)
        reward = format_trx_escaped(it.get("reward_amount", 0))
        reward_claimed = "\\(✅ Claimed\\)" if it.get("reward_claimed", False) else ""
        reward_status = "⏳ In progress" if it.get("is_completed", False) else "✅ Completed"
        bar = _fmt_bar(float(prog_val or 0), float(it.get("target", 0) or 0))
        lines.extend([
            f"• *{name}* — _{t}_\n",
            f"  {desc}\n",
            f"  📈 `{escape_markdown_v2(str(prog_val))}` / `{target}`  \\[{escape_markdown_v2(bar)}\\]\n",
            f"  🎁 Reward: {reward}  —  {reward_status}{reward_claimed}\n",
            f"{sep}\n",
        ])
    return "".join(lines)

# ============================ GAME LEADERBOARD MESSAGES ============================

def msg_game_leaderboard_page(rows: list[dict], page: int, total_pages: int, period: str, metric: str, user_pos: int | None = None, user_value: float | None = None) -> str:
    """Render a leaderboard page for game results.

    rows: list of { rank, user_id, username, total_won, total_wagered, games_count }
    period: 'daily' | 'weekly' | 'monthly'
    metric: 'won' | 'wagered'
    """
    sep = get_separator()
    title_map = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}
    metric_map = {"won": "Top Winnings", "wagered": "Top Volume"}
    lines = [
        f"🏆 *{escape_markdown_v2(title_map.get(period, period).upper())} {escape_markdown_v2(metric_map.get(metric, metric))}* \\(Page {page}/{total_pages}\\)\n",
        f"{sep}\n",
    ]
    if not rows:
        lines.append("_No entries yet\._\n")
        return "".join(lines)

    for r in rows:
        rank = r.get("rank")
        username = r.get("username") or f"User {r.get('user_id')}"
        username = escape_markdown_v2(str(username))
        if metric == "won":
            val = format_trx_escaped(r.get("total_won", 0))
        else:
            val = format_trx_escaped(r.get("total_wagered", 0))
        lines.append(f"{rank}\\. `{username}` — {val}\n")

    if user_pos is not None:
        val_str = format_trx_escaped(user_value or 0)
        lines.extend([
            f"\n📍 Your position\\: `\\#{escape_markdown_v2(str(user_pos))}` — {val_str}\n",
        ])
    return "".join(lines)

# ============================ ADMIN MESSAGES ============================

def msg_admin_unauthorized() -> str:
    return "🚫 Unauthorized\."


def msg_admin_main() -> str:
    sep = get_separator()
    return (
        "🛠️ *ADMIN PANEL*\n"
        f"{sep}\n\n"
        "Welcome, admin\! Use the buttons below to navigate\:\n\n"
        "• 📊 Stats — Platform overview\n"
        "• 👤 Users — Accounts & balances\n"
        "• 🎲 Games — Recent games\n"
        "• 🚨 Alerts — System notices\n"
    )


def msg_admin_stats(overall: dict, emergency_stop: bool) -> str:
    """overall keys: users_total, users_active, games_today, vol_today, rev_today, hot_wallet_trx"""
    sep = get_separator()
    def _fmt_num(v):
        try:
            return escape_markdown_v2(f"{int(v):,}")
        except Exception:
            return escape_markdown_v2(str(v))
    vol = format_trx_escaped(overall.get("vol_today", 0))
    rev = format_trx_escaped(overall.get("rev_today", 0))
    hot = format_trx_escaped(overall.get("hot_wallet_trx", 0))
    status = "🛑 Games\\: DISABLED" if emergency_stop else "▶️ Games\\: ENABLED"
    return (
        "📊 *ADMIN STATS*\n"
        f"{sep}\n\n"
        f"👥 Users Total\\: `{_fmt_num(overall.get('users_total', 0))}`\n"
        f"✅ Active Users\\: `{_fmt_num(overall.get('users_active', 0))}`\n"
        f"🎲 Games Today\\: `{_fmt_num(overall.get('games_today', 0))}`\n"
        f"📈 Volume Today\\: {vol}\n"
        f"🏦 Revenue Today\\: {rev}\n"
        f"💼 Hot Wallet\\: {hot}\n\n"
        f"{status}"
    )


def msg_admin_users_page(rows: list[dict], page: int, total_pages: int) -> str:
    sep = get_separator()
    lines = [
        f"👤 *USERS* \\(Page {page}/{total_pages}\\)\n",
        f"{sep}\n\n",
    ]
    if not rows:
        lines.append("_No users found\._\n")
        return "".join(lines)
    
    for u in rows:
        username = u.get('username') or f"User {u.get('id')}"
        user_id = escape_markdown_v2(str(u.get('id')))
        balance = format_trx_escaped(u.get('account_balance', 0))
        games_played = escape_markdown_v2(str(u.get('total_games_played', 0)))
        
        lines.extend([
            f"• *{escape_markdown_v2(username)}*\n",
            f"  🆔 ID\\: `{user_id}`\n",
            f"  💰 Balance\\: {balance}\n", 
            f"  🎮 Games played\\: `{games_played}`\n",
            f"{sep}\n",
        ])
    return "".join(lines)


def msg_admin_alerts_page(rows: list[dict], page: int, total_pages: int) -> str:
    sep = get_separator()
    lines = [
        f"🚨 *ALERTS* \\(Page {page}/{total_pages}\\)\n",
        f"{sep}\n\n",
    ]
    if not rows:
        lines.append("_No alerts\._\n")
        return "".join(lines)
    for a in rows:
        title = escape_markdown_v2(a.get('title', 'Alert'))
        msg = escape_markdown_v2(a.get('message', ''))
        created = a.get('created_at')
        status = "🔴" if not a.get('is_read') else "🟢"
        lines.extend([
            f"{status} *{title}*\n",
            f"    {msg}\n",
            f"    📅 {escape_markdown_v2(format_date(created))}\n" if created else "",
            f"{sep}\n",
        ])
    return "".join(lines)


def msg_admin_games_page(rows: list[dict], page: int, total_pages: int) -> str:
    sep = get_separator()
    lines = [
        f"🎲 *GAMES* \\(Page {page}/{total_pages}\\)\n",
        f"{sep}\n\n",
    ]
    if not rows:
        lines.append("_No games found\._\n")
        return "".join(lines)
    for g in rows:
        is_win = bool(g.get('is_winner'))
        outcome = "✅ WIN" if is_win else "❌ LOSS"
        game_id = escape_markdown_v2(str(g.get('id')))
        username = escape_markdown_v2(str(g.get('username') or g.get('user_id')))
        target = escape_markdown_v2(str(g.get('target_number', '-')))
        result = escape_markdown_v2(str(g.get('result_number', '-')))
        bet = format_trx_escaped(g.get('bet_amount', 0))
        win = format_trx_escaped(g.get('win_amount', 0))
        ts = g.get('created_at')
        
        lines.extend([
            f"• *Game \\#{game_id}*\n",
            f"  👤 Player\\: `{username}`\n", 
            f"  🎯 Target\\: `{target}`\n",
            f"  🎲 Result\\: `{result}`\n",
            f"  💰 Bet\\: {bet}\n",
            f"  🏆 Win\\: {win}\n",
            f"  📊 Outcome\\: {escape_markdown_v2(outcome)}\n",
        ])
        
        if ts:
            lines.append(f"  📅 Date\\: `{escape_markdown_v2(format_date(ts))}`\n")
            
        lines.append(f"{sep}\n")
    return "".join(lines)


def msg_admin_controls_hint() -> str:
    return "Use the button below to toggle emergency stop\."

# ============================ USER STATS MESSAGES ============================
def msg_user_stats(
    balance: Decimal | float | str,
    games_played: int,
    games_won: int,
    biggest_win: Decimal | float | str,
    biggest_loss: Decimal | float | str,
    total_wagered: Decimal | float | str,
    total_won: Decimal | float | str,
) -> str:
    sep = get_separator()
    # Coerce and format values
    try:
        win_rate = (float(games_won) / float(games_played) * 100.0) if games_played > 0 else 0.0
    except Exception:
        win_rate = 0.0
    bal = format_trx_escaped(balance)
    bw = format_trx_escaped(biggest_win)
    bl = format_trx_escaped(biggest_loss)
    twag = format_trx_escaped(total_wagered)
    twon = format_trx_escaped(total_won)
    gp = escape_markdown_v2(str(games_played))
    gw = escape_markdown_v2(str(games_won))
    wr = escape_markdown_v2(f"{win_rate:.1f}%")
    return (
        "📊 *YOUR STATS*\n"
        f"{sep}\n\n"
        f"💰 Current balance\\: {bal}\n"
        f"🎮 Games played\\: `{gp}`\n"
        f"🏆 Games won\\: `{gw}` \\({wr}\\)\n"
        f"📈 Biggest win\\: {bw}\n"
        f"📉 Biggest loss\\: {bl}\n"
        f"💎 Total wagered\\: {twag}\n"
        f"🎁 Total won\\: {twon}\n"
    )
