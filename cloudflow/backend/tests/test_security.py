"""安全工具测试：口令哈希、历史明文兼容与密码本加解密。"""

import pytest
from cryptography.fernet import Fernet

from config import Config
from services.security import (
    decrypt_secret,
    encrypt_secret,
    hash_password,
    is_password_hashed,
    verify_password,
)


@pytest.fixture()
def fernet_key():
    """临时配置真实 Fernet 密钥，用完还原。"""
    original = Config.PASSWORD_BOOK_KEY
    Config.PASSWORD_BOOK_KEY = Fernet.generate_key().decode("ascii")
    yield Config.PASSWORD_BOOK_KEY
    Config.PASSWORD_BOOK_KEY = original


def test_password_hash_roundtrip():
    hashed = hash_password("s3cret-Pa55")
    assert is_password_hashed(hashed)
    assert verify_password(hashed, "s3cret-Pa55")
    assert not verify_password(hashed, "wrong")
    assert not is_password_hashed("plaintext-legacy")
    assert not is_password_hashed(None)


def test_verify_password_legacy_plaintext():
    """历史明文直接比对成功，供登录后升级为哈希。"""
    assert verify_password("legacy-pass", "legacy-pass")
    assert not verify_password("legacy-pass", "other")
    assert not verify_password("", "any")
    assert not verify_password(None, "any")


def test_password_book_roundtrip(fernet_key):
    cipher = encrypt_secret("网盘密码#123")
    assert cipher.startswith("enc:v1:")
    assert "网盘密码" not in cipher
    assert decrypt_secret(cipher) == "网盘密码#123"


def test_password_book_legacy_plaintext_passthrough(fernet_key):
    """无前缀的历史明文原样返回，不报错。"""
    assert decrypt_secret("plain-secret") == "plain-secret"
    assert decrypt_secret("") == ""


def test_password_book_degrades_without_key():
    """未配置密钥时降级为明文存取（演示环境），不抛异常。"""
    original = Config.PASSWORD_BOOK_KEY
    Config.PASSWORD_BOOK_KEY = ""
    try:
        assert encrypt_secret("demo") == "demo"
        assert decrypt_secret("demo") == "demo"
    finally:
        Config.PASSWORD_BOOK_KEY = original


def test_password_book_invalid_key_fails_closed(fernet_key):
    """密钥轮换后旧密文解不开：返回空串而不是抛异常或泄露密文。"""
    cipher = encrypt_secret("to-be-orphaned")
    Config.PASSWORD_BOOK_KEY = Fernet.generate_key().decode("ascii")
    assert decrypt_secret(cipher) == ""
