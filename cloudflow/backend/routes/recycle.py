from flask import Blueprint, g, request

from services.file_manager import FileManagerError
from services.recycle_service import (
    batch_restore_recycle_items,
    clear_recycle_bin,
    permanently_delete_recycle_item,
    restore_recycle_item,
)
from models import RecycleRecord
from utils.auth import login_required
from utils.response import error, list_success, success

bp = Blueprint('recycle', __name__, url_prefix='/api/recycle')

TYPE_LABEL_MAP = {
    'document': '文档',
    'image': '图片',
    'video': '视频',
    'archive': '压缩包',
}


def _serialize_recycle(item):
    return {
        'id': item.id,
        'fileName': item.file_name,
        'type': item.file_type,
        'typeLabel': TYPE_LABEL_MAP.get(item.file_type, '其他'),
        'sizeBytes': item.size_bytes,
        'deletedAt': item.deleted_at.strftime('%Y-%m-%d %H:%M'),
        'remainingDays': item.remaining_days,
    }


@bp.get('')
@login_required(role='USER')
def list_recycle():
    page = max(request.args.get('page', 1, type=int), 1)
    page_size = min(max(request.args.get('pageSize', 20, type=int), 1), 100)

    query = RecycleRecord.query.filter_by(user_id=g.current_identity['id']).order_by(RecycleRecord.deleted_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [_serialize_recycle(row) for row in rows]
    return list_success(items=items, total=total, page=page, page_size=page_size, message='获取回收站列表成功')


@bp.post('/<int:recycle_id>/restore')
@login_required(role='USER')
def restore_recycle(recycle_id):
    try:
        data = restore_recycle_item(user_id=g.current_identity['id'], recycle_id=recycle_id)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)
    return success(message='文件已恢复', data=data)


@bp.delete('/<int:recycle_id>')
@login_required(role='USER')
def delete_recycle(recycle_id):
    try:
        permanently_delete_recycle_item(user_id=g.current_identity['id'], recycle_id=recycle_id)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)
    return success(message='文件已彻底删除', data=None)


@bp.post('/batch-restore')
@login_required(role='USER')
def batch_restore():
    payload = request.get_json(silent=True) or {}
    recycle_ids = payload.get('recycleIds') or []
    if not isinstance(recycle_ids, list) or len(recycle_ids) == 0:
        return error(message='请选择需要恢复的文件', code=400)

    try:
        normalized = [int(item_id) for item_id in recycle_ids]
        data = batch_restore_recycle_items(user_id=g.current_identity['id'], recycle_ids=normalized)
    except (TypeError, ValueError):
        return error(message='恢复参数格式错误', code=400)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='批量恢复成功', data=data)


@bp.delete('/clear')
@login_required(role='USER')
def clear_recycle():
    data = clear_recycle_bin(user_id=g.current_identity['id'])
    return success(message='回收站已清空', data=data)
