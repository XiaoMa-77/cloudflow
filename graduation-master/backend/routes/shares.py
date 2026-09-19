from flask import Blueprint, g, request

from extensions import db
from models import ShareRecord
from utils.auth import login_required
from utils.response import error, list_success, success

bp = Blueprint('shares', __name__, url_prefix='/api/shares')


def _serialize_share(item):
    return {
        'id': item.id,
        'fileName': item.file_name,
        'status': item.status,
        'expireAt': item.expires_at.strftime('%Y-%m-%d %H:%M'),
        'accessMode': item.access_mode,
        'visits': item.visit_count,
        'link': item.share_url,
    }


@bp.get('')
@login_required(role='USER')
def list_shares():
    page = max(request.args.get('page', 1, type=int), 1)
    page_size = min(max(request.args.get('pageSize', 20, type=int), 1), 100)

    query = ShareRecord.query.filter_by(user_id=g.current_identity['id']).order_by(ShareRecord.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [_serialize_share(row) for row in rows]
    return list_success(items=items, total=total, page=page, page_size=page_size, message='获取分享记录成功')


@bp.patch('/<int:share_id>/cancel')
@login_required(role='USER')
def cancel_share(share_id):
    share = ShareRecord.query.filter_by(id=share_id, user_id=g.current_identity['id']).first()
    if not share:
        return error(message='分享记录不存在', code=404)

    if share.status == '已取消':
        return success(message='分享已取消', data=_serialize_share(share))

    share.status = '已取消'
    db.session.commit()
    return success(message='取消分享成功', data=_serialize_share(share))


@bp.post('/batch-cancel')
@login_required(role='USER')
def batch_cancel():
    payload = request.get_json(silent=True) or {}
    share_ids = payload.get('shareIds') or []
    if not isinstance(share_ids, list) or len(share_ids) == 0:
        return error(message='请选择需要取消的分享记录', code=400)

    try:
        normalized = [int(item_id) for item_id in share_ids]
    except (TypeError, ValueError):
        return error(message='分享参数格式错误', code=400)

    rows = ShareRecord.query.filter(ShareRecord.user_id == g.current_identity['id'], ShareRecord.id.in_(normalized)).all()
    for share in rows:
        share.status = '已取消'
    db.session.commit()
    return success(message='批量取消分享成功', data={'updatedCount': len(rows)})


@bp.delete('/<int:share_id>')
@login_required(role='USER')
def delete_share(share_id):
    share = ShareRecord.query.filter_by(id=share_id, user_id=g.current_identity['id']).first()
    if not share:
        return error(message='分享记录不存在', code=404)

    db.session.delete(share)
    db.session.commit()
    return success(message='分享记录已删除', data=None)
