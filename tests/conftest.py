import os
import sys
import base64
import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import itertools

# Make sure project root is on sys.path for module imports like `database`, `services`, etc.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure a default in-memory DATABASE_URL so importing database.database doesn't fail
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Initialize ENCRYPTION_KEY early (module import time) for tests
_key_bytes = b"A" * 32
_b64key = base64.b64encode(_key_bytes).decode().rstrip("=")
os.environ.setdefault("ENCRYPTION_KEY", _b64key)
try:
    import config as _cfg
    setattr(_cfg, "ENCRYPTION_KEY", os.environ["ENCRYPTION_KEY"])  # ensure config sees it
except Exception:
    pass

# Important: import project modules after env/monkeypatching when needed
from database import database as db_mod
from database.models import Base, User

# Global counter to ensure unique user telegram_ids across all tests (shared DB engine)
_user_id_counter = itertools.count(1000)


@pytest.fixture(scope="session")
def sqlite_memory_engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(sqlite_memory_engine, monkeypatch):
    """Provide a clean SQLAlchemy session and monkeypatch project's SessionLocal."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_memory_engine)
    monkeypatch.setattr(db_mod, "engine", sqlite_memory_engine, raising=False)
    monkeypatch.setattr(db_mod, "SessionLocal", TestingSessionLocal, raising=False)

    # Provide context manager behavior consistent with get_db_session
    yield TestingSessionLocal()


@pytest.fixture(scope="function")
def user_factory(db_session):
    def _create_user(telegram_id: str | None = None, username: str = "tester", balance: Decimal = Decimal("100.000000")) -> User:
        # Allocate a unique telegram_id if not provided to avoid UNIQUE constraint errors
        tid = str(telegram_id) if telegram_id is not None else str(next(_user_id_counter))
        u = User(
            telegram_id=tid,
            username=username,
            first_name="Test",
            last_name="User",
            referral_code=f"ref_{tid}",
            account_balance=Decimal(balance),
            is_active=True,
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        return u
    return _create_user


@pytest.fixture(autouse=True)
def mock_tron_client(monkeypatch):
    """Mock blockchain.tron_client.* for all tests (no network)."""
    import blockchain.tron_client as tron

    def fake_get_main_wallet():
        return ("TMockAddress1234567890123456789012345678", "privkey_dummy")

    def fake_get_trx_balance(address: str):
        return Decimal("10000.0")

    def fake_send_trx(from_priv: str, to_addr: str, amount: Decimal):
        # Return a fake tx hash
        return "0xTESTTXHASH"

    def fake_generate_wallet():
        return ("TUserMockAddress12345678901234567890123", "user_privkey_dummy")

    monkeypatch.setattr(tron, "get_main_wallet", fake_get_main_wallet, raising=True)
    monkeypatch.setattr(tron, "get_trx_balance", fake_get_trx_balance, raising=True)
    monkeypatch.setattr(tron, "send_trx", fake_send_trx, raising=True)
    monkeypatch.setattr(tron, "generate_wallet", fake_generate_wallet, raising=True)


@pytest.fixture(autouse=True)
def mock_telegram(monkeypatch):
    """Neutralize Telegram sends in bot.utils.safe_notify_user/notify_user."""
    import bot.utils as butils

    async def noop_notify_user(telegram_id, message, reply_markup=None):
        return None

    def noop_safe_notify_user(telegram_id, message, reply_markup=None):
        return None

    monkeypatch.setattr(butils, "notify_user", noop_notify_user, raising=True)
    monkeypatch.setattr(butils, "safe_notify_user", noop_safe_notify_user, raising=True)


@pytest.fixture(scope="function", autouse=True)
def ensure_encryption_key(monkeypatch):
    """Provide a valid ENCRYPTION_KEY for utils.encryption import-time validation."""
    key_bytes = b"A" * 32
    b64key = base64.b64encode(key_bytes).decode().rstrip("=")
    # Patch environment and config module
    monkeypatch.setenv("ENCRYPTION_KEY", b64key)
    import config as cfg
    monkeypatch.setattr(cfg, "ENCRYPTION_KEY", b64key, raising=False)
    yield
