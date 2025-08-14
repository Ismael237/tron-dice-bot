from decimal import Decimal
from typing import List, Optional

from database.database import get_db_session
from database.models import (
    User,
    Withdrawal,
    WithdrawalStatus,
    Transaction,
    TransactionType,
    TransactionStatus,
)
from utils.helpers import get_utc_date, get_utc_time
from config import DAILY_WITHDRAWAL_LIMIT, MIN_WITHDRAWAL_AMOUNT, WITHDRAWAL_FEE_RATE
from utils.validators import is_valid_tron_address


class WithdrawalService:
    """DB/business logic for withdrawals."""

    @staticmethod
    def get_user_by_telegram(telegram_id: str):
        with get_db_session() as session:
            return session.query(User).filter_by(telegram_id=telegram_id).first()

    @staticmethod
    def get_daily_withdrawals(user_id: int) -> List[Withdrawal]:
        with get_db_session() as session:
            today = get_utc_date()
            return session.query(Withdrawal).filter(
                Withdrawal.user_id == user_id,
                Withdrawal.status != WithdrawalStatus.failed,
                Withdrawal.created_at >= today,
            ).all()

    @staticmethod
    def create_withdrawal(user_id: int, amount: Decimal, to_address: str) -> Withdrawal:
        with get_db_session() as session:
            try:
                user = session.query(User).get(user_id)
                if not user:
                    raise ValueError("User not found")

                if Decimal(user.account_balance) < amount:
                    raise ValueError("Insufficient balance")
                
                user.account_balance -= amount
                fee_rate = Decimal(str(WITHDRAWAL_FEE_RATE))
                fee = (amount * fee_rate)
                withdrawal = Withdrawal(
                    user_id=user_id,
                    amount_trx=amount,
                    fee_trx=fee,
                    to_address=to_address,
                    status=WithdrawalStatus.pending,
                    created_at=get_utc_time(),
                )
                session.add(withdrawal)
                session.commit()
                session.refresh(withdrawal)
                return withdrawal
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def create_withdrawal_transaction(user_id: int, amount: Decimal, withdrawal_id: int) -> Transaction:
        with get_db_session() as session:
            try:
                tx = Transaction(
                    user_id=user_id,
                    type=TransactionType.withdrawal,
                    amount_trx=amount,
                    status=TransactionStatus.pending,
                    description="User initiated withdrawal",
                    reference_id=str(withdrawal_id),
                )
                session.add(tx)
                session.commit()
                session.refresh(tx)
                return tx
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def validate_amount(amount: Decimal):
        if amount < Decimal(str(MIN_WITHDRAWAL_AMOUNT)) or amount > Decimal(str(DAILY_WITHDRAWAL_LIMIT)):
            return False
        return True

    @staticmethod
    def calculate_net_amount(amount: Decimal):
        fee_rate = Decimal(str(WITHDRAWAL_FEE_RATE))
        return amount * (Decimal('1') - fee_rate)

    @staticmethod
    def validate_address(address: str):
        return is_valid_tron_address(address)

    # -------- Helpers used by the withdrawal processor worker --------
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        with get_db_session() as session:
            return session.query(User).get(user_id)

    @staticmethod
    def list_pending_withdrawals() -> List[Withdrawal]:
        with get_db_session() as session:
            return session.query(Withdrawal).filter(
                Withdrawal.status.in_([WithdrawalStatus.pending, WithdrawalStatus.processing])
            ).all()

    @staticmethod
    def complete_withdrawal(user_id: int, withdrawal_id: int, amount_trx: Decimal, tx_hash: str) -> None:
        """Mark withdrawal completed, set tx_hash and processed_at, decrement user account_balance, update tx record."""
        with get_db_session() as session:
            try:
                wd = session.query(Withdrawal).get(withdrawal_id)
                user = session.query(User).get(user_id)
                if not wd or not user:
                    raise ValueError("Withdrawal or User not found")

                wd.tx_hash = tx_hash
                wd.status = WithdrawalStatus.completed
                wd.processed_at = get_utc_time()

                user.total_withdrawn += Decimal(amount_trx)

                tx_record = session.query(Transaction).filter_by(
                    reference_id=str(withdrawal_id), type=TransactionType.withdrawal
                ).first()
                if tx_record:
                    tx_record.description = f"Withdrawal {tx_hash}"
                session.commit()
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def fail_withdrawal(withdrawal_id: int, user_id: int, reason: str, tx_hash: Optional[str] = None) -> None:
        """Mark withdrawal as failed and update related transaction description."""
        with get_db_session() as session:
            try:
                wd = session.query(Withdrawal).get(withdrawal_id)
                user = session.query(User).get(user_id)
                if not wd or not user:
                    raise ValueError("Withdrawal or User not found")
                user.account_balance += wd.amount_trx + wd.fee_trx
                wd.status = WithdrawalStatus.failed
                tx_record = session.query(Transaction).filter_by(
                    reference_id=str(withdrawal_id), type=TransactionType.withdrawal
                ).first()
                if tx_record:
                    suffix = f" (tx {tx_hash})" if tx_hash else ""
                    tx_record.description = f"Withdrawal failed: {reason}{suffix}"
                session.commit()
            except Exception:
                session.rollback()
                raise