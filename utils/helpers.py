from datetime import datetime, timezone
import random
import string
import re

def generate_referral_code(length: int = 8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_share_link(bot_username: str, referral_code: str):
    return f"https://t.me/{bot_username}?start={referral_code}"

def escape_markdown_v2(text: str) -> str:
    escape_chars = r'\\`*_\[\]()~>#+=|{}.!-'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def get_utc_time():
    return datetime.now(timezone.utc)

def get_utc_date():
    return get_utc_time().date()

def get_separator():
    return "─" * 20