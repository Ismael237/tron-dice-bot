import re

def is_valid_tron_address(address: str) -> bool:
    return bool(re.match(r'^T[1-9A-HJ-NP-Za-km-z]{33}$', address))

def is_valid_amount(amount: float, min_value: float = 0) -> bool:
    try:
        return float(amount) >= min_value
    except Exception:
        return False 