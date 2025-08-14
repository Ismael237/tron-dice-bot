from typing import List, Optional

from database.database import get_db_session
from database.models import User, ReferralCommission, CommissionStatus


class ReferralService:
    """DB/business logic for referrals (single-level). Telegram logic lives in bot/handlers/referral_handler.py"""

    # Users
    @staticmethod
    def get_user_by_telegram(telegram_id: str) -> Optional[User]:
        with get_db_session() as session:
            return session.query(User).filter_by(telegram_id=telegram_id).first()

    @staticmethod
    def get_direct_referrals(user_id: int) -> List[User]:
        with get_db_session() as session:
            return session.query(User).filter_by(sponsor_id=user_id).all()

    # Commissions
    @staticmethod
    def get_commissions(user_id: int) -> List[ReferralCommission]:
        with get_db_session() as session:
            return session.query(ReferralCommission).filter_by(user_id=user_id).all()

    @staticmethod
    def summarize_commissions(user_id: int):
        """Return a simple summary for single-level referrals: total_paid, total_pending."""
        with get_db_session() as session:
            total_paid = 0.0
            total_pending = 0.0
            rows = session.query(ReferralCommission).filter_by(user_id=user_id).all()
            for row in rows:
                # Align to models: field is amount_trx (Decimal)
                amount = float(row.amount_trx)
                if row.status == CommissionStatus.paid:
                    total_paid += amount
                else:
                    total_pending += amount
            return {
                "total_paid": total_paid,
                "total_pending": total_pending,
            }


# Backward-compatible forwarders to preserve existing routing (Telegram logic in handlers)
async def handle_referral(update, context):
    from bot.handlers.referral_handler import handle_referral as _h

    return await _h(update, context)


async def handle_referral_info(update, context):
    from bot.handlers.referral_handler import handle_referral_info as _h

    return await _h(update, context)


