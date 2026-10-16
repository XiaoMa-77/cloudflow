"""分片上传 / 断点续传服务。

流程：
1. ``init_chunk_upload``   —— 创建（或复用）上传会话，返回已收分片索引实现续传；
2. ``save_chunk``          —— 逐片写入临时目录 ``uploads/.chunks/<token>/``；
3. ``complete_chunk_upload`` —— 合并分片、校验大小、按 SHA-256 去重落盘并创建文件记录。
"""
from __future__ import annotations

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from config import UPLOAD_DIR
from extensions import db
from models import FileBlob, UploadSession, User
from services.file_manager import (
    CHUNK_TMP_DIR,
    FileManagerError,
    PREVIEW_MIME_BY_EXTENSION,
    _create_file_node,
    _extract_extension,
    _get_user_node,
    _normalize_client_filename,
    _resolve_duplicate_name,
    ensure_root_folder,
)

_MIN_CHUNK_SIZE = 256 * 1024
_MAX_CHUNK_SIZE = 16 * 1024 * 1024
_MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024


def init_chunk_upload(user_id: int, payload: dict) -> dict:
    file_name = _normalize_client_filename(str(payload.get('fileName', '')))
    total_bytes = _to_int(payload.get('fileSize'))
    chunk_size = _to_int(payload.get('chunkSize')) or 4 * 1024 * 1024
    total_chunks = _to_int(payload.get('totalChunks'))
    parent_id = payload.get('parentId')
    content_hash = str(payload.get('contentHash', '')).strip().lower()

    if not file_name:
        raise FileManagerError('文件名不能为空', code=400)
    if not total_bytes or total_bytes <= 0:
        raise FileManagerError('文件大小无效', code=400)
    if total_bytes > _MAX_TOTAL_BYTES:
        raise FileManagerError('文件大小超出单文件上限（2GB）', code=400)
    if chunk_size < _MIN_CHUNK_SIZE or chunk_size > _MAX_CHUNK_SIZE:
        raise FileManagerError('分片大小需在 256KB 到 16MB 之间', code=400)
    if not total_chunks or total_chunks <= 0:
        total_chunks = (total_bytes + chunk_size - 1) // chunk_size

    root = ensure_root_folder(user_id)
    parent = root if parent_id is None else _get_user_node(user_id, int(parent_id))
    if parent.node_type != 'folder':
        raise FileManagerError('上传目录不存在', code=404)

    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise FileManagerError('用户不存在', code=404)
    if user.used_space_bytes + total_bytes > user.space_limit_bytes:
        raise FileManagerError('存储空间不足，上传失败', code=409)

    # 续传：同用户 + 同名 + 同大小的进行中会话直接复用
    session = (
        UploadSession.query.filter_by(
            user_id=user_id,
            file_name=file_name,
            total_bytes=total_bytes,
            status='UPLOADING',
        )
        .order_by(UploadSession.created_at.desc())
        .first()
    )

    if session is None:
        session = UploadSession(
            user_id=user_id,
            upload_token=uuid4().hex,
            file_name=file_name,
            parent_id=parent.id,
            total_bytes=total_bytes,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            received_chunks='',
            status='UPLOADING',
        )
        db.session.add(session)
        db.session.commit()

    return {
        'uploadId': session.upload_token,
        'chunkSize': session.chunk_size,
        'totalChunks': session.total_chunks,
        'uploadedChunks': _parse_received(session.received_chunks),
    }


def save_chunk(user_id: int, upload_token: str, chunk_index: int, chunk_bytes: bytes) -> dict:
    session = _get_session(user_id, upload_token)
    if not chunk_bytes:
        raise FileManagerError('分片内容为空', code=400)
    if chunk_index < 0 or chunk_index >= session.total_chunks:
        raise FileManagerError('分片序号超出范围', code=400)

    session_dir = CHUNK_TMP_DIR / session.upload_token
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / f'{chunk_index}.part').write_bytes(chunk_bytes)

    received = _parse_received(session.received_chunks)
    if chunk_index not in received:
        received.append(chunk_index)
    session.received_chunks = ','.join(str(index) for index in sorted(received))
    session.updated_at = datetime.utcnow()
    db.session.commit()

    return {
        'chunkIndex': chunk_index,
        'receivedCount': len(received),
        'totalChunks': session.total_chunks,
    }


def complete_chunk_upload(user_id: int, upload_token: str) -> dict:
    session = _get_session(user_id, upload_token)
    received = _parse_received(session.received_chunks)
    if len(received) != session.total_chunks:
        missing = [index for index in range(session.total_chunks) if index not in received]
        raise FileManagerError(f'分片不完整，缺少 {len(missing)} 片，请续传后再合并', code=409)

    session_dir = CHUNK_TMP_DIR / session.upload_token
    merged_path = session_dir / 'merged.bin'

    # 合并分片并流式计算 SHA-256
    hasher = hashlib.sha256()
    merged_size = 0
    with merged_path.open('wb') as merged:
        for index in range(session.total_chunks):
            part_path = session_dir / f'{index}.part'
            if not part_path.exists():
                raise FileManagerError('分片文件丢失，请重新上传该文件', code=409)
            with part_path.open('rb') as part:
                while True:
                    block = part.read(1024 * 1024)
                    if not block:
                        break
                    merged.write(block)
                    hasher.update(block)
                    merged_size += len(block)

    if merged_size != session.total_bytes:
        shutil.rmtree(session_dir, ignore_errors=True)
        session.status = 'FAILED'
        db.session.commit()
        raise FileManagerError('合并后文件大小与预期不符，请重新上传', code=409)

    content_hash = hasher.hexdigest()

    # 去重：内容指纹已存在且物理文件在，则丢弃合并结果直接复用
    blob = FileBlob.query.filter_by(content_hash=content_hash).first()
    if blob and blob.storage_rel_path:
        absolute_path = UPLOAD_DIR / Path(blob.storage_rel_path)
        if absolute_path.exists() and absolute_path.is_file():
            storage_rel_path = blob.storage_rel_path
            blob.ref_count = (blob.ref_count or 0) + 1
            blob.updated_at = datetime.utcnow()
            shutil.rmtree(session_dir, ignore_errors=True)
        else:
            storage_rel_path = _promote_merged_file(merged_path, content_hash, blob)
    else:
        storage_rel_path = _promote_merged_file(merged_path, content_hash, None)

    parent = _get_user_node(user_id, session.parent_id) if session.parent_id else ensure_root_folder(user_id)
    if parent.node_type != 'folder':
        shutil.rmtree(session_dir, ignore_errors=True)
        raise FileManagerError('上传目录不存在', code=404)

    # 配额复查（会话期间可能有其他上传）
    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise FileManagerError('用户不存在', code=404)
    if user.used_space_bytes + session.total_bytes > user.space_limit_bytes:
        shutil.rmtree(session_dir, ignore_errors=True)
        session.status = 'FAILED'
        db.session.commit()
        raise FileManagerError('存储空间不足，上传失败', code=409)

    safe_name = _resolve_duplicate_name(user_id, parent.id, session.file_name)
    extension = _extract_extension(safe_name)

    session.status = 'COMPLETED'
    node = _create_file_node(
        user_id=user_id,
        parent=parent,
        name=safe_name,
        extension=extension,
        mime_type=PREVIEW_MIME_BY_EXTENSION.get(extension, ''),
        size_bytes=session.total_bytes,
        storage_rel_path=storage_rel_path,
        content_hash=content_hash,
        action='上传文件（分片）',
    )
    shutil.rmtree(session_dir, ignore_errors=True)
    db.session.delete(session)
    db.session.commit()

    from services.file_manager import _serialize_node

    return _serialize_node(node, 0, is_favorite=False)


def _promote_merged_file(merged_path: Path, content_hash: str, blob: FileBlob | None) -> str:
    rel_path = str(Path('blobs') / content_hash[:2] / content_hash)
    absolute_path = UPLOAD_DIR / Path(rel_path)
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(merged_path), str(absolute_path))

    if blob:
        blob.storage_rel_path = rel_path
        blob.size_bytes = absolute_path.stat().st_size
        blob.updated_at = datetime.utcnow()
    else:
        db.session.add(
            FileBlob(
                content_hash=content_hash,
                size_bytes=absolute_path.stat().st_size,
                storage_rel_path=rel_path,
                ref_count=1,
            )
        )
    return rel_path


def _get_session(user_id: int, upload_token: str) -> UploadSession:
    session = UploadSession.query.filter_by(upload_token=upload_token, user_id=user_id).first()
    if not session:
        raise FileManagerError('上传会话不存在或已过期，请重新上传', code=404)
    if session.status != 'UPLOADING':
        raise FileManagerError('上传会话已结束，请重新上传', code=409)
    return session


def _parse_received(raw: str) -> list[int]:
    if not raw:
        return []
    values = []
    for piece in raw.split(','):
        piece = piece.strip()
        if piece.isdigit():
            values.append(int(piece))
    return sorted(set(values))


def _to_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
