from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from threading import Lock
from typing import Optional, Dict

from database.database import get_db_session
from database.models import User, Transaction, TransactionType
from services.fairness_service import FairnessService
from config import HOUSE_EDGE, MIN_BET_AMOUNT, MAX_BET_AMOUNT
from utils.helpers import get_utc_time
from utils.logger import get_logger

logger = get_logger(__name__)


# In-memory user locks to prevent concurrent betting for the same user (per-process)
_user_locks: Dict[int, Lock] = {}


def _get_user_lock(user_id: int) -> Lock:
    if user_id not in _user_locks:
        _user_locks[user_id] = Lock()
    return _user_locks[user_id]


@dataclass
class GameOutcome:
    """Lightweight return type for a played game."""
    game_id: int
    is_winner: bool
    bet_amount: Decimal
    win_amount: Decimal
    target_number: int
    result_number: int
    multiplier: Decimal
    balance_after: Decimal


class GameService:
    """Core game mechanics and orchestration service.

    Responsibilities (see devbook.md and roadmap.md commits 1–4):
    - Validate bets and balance
    - Calculate multiplier using 2% default house edge
    - Execute full game flow (uses FairnessService for provably fair roll + Game persistence)
    - Update user balance for wins/losses and record transactions
    - Track user statistics (games played/won, biggest win/loss)
    - Prevent concurrent bets per-user using a simple in-memory lock
    """

    # Defaults aligned with DevBook (can be overridden via environment)
    HOUSE_EDGE: float = float(HOUSE_EDGE)
    MIN_BET_AMOUNT: Decimal = Decimal(str(MIN_BET_AMOUNT))
    MAX_BET_AMOUNT: Decimal = Decimal(str(MAX_BET_AMOUNT))

    # TRX precision: 6 decimals
    TRX_PRECISION = Decimal("0.000001")

    # ---------------------- Validation helpers ----------------------
    @classmethod
    def _validate_bet_amount(cls, amount: Decimal):
        try:
            amt = Decimal(amount).quantize(cls.TRX_PRECISION)
        except (InvalidOperation, TypeError):
            raise ValueError("Invalid bet amount")
        if amt <= 0:
            raise ValueError("Bet amount must be positive")
        if amt < cls.MIN_BET_AMOUNT:
            raise ValueError(f"Bet amount below minimum: {cls.MIN_BET_AMOUNT}")
        if amt > cls.MAX_BET_AMOUNT:
            raise ValueError(f"Bet amount above maximum: {cls.MAX_BET_AMOUNT}")
        return amt

    @staticmethod
    def _validate_target_number(target_number: int):
        if not isinstance(target_number, int):
            raise ValueError("Target number must be an integer")
        if target_number < 1 or target_number > 100:
            raise ValueError("Target number must be between 1 and 100")

    @staticmethod
    def _ensure_sufficient_balance(user: User, amount: Decimal):
        if user.account_balance is None:
            raise ValueError("User balance not initialized")
        if Decimal(user.account_balance) < amount:
            raise ValueError("Insufficient balance")

    # ---------------------- Public API ----------------------
    @classmethod
    def play(
        cls,
        user_id: int,
        bet_amount: Decimal,
        target_number: int,
        client_seed: Optional[str] = None,
    ) -> GameOutcome:
        """Place a bet and play a single dice game.

        Flow:
        - Validate inputs and limits
        - Lock per-user to avoid concurrent bets
        - Debit bet, record bet transaction
        - Call FairnessService.play_game (persists Game row)
        - If win: credit payout, record payout transaction
        - Update user statistics and last activity
        - Commit, then return outcome with final balance
        """
        cls._validate_target_number(target_number)
        bet_amount = cls._validate_bet_amount(bet_amount)

        user_lock = _get_user_lock(user_id)
        if not user_lock.acquire(blocking=False):
            raise RuntimeError("A bet is already in progress for this user. Please wait.")

        try:
            with get_db_session() as session:
                try:
                    user = session.query(User).get(user_id)
                    if not user or not user.is_active:
                        raise ValueError("User not found or inactive")

                    # Balance check and debit
                    cls._ensure_sufficient_balance(user, bet_amount)
                    user.account_balance = (Decimal(user.account_balance) - bet_amount).quantize(cls.TRX_PRECISION)

                    # Record bet transaction (custom type)
                    bet_tx = Transaction(
                        user_id=user_id,
                        type=TransactionType.bet,
                        amount_trx=bet_amount,
                        description=f"Bet placed: target={target_number}",
                        reference_id=None,
                    )
                    session.add(bet_tx)

                    # Persist intermediate state before external call
                    session.commit()

                except Exception:
                    session.rollback()
                    raise

            # FairnessService manages its own DB session and will persist the Game
            try:
                game = FairnessService.play_game(
                    user_id=user_id,
                    bet_amount=bet_amount,
                    target_number=target_number,
                    house_edge=cls.HOUSE_EDGE,
                    client_seed=client_seed,
                )
            except Exception as e:
                # Early-fail refund if roll/persistence fails
                with get_db_session() as session:
                    refund_user = session.query(User).get(user_id)
                    if refund_user is not None:
                        refund_user.account_balance = (Decimal(refund_user.account_balance) + bet_amount).quantize(cls.TRX_PRECISION)
                        session.commit()
                        logger.error(f"Fairness play failed. Refunded bet {bet_amount} to user={user_id}: {e}")
                raise

            # Post-game balance and stats updates in a new DB session
            with get_db_session() as session:
                try:
                    user = session.query(User).get(user_id)
                    if not user:
                        # Extremely unlikely here
                        raise ValueError("User not found after game")

                    is_winner = bool(game.is_winner)
                    win_amount = Decimal(game.win_amount).quantize(cls.TRX_PRECISION)

                    if is_winner and win_amount > 0:
                        user.account_balance = (Decimal(user.account_balance) + win_amount).quantize(cls.TRX_PRECISION)
                        payout_tx = Transaction(
                            user_id=user_id,
                            type=TransactionType.payout,
                            amount_trx=win_amount,
                            description=f"Payout for game #{game.id}",
                            reference_id=str(game.id),
                        )
                        session.add(payout_tx)

                    # Update stats
                    user.total_games_played = int(user.total_games_played or 0) + 1
                    if is_winner:
                        user.total_games_won = int(user.total_games_won or 0) + 1
                        # Biggest win by absolute payout
                        if Decimal(user.biggest_win or 0) < win_amount:
                            user.biggest_win = win_amount
                    else:
                        # Biggest loss by bet size (loss = full bet at MVP)
                        if Decimal(user.biggest_loss or 0) < bet_amount:
                            user.biggest_loss = bet_amount

                    user.last_activity_at = get_utc_time()

                    session.commit()

                    # Prepare outcome
                    outcome = GameOutcome(
                        game_id=game.id,
                        is_winner=is_winner,
                        bet_amount=Decimal(game.bet_amount).quantize(cls.TRX_PRECISION),
                        win_amount=win_amount,
                        target_number=int(game.target_number),
                        result_number=int(game.result_number),
                        multiplier=Decimal(game.multiplier),
                        balance_after=Decimal(user.account_balance).quantize(cls.TRX_PRECISION),
                    )
                    logger.info(
                        f"Game #{outcome.game_id} user={user_id} target={outcome.target_number} "
                        f"result={outcome.result_number} bet={outcome.bet_amount} win={outcome.win_amount} "
                        f"balance_after={outcome.balance_after}"
                    )
                    return outcome
                except Exception:
                    session.rollback()
                    # Attempt refund on failure after game persistence
                    try:
                        with get_db_session() as refund_sess:
                            refund_user = refund_sess.query(User).get(user_id)
                            if refund_user is not None:
                                refund_user.account_balance = (Decimal(refund_user.account_balance) + bet_amount).quantize(cls.TRX_PRECISION)
                                refund_sess.commit()
                                logger.error(
                                    f"Post-game failure. Refunded bet {bet_amount} to user={user_id}"
                                )
                    except Exception as refund_err:
                        logger.exception(
                            f"Failed to refund user={user_id} after post-game error: {refund_err}"
                        )
                    raise
        finally:
            user_lock.release()

    # ---------------------- Read helpers ----------------------
    @staticmethod
    def user_can_bet(user_id: int, amount: Decimal) -> bool:
        """Quick check without side effects."""
        try:
            amount = Decimal(amount)
        except (InvalidOperation, TypeError):
            return False
        with get_db_session() as session:
            user = session.query(User).get(user_id)
            if not user or not user.is_active:
                return False
            return Decimal(user.account_balance or 0) >= amount
