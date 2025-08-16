from decimal import Decimal
import pytest

from services.game_service import GameService
from services.fairness_service import FairnessService
from database.models import Transaction, TransactionType, User


# --- Helpers -----------------------------------------------------------------
TRX = Decimal("1.000000")


# --- Multiplier and mechanics -------------------------------------------------
class TestMultiplier:
    def test_calculate_multiplier_matches_formula(self):
        # Example from DevBook: N=50 => ~1.96x with 2% house edge
        m = FairnessService.calculate_multiplier(50, Decimal("0.02"))
        # Theoretical ~ 1/(0.51) * 0.98 = 1.9215686...
        assert m > Decimal("1.90") and m < Decimal("1.95")

    @pytest.mark.parametrize("n", [1, 2, 50, 99, 100])
    def test_calculate_multiplier_bounds(self, n):
        m = FairnessService.calculate_multiplier(n, Decimal("0.02"))
        assert m > 0

    @pytest.mark.parametrize("n", [0, 101, -5])
    def test_calculate_multiplier_invalid_target_raises(self, n):
        with pytest.raises(ValueError):
            FairnessService.calculate_multiplier(n)


# --- Validation and graceful errors ------------------------------------------
class TestValidation:
    def test_bet_below_minimum_raises(self, user_factory):
        u = user_factory(balance=Decimal("10.000000"))
        with pytest.raises(ValueError):
            GameService.play(u.id, Decimal("0.000001"), 50)

    def test_bet_above_maximum_raises(self, user_factory, monkeypatch):
        u = user_factory(balance=Decimal("1000000.000000"))
        # Force a very small MAX to trigger
        monkeypatch.setattr(GameService, "MAX_BET_AMOUNT", Decimal("1.000000"), raising=False)
        with pytest.raises(ValueError):
            GameService.play(u.id, Decimal("2.000000"), 50)

    def test_insufficient_balance_raises(self, user_factory):
        u = user_factory(balance=Decimal("0.500000"))
        with pytest.raises(ValueError):
            GameService.play(u.id, Decimal("1.000000"), 50)

    @pytest.mark.parametrize("target", [1, 100])
    def test_target_bounds_valid(self, user_factory, target):
        u = user_factory(balance=Decimal("100.000000"))
        # Should not raise
        GameService.play(u.id, Decimal("1.000000"), target)

    @pytest.mark.parametrize("target", [0, 101])
    def test_target_bounds_invalid(self, user_factory, target):
        u = user_factory(balance=Decimal("100.000000"))
        with pytest.raises(ValueError):
            GameService.play(u.id, Decimal("1.000000"), target)


# --- Win/loss logic and balance updates --------------------------------------
class TestWinLossFlow:
    def test_loss_debits_only(self, user_factory):
        u = user_factory(balance=Decimal("10.000000"))
        # Force a target so that winning is very hard (e.g., 100)
        outcome = GameService.play(u.id, Decimal("1.000000"), 100, client_seed="fixed")
        # Reload user to check final balance
        from database.database import get_db_session
        with get_db_session() as s:
            ru = s.query(User).get(u.id)
            assert ru.account_balance == Decimal("9.000000")
            # Transactions include bet; payout may or may not exist depending on RNG
            txs = s.query(Transaction).filter(Transaction.user_id == u.id).all()
            assert any(t.type == TransactionType.bet for t in txs)

    def test_win_credits_payout(self, user_factory, monkeypatch):
        u = user_factory(balance=Decimal("10.000000"))
        # Monkeypatch RNG to guarantee a win: result >= target
        from services.fairness_service import FairnessService as FS

        def fixed_roll(server_seed, client_seed, nonce):
            from services.fairness_service import FairnessResult
            return FairnessResult(result_number=100, hex_substring="ffffffff", decimal_result=2**32-1)

        monkeypatch.setattr(FS, "roll_dice", fixed_roll, raising=True)
        outcome = GameService.play(u.id, Decimal("1.000000"), 2, client_seed="any")
        assert outcome.is_winner is True
        # Reload and validate
        from database.database import get_db_session
        with get_db_session() as s:
            ru = s.query(User).get(u.id)
            assert ru.account_balance > Decimal("10.000000") - Decimal("1.000000")
            txs = s.query(Transaction).filter(Transaction.user_id == u.id).all()
            assert any(t.type == TransactionType.bet for t in txs)
            assert any(t.type == TransactionType.payout for t in txs)


# --- Concurrency (light) ------------------------------------------------------
class TestConcurrency:
    def test_second_parallel_bet_is_rejected(self, user_factory):
        u = user_factory(balance=Decimal("50.000000"))
        lock = None
        # Acquire the internal lock to simulate an in-flight bet
        from services.game_service import _get_user_lock
        lock = _get_user_lock(u.id)
        assert lock.acquire(blocking=False) is True
        try:
            with pytest.raises(RuntimeError):
                GameService.play(u.id, Decimal("1.000000"), 50)
        finally:
            try:
                lock.release()
            except Exception:
                pass
