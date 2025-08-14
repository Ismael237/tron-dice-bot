import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path, override=True)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_ADMIN_ID = os.getenv('TELEGRAM_ADMIN_ID')
TELEGRAM_ADMIN_USERNAME = os.getenv('TELEGRAM_ADMIN_USERNAME')

DATABASE_URL = os.getenv('DATABASE_URL')

# Limits
DAILY_WITHDRAWAL_LIMIT = float(os.getenv('DAILY_WITHDRAWAL_LIMIT', 1000))
MIN_WITHDRAWAL_AMOUNT = float(os.getenv('MIN_WITHDRAWAL_AMOUNT', 1))
ITEMS_PER_PAGE = int(os.getenv('ITEMS_PER_PAGE', 3))

# TRON Blockchain
TRON_PRIVATE_KEY = os.getenv('TRON_PRIVATE_KEY')
TRON_API_URL = os.getenv('TRON_API_URL')
TRON_EXPLORER_URL = os.getenv('TRON_EXPLORER_URL')

# Deposit to main wallet rate (e.g. 0.9 = 90%)
DEPOSIT_TO_MAIN_WALLET_RATE = float(os.getenv('DEPOSIT_TO_MAIN_WALLET_RATE', 0.9))

# Withdrawal fee rate (e.g. 0.01 = 1%)
WITHDRAWAL_FEE_RATE = float(os.getenv('WITHDRAWAL_FEE_RATE', 0.01))

# Referral rate (e.g. 0.01 = 1%)
REFERRAL_RATE = float(os.getenv('REFERRAL_RATE', 0.01))

# Worker Configuration (in minutes)
DEPOSIT_CHECK_INTERVAL = int(os.getenv('DEPOSIT_CHECK_INTERVAL', 4))
WITHDRAWAL_PROCESS_INTERVAL = int(os.getenv('WITHDRAWAL_PROCESS_INTERVAL', 5))

# Security
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/bot_marketplace.log')
ERROR_LOG_FILE = os.getenv('ERROR_LOG_FILE', 'logs/errors.log')

# APScheduler
AP_SCHEDULER_THREAD_POOL_SIZE = int(os.getenv('AP_SCHEDULER_THREAD_POOL_SIZE', 5))