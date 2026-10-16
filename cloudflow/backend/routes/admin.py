from flask import Blueprint, g, request

from services.admin_service import (
    create_admin,
    delete_admin,
    delete_user,
    get_admin_overview,
    get_admin_profile,
    list_admins,
    list_users,
    update_admin_password,
    update_user_status,
    update_user_storage_limit,
)
from services.file_manager import FileManagerError
from utils.auth import login_required
from utils.response import error, success

bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def _require_super_admin():
    if g.current_identity.get('account') != 'admin':
        return error(message='仅 admin 账号可访问管理员管理功能', code=403)
    return None


@bp.get('/overview')
@login_required(role='ADMIN')
def overview():
    data = get_admin_overview()
    return success(message='获取管理员首页数据成功', data=data)


@bp.get('/users')
@login_required(role='ADMIN')
def users():
    return success(message='获取用户列表成功', data={'items': list_users()})


@bp.patch('/users/<int:user_id>/status')
@login_required(role='ADMIN')
def user_status(user_id):
    payload = request.get_json(silent=True) or {}
    try:
        data = update_user_status(user_id=user_id, status=str(payload.get('status', '')).strip())
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='用户状态更新成功', data=data)


@bp.patch('/users/<int:user_id>/storage-limit')
@login_required(role='ADMIN')
def user_storage_limit(user_id):
    payload = request.get_json(silent=True) or {}
    try:
        limit_value = int(payload.get('spaceLimitBytes'))
        data = update_user_storage_limit(user_id=user_id, space_limit_bytes=limit_value)
    except (TypeError, ValueError):
        return error(message='存储上限参数无效', code=400)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='用户存储上限更新成功', data=data)


@bp.delete('/users/<int:user_id>')
@login_required(role='ADMIN')
def delete_user_route(user_id):
    try:
        delete_user(user_id=user_id)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='用户删除成功', data=None)


@bp.get('/admins')
@login_required(role='ADMIN')
def admins():
    deny = _require_super_admin()
    if deny:
        return deny
    return success(message='获取管理员列表成功', data={'items': list_admins()})


@bp.post('/admins')
@login_required(role='ADMIN')
def add_admin():
    deny = _require_super_admin()
    if deny:
        return deny

    payload = request.get_json(silent=True) or {}
    try:
        data = create_admin(username=str(payload.get('username', '')).strip(), password=str(payload.get('password', '')))
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='管理员创建成功', data=data)


@bp.delete('/admins/<int:admin_id>')
@login_required(role='ADMIN')
def remove_admin(admin_id):
    deny = _require_super_admin()
    if deny:
        return deny

    try:
        delete_admin(admin_id=admin_id, current_admin_id=g.current_identity['id'])
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='管理员删除成功', data=None)


@bp.patch('/admins/<int:admin_id>/password')
@login_required(role='ADMIN')
def reset_admin_password(admin_id):
    deny = _require_super_admin()
    if deny:
        return deny

    payload = request.get_json(silent=True) or {}
    try:
        update_admin_password(admin_id=admin_id, new_password=str(payload.get('newPassword', '')))
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='管理员密码更新成功', data=None)


@bp.get('/profile')
@login_required(role='ADMIN')
def profile():
    try:
        data = get_admin_profile(admin_id=g.current_identity['id'])
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)

    return success(message='获取管理员资料成功', data=data)
