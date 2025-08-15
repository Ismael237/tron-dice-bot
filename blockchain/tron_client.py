""" Blockchain client for TRON """
from decimal import Decimal
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from config import TRON_API_URL, TRON_PRIVATE_KEY
import requests
from utils.logger import logger


tron = Tron(HTTPProvider(TRON_API_URL))


def get_main_wallet() -> tuple[str, PrivateKey] | None:
    """Get the main wallet address and private key"""
    try:
        priv_key = PrivateKey(bytes.fromhex(TRON_PRIVATE_KEY))
        address = priv_key.public_key.to_base58check_address()
        return address, priv_key
    except Exception as e:
        logger.error(f"Error getting main wallet: {e}")
        return None, None


def generate_wallet() -> tuple[str, str]:
    """Generate a new wallet address and private key"""
    priv = PrivateKey.random()
    address = priv.public_key.to_base58check_address()
    return address, priv.hex()


def get_trx_transactions(address: str) -> list[dict]:
    """Get the list of transactions for a given address"""
    try:
        url = f"{TRON_API_URL}/v1/accounts/{address}/transactions?limit=50&only_to=true&sort=-timestamp"
        headers = {
            "accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            transactions = []
            for tx in data.get('data', []):
                # Vérifier que c'est un transfert de TRX
                if tx.get('raw_data', {}).get('contract', [{}])[0].get('type') == 'TransferContract':
                    contract = tx['raw_data']['contract'][0]['parameter']['value']
                    transactions.append({
                        'txID': tx['txID'],
                        'from': contract.get('owner_address'),
                        'to': contract.get('to_address'),
                        'amount': contract.get('amount'),
                        'confirmations': tx.get('ret', [{}])[0].get('contractRet') == 'SUCCESS' and 20 or 0  # Hypothèse
                    })
            return transactions
        else:
            logger.error(f"Erreur API TronGrid: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Erreur dans get_trx_transactions: {e}")
        return []


def send_trx(from_privkey_hex: str, to_address: str, amount: Decimal) -> str:
    """Send TRX from a private key to an address"""
    priv = PrivateKey(bytes.fromhex(from_privkey_hex))
    address = priv.public_key.to_base58check_address()
    txn = (
        tron.trx.transfer(address, to_address, int(amount * 1_000_000))
        .build()
        .sign(priv)
    )
    result = txn.broadcast().wait()
    return result['id']



def get_trx_balance(address: str) -> int | None:
    """Get the balance of an address"""
    try:
        return tron.get_account_balance(address) 
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return None