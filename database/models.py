"""
Database models
Defines all database tables and relationships
Integrates base models, utilities, and models
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Enum, Boolean, Text, Date, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, Session
import enum
from sqlalchemy.dialects.postgresql import JSONB
from datetime import date
from utils.helpers import get_utc_time

# Create the base class for all models
Base = declarative_base()


class TimestampMixin:
    """Mixin to add timestamp fields to models"""
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=get_utc_time, nullable=False)
    
    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=get_utc_time, onupdate=get_utc_time, nullable=False)


class BaseModel(Base, TimestampMixin):
    """
    Base model class with common fields and methods
    All models should inherit from this class
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    
    def to_dict(self) -> dict:
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: dict):
        """Update model instance from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def create(cls, db: Session, **kwargs):
        """Create a new instance and save to database"""
        instance = cls(**kwargs)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance
    
    @classmethod
    def get_by_id(cls, db: Session, id: int):
        """Get instance by ID"""
        return db.query(cls).filter(cls.id == id).first()
    
    @classmethod
    def get_all(cls, db: Session, skip: int = 0, limit: int = 100):
        """Get all instances with pagination"""
        return db.query(cls).offset(skip).limit(limit).all()
    
    def save(self, db: Session):
        """Save instance to database"""
        db.add(self)
        db.commit()
        db.refresh(self)
        return self
    
    def delete(self, db: Session):
        """Delete instance from database"""
        db.delete(self)
        db.commit()
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"

# Enums for the system
class DepositStatus(enum.Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    failed = 'failed'


class WithdrawalStatus(enum.Enum):
    pending = 'pending'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'


class TransactionType(enum.Enum):
    deposit = 'deposit'
    withdrawal = 'withdrawal'
    referral_commission = 'referral_commission'
    fee = 'fee'
    bet = 'bet'
    payout = 'payout'
    custom = 'custom'
    bonus = 'bonus'


class TransactionStatus(enum.Enum):
    pending = 'pending'
    completed = 'completed'
    failed = 'failed'


class CommissionType(enum.Enum):
    deposit = 'deposit'
    earning = 'earning'
    custom = 'custom'


class CommissionStatus(enum.Enum):
    pending = 'pending'
    paid = 'paid'


class GameStatus(enum.Enum):
    pending = 'pending'
    completed = 'completed'
    cancelled = 'cancelled'


# Models
class User(BaseModel):
    """User model for marketplace participants and advertisers"""
    __tablename__ = 'users'
    
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    referral_code = Column(String, unique=True, nullable=False, index=True)
    sponsor_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    account_balance = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    total_deposited = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    total_withdrawn = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    total_referral_earnings = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # Added per DevBook 3.1.1
    total_games_played = Column(Integer, default=0, nullable=False)
    total_games_won = Column(Integer, default=0, nullable=False)
    biggest_win = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    biggest_loss = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    first_bet_bonus_used = Column(Boolean, default=False, nullable=False)
    first_deposit_bonus_used = Column(Boolean, default=False, nullable=False)
    last_activity_at = Column(DateTime, nullable=True)
    
    # Relationships
    sponsor = relationship("User", remote_side=lambda: [User.id], back_populates="referrals")
    referrals = relationship("User", back_populates="sponsor", foreign_keys=[sponsor_id])
    wallets = relationship("UserWallet", back_populates="user")
    deposits = relationship("Deposit", back_populates="user")
    withdrawals = relationship("Withdrawal", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    commissions_received = relationship("ReferralCommission", foreign_keys="ReferralCommission.user_id", back_populates="beneficiary")
    commissions_generated = relationship("ReferralCommission", foreign_keys="ReferralCommission.referred_user_id", back_populates="referrer")
    # New relationships
    games = relationship("Game", back_populates="user")
    game_seeds = relationship("GameSeed", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    user_challenges = relationship("UserChallenge", back_populates="user")
    leaderboard_entries = relationship("Leaderboard", back_populates="user")


class UserWallet(BaseModel):
    """User wallet model for TRON addresses"""
    __tablename__ = 'user_wallets'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    address = Column(String, nullable=False, unique=True)
    private_key_encrypted = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="wallets")
    deposits = relationship("Deposit", back_populates="wallet")


class Deposit(BaseModel):
    """Deposit model for tracking TRX deposits"""
    __tablename__ = 'deposits'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    wallet_id = Column(Integer, ForeignKey('user_wallets.id'), nullable=False)
    tx_hash = Column(String, nullable=False, unique=True)
    amount_trx = Column(Numeric(precision=18, scale=6), nullable=False)
    confirmations = Column(Integer, default=0, nullable=False)
    status = Column(Enum(DepositStatus), default=DepositStatus.pending, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="deposits")
    wallet = relationship("UserWallet", back_populates="deposits")


class Withdrawal(BaseModel):
    """Withdrawal model for tracking TRX withdrawals"""
    __tablename__ = 'withdrawals'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount_trx = Column(Numeric(precision=18, scale=6), nullable=False)
    fee_trx = Column(Numeric(precision=18, scale=6), nullable=False)
    to_address = Column(String, nullable=False)
    tx_hash = Column(String, nullable=True)
    status = Column(Enum(WithdrawalStatus), default=WithdrawalStatus.pending, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="withdrawals")


class ReferralCommission(BaseModel):
    """Referral commission model for tracking commissions"""
    __tablename__ = 'referral_commissions'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Commission recipient
    referred_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Commission generator
    transaction_id = Column(String, nullable=False)  # Reference transaction ID
    commission_type = Column(Enum(CommissionType), nullable=False)
    amount_trx = Column(Numeric(precision=18, scale=6), nullable=False)
    percentage = Column(Numeric(precision=5, scale=4), nullable=False)
    status = Column(Enum(CommissionStatus), default=CommissionStatus.pending, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    
    # Relationships
    beneficiary = relationship("User", foreign_keys=[user_id], back_populates="commissions_received")
    referrer = relationship("User", foreign_keys=[referred_user_id], back_populates="commissions_generated")


class Transaction(BaseModel):
    """Transaction model for tracking all financial operations"""
    __tablename__ = 'transactions'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount_trx = Column(Numeric(precision=18, scale=6), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.pending, nullable=False)
    description = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)
    tx_hash = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")


class Game(BaseModel):
    """Game (dice roll) result and fairness data"""
    __tablename__ = 'games'

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    bet_amount = Column(Numeric(precision=18, scale=6), nullable=False)
    target_number = Column(Integer, nullable=False)  # 1-100
    result_number = Column(Integer, nullable=False)  # 1-100
    multiplier = Column(Numeric(precision=10, scale=4), nullable=False)
    win_amount = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    is_winner = Column(Boolean, nullable=False)
    house_edge = Column(Numeric(precision=5, scale=4), default=0.02, nullable=False)
    server_seed = Column(String(64), nullable=False)
    client_seed = Column(String(64), nullable=False)
    nonce = Column(Integer, nullable=False)
    game_hash = Column(String(128), nullable=False)
    status = Column(Enum(GameStatus), default=GameStatus.completed, nullable=False)

    # Relationships
    user = relationship("User", back_populates="games")

    __table_args__ = (
        UniqueConstraint('game_hash', name='uq_games_game_hash'),
    )


class GameSeed(BaseModel):
    """Provably fair seeds per user"""
    __tablename__ = 'game_seeds'

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    server_seed = Column(String(64), nullable=False)
    server_seed_hash = Column(String(128), nullable=False)
    client_seed = Column(String(64), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    nonce_counter = Column(Integer, default=0, nullable=False)
    revealed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="game_seeds")

    __table_args__ = (
        UniqueConstraint('server_seed_hash', name='uq_game_seeds_server_seed_hash'),
    )


class Leaderboard(BaseModel):
    """Aggregated leaderboard per period"""
    __tablename__ = 'leaderboard'

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    period_type = Column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly'
    period_date = Column(Date, nullable=False)
    total_wagered = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    total_won = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    net_profit = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    games_count = Column(Integer, default=0, nullable=False)
    biggest_win = Column(Numeric(precision=18, scale=6), default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="leaderboard_entries")

    __table_args__ = (
        UniqueConstraint('user_id', 'period_type', 'period_date', name='uq_leaderboard_user_period'),
    )


class Challenge(BaseModel):
    """Challenge definitions"""
    __tablename__ = 'challenges'

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    challenge_type = Column(String(50), nullable=False)  # 'bet_count', 'wagered_amount', 'win_streak'
    target_value = Column(Numeric(precision=18, scale=6), nullable=False)
    reward_amount = Column(Numeric(precision=18, scale=6), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user_challenges = relationship("UserChallenge", back_populates="challenge")


class UserChallenge(BaseModel):
    """User progress on challenges"""
    __tablename__ = 'user_challenges'

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    challenge_id = Column(Integer, ForeignKey('challenges.id'), nullable=False)
    current_progress = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    reward_claimed = Column(Boolean, default=False, nullable=False)
    date_started = Column(Date, default=date.today, nullable=False)

    # Relationships
    user = relationship("User", back_populates="user_challenges")
    challenge = relationship("Challenge", back_populates="user_challenges")

    __table_args__ = (
        UniqueConstraint('user_id', 'challenge_id', name='uq_user_challenges_user_challenge'),
    )


class Notification(BaseModel):
    """User notifications with optional payload"""
    __tablename__ = 'notifications'

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    data = Column(JSONB, nullable=True)  # Additional data

    # Relationships
    user = relationship("User", back_populates="notifications")
