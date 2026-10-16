"""安全工具：账号密码哈希与密码本静态加密。

- 账号密码使用 werkzeug 的 pbkdf2:sha256 哈希存储，兼容历史明文（登录成功后自动升级为哈希）。
- 密码本条目使用 Fernet (AES-128-CBC + HMAC) 加密存储，密文带 ``enc:v1:`` 前缀。
"""
from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

try:
    from cryptography.fernet import Fernet
    FERNET_AVAILABLE = True
except ImportError:  # pragma: no cover
    FERNET_AVAILABLE = False

from config import Config

_HASH_PREFIXES = ('pbkdf2:', 'scrypt:')
_ENC_PREFIX = 'enc:v1:'


def hash_password(raw: str) -> str:
    return generate_password_hash(raw or '', method='pbkdf2:sha256')


def is_password_hashed(stored: str | None) -> bool:
    return bool(stored) and str(stored).startswith(_HASH_PREFIXES)


def verify_password(stored: str | None, raw: str) -> bool:
    """校验密码；历史明文密码直接比对（调用方应在成功后调用 hash_password 升级）。"""
    stored = stored or ''
    raw = raw or ''
    if not stored:
        return False
    if stored.startswith(_HASH_PREFIXES):
        try:
            return check_password_hash(stored, raw)
        except Exception:
            return False
    return stored == raw


def _get_fernet() -> Fernet | None:
    if not FERNET_AVAILABLE:
        return None
    key = (Config.PASSWORD_BOOK_KEY or '').strip()
    if not key:
        return None
    try:
        return Fernet(key.encode('ascii'))
    except Exception:
        return None


def encrypt_secret(plain: str | None) -> str:
    """加密敏感字段；未配置密钥时原样返回（降级为明文，便于演示环境）。"""
    f = _get_fernet()
    if f is None or plain is None:
        return plain or ''
    token = f.encrypt(str(plain).encode('utf-8'))
    return _ENC_PREFIX + token.decode('ascii')


def decrypt_secret(stored: str | None) -> str:
    """解密敏感字段；历史明文（无前缀）原样返回。"""
    if not stored:
        return ''
    if not stored.startswith(_ENC_PREFIX):
        return stored
    f = _get_fernet()
    if f is None:
        return ''
    try:
        return f.decrypt(stored[len(_ENC_PREFIX):].encode('ascii')).decode('utf-8')
    except Exception:
        return ''
