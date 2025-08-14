from database.database import get_db_session
from database.models import UserWallet
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