from flask import Blueprint, g, request

from extensions import db
from services.file_manager import FileManagerError
from services.ai_task_queue import enqueue_ai_task
from services.user_portal import list_ai_records, run_ai_analysis
from utils.auth import login_required
from utils.response import error, success

bp = Blueprint('ai_analysis', __name__, url_prefix='/api/ai-analysis')


@bp.get('')
@login_required(role='USER')
def list_records():
    data = list_ai_records(g.current_identity['id'])
    return success(message='获取 AI 分析记录成功', data=data)


@bp.post('/run')
@login_required(role='USER')
def run_analysis():
    payload = request.get_json(silent=True) or {}
    node_id = payload.get('nodeId')

    if not node_id:
        return error(message='缺少待分析文件', code=400)

    try:
        data = run_ai_analysis(user_id=g.current_identity['id'], node_id=int(node_id))
        db.session.commit()
        enqueue_ai_task(data['id'])
    except (TypeError, ValueError):
        return error(message='参数格式错误', code=400)
    except FileManagerError as exc:
        db.session.rollback()
        return error(message=exc.message, code=exc.code)

    return success(message='AI 分析任务已提交', data=data)
