"""
Security & Encryption tools
Libraries: cryptography, pycryptodome, bcrypt, argon2-cffi, pyotp, jwt, rsa, nacl
"""
import asyncio
import base64
import hashlib
import os
from typing import Any

# ── Cryptography ──
HAS_CRYPTOGRAPHY = False
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    pass


async def generate_fernet_key() -> dict[str, Any]:
    if not HAS_CRYPTOGRAPHY:
        return {"error": "cryptography not installed"}
    key = Fernet.generate_key()
    return {"key": key.decode(), "type": "Fernet"}


async def encrypt_text(plaintext: str, key: str) -> dict[str, Any]:
    if not HAS_CRYPTOGRAPHY:
        return {"error": "cryptography not installed"}
    try:
        f = Fernet(key.encode() if isinstance(key, str) else key)
        encrypted = f.encrypt(plaintext.encode())
        return {"encrypted": encrypted.decode(), "algorithm": "Fernet"}
    except Exception as e:
        return {"error": str(e)}


async def decrypt_text(ciphertext: str, key: str) -> dict[str, Any]:
    if not HAS_CRYPTOGRAPHY:
        return {"error": "cryptography not installed"}
    try:
        f = Fernet(key.encode() if isinstance(key, str) else key)
        decrypted = f.decrypt(ciphertext.encode())
        return {"decrypted": decrypted.decode(), "algorithm": "Fernet"}
    except Exception as e:
        return {"error": str(e)}


async def generate_rsa_keypair(key_size: int = 2048) -> dict[str, Any]:
    if not HAS_CRYPTOGRAPHY:
        return {"error": "cryptography not installed"}
    try:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size, backend=default_backend())
        private_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                                format=serialization.PrivateFormat.PKCS8,
                                                encryption_algorithm=serialization.NoEncryption())
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
                                             format=serialization.PublicFormat.SubjectPublicKeyInfo)
        return {"private_key": private_pem.decode()[:200] + "...", "public_key": public_pem.decode(),
                "key_size": key_size, "algorithm": "RSA"}
    except Exception as e:
        return {"error": str(e)}


async def hash_text(text: str, algorithm: str = "sha256") -> dict[str, Any]:
    algos = {
        "md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256,
        "sha512": hashlib.sha512, "blake2b": hashlib.blake2b, "blake2s": hashlib.blake2s,
    }
    h = algos.get(algorithm, hashlib.sha256)(text.encode())
    return {"text": text[:100], "algorithm": algorithm, "hash": h.hexdigest(), "digest_size": h.digest_size}


# ── Bcrypt ──
HAS_BCRYPT = False
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    pass


async def bcrypt_hash(password: str, rounds: int = 12) -> dict[str, Any]:
    if not HAS_BCRYPT:
        return {"error": "bcrypt not installed"}
    try:
        hashed = await asyncio.get_event_loop().run_in_executor(None, lambda: bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=rounds)))
        return {"hash": hashed.decode(), "rounds": rounds, "algorithm": "bcrypt"}
    except Exception as e:
        return {"error": str(e)}


async def bcrypt_verify(password: str, hash_str: str) -> dict[str, Any]:
    if not HAS_BCRYPT:
        return {"error": "bcrypt not installed"}
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, lambda: bcrypt.checkpw(password.encode(), hash_str.encode()))
        return {"valid": result}
    except Exception as e:
        return {"error": str(e)}


# ── Argon2 ──
HAS_ARGON2 = False
try:
    from argon2 import PasswordHasher
    HAS_ARGON2 = True
except ImportError:
    pass


async def argon2_hash(password: str) -> dict[str, Any]:
    if not HAS_ARGON2:
        return {"error": "argon2-cffi not installed"}
    try:
        ph = PasswordHasher()
        h = await asyncio.get_event_loop().run_in_executor(None, lambda: ph.hash(password))
        return {"hash": h, "algorithm": "argon2id"}
    except Exception as e:
        return {"error": str(e)}


# ── 2FA/TOTP (pyotp) ──
HAS_PYOTP = False
try:
    import pyotp
    HAS_PYOTP = True
except ImportError:
    pass


async def generate_totp_secret() -> dict[str, Any]:
    if not HAS_PYOTP:
        return {"error": "pyotp not installed"}
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name="FRIDAY", issuer_name="SovereignAI")
    return {"secret": secret, "uri": uri, "algorithm": "TOTP"}


async def verify_totp(secret: str, token: str) -> dict[str, Any]:
    if not HAS_PYOTP:
        return {"error": "pyotp not installed"}
    try:
        totp = pyotp.TOTP(secret)
        valid = totp.verify(token)
        return {"valid": valid}
    except Exception as e:
        return {"error": str(e)}


# ── JWT ──
HAS_JWT = False
try:
    import jwt as pyjwt
    HAS_JWT = True
except ImportError:
    pass


async def jwt_encode(payload: dict, secret: str, algorithm: str = "HS256") -> dict[str, Any]:
    if not HAS_JWT:
        return {"error": "jwt (PyJWT) not installed"}
    try:
        token = pyjwt.encode(payload, secret, algorithm=algorithm)
        return {"token": token, "algorithm": algorithm}
    except Exception as e:
        return {"error": str(e)}


async def jwt_decode(token: str, secret: str, algorithms: list[str] | None = None) -> dict[str, Any]:
    if not HAS_JWT:
        return {"error": "jwt not installed"}
    try:
        payload = pyjwt.decode(token, secret, algorithms=algorithms or ["HS256"])
        return {"payload": payload, "valid": True}
    except Exception as e:
        return {"error": str(e), "valid": False}


# ── RSA (rsa library) ──
HAS_RSA = False
try:
    import rsa as rsalib
    HAS_RSA = True
except ImportError:
    pass


async def rsa_encrypt(plaintext: str, public_key_pem: str) -> dict[str, Any]:
    if not HAS_RSA:
        return {"error": "rsa library not installed"}
    try:
        pubkey = rsalib.PublicKey.load_pkcs1(public_key_pem.encode())
        encrypted = rsalib.encrypt(plaintext.encode(), pubkey)
        return {"encrypted": base64.b64encode(encrypted).decode(), "algorithm": "RSA-OAEP"}
    except Exception as e:
        return {"error": str(e)}


async def rsa_decrypt(ciphertext_b64: str, private_key_pem: str) -> dict[str, Any]:
    if not HAS_RSA:
        return {"error": "rsa library not installed"}
    try:
        privkey = rsalib.PrivateKey.load_pkcs1(private_key_pem.encode())
        decrypted = rsalib.decrypt(base64.b64decode(ciphertext_b64), privkey)
        return {"decrypted": decrypted.decode(), "algorithm": "RSA-OAEP"}
    except Exception as e:
        return {"error": str(e)}


# ── NaCl / libsodium ──
HAS_NACL = False
try:
    import nacl.secret
    import nacl.utils
    from nacl.public import PrivateKey, Box
    HAS_NACL = True
except ImportError:
    pass


async def nacl_generate_key() -> dict[str, Any]:
    if not HAS_NACL:
        return {"error": "PyNaCl not installed"}
    try:
        private = PrivateKey.generate()
        public = private.public_key
        return {"private_key": base64.b64encode(bytes(private)).decode(),
                "public_key": base64.b64encode(bytes(public)).decode(), "algorithm": "Curve25519"}
    except Exception as e:
        return {"error": str(e)}


async def nacl_box_encrypt(plaintext: str, recipient_public_key_b64: str) -> dict[str, Any]:
    if not HAS_NACL:
        return {"error": "PyNaCl not installed"}
    try:
        priv = PrivateKey.generate()
        pub = nacl.public.PublicKey(base64.b64decode(recipient_public_key_b64))
        box = Box(priv, pub)
        encrypted = box.encrypt(plaintext.encode())
        return {"encrypted": base64.b64encode(encrypted).decode(), "algorithm": "NaCl Box"}
    except Exception as e:
        return {"error": str(e)}
