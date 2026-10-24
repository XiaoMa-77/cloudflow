"""API 冒烟测试：健康检查、未认证拦截与种子账号口令可验证。"""

from extensions import db
from models import User
from services.security import is_password_hashed, verify_password


def test_health_endpoint(app):
    resp = app.test_client().get("/api/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 200
    assert body["data"]["service"] == "cloudflow"


def test_unknown_api_returns_404(app):
    resp = app.test_client().get("/api/no-such-endpoint")
    assert resp.status_code == 404


def test_protected_endpoint_requires_token(app):
    """/api/auth/me 未携带令牌时应被登录装饰器拦下。"""
    resp = app.test_client().get("/api/auth/me")
    body = resp.get_json()
    assert body["code"] == 401


def test_seeded_user_credentials_verifiable(app):
    """初始化数据种下的演示账号必须是可验证的哈希口令（123456）。"""
    with app.app_context():
        user = User.query.filter_by(username="user").first()
        assert user is not None
        assert user.status == "ACTIVE"
        assert is_password_hashed(user.password)
        assert verify_password(user.password, "123456")
        assert not verify_password(user.password, "wrong-password")
        assert db.session.query(User.query.filter(User.status == "DISABLED").exists()).scalar()
