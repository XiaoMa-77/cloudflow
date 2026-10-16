from flask import Blueprint, g, request
from datetime import datetime

from models.entities import TodoItem, LongTermTask, PasswordEntry
from services.file_manager import FileManagerError
from services.security import decrypt_secret, encrypt_secret
from services.user_portal import get_dashboard, get_user_profile, list_favorites
from utils.auth import login_required
from utils.response import error, success

bp = Blueprint('user_portal', __name__, url_prefix='/api/user')


@bp.get('/dashboard')
@login_required(role='USER')
def dashboard():
    try:
        data = get_dashboard(g.current_identity['id'])
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)
    return success(message='获取用户首页信息成功', data=data)


@bp.get('/favorites')
@login_required(role='USER')
def favorites():
    data = list_favorites(g.current_identity['id'])
    return success(message='获取收藏列表成功', data=data)


@bp.get('/profile')
@login_required(role='USER')
def profile():
    try:
        data = get_user_profile(g.current_identity['id'])
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)
    return success(message='获取个人资料成功', data=data)


# 待办事项相关路由
@bp.get('/todos')
@login_required(role='USER')
def get_todos():
    todos = TodoItem.query.filter_by(user_id=g.current_identity['id']).all()
    data = [{"id": t.id, "title": t.title, "description": t.description, "due_date": t.due_date.isoformat() if t.due_date else None, "priority": t.priority, "completed": t.completed} for t in todos]
    return success(message='获取待办事项成功', data=data)

@bp.post('/todos')
@login_required(role='USER')
def create_todo():
    data = request.json
    due_date = data.get('due_date')
    if due_date:
        due_date = datetime.fromisoformat(due_date).date()
    todo = TodoItem(
        user_id=g.current_identity['id'],
        title=data['title'],
        description=data.get('description', ''),
        due_date=due_date,
        priority=data.get('priority', 'medium'),
        completed=data.get('completed', False)
    )
    from extensions import db
    db.session.add(todo)
    db.session.commit()
    return success(message='创建待办事项成功', data={"id": todo.id})

@bp.put('/todos/<int:todo_id>')
@login_required(role='USER')
def update_todo(todo_id):
    todo = TodoItem.query.filter_by(id=todo_id, user_id=g.current_identity['id']).first()
    if not todo:
        return error(message='待办事项不存在', code=404)
    data = request.json
    for key, value in data.items():
        if key == 'due_date' and value:
            value = datetime.fromisoformat(value).date()
        setattr(todo, key, value)
    from extensions import db
    db.session.commit()
    return success(message='更新待办事项成功')

@bp.delete('/todos/<int:todo_id>')
@login_required(role='USER')
def delete_todo(todo_id):
    todo = TodoItem.query.filter_by(id=todo_id, user_id=g.current_identity['id']).first()
    if not todo:
        return error(message='待办事项不存在', code=404)
    from extensions import db
    db.session.delete(todo)
    db.session.commit()
    return success(message='删除待办事项成功')

# 长期任务相关路由
@bp.get('/long-term-tasks')
@login_required(role='USER')
def get_long_term_tasks():
    tasks = LongTermTask.query.filter_by(user_id=g.current_identity['id']).all()
    data = []
    from datetime import datetime
    for t in tasks:
        days_left = 0
        if t.end_date:
            days_left = (t.end_date - datetime.now().date()).days
        data.append({"id": t.id, "title": t.title, "description": t.description, "progress": t.progress, "end_date": t.end_date.isoformat() if t.end_date else None, "status": t.status, "days_left": days_left})
    return success(message='获取长期任务成功', data=data)

@bp.post('/long-term-tasks')
@login_required(role='USER')
def create_long_term_task():
    data = request.json
    end_date = data.get('end_date')
    if end_date:
        end_date = datetime.fromisoformat(end_date).date()
    task = LongTermTask(
        user_id=g.current_identity['id'],
        title=data['title'],
        description=data.get('description', ''),
        progress=data.get('progress', 0),
        end_date=end_date,
        status=data.get('status', '进行中')
    )
    from extensions import db
    db.session.add(task)
    db.session.commit()
    return success(message='创建长期任务成功', data={"id": task.id})

@bp.put('/long-term-tasks/<int:task_id>')
@login_required(role='USER')
def update_long_term_task(task_id):
    task = LongTermTask.query.filter_by(id=task_id, user_id=g.current_identity['id']).first()
    if not task:
        return error(message='长期任务不存在', code=404)
    data = request.json
    for key, value in data.items():
        if key == 'end_date' and value:
            value = datetime.fromisoformat(value).date()
        setattr(task, key, value)
    from extensions import db
    db.session.commit()
    return success(message='更新长期任务成功')

@bp.delete('/long-term-tasks/<int:task_id>')
@login_required(role='USER')
def delete_long_term_task(task_id):
    task = LongTermTask.query.filter_by(id=task_id, user_id=g.current_identity['id']).first()
    if not task:
        return error(message='长期任务不存在', code=404)
    from extensions import db
    db.session.delete(task)
    db.session.commit()
    return success(message='删除长期任务成功')

# 密码本相关路由（密码字段静态加密存储，读取时解密）
@bp.get('/passwords')
@login_required(role='USER')
def get_passwords():
    passwords = PasswordEntry.query.filter_by(user_id=g.current_identity['id']).all()
    data = [{"id": p.id, "app": p.app, "username": p.username, "password": decrypt_secret(p.password), "note": p.note} for p in passwords]
    return success(message='获取密码本成功', data=data)

@bp.post('/passwords')
@login_required(role='USER')
def create_password():
    data = request.json
    password = PasswordEntry(
        user_id=g.current_identity['id'],
        app=data['app'],
        username=data['username'],
        password=encrypt_secret(data['password']),
        note=data.get('note', '')
    )
    from extensions import db
    db.session.add(password)
    db.session.commit()
    return success(message='添加密码成功', data={"id": password.id})

@bp.put('/passwords/<int:password_id>')
@login_required(role='USER')
def update_password(password_id):
    password = PasswordEntry.query.filter_by(id=password_id, user_id=g.current_identity['id']).first()
    if not password:
        return error(message='密码不存在', code=404)
    data = request.json
    for key, value in data.items():
        if key == 'password':
            value = encrypt_secret(value)
        setattr(password, key, value)
    from extensions import db
    db.session.commit()
    return success(message='更新密码成功')

@bp.delete('/passwords/<int:password_id>')
@login_required(role='USER')
def delete_password(password_id):
    password = PasswordEntry.query.filter_by(id=password_id, user_id=g.current_identity['id']).first()
    if not password:
        return error(message='密码不存在', code=404)
    from extensions import db
    db.session.delete(password)
    db.session.commit()
    return success(message='删除密码成功')
