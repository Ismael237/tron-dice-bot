from __future__ import annotations

import time
from decimal import Decimal

from bot.keyboards import transaction_details_inline_keyboard
from services.deposit_service import DepositService
from database.models import UserWallet, DepositStatus
from utils.encryption import decrypt_text
from blockchain.tron_client import get_trx_transactions, send_trx, get_main_wallet
from utils.logger import get_logger
from bot.utils import safe_notify_user
from config import DEPOSIT_TO_MAIN_WALLET_RATE, TELEGRAM_ADMIN_ID
from bot.messages import (
    msg_deposit_confirmed,
    msg_deposit_failed,
    msg_deposit_forwarded,
    msg_deposit_forward_failed,
)


logger = get_logger(__name__)


def forward_deposit_to_main_wallet(wallet: UserWallet, amount: Decimal, deposit_tx_id: str) -> None:
    """Forward a proportion of a user's deposit to the main wallet."""
    try:
        encrypted_key = wallet.private_key_encrypted
        # Decrypt the private key and convert to hex string expected by tron_client
        private_key = decrypt_text(encrypted_key)

        main_wallet_address, _ = get_main_wallet()
        if not main_wallet_address:
            logger.error("[Deposit] Main wallet address not configured.")
            return

        # Calculate amount to forward according to configurable rate
        amount_to_send = (amount * Decimal(str(DEPOSIT_TO_MAIN_WALLET_RATE))).quantize(Decimal('0.000001'))
        if amount_to_send <= 0:
            logger.warning("[Deposit] Calculated amount to send to main wallet is zero, skipping.")
            return
        tx_id = send_trx(private_key, main_wallet_address, amount_to_send)
        if tx_id:
            logger.info(f"[Deposit] {amount_to_send} TRX sent to main wallet {main_wallet_address} (tx {tx_id})")
            # Create admin transaction log for this forward
            try:
                DepositService.create_admin_forward_transaction(amount_to_send, deposit_tx_id, tx_id)
            except Exception as _log_err:
                logger.warning(f"[Deposit] Failed to create admin forward transaction: {_log_err}")
            msg = msg_deposit_forwarded(amount_to_send, deposit_tx_id, tx_id)
            safe_notify_user(TELEGRAM_ADMIN_ID, msg, reply_markup=transaction_details_inline_keyboard(tx_id))

    except Exception as e:
        logger.error(f"[Deposit] Error forwarding deposit to main wallet: {e}")
        try:
            msg = msg_deposit_forward_failed(amount, deposit_tx_id, str(e))
            safe_notify_user(TELEGRAM_ADMIN_ID, msg)
        except Exception:
            pass


def monitor_deposits():
    logger.info("[Worker] Monitoring TRON deposits started.")
    call_count = 0
    try:
        wallets = DepositService.list_user_wallets()
        for wallet in wallets:
            call_count += 1
            if call_count % 10 == 0:  # Every 10th call
                time.sleep(1.2)  # Sleep for 1.2 seconds
            txs = get_trx_transactions(wallet.address)
            for tx in txs:
                tx_id = tx['txID']
                exists = DepositService.get_deposit_by_tx_hash(tx_id)
                if not exists:
                    amount = Decimal(tx['amount']) / Decimal('1000000')
                    confirmations = tx.get('confirmations', 0)
                    deposit = DepositService.create_deposit_if_new(
                        user_id=wallet.user_id,
                        wallet_id=wallet.id,
                        tx_hash=tx_id,
                        amount_trx=amount,
                        confirmations=confirmations,
                    )
                    if deposit.status == DepositStatus.confirmed:
                        user = DepositService.get_user_by_id(wallet.user_id)
                        if user:
                            DepositService.credit_user_balance_and_log_tx(user.id, amount, deposit.id, tx_id)
                            logger.info(f"[Deposit] {amount} TRX credited to user {user.id} (tx {tx_id})")
                            # Telegram notification
                            msg = msg_deposit_confirmed(amount, tx_id)
                            safe_notify_user(user.telegram_id, msg, reply_markup=transaction_details_inline_keyboard(tx_id))

                            forward_deposit_to_main_wallet(wallet, amount, tx_id)
    except Exception as e:
        logger.error(f"[Deposit] Error: {e}")
        try:
            # best-effort notification if we have context
            if 'user' in locals() and 'amount' in locals():
                msg = msg_deposit_failed(amount, str(e))
                safe_notify_user(user.telegram_id, msg)
        except Exception:
            pass


def run_deposit_monitor():
    try:
        monitor_deposits()
    except Exception as exc:
        logger.error(f"run_deposit_monitor failed: {exc}")