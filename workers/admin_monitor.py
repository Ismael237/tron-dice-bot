from __future__ import annotations
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func

import config
from database.database import get_db_session
from database.models import Game, Notification, User
from blockchain.tron_client import get_main_wallet, get_trx_balance
from bot.utils import safe_notify_user
from utils.logger import logger
from utils.helpers import escape_markdown_v2


def _notify_admin(title: str, message: str):
    try:
        admin_tid = str(config.TELEGRAM_ADMIN_ID) if config.TELEGRAM_ADMIN_ID is not None else None
        if admin_tid:
            safe_notify_user(admin_tid, f"*{escape_markdown_v2(title)}*\n{escape_markdown_v2(message)}")
    except Exception as e:
        logger.error(f"[AdminMonitor] Failed to notify admin: {e}")


def _create_alert(db, title: str, message: str):
    try:
        # Try link to admin user if exists
        admin_user_id = None
        if config.TELEGRAM_ADMIN_ID is not None:
            u = db.query(User).filter(User.telegram_id == str(config.TELEGRAM_ADMIN_ID)).first()
            if u:
                admin_user_id = u.id
        Notification.create(db,
            user_id=admin_user_id or 1,  # fallback to 1 if admin user not present
            notification_type='system',
            title=title,
            message=message,
            data=None,
        )
    except Exception as e:
        logger.error(f"[AdminMonitor] Failed to persist alert: {e}")


def run_admin_monitor():
    """Periodic checks for admin monitoring."""
    logger.info("[AdminMonitor] Running checks...")
    now = datetime.now(timezone.utc)
    one_min_ago = now - timedelta(minutes=1)
    interval_ago = now - timedelta(minutes=max(1, int(config.ADMIN_MONITOR_INTERVAL or 5)))

    big_win_threshold = Decimal(config.ADMIN_BIG_WIN_TRX or 5000)
    low_wallet_min = Decimal(config.ADMIN_HOT_WALLET_MIN_TRX or 300)
    spike_games_per_min = int(config.ADMIN_SPIKE_GAMES_PER_MIN or 50)

    with get_db_session() as db:
        # Big win detection
        try:
            big_win = db.query(Game).filter(
                Game.created_at >= interval_ago,
                Game.win_amount >= big_win_threshold
            ).order_by(Game.win_amount.desc()).first()
            if big_win:
                title = "Big Win Detected"
                message = f"Game #{big_win.id}: user {big_win.user_id} won {big_win.win_amount} TRX"
                _create_alert(db, title, message)
                _notify_admin(title, message)
        except Exception as e:
            logger.error(f"[AdminMonitor] Big win check error: {e}")

        # Hot wallet low balance
        try:
            addr, _ = get_main_wallet()
            if addr:
                bal = get_trx_balance(addr)
                if bal is not None and Decimal(bal) < low_wallet_min:
                    title = "Hot Wallet Low Balance"
                    message = f"Balance {bal} TRX below minimum {low_wallet_min} TRX"
                    _create_alert(db, title, message)
                    _notify_admin(title, message)
        except Exception as e:
            logger.error(f"[AdminMonitor] Hot wallet check error: {e}")

        # Games spike per minute
        try:
            games_last_min = db.query(func.count(Game.id)).filter(Game.created_at >= one_min_ago).scalar() or 0
            if int(games_last_min) > spike_games_per_min:
                title = "Traffic Spike Detected"
                message = f"{games_last_min} games in the last minute (threshold {spike_games_per_min})"
                _create_alert(db, title, message)
                _notify_admin(title, message)
        except Exception as e:
            logger.error(f"[AdminMonitor] Spike check error: {e}")

    logger.info("[AdminMonitor] Checks completed.")
