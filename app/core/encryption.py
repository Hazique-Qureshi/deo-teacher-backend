import os
from cryptography.fernet import Fernet
from app.core.config import get_settings

settings = get_settings()

ENCRYPTION_KEY = settings.ENCRYPTION_KEY.encode() if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY else None

if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    if not ENCRYPTION_KEY:
        ENCRYPTION_KEY = Fernet.generate_key().decode()
        print(f"WARNING: No ENCRYPTION_KEY found. Generated temporary key: {ENCRYPTION_KEY}")
        print("Set ENCRYPTION_KEY environment variable for production.")

cipher = Fernet(ENCRYPTION_KEY)

def encrypt_value(value: str) -> str:
    if not value:
        return value
    return cipher.encrypt(value.encode()).decode()

def decrypt_value(value: str) -> str:
    if not value:
        return value
    try:
        return cipher.decrypt(value.encode()).decode()
    except Exception:
        return value
