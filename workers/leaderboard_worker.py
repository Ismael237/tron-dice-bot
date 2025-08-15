from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from typing import Dict, Iterable, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.database import get_db_session
from database.models import Game, Leaderboard, User, Notification
from utils.logger import get_logger

logger = get_logger("leaderboard_worker")


def _period_bounds(period: str, now: datetime) -> Tuple[date, datetime, datetime]:
    """Return (period_date, start_dt, end_dt) for the given period at 'now' (UTC)."""
    if period == "daily":
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        period_date = start.date()
    elif period == "weekly":
        # ISO week: Monday start
        weekday = (now.weekday())  # 0 Monday
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=weekday)
        end = start + timedelta(days=7)
        period_date = start.date()
    elif period == "monthly":
        start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        end = next_month
        period_date = start.date()
    else:
        raise ValueError(f"Unknown period: {period}")
    return period_date, start, end


def _aggregate_for_period(session: Session, period: str, now: datetime) -> int:
    """Aggregate Game data into Leaderboard for the given period.
    Returns number of rows upserted.
    """
    period_date, start_dt, end_dt = _period_bounds(period, now)

    # Query per user aggregates in one pass
    agg_rows = (
        session.query(
            Game.user_id,
            func.count(Game.id),
            func.coalesce(func.sum(Game.bet_amount), 0),
            func.coalesce(func.sum(Game.win_amount), 0),
            func.coalesce(func.max(Game.win_amount), 0),
        )
        .filter(Game.created_at >= start_dt, Game.created_at < end_dt)
        .group_by(Game.user_id)
        .all()
    )

    upserts = 0
    for user_id, games_count, total_wagered, total_won, biggest_win in agg_rows:
        # Find existing entry or create new
        lb = (
            session.query(Leaderboard)
            .filter(
                Leaderboard.user_id == user_id,
                Leaderboard.period_type == period,
                Leaderboard.period_date == period_date,
            )
            .first()
        )
        if not lb:
            lb = Leaderboard(
                user_id=user_id,
                period_type=period,
                period_date=period_date,
            )
            session.add(lb)
        lb.games_count = int(games_count or 0)
        lb.total_wagered = Decimal(str(total_wagered or 0))
        lb.total_won = Decimal(str(total_won or 0))
        lb.net_profit = Decimal(str((total_won or 0))) - Decimal(str((total_wagered or 0)))
        lb.biggest_win = Decimal(str(biggest_win or 0))
        upserts += 1

    if upserts:
        session.commit()
    return upserts


def _notify_top_players(session: Session, period: str, now: datetime, top_n: int = 3) -> int:
    """Create Notification entries for top N players by total_won for the current period."""
    period_date, _, _ = _period_bounds(period, now)

    rows = (
        session.query(Leaderboard, User.username)
        .join(User, User.id == Leaderboard.user_id)
        .filter(Leaderboard.period_type == period, Leaderboard.period_date == period_date)
        .order_by(Leaderboard.total_won.desc())
        .limit(top_n)
        .all()
    )
    created = 0
    for lb, username in rows:
        title = f"Leaderboard — {period.capitalize()} Top {top_n}"
        msg = (
            f"Congrats {username or 'player'}! You are in the Top {top_n} for {period} with "
            f"winnings: {lb.total_won} TRX and volume: {lb.total_wagered} TRX."
        )
        n = Notification(
            user_id=lb.user_id,
            notification_type="leaderboard_top",
            title=title,
            message=msg,
            data={"period": period, "period_date": str(period_date), "ranked": True},
        )
        session.add(n)
        created += 1
    if created:
        session.commit()
    return created


def run_leaderboard_worker():
    """Entry point for scheduler. Recalculate daily/weekly/monthly leaderboards and notify top players."""
    now = datetime.now(timezone.utc)
    try:
        with get_db_session() as session:
            total_upserts = 0
            for period in ("daily", "weekly", "monthly"):
                up = _aggregate_for_period(session, period, now)
                total_upserts += up
                _notify_top_players(session, period, now, top_n=3)
            logger.info(f"[LeaderboardWorker] Upserts: {total_upserts}")
    except Exception as e:
        logger.error(f"[LeaderboardWorker] Error: {e}")
        raise
