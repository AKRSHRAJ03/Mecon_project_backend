import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from typing import Tuple
import uuid

def generate_key() -> Tuple[bytes, bytes]:
    """Generate a random encryption key and salt"""
    salt = os.urandom(16)
    key = Fernet.generate_key()
    return key, salt

def derive_key_from_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """Derive an encryption key from a password"""
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt

def encrypt_file(file_path: str, output_path: str, key: bytes) -> None:
    """Encrypt a file using the provided key"""
    fernet = Fernet(key)
    
    with open(file_path, 'rb') as file:
        file_data = file.read()
    
    encrypted_data = fernet.encrypt(file_data)
    
    with open(output_path, 'wb') as file:
        file.write(encrypted_data)

def decrypt_file(file_path: str, output_path: str, key: bytes) -> None:
    """Decrypt a file using the provided key"""
    fernet = Fernet(key)
    
    with open(file_path, 'rb') as file:
        encrypted_data = file.read()
    
    decrypted_data = fernet.decrypt(encrypted_data)
    
    with open(output_path, 'wb') as file:
        file.write(decrypted_data)

def encrypt_key(key: bytes, master_key: bytes) -> bytes:
    """Encrypt a file encryption key with the master key"""
    fernet = Fernet(master_key)
    return fernet.encrypt(key)

def decrypt_key(encrypted_key: bytes, master_key: bytes) -> bytes:
    """Decrypt a file encryption key with the master key"""
    fernet = Fernet(master_key)
    return fernet.decrypt(encrypted_key)

def get_master_key() -> bytes:
    """Get the master key for encrypting file keys"""
    # In a production environment, this should be securely stored
    # For this example, we'll use a fixed key
    # In real applications, consider using a key management service
    return base64.urlsafe_b64encode(b"master_key_for_encrypting_file_keys_12345"[:32])

def generate_temp_file_path() -> str:
    """Generate a temporary file path for decrypted files"""
    return f"temp_{uuid.uuid4()}.tmp"