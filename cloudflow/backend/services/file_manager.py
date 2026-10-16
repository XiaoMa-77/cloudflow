from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import case, func
from werkzeug.datastructures import FileStorage

from config import UPLOAD_DIR
from extensions import db
from models import EmbeddingChunk, FavoriteRecord, FileBlob, FileNode, RecycleRecord, ShareRecord, User

AI_SUPPORTED_EXTENSIONS = {'txt', 'doc', 'docx', 'md', 'csv', 'xls', 'xlsx', 'pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp'}
AI_DOCUMENT_EXTENSIONS = {'txt', 'doc', 'docx', 'md', 'csv', 'xls', 'xlsx', 'pdf'}
AI_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
BLOB_DIR = UPLOAD_DIR / 'blobs'
CHUNK_TMP_DIR = UPLOAD_DIR / '.chunks'
_HASH_HEX_LENGTH = 64
IMAGE_PREVIEW_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
VIDEO_PREVIEW_EXTENSIONS = {'mp4', 'webm'}
PREVIEW_MIME_BY_EXTENSION = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'mp4': 'video/mp4',
    'webm': 'video/webm',
}
FILE_TYPE_BY_EXTENSION = {
    'pdf': 'document',
    'doc': 'document',
    'docx': 'document',
    'txt': 'document',
    'md': 'document',
    'csv': 'document',
    'xlsx': 'document',
    'xls': 'document',
    'ppt': 'document',
    'pptx': 'document',
    'jpg': 'image',
    'jpeg': 'image',
    'png': 'image',
    'gif': 'image',
    'webp': 'image',
    'mp4': 'video',
    'webm': 'video',
    'zip': 'archive',
    'rar': 'archive',
    '7z': 'archive',
}


class FileManagerError(Exception):
    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code


def ensure_root_folder(user_id: int) -> FileNode:
    root = (
        FileNode.query.filter_by(user_id=user_id, node_type='folder')
        .filter(FileNode.parent_id.is_(None))
        .first()
    )
    if root:
        return root

    root = FileNode(
        user_id=user_id,
        parent_id=None,
        node_type='folder',
        name='我的文件',
        extension='',
        size_bytes=0,
    )
    db.session.add(root)
    db.session.commit()
    return root


def get_workspace(user_id: int, folder_id: int | None = None, keyword: str = '', sort: str = 'name_asc') -> dict:
    root = ensure_root_folder(user_id)
    current = root

    if folder_id is not None:
        current = _get_user_node(user_id, folder_id)
        if current.node_type != 'folder':
            raise FileManagerError('目标目录不存在', code=404)

    normalized_sort = (sort or 'name_asc').strip().lower()
    if normalized_sort not in {'name_asc', 'name_desc', 'updated_desc', 'updated_asc', 'size_desc', 'size_asc'}:
        normalized_sort = 'name_asc'

    query = FileNode.query.filter_by(user_id=user_id, parent_id=current.id)
    normalized_keyword = (keyword or '').strip()
    if normalized_keyword:
        query = query.filter(func.lower(FileNode.name).like(f'%{normalized_keyword.lower()}%'))

    entries = query.all()

    folder_ids = [item.id for item in entries if item.node_type == 'folder']
    children_counts = {}
    if folder_ids:
        rows = (
            db.session.query(FileNode.parent_id, func.count(FileNode.id))
            .filter(FileNode.user_id == user_id, FileNode.parent_id.in_(folder_ids))
            .group_by(FileNode.parent_id)
            .all()
        )
        children_counts = {parent_id: count for parent_id, count in rows}

    entry_ids = [item.id for item in entries if item.node_type == 'file']
    favorite_ids = set()
    if entry_ids:
        favorite_rows = FavoriteRecord.query.filter(
            FavoriteRecord.user_id == user_id, FavoriteRecord.file_node_id.in_(entry_ids)
        ).all()
        favorite_ids = {item.file_node_id for item in favorite_rows}

    entries = _sort_workspace_entries(entries=entries, sort=normalized_sort, children_counts=children_counts)

    return {
        'currentFolder': {
            'id': current.id,
            'name': current.name,
            'parentId': current.parent_id,
        },
        'breadcrumbs': _build_breadcrumbs(current),
        'keyword': normalized_keyword,
        'sort': normalized_sort,
        'items': [
            _serialize_node(item, children_counts.get(item.id, 0), is_favorite=item.id in favorite_ids) for item in entries
        ],
    }


def create_folder(user_id: int, parent_id: int | None, name: str) -> dict:
    root = ensure_root_folder(user_id)
    parent = root if parent_id is None else _get_user_node(user_id, parent_id)
    if parent.node_type != 'folder':
        raise FileManagerError('父级目录不存在', code=404)

    folder_name = (name or '').strip()
    if not folder_name:
        raise FileManagerError('文件夹名称不能为空', code=400)

    if _sibling_name_exists(user_id, parent.id, folder_name):
        raise FileManagerError('同级目录已存在同名文件或文件夹', code=409)

    node = FileNode(
        user_id=user_id,
        parent_id=parent.id,
        node_type='folder',
        name=folder_name,
        extension='',
        mime_type='',
        storage_rel_path='',
        size_bytes=0,
        updated_at=datetime.utcnow(),
    )
    db.session.add(node)
    from services.user_portal import record_activity

    record_activity(user_id=user_id, file_name=folder_name, action='新建文件夹')
    db.session.commit()
    return _serialize_node(node, 0, is_favorite=False)


def upload_file(user_id: int, parent_id: int | None, upload: FileStorage) -> dict:
    if not upload:
        raise FileManagerError('请先选择要上传的文件', code=400)

    root = ensure_root_folder(user_id)
    parent = root if parent_id is None else _get_user_node(user_id, parent_id)
    if parent.node_type != 'folder':
        raise FileManagerError('上传目录不存在', code=404)

    original_name = _normalize_client_filename(upload.filename or '')
    if not original_name:
        original_name = f'未命名文件-{uuid4().hex[:6]}.bin'

    original_extension = _extract_extension(original_name)
    inferred_extension = _infer_extension_from_mime(upload.mimetype or '')
    if not original_extension and inferred_extension:
        original_name = f'{original_name}.{inferred_extension}'

    file_bytes = upload.read()
    size_bytes = len(file_bytes)

    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise FileManagerError('用户不存在', code=404)
    if user.used_space_bytes + size_bytes > user.space_limit_bytes:
        raise FileManagerError('存储空间不足，上传失败', code=409)

    safe_name = _resolve_duplicate_name(user_id, parent.id, original_name)
    extension = _extract_extension(safe_name)
    mime_type = _normalize_mime_type(upload.mimetype or '')
    if not mime_type:
        mime_type = PREVIEW_MIME_BY_EXTENSION.get(extension, '')

    content_hash, storage_rel_path, _ = _store_blob_from_bytes(file_bytes)

    node = _create_file_node(
        user_id=user_id,
        parent=parent,
        name=safe_name,
        extension=extension,
        mime_type=mime_type,
        size_bytes=size_bytes,
        storage_rel_path=storage_rel_path,
        content_hash=content_hash,
        action='上传文件',
    )
    return _serialize_node(node, 0, is_favorite=False)


def check_instant_upload(user_id: int, parent_id: int | None, file_name: str, size_bytes: int, content_hash: str) -> dict:
    """秒传检查：内容指纹命中且物理文件存在时，直接创建文件记录，不再传输数据。"""
    normalized_hash = (content_hash or '').strip().lower()
    if len(normalized_hash) != _HASH_HEX_LENGTH:
        return {'instant': False}

    root = ensure_root_folder(user_id)
    parent = root if parent_id is None else _get_user_node(user_id, parent_id)
    if parent.node_type != 'folder':
        raise FileManagerError('上传目录不存在', code=404)

    blob = FileBlob.query.filter_by(content_hash=normalized_hash).first()
    if not blob or not blob.storage_rel_path:
        return {'instant': False}

    absolute_path = UPLOAD_DIR / Path(blob.storage_rel_path)
    if not absolute_path.exists() or not absolute_path.is_file():
        return {'instant': False}

    size = int(size_bytes or blob.size_bytes or 0)
    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise FileManagerError('用户不存在', code=404)
    if user.used_space_bytes + size > user.space_limit_bytes:
        raise FileManagerError('存储空间不足，上传失败', code=409)

    original_name = _normalize_client_filename(file_name or '') or f'未命名文件-{uuid4().hex[:6]}.bin'
    safe_name = _resolve_duplicate_name(user_id, parent.id, original_name)
    extension = _extract_extension(safe_name)
    blob.ref_count = (blob.ref_count or 0) + 1
    blob.updated_at = datetime.utcnow()

    node = _create_file_node(
        user_id=user_id,
        parent=parent,
        name=safe_name,
        extension=extension,
        mime_type=PREVIEW_MIME_BY_EXTENSION.get(extension, ''),
        size_bytes=size,
        storage_rel_path=blob.storage_rel_path,
        content_hash=normalized_hash,
        action='秒传文件',
    )
    return {'instant': True, 'entry': _serialize_node(node, 0, is_favorite=False)}


def _store_blob_from_bytes(file_bytes: bytes) -> tuple[str, str, bool]:
    """按内容指纹落盘：命中已有 blob 则复用（去重），否则写入 blobs/<xx>/<hash>。"""
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    blob = FileBlob.query.filter_by(content_hash=content_hash).first()

    if blob and blob.storage_rel_path:
        absolute_path = UPLOAD_DIR / Path(blob.storage_rel_path)
        if absolute_path.exists() and absolute_path.is_file():
            blob.ref_count = (blob.ref_count or 0) + 1
            blob.updated_at = datetime.utcnow()
            return content_hash, blob.storage_rel_path, False

    rel_path = str(Path('blobs') / content_hash[:2] / content_hash)
    absolute_path = UPLOAD_DIR / Path(rel_path)
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(file_bytes)

    if blob:
        blob.size_bytes = len(file_bytes)
        blob.storage_rel_path = rel_path
        blob.updated_at = datetime.utcnow()
    else:
        blob = FileBlob(
            content_hash=content_hash,
            size_bytes=len(file_bytes),
            storage_rel_path=rel_path,
            ref_count=1,
        )
        db.session.add(blob)
    return content_hash, rel_path, True


def _create_file_node(user_id: int, parent: FileNode, name: str, extension: str, mime_type: str,
                      size_bytes: int, storage_rel_path: str, content_hash: str, action: str = '上传文件') -> FileNode:
    node = FileNode(
        user_id=user_id,
        parent_id=parent.id,
        node_type='file',
        name=name,
        extension=extension,
        mime_type=mime_type,
        storage_rel_path=storage_rel_path,
        content_hash=content_hash,
        size_bytes=size_bytes,
        updated_at=datetime.utcnow(),
    )
    db.session.add(node)
    from services.user_portal import recalculate_user_storage, record_activity

    recalculate_user_storage(user_id)
    record_activity(user_id=user_id, file_name=name, action=action)
    db.session.commit()
    return node


def release_storage_reference(storage_rel_path: str, content_hash: str = '') -> None:
    """释放一处存储引用：仅在没有任何文件节点/回收站记录再引用该物理文件时才删除。"""
    if not storage_rel_path:
        return

    still_referenced = (
        FileNode.query.filter(FileNode.storage_rel_path == storage_rel_path).first() is not None
        or RecycleRecord.query.filter(RecycleRecord.storage_rel_path == storage_rel_path).first() is not None
    )
    if still_referenced:
        return

    absolute_path = UPLOAD_DIR / Path(storage_rel_path)
    if absolute_path.exists() and absolute_path.is_file():
        absolute_path.unlink(missing_ok=True)

    normalized_hash = (content_hash or '').strip().lower()
    if normalized_hash:
        blob = FileBlob.query.filter_by(content_hash=normalized_hash).first()
        if blob:
            db.session.delete(blob)


def get_download_payload(user_id: int, node_id: int) -> dict:
    node = _get_user_node(user_id, node_id)
    if node.node_type != 'file':
        raise FileManagerError('仅支持下载文件', code=400)

    if node.storage_rel_path:
        absolute_path = UPLOAD_DIR / node.storage_rel_path
        if absolute_path.exists() and absolute_path.is_file():
            return {
                'name': node.name,
                'mimeType': node.mime_type or 'application/octet-stream',
                'path': absolute_path,
                'bytes': None,
            }

    fallback = f'文件名：{node.name}\n当前仅保留文件记录信息，系统已生成说明文件用于下载。'.encode('utf-8')
    return {
        'name': node.name,
        'mimeType': 'text/plain; charset=utf-8',
        'path': None,
        'bytes': fallback,
    }


def get_preview_payload(user_id: int, node_id: int) -> dict:
    node = _get_user_node(user_id, node_id)
    if node.node_type != 'file':
        raise FileManagerError('仅支持预览文件', code=400)

    preview_kind = _resolve_preview_kind(node.extension, node.mime_type)
    if not preview_kind:
        raise FileManagerError('当前文件类型暂不支持在线预览', code=409)

    if not node.storage_rel_path:
        raise FileManagerError('未找到可预览的文件内容', code=404)

    absolute_path = UPLOAD_DIR / node.storage_rel_path
    if not absolute_path.exists() or not absolute_path.is_file():
        raise FileManagerError('预览文件不存在，请重新上传后重试', code=404)

    mime = _resolve_preview_mime(preview_kind=preview_kind, extension=node.extension, mime_type=node.mime_type)

    return {
        'path': absolute_path,
        'name': node.name,
        'mimeType': mime,
        'previewType': preview_kind,
    }


def batch_delete_nodes(user_id: int, node_ids: list[int]) -> dict:
    unique_ids = []
    for node_id in node_ids:
        if node_id not in unique_ids:
            unique_ids.append(node_id)

    deleted_count = 0
    recycled_count = 0
    for node_id in unique_ids:
        result = delete_node(user_id=user_id, node_id=node_id)
        deleted_count += result.get('removedNodeCount', 0)
        recycled_count += result.get('movedToRecycleCount', 0)

    return {
        'deletedNodeCount': deleted_count,
        'movedToRecycleCount': recycled_count,
    }


def rename_node(user_id: int, node_id: int, name: str) -> dict:
    target = _get_user_node(user_id, node_id)

    if target.parent_id is None:
        raise FileManagerError('根目录不支持重命名', code=409)

    next_name = (name or '').strip()
    if not next_name:
        raise FileManagerError('名称不能为空', code=400)

    if _sibling_name_exists(user_id, target.parent_id, next_name, exclude_id=target.id):
        raise FileManagerError('同级目录已存在同名文件或文件夹', code=409)

    target.name = next_name
    if target.node_type == 'file':
        target.extension = _extract_extension(next_name)
    target.updated_at = datetime.utcnow()
    from services.user_portal import record_activity

    record_activity(user_id=user_id, file_name=target.name, action='重命名文件')
    db.session.commit()

    return _serialize_node(target, 0, is_favorite=_is_favorite(user_id, target.id))


def delete_node(user_id: int, node_id: int) -> dict:
    target = _get_user_node(user_id, node_id)
    if target.parent_id is None:
        raise FileManagerError('根目录不支持删除', code=409)

    all_nodes = FileNode.query.filter_by(user_id=user_id).all()
    descendants = _collect_subtree_ids(node_id, all_nodes)

    recycle_count = 0
    now = datetime.utcnow()
    for node in all_nodes:
        if node.id not in descendants or node.node_type != 'file':
            continue

        db.session.add(
            RecycleRecord(
                user_id=user_id,
                file_name=node.name,
                file_type=FILE_TYPE_BY_EXTENSION.get(node.extension, 'other'),
                extension=node.extension or '',
                mime_type=node.mime_type or '',
                storage_rel_path=node.storage_rel_path or '',
                content_hash=node.content_hash or '',
                size_bytes=node.size_bytes,
                deleted_at=now,
                remaining_days=30,
            )
        )
        recycle_count += 1

    FavoriteRecord.query.filter(FavoriteRecord.user_id == user_id, FavoriteRecord.file_node_id.in_(descendants)).delete(
        synchronize_session=False
    )
    EmbeddingChunk.query.filter(EmbeddingChunk.user_id == user_id, EmbeddingChunk.file_node_id.in_(descendants)).delete(
        synchronize_session=False
    )
    FileNode.query.filter(FileNode.user_id == user_id, FileNode.id.in_(descendants)).delete(synchronize_session=False)
    from services.user_portal import recalculate_user_storage, record_activity

    recalculate_user_storage(user_id)
    record_activity(user_id=user_id, file_name=target.name, action='删除到回收站')
    db.session.commit()

    return {
        'removedNodeCount': len(descendants),
        'movedToRecycleCount': recycle_count,
    }


def create_share(user_id: int, node_id: int, expire_days: int = 7, share_host: str = '') -> dict:
    target = _get_user_node(user_id, node_id)
    if expire_days < 1 or expire_days > 30:
        raise FileManagerError('分享有效期需在 1 到 30 天之间', code=400)

    now = datetime.utcnow()
    base = (share_host or '').rstrip('/')
    if not base:
        base = 'https://localhost'
    share_url = f'{base}/share/u{user_id}-n{target.id}-{int(now.timestamp())}'

    share = ShareRecord(
        user_id=user_id,
        file_record_id=None,
        file_name=target.name,
        share_url=share_url,
        access_mode='公开访问',
        status='生效中',
        expires_at=now + timedelta(days=expire_days),
        visit_count=0,
    )
    db.session.add(share)
    from services.user_portal import record_activity

    record_activity(user_id=user_id, file_name=target.name, action='创建分享链接')
    db.session.commit()

    return {
        'id': share.id,
        'fileName': share.file_name,
        'link': share.share_url,
        'status': share.status,
        'expireAt': share.expires_at.strftime('%Y-%m-%d %H:%M'),
    }


def paste_node(user_id: int, source_id: int, target_folder_id: int, mode: str) -> dict:
    action_mode = (mode or '').strip().lower()
    if action_mode not in {'copy', 'move'}:
        raise FileManagerError('粘贴模式无效', code=400)

    source = _get_user_node(user_id, source_id)
    target_folder = _get_user_node(user_id, target_folder_id)

    if target_folder.node_type != 'folder':
        raise FileManagerError('粘贴目标必须是文件夹', code=400)

    if action_mode == 'move':
        if source.parent_id is None:
            raise FileManagerError('根目录不支持移动', code=409)
        if source.id == target_folder.id:
            raise FileManagerError('不能移动到自身目录', code=409)

        all_nodes = FileNode.query.filter_by(user_id=user_id).all()
        descendants = _collect_subtree_ids(source.id, all_nodes)
        if target_folder.id in descendants:
            raise FileManagerError('不能移动到子目录中', code=409)

        source.parent_id = target_folder.id
        source.name = _resolve_duplicate_name(user_id, target_folder.id, source.name, exclude_id=source.id)
        source.updated_at = datetime.utcnow()
        from services.user_portal import record_activity

        record_activity(user_id=user_id, file_name=source.name, action='移动文件')
        db.session.commit()

        return {
            'mode': 'move',
            'entry': _serialize_node(source, 0, is_favorite=_is_favorite(user_id, source.id)),
        }

    copied = _copy_subtree(user_id, source, target_folder.id)
    from services.user_portal import record_activity

    record_activity(user_id=user_id, file_name=source.name, action='复制文件')
    db.session.commit()
    return {
        'mode': 'copy',
        'entry': _serialize_node(copied, 0, is_favorite=_is_favorite(user_id, copied.id)),
    }


def _copy_subtree(user_id: int, source: FileNode, parent_id: int) -> FileNode:
    node_copy = FileNode(
        user_id=user_id,
        parent_id=parent_id,
        node_type=source.node_type,
        name=_resolve_duplicate_name(user_id, parent_id, source.name),
        extension=source.extension,
        mime_type=source.mime_type,
        storage_rel_path=source.storage_rel_path,
        content_hash=source.content_hash or '',
        size_bytes=source.size_bytes,
        updated_at=datetime.utcnow(),
    )
    db.session.add(node_copy)
    db.session.flush()

    if source.node_type == 'folder':
        children = (
            FileNode.query.filter_by(user_id=user_id, parent_id=source.id)
            .order_by(case((FileNode.node_type == 'folder', 0), else_=1), FileNode.name.asc())
            .all()
        )
        for child in children:
            _copy_subtree(user_id, child, node_copy.id)

    return node_copy


def _build_breadcrumbs(folder: FileNode) -> list[dict]:
    nodes = []
    current = folder
    while current:
        nodes.append({'id': current.id, 'name': current.name})
        if current.parent_id is None:
            break
        current = FileNode.query.filter_by(id=current.parent_id).first()
    nodes.reverse()
    return nodes


def _collect_subtree_ids(root_id: int, all_nodes: list[FileNode]) -> set[int]:
    children_map = defaultdict(list)
    for node in all_nodes:
        children_map[node.parent_id].append(node.id)

    collected = set()
    queue = [root_id]
    while queue:
        node_id = queue.pop(0)
        if node_id in collected:
            continue
        collected.add(node_id)
        queue.extend(children_map.get(node_id, []))
    return collected


def _sibling_name_exists(user_id: int, parent_id: int | None, name: str, exclude_id: int | None = None) -> bool:
    query = FileNode.query.filter_by(user_id=user_id)
    if parent_id is None:
        query = query.filter(FileNode.parent_id.is_(None))
    else:
        query = query.filter_by(parent_id=parent_id)

    query = query.filter(func.lower(FileNode.name) == name.lower())
    if exclude_id is not None:
        query = query.filter(FileNode.id != exclude_id)

    return query.first() is not None


def _resolve_duplicate_name(user_id: int, parent_id: int, base_name: str, exclude_id: int | None = None) -> str:
    if not _sibling_name_exists(user_id, parent_id, base_name, exclude_id=exclude_id):
        return base_name

    main, extension = _split_name(base_name)
    index = 1
    while True:
        suffix = '' if index == 1 else str(index)
        candidate = f'{main}-副本{suffix}{extension}'
        if not _sibling_name_exists(user_id, parent_id, candidate, exclude_id=exclude_id):
            return candidate
        index += 1


def _split_name(name: str) -> tuple[str, str]:
    dot = name.rfind('.')
    if dot < 0:
        return name, ''
    return name[:dot], name[dot:]


def _extract_extension(name: str) -> str:
    dot = name.rfind('.')
    if dot < 0:
        return ''
    return name[dot + 1 :].lower()


def _get_user_node(user_id: int, node_id: int) -> FileNode:
    node = FileNode.query.filter_by(id=node_id, user_id=user_id).first()
    if not node:
        raise FileManagerError('文件或文件夹不存在', code=404)
    return node


def _is_favorite(user_id: int, node_id: int) -> bool:
    return FavoriteRecord.query.filter_by(user_id=user_id, file_node_id=node_id).first() is not None


def _serialize_node(node: FileNode, children_count: int, is_favorite: bool) -> dict:
    extension = (node.extension or '').lower()
    preview_type = _resolve_preview_kind(extension, node.mime_type)
    return {
        'id': node.id,
        'type': node.node_type,
        'name': node.name,
        'sizeBytes': node.size_bytes,
        'childrenCount': children_count,
        'updatedAt': node.updated_at.strftime('%Y-%m-%d %H:%M'),
        'extension': extension,
        'canAiAnalyze': node.node_type == 'file' and extension in AI_SUPPORTED_EXTENSIONS,
        'canPreview': node.node_type == 'file' and preview_type is not None and bool(node.storage_rel_path),
        'previewType': preview_type,
        'isFavorite': bool(is_favorite),
    }


def _sort_workspace_entries(entries: list[FileNode], sort: str, children_counts: dict[int, int]) -> list[FileNode]:
    folders = [item for item in entries if item.node_type == 'folder']
    files = [item for item in entries if item.node_type == 'file']

    def name_key(node: FileNode):
        return (node.name or '').lower()

    def updated_key(node: FileNode):
        return node.updated_at

    def size_key(node: FileNode):
        return _node_size_metric(node, children_counts)

    if sort == 'name_desc':
        folders.sort(key=name_key, reverse=True)
        files.sort(key=name_key, reverse=True)
    elif sort == 'updated_desc':
        folders.sort(key=updated_key, reverse=True)
        files.sort(key=updated_key, reverse=True)
    elif sort == 'updated_asc':
        folders.sort(key=updated_key)
        files.sort(key=updated_key)
    elif sort == 'size_desc':
        folders.sort(key=size_key, reverse=True)
        files.sort(key=size_key, reverse=True)
    elif sort == 'size_asc':
        folders.sort(key=size_key)
        files.sort(key=size_key)
    else:
        folders.sort(key=name_key)
        files.sort(key=name_key)

    return folders + files


def _node_size_metric(node: FileNode, children_counts: dict[int, int]) -> int:
    if node.node_type == 'folder':
        return children_counts.get(node.id, 0)
    return node.size_bytes


def _resolve_preview_kind(extension: str, mime_type: str = '') -> str | None:
    ext = (extension or '').lower()
    if ext in IMAGE_PREVIEW_EXTENSIONS:
        return 'image'
    if ext in VIDEO_PREVIEW_EXTENSIONS:
        return 'video'
    normalized_mime = _normalize_mime_type(mime_type)
    if normalized_mime.startswith('image/'):
        return 'image'
    if normalized_mime.startswith('video/'):
        return 'video'
    return None


def _normalize_client_filename(raw_name: str) -> str:
    normalized = (raw_name or '').replace('\\', '/').split('/')[-1].strip()
    if normalized in {'', '.', '..'}:
        return ''
    return normalized


def _normalize_mime_type(raw_mime_type: str) -> str:
    return (raw_mime_type or '').split(';', 1)[0].strip().lower()


def _infer_extension_from_mime(mime_type: str) -> str:
    normalized = _normalize_mime_type(mime_type)
    for extension, mapped_mime in PREVIEW_MIME_BY_EXTENSION.items():
        if mapped_mime == normalized:
            return extension
    return ''


def _resolve_preview_mime(preview_kind: str, extension: str, mime_type: str) -> str:
    normalized_mime = _normalize_mime_type(mime_type)
    if normalized_mime.startswith(f'{preview_kind}/'):
        return normalized_mime

    ext = (extension or '').lower()
    mapped_mime = PREVIEW_MIME_BY_EXTENSION.get(ext)
    if mapped_mime and mapped_mime.startswith(f'{preview_kind}/'):
        return mapped_mime

    if preview_kind == 'image':
        return 'image/jpeg'
    return 'video/mp4'
