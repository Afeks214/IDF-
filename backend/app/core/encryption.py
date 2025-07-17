#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Military-Grade Data Encryption Utilities
IDF Testing Infrastructure
"""

import os
import base64
import secrets
import hashlib
import hmac
from typing import Optional, Tuple, Union, Dict, Any
from dataclasses import dataclass
from enum import Enum
import structlog
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, MultiFernet
import json

from .config import settings

logger = structlog.get_logger()


class EncryptionAlgorithm(str, Enum):
    """Supported encryption algorithms"""
    AES_256_GCM = "aes_256_gcm"
    AES_256_CBC = "aes_256_cbc"
    FERNET = "fernet"
    RSA_4096 = "rsa_4096"
    CHACHA20_POLY1305 = "chacha20_poly1305"


class KeyDerivationFunction(str, Enum):
    """Key derivation functions"""
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"
    HKDF = "hkdf"


@dataclass
class EncryptionMetadata:
    """Metadata for encrypted data"""
    algorithm: EncryptionAlgorithm
    key_derivation: Optional[KeyDerivationFunction]
    salt: Optional[bytes]
    nonce: Optional[bytes]
    tag: Optional[bytes]
    iterations: Optional[int]
    version: str = "1.0"


class EncryptionError(Exception):
    """Custom encryption error"""
    pass


class SecureEncryption:
    """
    Military-grade encryption utilities using industry standards
    """
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or settings.security.ENCRYPTION_KEY
        self.backend = default_backend()
        
        # Initialize Fernet with key rotation support
        self._init_fernet_keys()
    
    def _init_fernet_keys(self):
        """Initialize Fernet encryption with key rotation"""
        try:
            # Primary key from settings
            primary_key = self._derive_fernet_key(self.master_key)
            
            # Secondary key for rotation (derived from primary)
            secondary_seed = hashlib.sha256(self.master_key.encode()).hexdigest()
            secondary_key = self._derive_fernet_key(secondary_seed)
            
            # Create MultiFernet for key rotation
            self.fernet = MultiFernet([
                Fernet(primary_key),
                Fernet(secondary_key)
            ])
            
        except Exception as e:
            logger.error("Failed to initialize Fernet keys", error=str(e))
            raise EncryptionError("Encryption initialization failed")
    
    def _derive_fernet_key(self, password: str) -> bytes:
        """Derive a Fernet-compatible key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'idf_testing_salt',  # Static salt for consistency
            iterations=100000,
            backend=self.backend
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def encrypt_aes_gcm(
        self, 
        plaintext: Union[str, bytes], 
        key: Optional[bytes] = None,
        associated_data: Optional[bytes] = None
    ) -> Tuple[bytes, EncryptionMetadata]:
        """
        Encrypt data using AES-256-GCM (Authenticated Encryption)
        """
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')
            
            # Generate or use provided key
            if key is None:
                key = os.urandom(32)  # 256-bit key
            
            # Generate random nonce
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce),
                backend=self.backend
            )
            
            encryptor = cipher.encryptor()
            
            # Add associated data if provided
            if associated_data:
                encryptor.authenticate_additional_data(associated_data)
            
            # Encrypt data
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()
            
            # Get authentication tag
            tag = encryptor.tag
            
            metadata = EncryptionMetadata(
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                key_derivation=None,
                salt=None,
                nonce=nonce,
                tag=tag,
                iterations=None
            )
            
            return ciphertext, metadata
            
        except Exception as e:
            logger.error("AES-GCM encryption failed", error=str(e))
            raise EncryptionError(f"Encryption failed: {str(e)}")
    
    def decrypt_aes_gcm(
        self,
        ciphertext: bytes,
        key: bytes,
        metadata: EncryptionMetadata,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypt data using AES-256-GCM
        """
        try:
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(metadata.nonce, metadata.tag),
                backend=self.backend
            )
            
            decryptor = cipher.decryptor()
            
            # Add associated data if provided
            if associated_data:
                decryptor.authenticate_additional_data(associated_data)
            
            # Decrypt data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext
            
        except Exception as e:
            logger.error("AES-GCM decryption failed", error=str(e))
            raise EncryptionError(f"Decryption failed: {str(e)}")
    
    def encrypt_with_password(
        self,
        plaintext: Union[str, bytes],
        password: str,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
        kdf: KeyDerivationFunction = KeyDerivationFunction.SCRYPT
    ) -> Tuple[bytes, EncryptionMetadata]:
        """
        Encrypt data with password-based encryption
        """
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')
            
            # Generate salt
            salt = os.urandom(32)
            
            # Derive key from password
            if kdf == KeyDerivationFunction.SCRYPT:
                key_derivation = Scrypt(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    n=2**14,  # CPU/memory cost
                    r=8,      # Block size
                    p=1,      # Parallelization
                    backend=self.backend
                )
                iterations = 2**14
            elif kdf == KeyDerivationFunction.PBKDF2:
                key_derivation = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                    backend=self.backend
                )
                iterations = 100000
            else:
                raise EncryptionError(f"Unsupported KDF: {kdf}")
            
            key = key_derivation.derive(password.encode())
            
            # Encrypt with derived key
            if algorithm == EncryptionAlgorithm.AES_256_GCM:
                ciphertext, metadata = self.encrypt_aes_gcm(plaintext, key)
                metadata.salt = salt
                metadata.key_derivation = kdf
                metadata.iterations = iterations
                return ciphertext, metadata
            else:
                raise EncryptionError(f"Unsupported algorithm: {algorithm}")
            
        except Exception as e:
            logger.error("Password-based encryption failed", error=str(e))
            raise EncryptionError(f"Password encryption failed: {str(e)}")
    
    def decrypt_with_password(
        self,
        ciphertext: bytes,
        password: str,
        metadata: EncryptionMetadata
    ) -> bytes:
        """
        Decrypt data with password-based encryption
        """
        try:
            # Derive key from password
            if metadata.key_derivation == KeyDerivationFunction.SCRYPT:
                key_derivation = Scrypt(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=metadata.salt,
                    n=metadata.iterations,
                    r=8,
                    p=1,
                    backend=self.backend
                )
            elif metadata.key_derivation == KeyDerivationFunction.PBKDF2:
                key_derivation = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=metadata.salt,
                    iterations=metadata.iterations,
                    backend=self.backend
                )
            else:
                raise EncryptionError(f"Unsupported KDF: {metadata.key_derivation}")
            
            key = key_derivation.derive(password.encode())
            
            # Decrypt with derived key
            if metadata.algorithm == EncryptionAlgorithm.AES_256_GCM:
                return self.decrypt_aes_gcm(ciphertext, key, metadata)
            else:
                raise EncryptionError(f"Unsupported algorithm: {metadata.algorithm}")
            
        except Exception as e:
            logger.error("Password-based decryption failed", error=str(e))
            raise EncryptionError(f"Password decryption failed: {str(e)}")
    
    def encrypt_fernet(self, plaintext: Union[str, bytes]) -> bytes:
        """
        Encrypt data using Fernet (simple, secure)
        """
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')
            
            return self.fernet.encrypt(plaintext)
            
        except Exception as e:
            logger.error("Fernet encryption failed", error=str(e))
            raise EncryptionError(f"Fernet encryption failed: {str(e)}")
    
    def decrypt_fernet(self, ciphertext: bytes) -> bytes:
        """
        Decrypt data using Fernet
        """
        try:
            return self.fernet.decrypt(ciphertext)
            
        except Exception as e:
            logger.error("Fernet decryption failed", error=str(e))
            raise EncryptionError(f"Fernet decryption failed: {str(e)}")
    
    def generate_rsa_keypair(self, key_size: int = 4096) -> Tuple[bytes, bytes]:
        """
        Generate RSA public/private key pair
        """
        try:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=self.backend
            )
            
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return public_pem, private_pem
            
        except Exception as e:
            logger.error("RSA key generation failed", error=str(e))
            raise EncryptionError(f"RSA key generation failed: {str(e)}")
    
    def encrypt_rsa(self, plaintext: Union[str, bytes], public_key_pem: bytes) -> bytes:
        """
        Encrypt data using RSA public key
        """
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')
            
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=self.backend
            )
            
            # Encrypt with OAEP padding
            ciphertext = public_key.encrypt(
                plaintext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return ciphertext
            
        except Exception as e:
            logger.error("RSA encryption failed", error=str(e))
            raise EncryptionError(f"RSA encryption failed: {str(e)}")
    
    def decrypt_rsa(self, ciphertext: bytes, private_key_pem: bytes) -> bytes:
        """
        Decrypt data using RSA private key
        """
        try:
            # Load private key
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=self.backend
            )
            
            # Decrypt with OAEP padding
            plaintext = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return plaintext
            
        except Exception as e:
            logger.error("RSA decryption failed", error=str(e))
            raise EncryptionError(f"RSA decryption failed: {str(e)}")
    
    def sign_data(self, data: Union[str, bytes], private_key_pem: bytes) -> bytes:
        """
        Create digital signature for data
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Load private key
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=self.backend
            )
            
            # Sign data
            signature = private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return signature
            
        except Exception as e:
            logger.error("Data signing failed", error=str(e))
            raise EncryptionError(f"Data signing failed: {str(e)}")
    
    def verify_signature(
        self,
        data: Union[str, bytes],
        signature: bytes,
        public_key_pem: bytes
    ) -> bool:
        """
        Verify digital signature
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=self.backend
            )
            
            # Verify signature
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except Exception as e:
            logger.warning("Signature verification failed", error=str(e))
            return False
    
    def secure_hash(self, data: Union[str, bytes], algorithm: str = "sha256") -> str:
        """
        Create secure hash of data
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            if algorithm.lower() == "sha256":
                hash_obj = hashlib.sha256(data)
            elif algorithm.lower() == "sha512":
                hash_obj = hashlib.sha512(data)
            elif algorithm.lower() == "blake2b":
                hash_obj = hashlib.blake2b(data)
            else:
                raise EncryptionError(f"Unsupported hash algorithm: {algorithm}")
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error("Hashing failed", error=str(e))
            raise EncryptionError(f"Hashing failed: {str(e)}")
    
    def create_hmac(
        self,
        data: Union[str, bytes],
        key: Union[str, bytes],
        algorithm: str = "sha256"
    ) -> str:
        """
        Create HMAC for data integrity
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            if isinstance(key, str):
                key = key.encode('utf-8')
            
            if algorithm.lower() == "sha256":
                mac = hmac.new(key, data, hashlib.sha256)
            elif algorithm.lower() == "sha512":
                mac = hmac.new(key, data, hashlib.sha512)
            else:
                raise EncryptionError(f"Unsupported HMAC algorithm: {algorithm}")
            
            return mac.hexdigest()
            
        except Exception as e:
            logger.error("HMAC creation failed", error=str(e))
            raise EncryptionError(f"HMAC creation failed: {str(e)}")
    
    def verify_hmac(
        self,
        data: Union[str, bytes],
        provided_hmac: str,
        key: Union[str, bytes],
        algorithm: str = "sha256"
    ) -> bool:
        """
        Verify HMAC for data integrity
        """
        try:
            calculated_hmac = self.create_hmac(data, key, algorithm)
            return hmac.compare_digest(calculated_hmac, provided_hmac)
            
        except Exception as e:
            logger.error("HMAC verification failed", error=str(e))
            return False


class SecureStorage:
    """
    Secure storage for sensitive data with encryption
    """
    
    def __init__(self, encryption: Optional[SecureEncryption] = None):
        self.encryption = encryption or SecureEncryption()
    
    def encrypt_json(self, data: Dict[str, Any], password: Optional[str] = None) -> str:
        """
        Encrypt JSON data and return base64-encoded result
        """
        try:
            # Serialize to JSON
            json_data = json.dumps(data, separators=(',', ':'))
            
            if password:
                # Password-based encryption
                ciphertext, metadata = self.encryption.encrypt_with_password(
                    json_data,
                    password
                )
                
                # Package with metadata
                package = {
                    'ciphertext': base64.b64encode(ciphertext).decode('ascii'),
                    'metadata': {
                        'algorithm': metadata.algorithm.value,
                        'key_derivation': metadata.key_derivation.value if metadata.key_derivation else None,
                        'salt': base64.b64encode(metadata.salt).decode('ascii') if metadata.salt else None,
                        'nonce': base64.b64encode(metadata.nonce).decode('ascii') if metadata.nonce else None,
                        'tag': base64.b64encode(metadata.tag).decode('ascii') if metadata.tag else None,
                        'iterations': metadata.iterations,
                        'version': metadata.version
                    }
                }
            else:
                # Simple Fernet encryption
                ciphertext = self.encryption.encrypt_fernet(json_data)
                package = {
                    'ciphertext': base64.b64encode(ciphertext).decode('ascii'),
                    'metadata': {
                        'algorithm': 'fernet',
                        'version': '1.0'
                    }
                }
            
            return base64.b64encode(
                json.dumps(package, separators=(',', ':')).encode()
            ).decode('ascii')
            
        except Exception as e:
            logger.error("JSON encryption failed", error=str(e))
            raise EncryptionError(f"JSON encryption failed: {str(e)}")
    
    def decrypt_json(self, encrypted_data: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Decrypt base64-encoded encrypted JSON data
        """
        try:
            # Decode and parse package
            package_data = base64.b64decode(encrypted_data.encode()).decode()
            package = json.loads(package_data)
            
            ciphertext = base64.b64decode(package['ciphertext'].encode())
            metadata_dict = package['metadata']
            
            if metadata_dict.get('algorithm') == 'fernet':
                # Simple Fernet decryption
                plaintext = self.encryption.decrypt_fernet(ciphertext)
            else:
                # Password-based decryption
                if not password:
                    raise EncryptionError("Password required for decryption")
                
                # Reconstruct metadata
                metadata = EncryptionMetadata(
                    algorithm=EncryptionAlgorithm(metadata_dict['algorithm']),
                    key_derivation=KeyDerivationFunction(metadata_dict['key_derivation']) if metadata_dict.get('key_derivation') else None,
                    salt=base64.b64decode(metadata_dict['salt'].encode()) if metadata_dict.get('salt') else None,
                    nonce=base64.b64decode(metadata_dict['nonce'].encode()) if metadata_dict.get('nonce') else None,
                    tag=base64.b64decode(metadata_dict['tag'].encode()) if metadata_dict.get('tag') else None,
                    iterations=metadata_dict.get('iterations'),
                    version=metadata_dict.get('version', '1.0')
                )
                
                plaintext = self.encryption.decrypt_with_password(
                    ciphertext,
                    password,
                    metadata
                )
            
            # Parse JSON
            return json.loads(plaintext.decode())
            
        except Exception as e:
            logger.error("JSON decryption failed", error=str(e))
            raise EncryptionError(f"JSON decryption failed: {str(e)}")


class TokenEncryption:
    """
    Specialized encryption for tokens and sensitive strings
    """
    
    def __init__(self, encryption: Optional[SecureEncryption] = None):
        self.encryption = encryption or SecureEncryption()
    
    def encrypt_token(self, token: str, context: Optional[str] = None) -> str:
        """
        Encrypt a token with optional context for additional security
        """
        try:
            # Add context if provided
            if context:
                data = f"{context}:{token}"
            else:
                data = token
            
            # Encrypt with Fernet
            ciphertext = self.encryption.encrypt_fernet(data)
            
            # Return base64 encoded
            return base64.urlsafe_b64encode(ciphertext).decode('ascii')
            
        except Exception as e:
            logger.error("Token encryption failed", error=str(e))
            raise EncryptionError(f"Token encryption failed: {str(e)}")
    
    def decrypt_token(self, encrypted_token: str, context: Optional[str] = None) -> str:
        """
        Decrypt a token with optional context verification
        """
        try:
            # Decode from base64
            ciphertext = base64.urlsafe_b64decode(encrypted_token.encode())
            
            # Decrypt with Fernet
            plaintext = self.encryption.decrypt_fernet(ciphertext).decode()
            
            # Verify context if provided
            if context:
                if not plaintext.startswith(f"{context}:"):
                    raise EncryptionError("Invalid token context")
                return plaintext[len(context) + 1:]
            else:
                return plaintext
            
        except Exception as e:
            logger.error("Token decryption failed", error=str(e))
            raise EncryptionError(f"Token decryption failed: {str(e)}")


# Global instances
encryption = SecureEncryption()
secure_storage = SecureStorage(encryption)
token_encryption = TokenEncryption(encryption)


# Convenience functions
def encrypt_sensitive_data(data: Union[str, Dict], password: Optional[str] = None) -> str:
    """Encrypt sensitive data (convenience function)"""
    if isinstance(data, dict):
        return secure_storage.encrypt_json(data, password)
    else:
        if password:
            ciphertext, _ = encryption.encrypt_with_password(data, password)
            return base64.b64encode(ciphertext).decode()
        else:
            return base64.b64encode(encryption.encrypt_fernet(data)).decode()


def decrypt_sensitive_data(encrypted_data: str, password: Optional[str] = None) -> Union[str, Dict]:
    """Decrypt sensitive data (convenience function)"""
    try:
        # Try as JSON first
        return secure_storage.decrypt_json(encrypted_data, password)
    except:
        # Fall back to string decryption
        ciphertext = base64.b64decode(encrypted_data.encode())
        if password:
            # This would need metadata - simplified for convenience
            return encryption.decrypt_fernet(ciphertext).decode()
        else:
            return encryption.decrypt_fernet(ciphertext).decode()


def generate_secure_key() -> str:
    """Generate a secure encryption key"""
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


def secure_compare(a: str, b: str) -> bool:
    """Secure string comparison to prevent timing attacks"""
    return hmac.compare_digest(a.encode(), b.encode())