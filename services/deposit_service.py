from decimal import Decimal
from typing import List, Optional

from database.database import get_db_session
from database.models import (
    User,
    UserWallet,
    Deposit,
    DepositStatus,
    Transaction,
    TransactionType,
    TransactionStatus,
)
from services.wallet_service import get_wallet
from utils.helpers import get_utc_time
from config import TELEGRAM_ADMIN_ID


class DepositService:
    """DB/business logic for deposit domain. Telegram logic lives in bot/handlers/deposit_handler.py"""

    @staticmethod
    def get_user_by_telegram(telegram_id: str):
        with get_db_session() as session:
            return session.query(User).filter_by(telegram_id=telegram_id).first()

    @staticmethod
    def get_wallet_for_user(user_id: int):
        return get_wallet(user_id)

    # -------- Added helpers for deposit monitor --------
    @staticmethod
    def list_user_wallets() -> List[UserWallet]:
        with get_db_session() as session:
            return session.query(UserWallet).all()

    @staticmethod
    def get_deposit_by_tx_hash(tx_hash: str) -> Optional[Deposit]:
        with get_db_session() as session:
            return session.query(Deposit).filter_by(tx_hash=tx_hash).first()

    @staticmethod
    def create_deposit_if_new(
        user_id: int,
        wallet_id: int,
        tx_hash: str,
        amount_trx: Decimal,
        confirmations: int,
    ) -> Deposit:
        """Create a deposit row if not exists. Returns the persisted row."""
        with get_db_session() as session:
            try:
                existing = session.query(Deposit).filter_by(tx_hash=tx_hash).first()
                if existing:
                    return existing

                status = DepositStatus.confirmed if confirmations >= 19 else DepositStatus.pending
                deposit = Deposit(
                    user_id=user_id,
                    wallet_id=wallet_id,
                    tx_hash=tx_hash,
                    amount_trx=amount_trx,
                    confirmations=confirmations,
                    status=status,
                    created_at=get_utc_time(),
                    confirmed_at=get_utc_time() if status == DepositStatus.confirmed else None,
                )
                session.add(deposit)
                session.commit()
                session.refresh(deposit)
                return deposit
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def credit_user_balance_and_log_tx(user_id: int, amount_trx: Decimal, reference_id: int, reference_tx_id: str) -> Transaction:
        """Credits user's ad balance and records a deposit transaction."""
        with get_db_session() as session:
            try:
                user = session.query(User).get(user_id)
                if not user:
                    raise ValueError(f"User {user_id} not found")

                user.account_balance += amount_trx
                user.total_deposited += amount_trx
                tx = Transaction(
                    user_id=user.id,
                    type=TransactionType.deposit,
                    status=TransactionStatus.completed,
                    amount_trx=amount_trx,
                    description=f"Deposit {reference_tx_id}",
                    reference_id=str(reference_id),
                    tx_hash=reference_tx_id,
                )
                session.add(tx)
                session.commit()
                session.refresh(tx)
                return tx
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        with get_db_session() as session:
            return session.query(User).get(user_id)

    @staticmethod
    def create_admin_forward_transaction(amount_trx: Decimal, deposit_tx_id: str, forward_tx_id: str) -> Optional[Transaction]:
        """Create a transaction record for the admin when a part of a user's deposit is forwarded to the main wallet.

        - amount_trx: amount forwarded to the main wallet
        - deposit_tx_id: original user's deposit tx hash
        - forward_tx_id: tx hash of the forwarding transaction to the main wallet
        """
        if not TELEGRAM_ADMIN_ID:
            return None

        with get_db_session() as session:
            try:
                admin_user = session.query(User).filter_by(telegram_id=str(TELEGRAM_ADMIN_ID)).first()
                if not admin_user:
                    return None

                tx = Transaction(
                    user_id=admin_user.id,
                    type=TransactionType.custom,
                    amount_trx=amount_trx,
                    status=TransactionStatus.completed,
                    description=f"Forwarded to main wallet from deposit {deposit_tx_id}",
                    reference_id=str(deposit_tx_id),
                    tx_hash=forward_tx_id,
                )
                session.add(tx)
                session.commit()
                session.refresh(tx)
                return tx
            except Exception:
                session.rollback()
                raise