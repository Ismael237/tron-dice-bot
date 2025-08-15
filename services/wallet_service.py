from decimal import Decimal
from typing import Optional

from database.database import get_db_session
from database.models import User, Transaction, TransactionType, TransactionStatus, UserWallet
from blockchain.tron_client import generate_wallet
from utils.encryption import encrypt_data


def get_or_create_wallet(user_id):
    with get_db_session() as session:
        wallet = session.query(UserWallet).filter_by(user_id=user_id).first()
        if wallet:
            return wallet
        address, privkey = generate_wallet()
        encrypted_key = encrypt_data(privkey.encode())
        wallet = UserWallet(
            user_id=user_id,
            address=address,
            private_key_encrypted=encrypted_key
        )
        try:
            session.add(wallet)
            session.commit()
            session.refresh(wallet)
            return wallet
        except Exception:
            session.rollback()
            raise


def get_wallet(user_id):
    with get_db_session() as session:
        wallet = session.query(UserWallet).filter_by(user_id=user_id).first()
        return wallet


# ---------------- Generic helpers for balance + transactions ----------------

def credit_balance(
    user_id: int,
    amount: Decimal,
    *,
    tx_type: TransactionType = TransactionType.custom,
    description: Optional[str] = None,
    reference_id: Optional[str] = None,
    tx_hash: Optional[str] = None,
) -> Transaction:
    """Credit user's account balance and create a transaction record.
    Idempotency is NOT enforced here; caller should ensure no duplicates.
    """
    with get_db_session() as session:
        try:
            user = session.query(User).get(user_id)
            if not user:
                raise ValueError("User not found")
            user.account_balance += Decimal(amount)
            tx = Transaction(
                user_id=user.id,
                type=tx_type,
                status=TransactionStatus.completed,
                amount_trx=Decimal(amount),
                description=description,
                reference_id=str(reference_id) if reference_id is not None else None,
                tx_hash=tx_hash,
            )
            session.add(tx)
            session.commit()
            session.refresh(tx)
            return tx
        except Exception:
            session.rollback()
            raise


def debit_balance(
    user_id: int,
    amount: Decimal,
    *,
    tx_type: TransactionType = TransactionType.custom,
    description: Optional[str] = None,
    reference_id: Optional[str] = None,
    tx_hash: Optional[str] = None,
) -> Transaction:
    """Debit user's account balance and create a transaction record.
    Ensures user has sufficient balance.
    """
    with get_db_session() as session:
        try:
            user = session.query(User).get(user_id)
            if not user:
                raise ValueError("User not found")
            if Decimal(user.account_balance) < Decimal(amount):
                raise ValueError("Insufficient balance")
            user.account_balance -= Decimal(amount)
            tx = Transaction(
                user_id=user.id,
                type=tx_type,
                status=TransactionStatus.completed,
                amount_trx=Decimal(amount),
                description=description,
                reference_id=str(reference_id) if reference_id is not None else None,
                tx_hash=tx_hash,
            )
            session.add(tx)
            session.commit()
            session.refresh(tx)
            return tx
        except Exception:
            session.rollback()
            raise


def record_game_transaction(
    user_id: int,
    *,
    amount: Decimal,
    tx_type: TransactionType,
    description: Optional[str] = None,
    reference_id: Optional[str] = None,
    tx_hash: Optional[str] = None,
) -> Transaction:
    """Generic helper to log game-related transactions (bet/payout/etc.).
    Does not touch balance; use credit/debit helpers when needed.
    """
    with get_db_session() as session:
        try:
            user = session.query(User).get(user_id)
            if not user:
                raise ValueError("User not found")
            tx = Transaction(
                user_id=user.id,
                type=tx_type,
                status=TransactionStatus.completed,
                amount_trx=Decimal(amount),
                description=description,
                reference_id=str(reference_id) if reference_id is not None else None,
                tx_hash=tx_hash,
            )
            session.add(tx)
            session.commit()
            session.refresh(tx)
            return tx
        except Exception:
            session.rollback()
            raise