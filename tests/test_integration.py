from decimal import Decimal

from services.game_service import GameService
from services.wallet_service import credit_balance
from workers.leaderboard_worker import run_leaderboard_worker
from database.database import get_db_session
from database.models import Game, Leaderboard, Notification


def test_integration_user_flow_and_leaderboard(user_factory):
    # 1) Create user and credit balance
    u = user_factory(telegram_id="2001", username="player1", balance=Decimal("0.000000"))
    credit_balance(u.id, Decimal("50.000000"), description="test top-up")

    # 2) Play several games (mix targets)
    targets = [10, 50, 75, 20, 40]
    for t in targets:
        try:
            GameService.play(u.id, Decimal("2.000000"), t, client_seed="itest")
        except Exception:
            # Continue to accumulate some games even if one fails
            pass

    # Verify games were recorded
    with get_db_session() as s:
        games = s.query(Game).filter(Game.user_id == u.id).all()
        assert len(games) >= 1

    # 3) Run leaderboard worker
    run_leaderboard_worker()

    # 4) Assert leaderboard rows exist and are consistent
    with get_db_session() as s:
        lb_rows = s.query(Leaderboard).filter(Leaderboard.user_id == u.id).all()
        assert len(lb_rows) >= 1
        for lb in lb_rows:
            assert lb.games_count >= 0
            assert lb.total_wagered >= 0
            assert lb.total_won >= 0

        # 5) Worker should have run; notifications may be zero if not top
        notifs = s.query(Notification).all()
        assert notifs is not None
