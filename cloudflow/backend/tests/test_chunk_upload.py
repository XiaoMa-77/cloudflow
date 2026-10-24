"""分片上传集成测试：分片合并、SHA-256 去重秒传与引用计数、断点续传状态。"""

import pytest

from extensions import db
from models import FileBlob, User
from services.chunk_upload import (
    FileManagerError,
    _parse_received,
    complete_chunk_upload,
    init_chunk_upload,
    save_chunk,
)


@pytest.fixture()
def user_id(app):
    with app.app_context():
        user = User(
            username="chunk-tester",
            password="irrelevant",
            status="ACTIVE",
            used_space_bytes=0,
            space_limit_bytes=10 * 1024 * 1024 * 1024,
        )
        db.session.add(user)
        db.session.commit()
        yield user.id


def _payload(name: str, size: int, chunks: int) -> dict:
    return {
        "fileName": name,
        "fileSize": size,
        "chunkSize": 256 * 1024,  # 服务端允许的最小分片
        "totalChunks": chunks,
    }


def _upload_two_chunks(app, uid, name, first: bytes, second: bytes) -> dict:
    """走完 init → save × 2 → complete 全流程，返回文件节点。"""
    with app.app_context():
        info = init_chunk_upload(uid, _payload(name, len(first) + len(second), 2))
        token = info["uploadId"]
        save_chunk(uid, token, 0, first)
        save_chunk(uid, token, 1, second)
        return complete_chunk_upload(uid, token)


def test_chunk_upload_creates_blob_and_node(app, user_id):
    node = _upload_two_chunks(app, user_id, "report.bin", b"hello-", b"cloudflow")
    assert node["name"] == "report.bin"
    assert node["sizeBytes"] == len(b"hello-cloudflow")
    with app.app_context():
        blob = FileBlob.query.one()
        assert blob.ref_count == 1
        assert blob.size_bytes == len(b"hello-cloudflow")
        # 物理文件落在内容寻址路径 blobs/<hash[:2]>/<hash>
        from config import UPLOAD_DIR

        assert (UPLOAD_DIR / "blobs" / blob.content_hash[:2] / blob.content_hash).is_file()


def test_same_content_dedups_and_increments_ref_count(app, user_id):
    """去重秒传：同内容不同文件名，Blob 只有一份、引用计数 +1。"""
    _upload_two_chunks(app, user_id, "a.bin", b"same-", b"content")
    _upload_two_chunks(app, user_id, "b.bin", b"same-", b"content")
    with app.app_context():
        blob = FileBlob.query.one()
        assert blob.ref_count == 2
        from config import UPLOAD_DIR

        # 去重后物理文件仍只有一份
        blob_files = list((UPLOAD_DIR / "blobs").rglob("*"))
        assert len([p for p in blob_files if p.is_file()]) == 1


def test_incomplete_upload_cannot_complete(app, user_id):
    with app.app_context():
        info = init_chunk_upload(user_id, _payload("partial.bin", 20, 2))
        save_chunk(user_id, info["uploadId"], 0, b"only-first-half!!")
        with pytest.raises(FileManagerError, match="缺少 1 片"):
            complete_chunk_upload(user_id, info["uploadId"])


def test_resume_reuses_session_and_reports_received(app, user_id):
    """断点续传：同名同大小的进行中会话被复用，已收分片序号如实返回。"""
    with app.app_context():
        first = init_chunk_upload(user_id, _payload("resume.bin", 20, 2))
        save_chunk(user_id, first["uploadId"], 1, b"second-half")
        resumed = init_chunk_upload(user_id, _payload("resume.bin", 20, 2))
        assert resumed["uploadId"] == first["uploadId"]
        assert resumed["uploadedChunks"] == [1]


def test_oversize_file_rejected(app, user_id):
    with app.app_context():
        with pytest.raises(FileManagerError, match="上限"):
            init_chunk_upload(user_id, _payload("huge.bin", 3 * 1024 * 1024 * 1024, 2))


def test_parse_received_normalizes_input():
    assert _parse_received("") == []
    assert _parse_received("3,1,2") == [1, 2, 3]
    assert _parse_received("1,1,2") == [1, 2]      # 去重
    assert _parse_received("1, x, 02") == [1, 2]   # 容忍脏数据与前导零
