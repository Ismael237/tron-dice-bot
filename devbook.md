# TronDiceBot MVP - Complete DevBook

## 1. Project Overview

### 1.1 Description
TronDiceBot is a Telegram dice game bot using the TRON (TRX) blockchain. Users bet on the outcome of a virtual 1–100 die roll. Payouts are based on probability with a fixed 2% house edge.

### 1.2 MVP Objectives
- Simple, intuitive gameplay via Telegram
- Secure TRX payments
- Provably fair randomness
- Transparent bet and payout tracking
- Basic referral system

### 1.3 Target Audience
- Crypto users seeking a simple, transparent game
- Telegram users familiar with cryptocurrencies
- International audience (optional multilingual UI)

### 1.4 Development Estimate
- Duration: 2–3 weeks
- Complexity: Medium (crypto security + provable fairness)
- Technologies: Python, PostgreSQL, TRON API, Telegram Bot API

## 2. Technical Architecture

### 2.1 Tech Stack
- Backend: Python 3.10+, FastAPI/Flask (optional for admin panel)
- Database: PostgreSQL 13+ with SQLAlchemy ORM
- Blockchain: TRON Network (TRX)
- Bot: python-telegram-bot
- Scheduled tasks: APScheduler
- Encryption: cryptography (private keys)
- RNG: Python secrets module

### 2.2 Module Structure
```
tron-dice-bot/
├── main.py                     # Main entry point
├── config.py                   # Centralized configuration
├── blockchain/
│   └── tron_client.py          # TRON client
├── bot/
│   ├── handlers/
│   │   ├── game_handlers.py    # Game handlers
│   │   ├── wallet_handlers.py  # Wallet handlers
│   │   └── admin_handlers.py   # Admin handlers
│   ├── keyboards.py            # Telegram keyboards
│   ├── messages.py             # Messages and formatting
│   └── utils.py                # Bot utilities
├── services/
│   ├── game_service.py         # Core game logic
│   ├── fairness_service.py     # Provably fair system
│   ├── leaderboard_service.py  # Leaderboards
│   ├── referral_service.py     # Referral system
│   └── admin_service.py        # Admin services
├── workers/
│   ├── game_processor.py       # Game processing
│   ├── notification_worker.py  # Notifications
│   └── stats_aggregator.py     # Stats aggregation
└── database/
    ├── models.py               # Extended models
    └── migrations/             # Alembic migrations
```

## 3. Data Model

### 3.1 Extensions to Existing Models

#### 3.1.1 Additions to the `users` table
```sql
-- New columns to add
total_games_played INTEGER DEFAULT 0
total_games_won INTEGER DEFAULT 0
biggest_win NUMERIC(18,6) DEFAULT 0
biggest_loss NUMERIC(18,6) DEFAULT 0
first_bet_bonus_used BOOLEAN DEFAULT FALSE
referral_earnings NUMERIC(18,6) DEFAULT 0
last_activity_at TIMESTAMP
```

### 3.2 New Models

#### 3.2.1 Game
```sql
CREATE TYPE game_status AS ENUM ('pending', 'completed', 'cancelled');

CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    bet_amount NUMERIC(18,6) NOT NULL,
    target_number INTEGER NOT NULL, -- Chosen number (1–100)
    result_number INTEGER NOT NULL, -- Dice result
    multiplier NUMERIC(10,4) NOT NULL,
    win_amount NUMERIC(18,6) DEFAULT 0,
    is_winner BOOLEAN NOT NULL,
    house_edge NUMERIC(5,4) DEFAULT 0.02,
    server_seed VARCHAR(64) NOT NULL,
    client_seed VARCHAR(64) NOT NULL,
    nonce INTEGER NOT NULL,
    game_hash VARCHAR(128) NOT NULL,
    status game_status DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 3.2.2 GameSeed (Provably Fair Seeds)
```sql
CREATE TABLE game_seeds (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    server_seed VARCHAR(64) NOT NULL,
    server_seed_hash VARCHAR(128) NOT NULL,
    client_seed VARCHAR(64) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    nonce_counter INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    revealed_at TIMESTAMP
);
```

#### 3.2.3 Leaderboard
```sql
CREATE TABLE leaderboard (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    period_type VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'monthly'
    period_date DATE NOT NULL,
    total_wagered NUMERIC(18,6) DEFAULT 0,
    total_won NUMERIC(18,6) DEFAULT 0,
    net_profit NUMERIC(18,6) DEFAULT 0,
    games_count INTEGER DEFAULT 0,
    biggest_win NUMERIC(18,6) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 3.2.4 Challenge (Daily Challenges)
```sql
CREATE TABLE challenges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    challenge_type VARCHAR(50) NOT NULL, -- 'bet_count', 'wagered_amount', 'win_streak'
    target_value NUMERIC(18,6) NOT NULL,
    reward_amount NUMERIC(18,6) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_challenges (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    challenge_id INTEGER REFERENCES challenges(id),
    current_progress NUMERIC(18,6) DEFAULT 0,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    reward_claimed BOOLEAN DEFAULT FALSE,
    date_started DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 3.2.5 Notification System
```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    data JSONB, -- Additional payload
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 4. Game Logic

### 4.1 Core Mechanics

#### 4.1.1 Dice System
- Range: 1–100 (virtual 100-sided die)
- Rule: User selects number N and places a bet. If result ≥ N, they win
- House Edge: Fixed 2% for the MVP

#### 4.1.2 Multiplier Calculation
```
Win probability = (101 - N) / 100
Theoretical multiplier = 1 / probability
Actual multiplier = theoretical_multiplier × (1 - house_edge)
Payout = stake × actual_multiplier
```

#### 4.1.3 Examples
- N=50: P=51%, Mult=1.96x, Potential payout=196% of stake
- N=90: P=11%, Mult=8.82x, Potential payout=882% of stake
- N=99: P=2%, Mult=49.0x, Potential payout=4900% of stake

### 4.2 Provably Fair System

#### 4.2.1 Seed Generation
- Server Seed: Randomly generated by server (256 bits)
- Client Seed: Provided by user or auto-generated
- Nonce: Incrementing counter per game

#### 4.2.2 Generation Algorithm
```
hash_input = server_seed + ":" + client_seed + ":" + nonce
hash_result = HMAC-SHA256(hash_input)
hex_substring = hash_result[0:8]  # First 8 hex chars
decimal_result = parseInt(hex_substring, 16)
result = (decimal_result / 4294967295) * 100  # Normalize 0–100
final_result = Math.floor(result) + 1  # 1–100
```

#### 4.2.3 User Verification
- Server seed hash shown before the game
- Server seed revealed after the game
- Manual verification interface available

### 4.3 Limits and Controls

#### 4.3.1 Bet Limits
- Minimum: 1 TRX
- Maximum: 1000 TRX (admin configurable)
- Sufficient balance: Mandatory check before bet

#### 4.3.2 Bet Validation
- Check user balance
- Validate parameters (N between 1–100)
- Prevent concurrent bets (user-level lock)

## 5. User Interface (Telegram)

### 5.1 Main Commands

#### 5.1.1 Basic Commands
- `/start` - Onboarding and registration
- `/help` - Help and game rules
- `/balance` - Balance and stats
- `/deposit` - Generate deposit address
- `/withdraw [amount] [address]` - Withdrawal request

#### 5.1.2 Game Commands
- `/play` - Start a new game
- `/history` - Last 10 games
- `/stats` - Detailed personal stats
- `/leaderboard` - Player rankings
- `/verify [game_id]` - Provably fair verification

#### 5.1.3 System Commands
- `/referral` - Referral code and stats
- `/challenges` - Available daily challenges
- `/settings` - Personal settings

### 5.2 Game Interface

#### 5.2.1 Game Flow
1. Initiation: `/play` → Show betting UI
2. Configuration:
   - Select amount (buttons: 1, 5, 10, 50, 100, MAX)
   - Select target number (free input 1–100)
   - Show calculated multiplier
3. Confirmation: Button "🎲 Confirm Bet"
4. Result: Animated outcome + payout
5. Actions: Buttons "🔄 Replay", "📊 Stats", "🏠 Menu"

#### 5.2.2 Custom Keyboards

Main Menu
```
[🎲 Play] [💰 Balance] [📈 Stats]
[💳 Deposit] [💸 Withdraw] [🏆 Leaderboard]
[🎁 Challenges] [👥 Referral] [❓ Help]
```

Betting UI
```
Amount: [1] [5] [10] [50] [100] [MAX]
Target number: _____ (1–100)
Multiplier: 1.96x
Potential payout: 196 TRX

[🎲 Confirm Bet]
[🏠 Back to Menu]
```

### 5.3 Messages and Formatting

#### 5.3.1 Game Result Message
```
🎲 **GAME RESULT** 🎲

🎯 Your number: 50
🎲 Result: 73
💰 Stake: 10 TRX
🎊 **WIN!** Payout: 19.6 TRX

📊 Multiplier: 1.96x
🏦 New balance: 129.6 TRX

🔍 Game ID: #12345
✅ Provably fair verified
```

#### 5.3.2 Info Message
```
📊 **YOUR STATS** 📊

💰 Current balance: 245.80 TRX
🎮 Games played: 127
🏆 Games won: 63 (49.6%)
📈 Biggest win: 150 TRX
📉 Biggest loss: 25 TRX
💎 Total wagered: 1,250 TRX
🎁 Total won: 1,180 TRX
```

## 6. Bonuses and Marketing

### 6.1 First Deposit Bonus

#### 6.1.1 Mechanism
- Rate: +10% of the first deposit
- Maximum: 100 TRX bonus
- Minimum: 10 TRX deposit to activate
- Credit: Automatic after deposit confirmation

#### 6.1.2 Conditions
- One bonus per user
- Activated only on the first deposit
- No wagering requirements (bonus credited directly)

### 6.2 First Bet Cashback

#### 6.2.1 How It Works
- If a user's first bet loses
- Full stake refunded (max 50 TRX)
- Automatically credited after the first losing game

### 6.3 Referral System

#### 6.3.1 Commission Structure
- Referrer: 5% of referees' net winnings
- Calculation: Commission = (referee_winnings - referee_wagers) × 5%
- Minimum: Commission only if net winnings > 0

#### 6.3.2 Tracking Mechanism
- Unique referral code per user
- Personalized invite link
- Real-time commission tracking

### 6.4 Daily Challenges

#### 6.4.1 Challenge Types
```
🎯 "Active Bettor"
→ Place 5 bets in a day
→ Reward: 5 TRX

💰 "High Roller"
→ Wager at least 100 TRX total
→ Reward: 10 TRX

🎲 "Lucky"
→ Win 3 games in a row
→ Reward: 15 TRX
```

#### 6.4.2 Renewal
- Challenges reset daily at 00:00 UTC
- Max 3 active challenges per user
- Rewards credited automatically

## 7. Leaderboards

### 7.1 Leaderboard Types

#### 7.1.1 Winnings Leaderboard
- Periods: Daily, Weekly, Monthly
- Criterion: Total absolute winnings
- Display: Top 10 with usernames

#### 7.1.2 Volume Leaderboard
- Criterion: Total wagered amount
- Goal: Encourage activity
- Rewards: Monthly bonuses for top 3

### 7.2 Display Format
```
🏆 **DAILY LEADERBOARD** 🏆

🥇 @user123 - 1,250 TRX won
🥈 @player456 - 980 TRX won  
🥉 @winner789 - 750 TRX won
4️⃣ @lucky_one - 620 TRX won
5️⃣ @dice_master - 540 TRX won

📍 Your position: #12 (180 TRX)
```

## 8. Security and Prevention

### 8.1 Fund Security

#### 8.1.1 Private Key Management
- AES-256 encryption of private keys
- Encryption key stored separately
- Periodic rotation of encryption keys

#### 8.1.2 Hot/Cold Wallet Strategy
- Hot wallet: operational funds (max 1000 TRX)
- Cold wallet: main reserves
- Automatic transfers based on thresholds

### 8.2 Abuse Prevention

#### 8.2.1 Multi-Account Detection
- Tracking by IP and device fingerprinting
- Behavioral pattern analysis
- Bonus limits per device/IP

#### 8.2.2 Anomaly Detection
- Repetitive bets with identical parameters
- Statistically improbable win/loss patterns
- Suspicious activity (admin alerts)

### 8.3 Audit and Logging

#### 8.3.1 Security Logs
- All financial transactions
- Suspicious login attempts
- Changes to critical parameters

#### 8.3.2 Backup and Recovery
- Daily database backups
- Storage of fairness seeds
- Documented restoration procedures

## 9. Administration and Monitoring

### 9.1 Admin Panel

#### 9.1.1 Main Dashboard
```
📊 **GLOBAL STATS**

👥 Active users: 1,247
🎮 Games today: 3,456
💰 Daily volume: 12,450 TRX
📈 Revenue (house edge): 249 TRX
🏦 Hot wallet balance: 750 TRX
```

#### 9.1.2 Admin Features
- Real-time game view
- Manage bet limits
- Control bonuses and promotions
- Detailed per-user statistics
- Security and transaction logs

### 9.2 Alerting System

#### 9.2.1 Critical Alerts
- Hot wallet balance < minimum threshold
- User win > 5000 TRX
- Suspicious pattern detected
- Blockchain technical error

#### 9.2.2 Admin Notifications
- Daily summary via Telegram
- Real-time alerts for critical events
- Automated weekly reports

## 10. Testing and Validation

### 10.1 Unit Tests

#### 10.1.1 Game Logic Tests
- Correct multiplier calculation
- Bet limit validation
- Provably fair algorithm verification

#### 10.1.2 Security Tests
- Key encryption/decryption
- TRON address validation
- Injection and tampering tests

### 10.2 Integration Tests

#### 10.2.1 Blockchain Tests
- TRON deposits and withdrawals
- Transaction confirmations
- Network error handling

#### 10.2.2 Telegram Bot Tests
- Full gameplay flow
- Invalid command handling
- Performance under load

### 10.3 Load Testing

#### 10.3.1 Traffic Simulation
- 100 concurrent users
- 1000 games per minute
- Stress behavior

## 11. Deployment and DevOps

### 11.1 Environments

#### 11.1.1 Development
- Local PostgreSQL database
- TRON testnet (Nile)
- Test Telegram bot

#### 11.1.2 Production
- Managed PostgreSQL (AWS RDS/DigitalOcean)
- TRON mainnet
- Centralized monitoring and logs

### 11.2 Configuration

#### 11.2.1 Environment Variables
```
# Bot Configuration
TELEGRAM_BOT_TOKEN=
ADMIN_CHAT_IDS=

# Database
DATABASE_URL=

# TRON
TRON_API_URL=
MASTER_WALLET_PRIVATE_KEY=
MIN_CONFIRMATIONS=

# Game Settings
HOUSE_EDGE=0.02
MIN_BET_AMOUNT=1
MAX_BET_AMOUNT=1000
FIRST_DEPOSIT_BONUS_RATE=0.10

# Security
ENCRYPTION_KEY=
JWT_SECRET_KEY=

# Notifications
NOTIFICATION_THRESHOLD=1000
```

### 11.3 Monitoring

#### 11.3.1 Key Metrics
- Games per minute
- TRX transaction volume
- Bot response time
- Transaction error rate

#### 11.3.2 Monitoring Tools
- Structured logs (JSON)
- Prometheus metrics
- Grafana dashboards
- Telegram-based alerting

## 12. Roadmap and Evolution

### 12.1 Phase 1 - MVP (Weeks 1–3)
- [ ] Basic game interface
- [ ] Provably fair system
- [ ] TRX deposits/withdrawals
- [ ] First deposit bonus
- [ ] Basic admin panel

### 12.2 Phase 2 - Improvements (Weeks 4–6)
- [ ] Full referral system
- [ ] Daily challenges
- [ ] Advanced leaderboards
- [ ] Web verification interface
- [ ] Detailed statistics

### 12.3 Phase 3 - Next Steps (Months 2–3)
- [ ] Auto-bet mode
- [ ] Game variants (2 dice, etc.)
- [ ] VIP program
- [ ] Public API
- [ ] Mobile app

## 13. Budget and Resources

### 13.1 Development Costs
- Senior Developer: 3 weeks × 40h = 120h
- DevOps/Security: 1 week × 40h = 40h
- Testing and QA: 1 week × 20h = 20h
- Total: ~180 hours

### 13.2 Operational Costs (Monthly)
- Server: $50–100
- Database: $25–50  
- Monitoring: $20–30
- TRON fees: $10–50
- Total: ~$100–250/month

### 13.3 Projected Revenue
- Short term: 100–400 TRX/day (house edge)
- Long term: 800–2000 TRX/day
- Break-even: ~30–60 days

## 14. Risks and Mitigation

### 14.1 Technical Risks
- TRX volatility: USD/TRX conversion for limits
- Network congestion: Monitor fees and confirmation times
- Logic bugs: Extensive tests and code audit

### 14.2 Business Risks
- Regulation: Legal watch and disclaimers
- Competition: Focus on UX and innovation
- Adoption: Marketing and aggressive referrals

### 14.3 Security Risks
- Hacking: Secure architecture and audits
- Manipulation: Advanced monitoring and ML detection
- Fund loss: Multi-sig and insurance

## 15. Conclusion

This DevBook presents a comprehensive roadmap for developing the TronDiceBot MVP. The modular architecture, based on the existing boilerplate, enables rapid development while maintaining the security and scalability required for a crypto gambling bot.

The prioritized features (core game, provably fair, TRX payments) form the heart of the MVP, while advanced features (referrals, challenges, leaderboards) add value and user engagement.

A strong focus on security, transparency (provably fair), and user experience positions TronDiceBot as a reliable and attractive alternative in the Telegram crypto gaming ecosystem.

Next steps:
1. Set up the development environment
2. Extend the data models
3. Implement the core game service
4. Develop Telegram handlers
5. Test and deploy on testnet