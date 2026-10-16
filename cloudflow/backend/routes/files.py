from io import BytesIO

from flask import Blueprint, g, request, send_file

from extensions import db
from models import FileRecord
from services.file_manager import (
    FileManagerError,
    batch_delete_nodes,
    create_folder,
    create_share,
    delete_node,
    get_download_payload,
    get_preview_payload,
    get_workspace,
    paste_node,
    rename_node,
    upload_file,
)
from services.user_portal import toggle_favorite
from utils.auth import login_required
from utils.response import error, list_success, success

bp = Blueprint('files', __name__, url_prefix='/api/files')


def _serialize_file(item):
    return {
        'id': item.id,
        'name': item.file_name,
        'type': item.file_type,
        'sizeBytes': item.size_bytes,
        'folder': item.folder_name,
        'updatedAt': item.updated_at.strftime('%Y-%m-%d %H:%M'),
    }


@bp.get('')
@login_required(role='USER')
def list_files():
    keyword = request.args.get('keyword', '', type=str).strip()
    file_type = request.args.get('type', 'all', type=str).strip()
    sort = request.args.get('sort', 'updated_desc', type=str).strip()
    page = max(request.args.get('page', 1, type=int), 1)
    page_size = min(max(request.args.get('pageSize', 20, type=int), 1), 100)

    query = FileRecord.query.filter_by(user_id=g.current_identity['id'], is_deleted=False)

    if keyword:
        query = query.filter(FileRecord.file_name.like(f'%{keyword}%'))

    if file_type and file_type != 'all':
        query = query.filter_by(file_type=file_type)

    if sort == 'updated_asc':
        query = query.order_by(FileRecord.updated_at.asc())
    elif sort == 'size_desc':
        query = query.order_by(FileRecord.size_bytes.desc(), FileRecord.updated_at.desc())
    elif sort == 'size_asc':
        query = query.order_by(FileRecord.size_bytes.asc(), FileRecord.updated_at.desc())
    elif sort == 'name_asc':
        query = query.order_by(FileRecord.file_name.asc(), FileRecord.updated_at.desc())
    elif sort == 'name_desc':
        query = query.order_by(FileRecord.file_name.desc(), FileRecord.updated_at.desc())
    else:
        query = query.order_by(FileRecord.updated_at.desc())

    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [_serialize_file(row) for row in rows]
    return list_success(items=items, total=total, page=page, page_size=page_size, message='获取文件列表成功')


@bp.get('/workspace')
@login_required(role='USER')
def workspace():
    folder_id = request.args.get('folderId', type=int)
    keyword = request.args.get('keyword', '', type=str)
    sort = request.args.get('sort', 'name_asc', type=str)

    try:
        data = get_workspace(user_id=g.current_identity['id'], folder_id=folder_id, keyword=keyword, sort=sort)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='获取目录内容成功', data=data)


@bp.patch('/nodes/<int:node_id>/rename')
@login_required(role='USER')
def rename(node_id):
    payload = request.get_json(silent=True) or {}
    try:
        data = rename_node(user_id=g.current_identity['id'], node_id=node_id, name=payload.get('name', ''))
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='重命名成功', data=data)


@bp.delete('/nodes/<int:node_id>')
@login_required(role='USER')
def delete(node_id):
    try:
        data = delete_node(user_id=g.current_identity['id'], node_id=node_id)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='删除成功', data=data)


@bp.post('/nodes/<int:node_id>/share')
@login_required(role='USER')
def share(node_id):
    payload = request.get_json(silent=True) or {}
    expire_days = payload.get('expireDays', 7)
    host_base = request.host_url.rstrip('/')

    try:
        data = create_share(
            user_id=g.current_identity['id'],
            node_id=node_id,
            expire_days=int(expire_days),
            share_host=host_base,
        )
    except (TypeError, ValueError):
        return error(message='分享有效期参数无效', code=400)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='创建分享成功', data=data)


@bp.post('/paste')
@login_required(role='USER')
def paste():
    payload = request.get_json(silent=True) or {}
    source_id = payload.get('sourceId')
    target_folder_id = payload.get('targetFolderId')
    mode = payload.get('mode')

    if not source_id or not target_folder_id:
        return error(message='粘贴参数不完整', code=400)

    try:
        data = paste_node(
            user_id=g.current_identity['id'],
            source_id=int(source_id),
            target_folder_id=int(target_folder_id),
            mode=mode,
        )
    except (TypeError, ValueError):
        return error(message='粘贴参数格式错误', code=400)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='粘贴成功', data=data)


@bp.post('/nodes/<int:node_id>/favorite')
@login_required(role='USER')
def favorite(node_id):
    try:
        data = toggle_favorite(user_id=g.current_identity['id'], node_id=node_id)
        db.session.commit()
    except FileManagerError as exc:
        db.session.rollback()
        return error(message=exc.message, code=exc.code)

    return success(message='收藏状态更新成功', data=data)


@bp.post('/folders')
@login_required(role='USER')
def add_folder():
    payload = request.get_json(silent=True) or {}
    parent_id = payload.get('parentId')
    name = payload.get('name', '')

    try:
        data = create_folder(
            user_id=g.current_identity['id'],
            parent_id=int(parent_id) if parent_id is not None else None,
            name=name,
        )
    except (TypeError, ValueError):
        return error(message='父目录参数无效', code=400)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='文件夹创建成功', data=data)


@bp.post('/upload')
@login_required(role='USER')
def upload():
    file = request.files.get('file')
    parent_id = request.form.get('parentId')

    try:
        data = upload_file(
            user_id=g.current_identity['id'],
            parent_id=int(parent_id) if parent_id else None,
            upload=file,
        )
    except (TypeError, ValueError):
        return error(message='上传目录参数无效', code=400)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='文件上传成功', data=data)


@bp.get('/nodes/<int:node_id>/download')
@login_required(role='USER')
def download(node_id):
    try:
        payload = get_download_payload(user_id=g.current_identity['id'], node_id=node_id)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    if payload['path'] is not None:
        return send_file(
            payload['path'],
            as_attachment=True,
            download_name=payload['name'],
            mimetype=payload['mimeType'],
        )

    return send_file(
        BytesIO(payload['bytes']),
        as_attachment=True,
        download_name=f"{payload['name']}.txt",
        mimetype=payload['mimeType'],
    )


@bp.get('/nodes/<int:node_id>/preview')
@login_required(role='USER')
def preview(node_id):
    try:
        payload = get_preview_payload(user_id=g.current_identity['id'], node_id=node_id)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return send_file(
        payload['path'],
        as_attachment=False,
        download_name=payload['name'],
        mimetype=payload['mimeType'],
    )


@bp.post('/nodes/batch-delete')
@login_required(role='USER')
def batch_delete():
    payload = request.get_json(silent=True) or {}
    node_ids = payload.get('nodeIds') or []
    if not isinstance(node_ids, list) or len(node_ids) == 0:
        return error(message='请选择需要删除的文件或文件夹', code=400)

    try:
        normalized = [int(node_id) for node_id in node_ids]
        data = batch_delete_nodes(user_id=g.current_identity['id'], node_ids=normalized)
    except (TypeError, ValueError):
        return error(message='批量删除参数格式错误', code=400)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='批量删除成功', data=data)
