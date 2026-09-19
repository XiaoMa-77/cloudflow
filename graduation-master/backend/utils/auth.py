from functools import wraps

from flask import g, request

from models import AdminUser, AuthSession, User
from utils.response import error


def extract_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header.split(' ', 1)[1].strip()
    return request.headers.get('X-Auth-Token', '').strip()


def get_current_identity():
    token = extract_token()
    if not token:
        return None

    session = AuthSession.query.filter_by(token=token).first()
    if not session:
        return None

    if session.role == 'USER' and session.user_id:
        user = User.query.get(session.user_id)
        if not user:
            return None
        return {
            'token': token,
            'role': 'USER',
            'id': user.id,
            'account': user.username,
            'name': user.username,
            'status': user.status,
            'usedSpaceBytes': user.used_space_bytes,
            'spaceLimitBytes': user.space_limit_bytes,
        }

    if session.role == 'ADMIN' and session.admin_user_id:
        admin = AdminUser.query.get(session.admin_user_id)
        if not admin:
            return None
        return {
            'token': token,
            'role': 'ADMIN',
            'id': admin.id,
            'account': admin.username,
            'name': admin.username,
        }

    return None


def login_required(role=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            identity = get_current_identity()
            if not identity:
                return error(message='未登录或登录已失效', code=401)

            if role and identity.get('role') != role:
                return error(message='无权限访问当前资源', code=403)

            g.current_identity = identity
            return view_func(*args, **kwargs)

        return wrapper

    return decorator

