from __future__ import annotations

from decimal import Decimal

from bot.keyboards import transaction_details_inline_keyboard
from services.withdrawal_service import WithdrawalService
from blockchain.tron_client import send_trx
from utils.logger import get_logger
from bot.utils import safe_notify_user
from bot.messages import (
    msg_withdrawal_processed,
    msg_withdrawal_failed,
    msg_withdrawal_failed_insufficient_balance,
)
from config import TRON_PRIVATE_KEY


logger = get_logger("withdrawal_processor")


def process_withdrawals():
    logger.info("[Worker] Processing pending withdrawals started.")
    try:
        withdrawals = WithdrawalService.list_pending_withdrawals()
        for wd in withdrawals:
            user = WithdrawalService.get_user_by_id(wd.user_id)
            if user and user.account_balance >= Decimal(wd.amount_trx):
                tx_hash = None
                try:
                    amount_to_send = WithdrawalService.calculate_net_amount(Decimal(wd.amount_trx)).quantize(Decimal('0.000001'))
                    tx_hash = send_trx(TRON_PRIVATE_KEY, wd.to_address, amount_to_send)
                    WithdrawalService.complete_withdrawal(user.id, wd.id, Decimal(wd.amount_trx), tx_hash)
                    logger.info(f"[Withdrawal] {wd.amount_trx} TRX({amount_to_send} TRX) sent to {wd.to_address} (user {user.id}, tx {tx_hash})")
                    # Telegram notification
                    msg = msg_withdrawal_processed(Decimal(wd.amount_trx), tx_hash)
                    safe_notify_user(user.telegram_id, msg, reply_markup=transaction_details_inline_keyboard(tx_hash))
                except Exception as e:
                    WithdrawalService.fail_withdrawal(wd.id, user.id, str(e), tx_hash)
                    logger.error(f"[Withdrawal] TRX send error: {e}")
                    msg = msg_withdrawal_failed(Decimal(wd.amount_trx), str(e), tx_hash)
                    safe_notify_user(user.telegram_id, msg)
            else:
                WithdrawalService.fail_withdrawal(wd.id, user.id, "insufficient balance")
                logger.error(f"[Withdrawal] Insufficient balance for user {user.id if user else 'unknown'}")
                msg = msg_withdrawal_failed_insufficient_balance(Decimal(wd.amount_trx))
                if user:
                    safe_notify_user(user.telegram_id, msg)
    except Exception as e:
        logger.error(f"[Withdrawal] Error: {e}")
        try:
            if 'wd' in locals() and 'user' in locals() and user:
                msg = msg_withdrawal_failed(Decimal(wd.amount_trx), str(e))
                safe_notify_user(user.telegram_id, msg)
        except Exception:
            pass


def run_withdrawal_processor():
    try:
        process_withdrawals()
    except Exception as exc:
        logger.error(f"run_withdrawal_processor failed: {exc}")