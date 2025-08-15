from __future__ import annotations

from typing import List, Dict, Tuple
from decimal import Decimal

from sqlalchemy import desc

from database.database import get_db_session
from database.models import Leaderboard, User
from utils.logger import get_logger

logger = get_logger("leaderboard_service")


class LeaderboardService:
    PAGE_SIZE = 10

    @staticmethod
    def list_by_period(period: str, metric: str, limit: int = 200) -> List[Dict]:
        """Return leaderboard rows as dicts sorted by metric desc.
        metric: 'won' -> total_won, 'wagered' -> total_wagered
        """
        metric_col = Leaderboard.total_won if metric == "won" else Leaderboard.total_wagered
        with get_db_session() as session:
            q = (
                session.query(Leaderboard, User.username)
                .join(User, User.id == Leaderboard.user_id)
                .filter(Leaderboard.period_type == period)
                .order_by(desc(metric_col))
            )
            rows = q.limit(limit).all()
            result: List[Dict] = []
            rank = 1
            for lb, username in rows:
                result.append(
                    {
                        "rank": rank,
                        "user_id": lb.user_id,
                        "username": username,
                        "total_wagered": float(lb.total_wagered or 0),
                        "total_won": float(lb.total_won or 0),
                        "games_count": lb.games_count,
                    }
                )
                rank += 1
            return result

    @staticmethod
    def get_user_position(user_id: int, period: str, metric: str) -> Tuple[int | None, float | None]:
        metric_col = Leaderboard.total_won if metric == "won" else Leaderboard.total_wagered
        with get_db_session() as session:
            # Get user's value first
            me = (
                session.query(Leaderboard)
                .filter(Leaderboard.user_id == user_id, Leaderboard.period_type == period)
                .first()
            )
            if not me:
                return None, None
            my_value = float((me.total_won if metric == "won" else me.total_wagered) or 0)
            # Position: count how many strictly greater values
            higher = (
                session.query(Leaderboard)
                .filter(Leaderboard.period_type == period, metric_col > (me.total_won if metric == "won" else me.total_wagered))
                .count()
            )
            position = higher + 1
            return position, my_value
