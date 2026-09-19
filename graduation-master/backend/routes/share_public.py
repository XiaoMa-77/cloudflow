from __future__ import annotations

import re
from datetime import datetime

from flask import Blueprint, send_file

from config import UPLOAD_DIR
from extensions import db
from models import FileNode, ShareRecord
from utils.response import error

bp = Blueprint('share_public', __name__, url_prefix='/share')

_TOKEN_PATTERN = re.compile(r'^u(?P<user_id>\d+)-n(?P<node_id>\d+)-(?P<ts>\d+)$')


def _parse_token(token: str) -> tuple[int, int] | None:
    match = _TOKEN_PATTERN.match(token or '')
    if not match:
        return None
    return int(match.group('user_id')), int(match.group('node_id'))


@bp.get('/<string:token>')
def download_shared_file(token: str):
    share = ShareRecord.query.filter(ShareRecord.share_url.like(f'%/share/{token}')).first()
    if not share:
        return error(message='分享链接不存在', code=404)

    if share.status != '生效中':
        return error(message='分享已取消或失效', code=409)

    if share.expires_at < datetime.utcnow():
        return error(message='分享已过期', code=409)

    parsed = _parse_token(token)
    if not parsed:
        return error(message='分享链接无效', code=404)

    user_id, node_id = parsed
    if share.user_id != user_id:
        return error(message='分享链接无效', code=404)

    node = FileNode.query.filter_by(id=node_id, user_id=user_id, node_type='file').first()
    if not node:
        return error(message='分享文件不存在', code=404)

    if not node.storage_rel_path:
        return error(message='分享文件内容不存在', code=404)

    absolute_path = UPLOAD_DIR / node.storage_rel_path
    if not absolute_path.exists() or not absolute_path.is_file():
        return error(message='分享文件内容不存在', code=404)

    share.visit_count += 1
    db.session.commit()

    return send_file(
        absolute_path,
        as_attachment=True,
        download_name=node.name,
        mimetype=node.mime_type or 'application/octet-stream',
    )
