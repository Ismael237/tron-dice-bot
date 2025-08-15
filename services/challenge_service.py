from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Dict

from database.database import get_db_session
from database.models import Challenge, UserChallenge, User, Transaction, TransactionType
from utils.logger import get_logger

logger = get_logger("challenge_service")


class ChallengeService:
    PAGE_SIZE = 5

    @staticmethod
    def ensure_user_challenges(user_id: int) -> None:
        """Ensure a `UserChallenge` row exists for each active `Challenge` for given user.
        Does not mark completion; only ensures presence for tracking progress.
        """
        with get_db_session() as session:
            active = session.query(Challenge).filter(Challenge.is_active.is_(True)).all()
            if not active:
                return
            existing = (
                session.query(UserChallenge.challenge_id)
                .filter(UserChallenge.user_id == user_id)
                .all()
            )
            existing_ids = {cid for (cid,) in existing}
            to_create = [c for c in active if c.id not in existing_ids]
            for c in to_create:
                uc = UserChallenge(user_id=user_id, challenge_id=c.id, date_started=date.today())
                session.add(uc)
            if to_create:
                session.commit()

    @staticmethod
    def list_active_for_user(user_id: int) -> List[Dict]:
        """Return active challenges merged with user progress for UI consumption."""
        ChallengeService.ensure_user_challenges(user_id)
        with get_db_session() as session:
            rows = (
                session.query(Challenge, UserChallenge)
                .join(UserChallenge, (UserChallenge.challenge_id == Challenge.id) & (UserChallenge.user_id == user_id))
                .filter(Challenge.is_active.is_(True))
                .order_by(Challenge.id.asc())
                .all()
            )
            result: List[Dict] = []
            for ch, uc in rows:
                result.append(
                    {
                        "id": ch.id,
                        "name": ch.name,
                        "description": ch.description,
                        "type": ch.challenge_type,
                        "target": float(ch.target_value or 0),
                        "progress": float(uc.current_progress or 0),
                        "is_completed": bool(uc.is_completed),
                        "reward_amount": float(ch.reward_amount or 0),
                        "reward_claimed": bool(uc.reward_claimed),
                    }
                )
            return result

    @staticmethod
    def claim_reward(user_id: int, challenge_id: int) -> tuple[bool, str]:
        """Attempt to claim a completed challenge reward.
        Returns (success, message).
        """
        with get_db_session() as session:
            uc = (
                session.query(UserChallenge)
                .filter(
                    UserChallenge.user_id == user_id,
                    UserChallenge.challenge_id == challenge_id,
                )
                .first()
            )
            ch = session.query(Challenge).filter(Challenge.id == challenge_id).first()
            user = session.query(User).filter(User.id == user_id).first()
            if not uc or not ch or not user:
                return False, "Challenge not found"
            if not uc.is_completed:
                return False, "Challenge not completed"
            if uc.reward_claimed:
                return False, "Reward already claimed"

            reward = Decimal(ch.reward_amount or 0)
            # Update user balance
            user.account_balance = (user.account_balance or Decimal(0)) + reward
            # Mark claimed
            uc.reward_claimed = True

            # Record a bonus transaction
            tx = Transaction(
                user_id=user_id,
                type=TransactionType.bonus,
                amount_trx=reward,
                status=None,  # Will default per model; leave None to avoid overriding default
                description=f"Challenge reward: {ch.name}",
                reference_id=str(challenge_id),
            )
            session.add(tx)
            session.commit()
            logger.info(f"User {user_id} claimed challenge {challenge_id} reward {reward}")
            return True, "Reward claimed"
