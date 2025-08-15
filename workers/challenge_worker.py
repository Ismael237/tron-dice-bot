from __future__ import annotations

from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Iterable

from sqlalchemy.orm import Session

from database.database import get_db_session
from database.models import UserChallenge, Challenge, Game, User, Transaction, TransactionType
from utils.logger import get_logger

logger = get_logger("challenge_worker")


def _midnight_utc_today() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)


def _reset_daily_challenges(session: Session) -> int:
    """Reset daily challenges by setting date_started=today and clearing progress for active ones."""
    today = date.today()
    q = (
        session.query(UserChallenge)
        .join(Challenge, Challenge.id == UserChallenge.challenge_id)
        .filter(Challenge.is_active.is_(True))
    )
    updated = 0
    for uc in q.all():
        if uc.date_started != today:
            uc.date_started = today
            uc.current_progress = Decimal(0)
            uc.is_completed = False
            uc.completed_at = None
            uc.reward_claimed = False
            updated += 1
    if updated:
        session.commit()
    return updated


def _calc_win_streak(session: Session, user_id: int, since_dt: datetime) -> int:
    """Compute the longest winning streak since a timestamp for a user (simple pass)."""
    games = (
        session.query(Game)
        .filter(Game.user_id == user_id, Game.created_at >= since_dt)
        .order_by(Game.created_at.asc())
        .all()
    )
    best = curr = 0
    for g in games:
        if g.is_winner:
            curr += 1
            best = max(best, curr)
        else:
            curr = 0
    return best


def _update_progress_and_rewards(session: Session) -> tuple[int, int]:
    """Update progress for all active user challenges; auto-credit rewards for newly completed ones.
    Returns: (progress_updates, rewards_paid)
    """
    now = datetime.now(timezone.utc)
    progress_updates = 0
    rewards_paid = 0

    rows = (
        session.query(UserChallenge, Challenge, User)
        .join(Challenge, Challenge.id == UserChallenge.challenge_id)
        .join(User, User.id == UserChallenge.user_id)
        .filter(Challenge.is_active.is_(True))
        .all()
    )

    for uc, ch, user in rows:
        since_dt = datetime.combine(uc.date_started, datetime.min.time()).replace(tzinfo=timezone.utc)
        # Compute progress per challenge type
        if ch.challenge_type == "bet_count":
            cnt = (
                session.query(Game)
                .filter(Game.user_id == user.id, Game.created_at >= since_dt)
                .count()
            )
            progress_val = Decimal(cnt)
        elif ch.challenge_type == "wagered_amount":
            total = (
                session.query(Game)
                .filter(Game.user_id == user.id, Game.created_at >= since_dt)
                .with_entities(Game.bet_amount)
                .all()
            )
            s = sum(Decimal(str(x[0])) for x in total) if total else Decimal(0)
            progress_val = s
        elif ch.challenge_type == "win_streak":
            streak = _calc_win_streak(session, user.id, since_dt)
            progress_val = Decimal(streak)
        else:
            # Unknown type; skip
            continue

        # Update progress
        if uc.current_progress != progress_val:
            uc.current_progress = progress_val
            progress_updates += 1

        # Check completion
        target = Decimal(ch.target_value or 0)
        if not uc.is_completed and progress_val >= target:
            uc.is_completed = True
            uc.completed_at = now

        # Auto-distribute reward if completed and not yet claimed
        if uc.is_completed and not uc.reward_claimed:
            reward = Decimal(ch.reward_amount or 0)
            if reward > 0:
                user.account_balance = (user.account_balance or Decimal(0)) + reward
                tx = Transaction(
                    user_id=user.id,
                    type=TransactionType.bonus,
                    amount_trx=reward,
                    description=f"Daily challenge reward: {ch.name}",
                    reference_id=str(ch.id),
                )
                session.add(tx)
                uc.reward_claimed = True
                rewards_paid += 1

    if progress_updates or rewards_paid:
        session.commit()
    return progress_updates, rewards_paid


def run_challenge_worker():
    """Entry point for scheduler. Performs daily reset at midnight UTC and periodic updates."""
    try:
        with get_db_session() as session:
            # Daily reset when we cross midnight. This function can be called by a cron at 00:00 UTC.
            reset_count = _reset_daily_challenges(session)
            if reset_count:
                logger.info(f"[ChallengeWorker] Reset {reset_count} user challenges for new day")
            updates, paid = _update_progress_and_rewards(session)
            logger.info(f"[ChallengeWorker] Progress updates: {updates}, Rewards paid: {paid}")
    except Exception as e:
        logger.error(f"[ChallengeWorker] Error: {e}")
        raise
