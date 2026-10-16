import secrets
import random
import string
from io import BytesIO
from flask import Blueprint, g, request, session, send_file

from extensions import db
from models import AdminUser, AuthSession, User
from utils.auth import login_required
from utils.response import error, success

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def generate_captcha():
    """生成验证码图片"""
    # 验证码字符集
    chars = string.ascii_letters + string.digits
    # 生成4位验证码
    code = ''.join(random.choice(chars) for _ in range(4))
    
    # 存储验证码到session
    session['captcha'] = code.lower()
    
    if not PIL_AVAILABLE:
        # 如果PIL不可用，返回简单的文本验证码
        return code, None
    
    # 创建验证码图片
    width, height = 120, 40
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 绘制背景噪点
    for _ in range(50):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    
    # 绘制验证码文本
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype('arial', 24)
    except:
        # 如果系统字体不可用，使用默认字体
        font = ImageFont.load_default()
    
    for i, char in enumerate(code):
        x = 20 + i * 25
        y = random.randint(5, 10)
        draw.text((x, y), char, font=font, fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)))
    
    # 绘制干扰线
    for _ in range(5):
        x1 = random.randint(0, width - 1)
        y1 = random.randint(0, height - 1)
        x2 = random.randint(0, width - 1)
        y2 = random.randint(0, height - 1)
        draw.line((x1, y1, x2, y2), fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)), width=1)
    
    # 保存图片到内存
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    
    return code, buffer


@bp.get('/captcha')
def get_captcha():
    """获取验证码图片"""
    code, image_buffer = generate_captcha()
    
    if not PIL_AVAILABLE:
        # 如果PIL不可用，返回文本验证码
        return success(message='获取验证码成功', data={'code': code})
    
    # 返回验证码图片
    return send_file(image_buffer, mimetype='image/png')


@bp.post('/register')
def register():
    payload = request.get_json(silent=True) or {}
    account = str(payload.get('account', '')).strip()
    password = str(payload.get('password', ''))

    if not account or not password:
        return error(message='账号和密码不能为空', code=400)

    if len(account) < 3 or len(account) > 32:
        return error(message='账号长度需在 3 到 32 位之间', code=400)

    if len(password) < 6:
        return error(message='密码长度不能少于 6 位', code=400)

    if User.query.filter_by(username=account).first():
        return error(message='账号已存在，请更换后重试', code=409)

    if AdminUser.query.filter_by(username=account).first():
        return error(message='账号不可用，请更换后重试', code=409)

    user = User(username=account, password=password, status='ACTIVE')
    db.session.add(user)
    db.session.commit()

    return success(
        message='注册成功',
        data={
            'id': user.id,
            'account': user.username,
            'name': user.username,
            'role': 'USER',
        },
    )


@bp.post('/login')
def login():
    payload = request.get_json(silent=True) or {}
    account = str(payload.get('account', '')).strip()
    password = str(payload.get('password', ''))
    captcha = str(payload.get('captcha', '')).strip()

    if not account or not password:
        return error(message='账号和密码不能为空', code=400)

    if not captcha:
        return error(message='请输入验证码', code=400)

    # 验证验证码
    session_captcha = session.get('captcha')
    if not session_captcha:
        return error(message='验证码已过期，请重新获取', code=400)

    if captcha.lower() != session_captcha:
        return error(message='验证码错误', code=400)

    # 验证码验证成功后清除session中的验证码
    session.pop('captcha', None)

    user = User.query.filter_by(username=account).first()
    if user:
        if user.password != password:
            return error(message='账号或密码错误', code=401)
        if user.status != 'ACTIVE':
            return error(message='账号已被禁用', code=403)

        token = secrets.token_urlsafe(24)
        db.session.add(AuthSession(token=token, role='USER', user_id=user.id))
        db.session.commit()
        return success(
            message='登录成功',
            data={
                'token': token,
                'role': 'USER',
                'account': user.username,
                'name': user.username,
            },
        )

    admin = AdminUser.query.filter_by(username=account).first()
    if admin and admin.password == password:
        token = secrets.token_urlsafe(24)
        db.session.add(AuthSession(token=token, role='ADMIN', admin_user_id=admin.id))
        db.session.commit()
        return success(
            message='登录成功',
            data={
                'token': token,
                'role': 'ADMIN',
                'account': admin.username,
                'name': admin.username,
            },
        )

    return error(message='账号或密码错误', code=401)


@bp.get('/me')
@login_required()
def me():
    return success(message='获取当前用户成功', data=g.current_identity)


@bp.post('/logout')
@login_required()
def logout():
    token = g.current_identity.get('token')
    if token:
        AuthSession.query.filter_by(token=token).delete()
        db.session.commit()
    return success(message='退出登录成功', data=None)


@bp.patch('/password')
@login_required()
def change_password():
    payload = request.get_json(silent=True) or {}
    old_password = str(payload.get('oldPassword', ''))
    new_password = str(payload.get('newPassword', ''))

    if not old_password or not new_password:
        return error(message='请填写完整密码信息', code=400)

    if len(new_password) < 6:
        return error(message='新密码长度不能少于 6 位', code=400)

    identity = g.current_identity
    if identity.get('role') == 'USER':
        user = User.query.filter_by(id=identity['id']).first()
        if not user or user.password != old_password:
            return error(message='原密码不正确', code=409)
        user.password = new_password
        db.session.commit()
        return success(message='密码修改成功', data=None)

    admin = AdminUser.query.filter_by(id=identity['id']).first()
    if not admin or admin.password != old_password:
        return error(message='原密码不正确', code=409)
    admin.password = new_password
    db.session.commit()
    return success(message='密码修改成功', data=None)
