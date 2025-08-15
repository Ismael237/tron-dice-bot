from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import date as date_type, datetime, time, timezone

from database.database import get_db_session
from database.models import (
    User,
    ReferralCommission,
    CommissionStatus,
    CommissionType,
    Transaction,
    TransactionType,
    TransactionStatus,
    Game,
    GameStatus,
)
from utils.helpers import (
    generate_referral_code as _gen_code,
    generate_share_link as _gen_link,
    get_utc_date,
    get_utc_time,
)
from config import REFERRAL_RATE, REFERRAL_MIN_NET_FOR_COMMISSION, BOT_USERNAME


class ReferralService:
    """DB/business logic for referrals (single-level).
    - Sponsor linking with anti-fraud guards
    - Per-game net-win commission creation (immediate payout)
    - Stats helpers for UI
    Telegram logic lives in `bot/handlers/referral_handler.py`.
    """

    # ---------------------- User & Code helpers ----------------------
    @staticmethod
    def get_user_by_telegram(telegram_id: str) -> Optional[User]:
        with get_db_session() as session:
            return session.query(User).filter_by(telegram_id=telegram_id).first()

    @staticmethod
    def ensure_referral_code(user_id: int) -> str:
        """Ensure user has a referral_code. Generate and persist if missing."""
        with get_db_session() as session:
            user = session.query(User).get(user_id)
            if not user:
                raise ValueError("User not found")
            if not user.referral_code:
                user.referral_code = _gen_code()
                session.commit()
            return user.referral_code

    @staticmethod
    def get_user_by_referral_code(code: str) -> Optional[User]:
        with get_db_session() as session:
            return session.query(User).filter_by(referral_code=code).first()

    @staticmethod
    def generate_share_link(user_id: int, bot_username: Optional[str] = None) -> str:
        """Return a shareable t.me link with the user's referral code."""
        with get_db_session() as session:
            user = session.query(User).get(user_id)
            if not user:
                raise ValueError("User not found")
            code = user.referral_code or _gen_code()
            if not user.referral_code:
                user.referral_code = code
                session.commit()
        return _gen_link(bot_username or BOT_USERNAME, code)

    # ---------------------- Sponsor linking ----------------------
    @staticmethod
    def link_sponsor(referred_user_id: int, sponsor_code: str) -> bool:
        """Link a user to a sponsor by referral code.
        Anti-fraud rules:
        - Self-referral blocked
        - A user can have only one sponsor in their lifetime
        - Sponsor code must exist
        Returns True if sponsor was set, False if already set.
        """
        with get_db_session() as session:
            referred = session.query(User).get(referred_user_id)
            if not referred:
                raise ValueError("Referred user not found")
            sponsor = session.query(User).filter_by(referral_code=sponsor_code).first()
            if not sponsor:
                raise ValueError("Invalid referral code")
            if sponsor.id == referred.id:
                raise ValueError("Self-referral is not allowed")
            if referred.sponsor_id:
                return False  # already linked
            referred.sponsor_id = sponsor.id
            session.commit()
            return True

    # ---------------------- Commissions ----------------------
    @staticmethod
    def _compute_net_for_game(game: Game) -> Decimal:
        """Net winnings for a single game (win_amount - bet_amount)."""
        return Decimal(game.win_amount) - Decimal(game.bet_amount)

    @staticmethod
    def record_commission_for_game_if_applicable(referred_user_id: int, game_id: int) -> Optional[ReferralCommission]:
        """Create and pay a single-level commission if this game yielded a positive net win.
        Additional guards:
        - Only one commission per referred user per day (simple cap)
        - Minimal net threshold (config)
        - Requires the referred user to have at least one completed game (current game qualifies)
        Idempotency: uses transaction_id = f"GAME:{game_id}".
        """
        today = get_utc_date()
        with get_db_session() as session:
            # Load game and users
            game = session.query(Game).get(game_id)
            if not game or game.user_id != referred_user_id:
                raise ValueError("Game not found or owner mismatch")
            if game.status != GameStatus.completed:
                # Only completed games are eligible
                return None

            referred = session.query(User).get(referred_user_id)
            if not referred:
                raise ValueError("Referred user not found")
            if not referred.sponsor_id:
                return None  # no sponsor, nothing to do
            referrer = session.query(User).get(referred.sponsor_id)
            if not referrer or not referrer.is_active:
                return None

            # Anti-fraud: daily cap per referred user
            # Filter from start of today UTC
            start_of_day = datetime.combine(get_utc_date(), time.min).replace(tzinfo=timezone.utc)
            daily_count = (
                session.query(ReferralCommission)
                .filter(
                    ReferralCommission.referred_user_id == referred_user_id,
                    ReferralCommission.created_at >= start_of_day,
                )
                .count()
            )
            if daily_count >= 1:
                return None

            # Idempotency by game
            tx_id = f"GAME:{game.id}"
            existing = session.query(ReferralCommission).filter_by(transaction_id=tx_id).first()
            if existing:
                return None

            net = ReferralService._compute_net_for_game(game)
            if net <= Decimal(str(REFERRAL_MIN_NET_FOR_COMMISSION)):
                return None

            # Commission computation
            rate = Decimal(str(REFERRAL_RATE))
            commission_amount = (net * rate).quantize(Decimal('0.000001'))
            if commission_amount <= Decimal('0'):
                return None

            # Create commission as paid immediately
            commission = ReferralCommission(
                user_id=referrer.id,
                referred_user_id=referred.id,
                transaction_id=tx_id,
                commission_type=CommissionType.earning,
                amount_trx=commission_amount,
                percentage=rate,
                status=CommissionStatus.paid,
                paid_at=get_utc_time(),
            )
            session.add(commission)

            # Credit referrer balance and log transaction
            referrer.account_balance += commission_amount
            referrer.total_referral_earnings += commission_amount

            tx = Transaction(
                user_id=referrer.id,
                type=TransactionType.referral_commission,
                amount_trx=commission_amount,
                description=f"Referral commission from user {referred.id} (game {game.id})",
                reference_id=str(commission.transaction_id),
                status=TransactionStatus.completed,
            )
            session.add(tx)

            session.commit()
            session.refresh(commission)
            return commission

    # ---------------------- Queries ----------------------
    @staticmethod
    def get_commissions(user_id: int) -> List[ReferralCommission]:
        with get_db_session() as session:
            return session.query(ReferralCommission).filter_by(user_id=user_id).all()

    @staticmethod
    def summarize_commissions(user_id: int) -> Dict[str, float]:
        """Return a simple summary for single-level referrals: total_paid, total_pending (floats for UI)."""
        with get_db_session() as session:
            total_paid = Decimal('0')
            total_pending = Decimal('0')
            rows = session.query(ReferralCommission).filter_by(user_id=user_id).all()
            for row in rows:
                amount = Decimal(row.amount_trx)
                if row.status == CommissionStatus.paid:
                    total_paid += amount
                else:
                    total_pending += amount
            return {
                "total_paid": float(total_paid),
                "total_pending": float(total_pending),
            }

    @staticmethod
    def get_referral_stats(user_id: int, recent_limit: int = 10) -> Dict[str, Any]:
        """Aggregated referral stats for UI.
        - counts: direct_referrals, active_referrals, total_commissions_paid, total_commissions_pending
        - sums: total_paid_trx, total_pending_trx
        - recents: last N commissions (id, referred_user_id, amount, status, created_at)
        """
        with get_db_session() as session:
            # Direct referrals
            directs = session.query(User).filter_by(sponsor_id=user_id).all()
            direct_ids = [u.id for u in directs]

            # Active referrals: have at least 1 completed game
            active = (
                session.query(Game.user_id)
                .filter(Game.user_id.in_(direct_ids))
                .group_by(Game.user_id)
                .all()
            )
            active_count = len(active)

            # Commissions
            commissions = session.query(ReferralCommission).filter_by(user_id=user_id).all()
            total_paid = Decimal('0')
            total_pending = Decimal('0')
            paid_count = 0
            pending_count = 0
            for c in commissions:
                amt = Decimal(c.amount_trx)
                if c.status == CommissionStatus.paid:
                    total_paid += amt
                    paid_count += 1
                else:
                    total_pending += amt
                    pending_count += 1

            recents = (
                session.query(ReferralCommission)
                .filter_by(user_id=user_id)
                .order_by(ReferralCommission.created_at.desc())
                .limit(recent_limit)
                .all()
            )
            recents_list = [
                {
                    "id": r.id,
                    "referred_user_id": r.referred_user_id,
                    "amount": float(r.amount_trx),
                    "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
                    "created_at": r.created_at.isoformat() if hasattr(r, 'created_at') else None,
                }
                for r in recents
            ]

            return {
                "direct_referrals": len(directs),
                "active_referrals": active_count,
                "total_commissions_paid": paid_count,
                "total_commissions_pending": pending_count,
                "total_paid_trx": float(total_paid),
                "total_pending_trx": float(total_pending),
                "recent_commissions": recents_list,
            }

    @staticmethod
    def get_direct_referrals(user_id: int) -> List[User]:
        with get_db_session() as session:
            return session.query(User).filter_by(sponsor_id=user_id).all()

    # ---------------------- Leaderboard ----------------------
    @staticmethod
    def get_referral_leaderboard(limit: int = 100) -> List[Dict[str, Any]]:
        """Return top users by total referral earnings (all-time)."""
        with get_db_session() as session:
            rows = (
                session.query(User)
                .order_by(User.total_referral_earnings.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "user_id": u.id,
                    "username": u.username,
                    "total": float(Decimal(u.total_referral_earnings or 0)),
                }
                for u in rows
            ]


# Backward-compatible forwarders to preserve existing routing (Telegram logic in handlers)
async def handle_referral(update, context):
    from bot.handlers.referral_handler import handle_referral as _h

    return await _h(update, context)


async def handle_referral_info(update, context):
    from bot.handlers.referral_handler import handle_referral_info as _h

    return await _h(update, context)
