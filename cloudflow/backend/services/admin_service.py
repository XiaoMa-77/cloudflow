from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func

from extensions import db
from models import ActivityRecord, AdminUser, User
from services.file_manager import FileManagerError


def get_admin_overview() -> dict:
    total_users = User.query.count()
    active_users = User.query.filter_by(status='ACTIVE').count()
    total_admins = AdminUser.query.count()

    total_used = db.session.query(func.coalesce(func.sum(User.used_space_bytes), 0)).scalar() or 0
    total_limit = db.session.query(func.coalesce(func.sum(User.space_limit_bytes), 0)).scalar() or 0
    remaining = max(0, total_limit - total_used)

    top_rows = User.query.order_by(User.used_space_bytes.desc()).limit(5).all()

    return {
        'summary': {
            'totalUsers': total_users,
            'activeUsers': active_users,
            'totalAdmins': total_admins,
            'totalUsedBytes': int(total_used),
            'totalLimitBytes': int(total_limit),
            'remainingBytes': int(remaining),
        },
        'topUsers': [
            {
                'id': row.id,
                'username': row.username,
                'usedSpaceBytes': row.used_space_bytes,
                'spaceLimitBytes': row.space_limit_bytes,
            }
            for row in top_rows
        ],
    }


def list_users() -> list[dict]:
    rows = User.query.order_by(User.created_at.desc()).all()
    return [
        {
            'id': row.id,
            'username': row.username,
            'status': row.status,
            'createdAt': row.created_at.strftime('%Y-%m-%d %H:%M'),
            'usedSpaceBytes': row.used_space_bytes,
            'spaceLimitBytes': row.space_limit_bytes,
        }
        for row in rows
    ]


def update_user_status(user_id: int, status: str) -> dict:
    target = User.query.filter_by(id=user_id).first()
    if not target:
        raise FileManagerError('用户不存在', code=404)

    if status not in {'ACTIVE', 'DISABLED'}:
        raise FileManagerError('状态值无效', code=400)

    target.status = status
    db.session.commit()
    return {
        'id': target.id,
        'status': target.status,
    }


def update_user_storage_limit(user_id: int, space_limit_bytes: int) -> dict:
    target = User.query.filter_by(id=user_id).first()
    if not target:
        raise FileManagerError('用户不存在', code=404)

    if space_limit_bytes < target.used_space_bytes:
        raise FileManagerError('存储上限不能小于已用空间', code=409)

    target.space_limit_bytes = int(space_limit_bytes)
    db.session.commit()
    return {
        'id': target.id,
        'spaceLimitBytes': target.space_limit_bytes,
    }


def delete_user(user_id: int) -> None:
    target = User.query.filter_by(id=user_id).first()
    if not target:
        raise FileManagerError('用户不存在', code=404)

    db.session.delete(target)
    db.session.commit()


def list_admins() -> list[dict]:
    rows = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
    return [
        {
            'id': row.id,
            'username': row.username,
            'createdAt': row.created_at.strftime('%Y-%m-%d %H:%M'),
        }
        for row in rows
    ]


def create_admin(username: str, password: str) -> dict:
    account = (username or '').strip()
    passwd = (password or '').strip()

    if not account or not passwd:
        raise FileManagerError('账号和密码不能为空', code=400)

    if len(passwd) < 6:
        raise FileManagerError('密码长度不能少于 6 位', code=400)

    exists = AdminUser.query.filter_by(username=account).first()
    if exists:
        raise FileManagerError('管理员账号已存在', code=409)

    admin = AdminUser(username=account, password=passwd)
    db.session.add(admin)
    db.session.commit()
    return {
        'id': admin.id,
        'username': admin.username,
        'createdAt': admin.created_at.strftime('%Y-%m-%d %H:%M'),
    }


def delete_admin(admin_id: int, current_admin_id: int) -> None:
    target = AdminUser.query.filter_by(id=admin_id).first()
    if not target:
        raise FileManagerError('管理员不存在', code=404)

    if target.username == 'admin':
        raise FileManagerError('admin 账号为超级管理员，禁止删除', code=409)

    if target.id == current_admin_id:
        raise FileManagerError('不能删除当前登录管理员', code=409)

    db.session.delete(target)
    db.session.commit()


def update_admin_password(admin_id: int, new_password: str) -> None:
    target = AdminUser.query.filter_by(id=admin_id).first()
    if not target:
        raise FileManagerError('管理员不存在', code=404)

    if target.username == 'admin':
        raise FileManagerError('admin 账号为超级管理员，禁止重置密码', code=409)

    passwd = (new_password or '').strip()
    if len(passwd) < 6:
        raise FileManagerError('密码长度不能少于 6 位', code=400)

    target.password = passwd
    db.session.commit()


def get_admin_profile(admin_id: int) -> dict:
    admin = AdminUser.query.filter_by(id=admin_id).first()
    if not admin:
        raise FileManagerError('管理员不存在', code=404)

    return {
        'id': admin.id,
        'username': admin.username,
        'createdAt': admin.created_at.strftime('%Y-%m-%d %H:%M'),
    }
