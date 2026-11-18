"""内容寻址 / 鉴权边界 / 分享 / 回收站的补充离线集成测试。

全部走 Flask test_client + conftest 提供的临时 SQLite / 上传目录；
不联网、不调用 AI、不依赖外部服务。口令注入仅用于构造鉴权会话，
不经过登录验证码流程（验证码本身属于前端交互，见 DESIGN.md 假设）。
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from io import BytesIO

from extensions import db
from models import AdminUser, AuthSession, FileBlob, FileNode, RecycleRecord, ShareRecord, User


def _make_user(app, username="tester", space_limit=10 * 1024 ** 3):
    """创建普通用户并注入一个 USER 令牌，返回 (user_id, headers)。"""
    with app.app_context():
        user = User(
            username=username,
            password="not-used",
            status="ACTIVE",
            used_space_bytes=0,
            space_limit_bytes=space_limit,
        )
        db.session.add(user)
        db.session.commit()
        token = secrets.token_urlsafe(16)
        db.session.add(AuthSession(token=token, role="USER", user_id=user.id))
        db.session.commit()
        uid = user.id
    return uid, {"Authorization": f"Bearer {token}"}


def _make_admin(app, username, super_admin=False):
    """创建管理员并注入 ADMIN 令牌；super_admin 时复用种子账号 admin。"""
    with app.app_context():
        admin = AdminUser.query.filter_by(username=username).first()
        if admin is None:
            admin = AdminUser(username=username, password="not-used")
            db.session.add(admin)
            db.session.commit()
        token = secrets.token_urlsafe(16)
        db.session.add(AuthSession(token=token, role="ADMIN", admin_user_id=admin.id))
        db.session.commit()
    return {"Authorization": f"Bearer {token}"}


def _upload_small_file(client, headers, name="report.txt", content=b"cloudflow-dedup-payload"):
    """通过完整上传 API 落一个真实 blob，返回 (node_id, content_hash)。"""
    resp = client.post(
        "/api/files/upload",
        headers=headers,
        data={"file": (BytesIO(content), name)},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    node_id = resp.get_json()["data"]["id"]
    with client.application.app_context():
        node = FileNode.query.get(node_id)
        content_hash = node.content_hash
    return node_id, content_hash


# --------------------------------------------------------------------------
# 内容寻址 / 去重
# --------------------------------------------------------------------------

def test_direct_upload_reuses_blob_for_same_content(app):
    """整文件上传路径同样按 SHA-256 去重：两份同内容只保留一份物理文件。"""
    _, headers = _make_user(app, "dedup-direct")
    client = app.test_client()
    content = b"identical-bytes-for-dedup"

    first = client.post(
        "/api/files/upload", headers=headers,
        data={"file": (BytesIO(content), "a.txt")},
        content_type="multipart/form-data",
    )
    second = client.post(
        "/api/files/upload", headers=headers,
        data={"file": (BytesIO(content), "b.txt")},
        content_type="multipart/form-data",
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.get_json()["data"]["name"] == "a.txt"
    assert second.get_json()["data"]["name"] == "b.txt"  # 不同名，未触发副本重命名

    with app.app_context():
        blobs = FileBlob.query.all()
        assert len(blobs) == 1
        assert blobs[0].ref_count == 2
        from config import UPLOAD_DIR

        files = [p for p in (UPLOAD_DIR / "blobs").rglob("*") if p.is_file()]
        assert len(files) == 1
        assert files[0].name == blobs[0].content_hash


def test_instant_upload_hit_and_miss(app):
    """秒传：命中已有指纹直接建记录；格式非法或未命中均回退正常上传。"""
    uid, headers = _make_user(app, "dedup-instant")
    client = app.test_client()
    content = b"instant-upload-content"
    expected_hash = hashlib.sha256(content).hexdigest()
    _, node_hash = _upload_small_file(client, headers, "seed.txt", content)
    assert node_hash == expected_hash

    def check(value):
        return client.post(
            "/api/files/upload/check", headers=headers,
            json={"fileName": "again.txt", "fileSize": len(content),
                  "contentHash": value, "parentId": None},
        )

    # 非法指纹（长度不足）直接未命中
    assert check("deadbeef").get_json()["data"]["instant"] is False
    # 合法格式但库里不存在
    assert check("0" * 64).get_json()["data"]["instant"] is False
    # 命中：秒传成功，引用计数 +1
    hit = check(expected_hash.upper())  # 后端会小写归一
    assert hit.get_json()["data"]["instant"] is True
    assert hit.get_json()["data"]["entry"]["name"] == "again.txt"
    with app.app_context():
        assert FileBlob.query.filter_by(content_hash=expected_hash).one().ref_count == 2


# --------------------------------------------------------------------------
# 鉴权边界（越权 / 角色隔离）
# --------------------------------------------------------------------------

def test_cross_user_node_access_is_forbidden(app):
    """用户 B 不能读取/改名用户 A 的文件，统一按“不存在”(404) 处理。"""
    owner_id, owner_headers = _make_user(app, "owner")
    _, other_headers = _make_user(app, "intruder")
    client = app.test_client()
    node_id, _ = _upload_small_file(client, owner_headers, "secret.txt")

    assert client.get(
        f"/api/files/nodes/{node_id}/download", headers=other_headers
    ).status_code == 404
    rename = client.patch(
        f"/api/files/nodes/{node_id}/rename", headers=other_headers, json={"name": "hijacked.txt"}
    )
    assert rename.status_code == 404
    with app.app_context():
        assert FileNode.query.get(node_id).name == "secret.txt"


def test_role_based_access_control(app):
    """普通用户访问管理端接口、管理员访问用户端接口均被 403 拒绝。"""
    _, user_headers = _make_user(app, "role-user")
    admin_headers = _make_admin(app, "role-admin")
    client = app.test_client()

    assert client.get("/api/admin/overview", headers=user_headers).status_code == 403
    assert client.get("/api/files", headers=admin_headers).status_code == 403


def test_admin_management_requires_super_admin(app):
    """只有 admin 账号能访问管理员管理，普通管理员 403。"""
    sub_headers = _make_admin(app, "sub-admin")
    super_headers = _make_admin(app, "admin", super_admin=True)
    client = app.test_client()

    assert client.get("/api/admin/admins", headers=sub_headers).status_code == 403
    assert client.get("/api/admin/admins", headers=super_headers).status_code == 200


def test_no_token_is_rejected(app):
    """不带任何令牌访问受保护接口返回 401。"""
    resp = app.test_client().get("/api/files/workspace")
    assert resp.status_code == 401
    assert resp.get_json()["code"] == 401


# --------------------------------------------------------------------------
# 分享边界
# --------------------------------------------------------------------------

def test_public_share_validation(app):
    """公开分享：非法 token 404、有效可下载、取消与过期均 409。"""
    _, headers = _make_user(app, "sharer")
    client = app.test_client()
    node_id, _ = _upload_small_file(client, headers, "share-me.txt", b"share-content-here")

    created = client.post(
        f"/api/files/nodes/{node_id}/share", headers=headers, json={"expireDays": 7}
    )
    assert created.status_code == 200
    data = created.get_json()["data"]
    share_id = data["id"]
    token = data["link"].rsplit("/", 1)[-1]

    assert client.get("/share/not-a-valid-token").status_code == 404
    assert client.get(f"/share/{token}").status_code == 200

    assert client.patch(
        f"/api/shares/{share_id}/cancel", headers=headers
    ).status_code == 200
    assert client.get(f"/share/{token}").status_code == 409  # 已取消

    # 重新生效并置为过期
    with app.app_context():
        share = ShareRecord.query.get(share_id)
        share.status = "生效中"
        share.expires_at = datetime.utcnow() - timedelta(days=1)
        db.session.commit()
    assert client.get(f"/share/{token}").status_code == 409  # 已过期


# --------------------------------------------------------------------------
# 软删除 / 恢复
# --------------------------------------------------------------------------

def test_delete_and_restore_roundtrip(app):
    """删除进回收站后节点不可见，恢复后回到根目录且引用计数不变。"""
    uid, headers = _make_user(app, "recycle-user")
    client = app.test_client()
    node_id, content_hash = _upload_small_file(client, headers, "keep.txt", b"recycle-roundtrip-body")

    assert client.delete(
        f"/api/files/nodes/{node_id}", headers=headers
    ).status_code == 200
    assert client.get(
        f"/api/files/nodes/{node_id}/download", headers=headers
    ).status_code == 404

    with app.app_context():
        recycle = RecycleRecord.query.filter_by(user_id=uid).one()
        assert recycle.content_hash == content_hash
        recycle_id = recycle.id

    restored = client.post(f"/api/recycle/{recycle_id}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.get_json()["data"]["name"] == "keep.txt"
    with app.app_context():
        assert RecycleRecord.query.filter_by(user_id=uid).count() == 0
        assert FileNode.query.filter_by(user_id=uid, name="keep.txt", node_type="file").count() == 1
        assert FileBlob.query.filter_by(content_hash=content_hash).one().ref_count == 1
