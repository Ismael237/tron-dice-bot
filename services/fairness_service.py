from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Optional, Dict, Any
import secrets
import hmac
import hashlib

from utils.logger import get_logger
from utils.helpers import get_utc_time
from database.database import get_db_session
from database.models import GameSeed, Game, GameStatus, User

# Increase precision for multiplier computations
getcontext().prec = 28

logger = get_logger(__name__)


@dataclass
class FairnessResult:
    result_number: int  # 1-100
    hex_substring: str
    decimal_result: int


class FairnessService:
    """Provably fair engine for dice game.

    - Uses HMAC-SHA256 with key=server_seed and message=f"{client_seed}:{nonce}"
    - Normalizes to [1..100]
    - Provides helpers for seed lifecycle and verification
    - Persists Game/GameSeed using SQLAlchemy via get_db_session()
    """

    # ---------------------- Seed helpers ----------------------
    @staticmethod
    def generate_server_seed() -> str:
        """Return a 64-hex (256-bit) random server seed."""
        seed = secrets.token_hex(32)
        logger.debug(f"Generated server_seed (hex64)")
        return seed

    @staticmethod
    def generate_client_seed_fallback() -> str:
        """Return a shorter random client seed as fallback if user did not provide one."""
        seed = secrets.token_hex(8)  # 16 hex chars
        logger.debug("Generated fallback client_seed")
        return seed

    @staticmethod
    def sha256_hex(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    @classmethod
    def hash_server_seed(cls, server_seed: str) -> str:
        return cls.sha256_hex(server_seed)

    # ---------------------- RNG ----------------------
    @staticmethod
    def hmac_sha256_hex(key_hex: str, message: str) -> str:
        key = bytes.fromhex(key_hex)
        mac = hmac.new(key, message.encode(), hashlib.sha256).hexdigest()
        return mac

    @classmethod
    def roll_dice(cls, server_seed: str, client_seed: str, nonce: int) -> FairnessResult:
        """Compute 1..100 result using HMAC-SHA256.

        Steps per devbook/roadmap:
        - mac = HMAC-SHA256(key=server_seed, msg=f"{client_seed}:{nonce}")
        - take first 8 hex chars -> hex_substring
        - decimal_result = int(hex_substring, 16)
        - result = floor((decimal_result / 4294967295) * 100) + 1
        """
        message = f"{client_seed}:{nonce}"
        mac_hex = cls.hmac_sha256_hex(server_seed, message)
        hex_substring = mac_hex[:8]
        decimal_result = int(hex_substring, 16)
        # 0xFFFFFFFF = 4294967295
        normalized = (decimal_result / 4294967295) * 100
        result_number = int(normalized) + 1  # 1..100
        if result_number < 1:
            result_number = 1
        elif result_number > 100:
            result_number = 100
        logger.debug(
            f"HMAC roll -> msg={message}, mac[:8]={hex_substring}, dec={decimal_result}, result={result_number}"
        )
        return FairnessResult(result_number=result_number, hex_substring=hex_substring, decimal_result=decimal_result)

    @staticmethod
    def compute_game_hash(server_seed_hash: str, client_seed: str, nonce: int) -> str:
        """Stable game hash to disclose prior to revealing server_seed."""
        payload = f"{server_seed_hash}:{client_seed}:{nonce}"
        ghash = hashlib.sha256(payload.encode()).hexdigest()
        return ghash

    # ---------------------- DB hooks ----------------------
    @staticmethod
    def _get_active_seed(session, user_id: int) -> Optional[GameSeed]:
        return (
            session.query(GameSeed)
            .filter_by(user_id=user_id, is_active=True)
            .order_by(GameSeed.created_at.desc())
            .first()
        )

    @classmethod
    def ensure_active_seed(cls, user_id: int, client_seed: Optional[str] = None) -> GameSeed:
        """Return existing active seed or create one. Set/keep client_seed.
        Creates server_seed and its hash if needed. Does not reveal server_seed.
        """
        with get_db_session() as session:
            seed = cls._get_active_seed(session, user_id)
            if seed is None:
                server_seed = cls.generate_server_seed()
                server_seed_hash = cls.hash_server_seed(server_seed)
                cseed = client_seed or cls.generate_client_seed_fallback()
                seed = GameSeed(
                    user_id=user_id,
                    server_seed=server_seed,
                    server_seed_hash=server_seed_hash,
                    client_seed=cseed,
                    is_active=True,
                    nonce_counter=0,
                    created_at=get_utc_time(),
                )
                session.add(seed)
                session.commit()
                session.refresh(seed)
                logger.info(f"Created new active GameSeed for user={user_id}")
            else:
                # Update client_seed if not set and a new one is provided or fallback is needed
                if not seed.client_seed:
                    seed.client_seed = client_seed or cls.generate_client_seed_fallback()
                    session.commit()
                    session.refresh(seed)
                    logger.info(f"Updated client_seed for active GameSeed user={user_id}")
            return seed

    @classmethod
    def rotate_server_seed(cls, user_id: int) -> GameSeed:
        """Reveal/close current active seed, then create a new active seed."""
        with get_db_session() as session:
            current = cls._get_active_seed(session, user_id)
            if current:
                current.is_active = False
                current.revealed_at = get_utc_time()
                session.commit()
            server_seed = cls.generate_server_seed()
            server_seed_hash = cls.hash_server_seed(server_seed)
            new_seed = GameSeed(
                user_id=user_id,
                server_seed=server_seed,
                server_seed_hash=server_seed_hash,
                client_seed=current.client_seed if current else cls.generate_client_seed_fallback(),
                is_active=True,
                nonce_counter=0,
                created_at=get_utc_time(),
            )
            session.add(new_seed)
            session.commit()
            session.refresh(new_seed)
            logger.info(f"Rotated GameSeed for user={user_id}")
            return new_seed

    @staticmethod
    def _increment_nonce(session, seed: GameSeed) -> int:
        seed.nonce_counter = (seed.nonce_counter or 0) + 1
        session.commit()
        session.refresh(seed)
        return seed.nonce_counter

    # ---------------------- Game orchestration ----------------------
    @classmethod
    def calculate_multiplier(cls, target_number: int, house_edge: Decimal | float = Decimal("0.02")) -> Decimal:
        """Per devbook: p = (101 - N) / 100; multi = (1 / p) * (1 - house_edge)."""
        if isinstance(house_edge, float):
            house_edge = Decimal(str(house_edge))
        if not (1 <= target_number <= 100):
            raise ValueError("target_number must be between 1 and 100")
        p = Decimal(101 - target_number) / Decimal(100)
        if p <= 0:
            raise ValueError("Invalid probability computed")
        multi = (Decimal(1) / p) * (Decimal(1) - house_edge)
        return multi

    @classmethod
    def play_game(
        cls,
        user_id: int,
        bet_amount: Decimal,
        target_number: int,
        house_edge: Decimal | float = Decimal("0.02"),
        client_seed: Optional[str] = None,
    ) -> Game:
        """Execute a full provably fair roll and persist the Game row.

        Note: This does not manage user balance. That belongs to game engine/wallet services.
        """
        with get_db_session() as session:
            # Validate user exists
            user = session.query(User).get(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            seed = cls.ensure_active_seed(user_id=user_id, client_seed=client_seed)
            # Re-attach to this session if needed
            seed = session.query(GameSeed).get(seed.id)

            nonce = cls._increment_nonce(session, seed)
            roll = cls.roll_dice(seed.server_seed, seed.client_seed, nonce)

            multiplier = cls.calculate_multiplier(target_number, house_edge)
            is_winner = roll.result_number >= target_number
            win_amount = (bet_amount * multiplier) if is_winner else Decimal("0")

            game_hash = cls.compute_game_hash(seed.server_seed_hash, seed.client_seed, nonce)

            game = Game(
                user_id=user_id,
                bet_amount=bet_amount,
                target_number=target_number,
                result_number=roll.result_number,
                multiplier=multiplier,
                win_amount=win_amount,
                is_winner=is_winner,
                house_edge=Decimal(house_edge) if isinstance(house_edge, float) else house_edge,
                server_seed=seed.server_seed,
                client_seed=seed.client_seed,
                nonce=nonce,
                game_hash=game_hash,
                status=GameStatus.completed,
                created_at=get_utc_time(),
            )
            session.add(game)
            session.commit()
            session.refresh(game)
            logger.info(
                f"Game created user={user_id} bet={bet_amount} target={target_number} result={roll.result_number} win={win_amount}"
            )
            return game

    # ---------------------- Verification ----------------------
    @classmethod
    def verify_game_fields(
        cls,
        server_seed: str,
        client_seed: str,
        nonce: int,
        expected_result_number: int,
        expected_game_hash: str,
    ) -> Dict[str, Any]:
        """Recompute RNG and game_hash to verify stored game data."""
        roll = cls.roll_dice(server_seed, client_seed, nonce)
        server_seed_hash = cls.hash_server_seed(server_seed)
        game_hash = cls.compute_game_hash(server_seed_hash, client_seed, nonce)
        ok = (roll.result_number == expected_result_number) and (game_hash == expected_game_hash)
        logger.debug(
            f"verify -> expected_result={expected_result_number}, got={roll.result_number}, "
            f"expected_hash={expected_game_hash}, got={game_hash}, ok={ok}"
        )
        return {
            "ok": ok,
            "recomputed_result": roll.result_number,
            "recomputed_game_hash": game_hash,
            "hex_substring": roll.hex_substring,
            "decimal_result": roll.decimal_result,
        }

    @classmethod
    def verify_game_by_id(cls, game_id: int) -> Dict[str, Any]:
        with get_db_session() as session:
            game = session.query(Game).get(game_id)
            if not game:
                raise ValueError(f"Game {game_id} not found")
            return cls.verify_game_fields(
                server_seed=game.server_seed,
                client_seed=game.client_seed,
                nonce=game.nonce,
                expected_result_number=game.result_number,
                expected_game_hash=game.game_hash,
            )
