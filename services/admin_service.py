from __future__ import annotations
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Tuple
import os

from sqlalchemy import func, desc

import config
from database.database import get_db_session
from database.models import User, Game, Notification
from blockchain.tron_client import get_main_wallet, get_trx_balance


class AdminService:
    @staticmethod
    def is_admin(telegram_id: str | int | None, username: str | None) -> bool:
        if telegram_id is None and not username:
            return False
        try:
            admin_id = str(config.TELEGRAM_ADMIN_ID) if config.TELEGRAM_ADMIN_ID is not None else None
        except Exception:
            admin_id = None
        if admin_id and str(telegram_id) == str(admin_id):
            return True
        if config.TELEGRAM_ADMIN_USERNAME and username:
            return str(username).lstrip('@').lower() == str(config.TELEGRAM_ADMIN_USERNAME).lstrip('@').lower()
        return False

    @staticmethod
    def get_overall_stats() -> dict:
        now = datetime.now(timezone.utc)
        start_day = datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
        with get_db_session() as db:
            users_total = db.query(func.count(User.id)).scalar() or 0
            users_active = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
            games_today_q = db.query(Game).filter(Game.created_at >= start_day)
            games_today = games_today_q.count()
            sums = db.query(
                func.coalesce(func.sum(Game.bet_amount), 0),
                func.coalesce(func.sum(Game.win_amount), 0),
            ).filter(Game.created_at >= start_day).one()
            total_wagered_today = Decimal(sums[0]) if sums and sums[0] is not None else Decimal(0)
            total_won_today = Decimal(sums[1]) if sums and sums[1] is not None else Decimal(0)

        # Hot wallet balance (best effort)
        hot_wallet_trx = Decimal(0)
        try:
            addr, _ = get_main_wallet()
            if addr:
                bal = get_trx_balance(addr)
                if bal is not None:
                    hot_wallet_trx = Decimal(bal)
        except Exception:
            pass

        return {
            "users_total": users_total,
            "users_active": users_active,
            "games_today": games_today,
            "vol_today": total_wagered_today,
            "rev_today": (total_wagered_today - total_won_today),
            "hot_wallet_trx": hot_wallet_trx,
        }

    @staticmethod
    def list_users(page: int, per_page: int) -> Tuple[list[dict], int]:
        with get_db_session() as db:
            total = db.query(func.count(User.id)).scalar() or 0
            total_pages = max(1, (total + per_page - 1) // per_page)
            page = max(1, min(page, total_pages))
            rows = (
                db.query(User)
                .order_by(desc(User.created_at))
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            out = [
                {
                    "id": u.id,
                    "username": u.username,
                    "account_balance": u.account_balance,
                    "total_games_played": u.total_games_played,
                }
                for u in rows
            ]
            return out, total_pages

    @staticmethod
    def list_games(page: int, per_page: int) -> Tuple[list[dict], int]:
        with get_db_session() as db:
            total = db.query(func.count(Game.id)).scalar() or 0
            total_pages = max(1, (total + per_page - 1) // per_page)
            page = max(1, min(page, total_pages))
            rows = (
                db.query(Game, User.username)
                .join(User, User.id == Game.user_id)
                .order_by(desc(Game.created_at))
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            out = []
            for g, username in rows:
                out.append({
                    "id": g.id,
                    "user_id": g.user_id,
                    "username": username,
                    "bet_amount": g.bet_amount,
                    "win_amount": g.win_amount,
                    "is_winner": g.is_winner,
                    "target_number": g.target_number,
                    "result_number": g.result_number,
                })
            return out, total_pages

    @staticmethod
    def list_alerts(page: int, per_page: int) -> Tuple[list[dict], int]:
        with get_db_session() as db:
            total = db.query(func.count(Notification.id)).scalar() or 0
            total_pages = max(1, (total + per_page - 1) // per_page)
            page = max(1, min(page, total_pages))
            rows = (
                db.query(Notification)
                .order_by(desc(Notification.created_at))
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            out = [
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "is_read": n.is_read,
                }
                for n in rows
            ]
            return out, total_pages

    @staticmethod
    def toggle_emergency() -> bool:
        current = bool(config.EMERGENCY_STOP)
        new_val = not current
        # update env and config in-memory (process lifetime)
        os.environ['EMERGENCY_STOP'] = 'true' if new_val else 'false'
        config.EMERGENCY_STOP = new_val
        # persist an audit notification if admin user exists
        try:
            admin_user_id = None
            with get_db_session() as db:
                if config.TELEGRAM_ADMIN_ID:
                    u = db.query(User).filter(User.telegram_id == str(config.TELEGRAM_ADMIN_ID)).first()
                    if u:
                        admin_user_id = u.id
                if admin_user_id:
                    Notification.create(db,
                        user_id=admin_user_id,
                        notification_type='admin',
                        title='Emergency toggle',
                        message=f'Set to {"ENABLED" if new_val else "DISABLED"}',
                        data=None,
                    )
        except Exception:
            pass
        return new_val
