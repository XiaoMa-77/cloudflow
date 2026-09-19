from datetime import datetime
from pathlib import Path

from sqlalchemy import func

from config import UPLOAD_DIR
from extensions import db
from models import FileNode, RecycleRecord
from services.file_manager import FileManagerError, ensure_root_folder


def restore_recycle_item(user_id: int, recycle_id: int) -> dict:
    record = RecycleRecord.query.filter_by(id=recycle_id, user_id=user_id).first()
    if not record:
        raise FileManagerError('回收站记录不存在', code=404)

    root = ensure_root_folder(user_id)
    target_name = _resolve_duplicate_name(user_id, root.id, record.file_name)
    restored = FileNode(
        user_id=user_id,
        parent_id=root.id,
        node_type='file',
        name=target_name,
        extension=record.extension or _extract_extension(target_name),
        mime_type=record.mime_type or '',
        storage_rel_path=record.storage_rel_path or '',
        size_bytes=record.size_bytes,
        updated_at=datetime.utcnow(),
    )

    db.session.add(restored)
    db.session.delete(record)
    from services.user_portal import recalculate_user_storage, record_activity

    recalculate_user_storage(user_id)
    record_activity(user_id=user_id, file_name=restored.name, action='从回收站恢复')
    db.session.commit()

    return {
        'id': restored.id,
        'name': restored.name,
        'sizeBytes': restored.size_bytes,
        'updatedAt': restored.updated_at.strftime('%Y-%m-%d %H:%M'),
    }


def permanently_delete_recycle_item(user_id: int, recycle_id: int) -> None:
    record = RecycleRecord.query.filter_by(id=recycle_id, user_id=user_id).first()
    if not record:
        raise FileManagerError('回收站记录不存在', code=404)

    from services.user_portal import record_activity

    record_activity(user_id=user_id, file_name=record.file_name, action='彻底删除文件')
    if record.storage_rel_path:
        absolute_path = UPLOAD_DIR / Path(record.storage_rel_path)
        if absolute_path.exists() and absolute_path.is_file():
            absolute_path.unlink(missing_ok=True)
    db.session.delete(record)
    db.session.commit()


def batch_restore_recycle_items(user_id: int, recycle_ids: list[int]) -> dict:
    restored = []
    for recycle_id in recycle_ids:
        payload = restore_recycle_item(user_id=user_id, recycle_id=recycle_id)
        restored.append(payload)

    return {
        'restoredCount': len(restored),
        'items': restored,
    }


def clear_recycle_bin(user_id: int) -> dict:
    records = RecycleRecord.query.filter_by(user_id=user_id).all()
    for record in records:
        if record.storage_rel_path:
            absolute_path = UPLOAD_DIR / Path(record.storage_rel_path)
            if absolute_path.exists() and absolute_path.is_file():
                absolute_path.unlink(missing_ok=True)

    count = len(records)
    if count:
        from services.user_portal import record_activity

        record_activity(user_id=user_id, file_name='回收站', action='清空回收站')

    RecycleRecord.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    db.session.commit()

    return {'clearedCount': count}


def _resolve_duplicate_name(user_id: int, parent_id: int, base_name: str) -> str:
    if not _sibling_name_exists(user_id, parent_id, base_name):
        return base_name

    main, extension = _split_name(base_name)
    index = 1
    while True:
        suffix = '' if index == 1 else str(index)
        candidate = f'{main}-恢复{suffix}{extension}'
        if not _sibling_name_exists(user_id, parent_id, candidate):
            return candidate
        index += 1


def _sibling_name_exists(user_id: int, parent_id: int, name: str) -> bool:
    return (
        FileNode.query.filter_by(user_id=user_id, parent_id=parent_id)
        .filter(func.lower(FileNode.name) == name.lower())
        .first()
        is not None
    )


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
