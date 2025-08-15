from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os, base64
from config import ENCRYPTION_KEY

IV_SIZE = 16

# Chargement sécurisé
if not ENCRYPTION_KEY:
    raise ValueError("❌ ENCRYPTION_KEY is not set in environment variables.")

try:
    KEY = base64.b64decode(ENCRYPTION_KEY + '==')  # padding tolerant
except Exception as e:
    raise ValueError(f"❌ ENCRYPTION_KEY is invalid: {e}")

def encrypt_data(data: bytes) -> str:
    """Encrypt data using AES in CFB mode."""
    iv = os.urandom(IV_SIZE)
    cipher = Cipher(algorithms.AES(KEY), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(data) + encryptor.finalize()
    return base64.b64encode(iv + ct).decode("utf-8")

def decrypt_data(token: str) -> bytes:
    """Decrypt data using AES in CFB mode."""
    raw = base64.b64decode(token)
    iv = raw[:IV_SIZE]
    ct = raw[IV_SIZE:]
    cipher = Cipher(algorithms.AES(KEY), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(ct) + decryptor.finalize()


def encrypt_text(text: str) -> str:
    """Encrypt text using AES in CFB mode."""
    return encrypt_data(text.encode("utf-8"))

def decrypt_text(token: str) -> str:
    """Decrypt text using AES in CFB mode."""
    return decrypt_data(token).decode("utf-8")