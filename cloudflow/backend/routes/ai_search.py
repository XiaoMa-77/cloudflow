from flask import Blueprint, g, request

from services.ai_text_analysis import IMAGE_ANALYSIS_EXTENSIONS, extract_analysis_text
from services.file_manager import (
    AI_DOCUMENT_EXTENSIONS,
    FileManagerError,
    _get_user_node,
)
from services.semantic_search import (
    SemanticSearchError,
    get_index_status,
    index_file_text,
    rag_answer,
    semantic_search,
)
from utils.auth import login_required
from utils.response import error, success

bp = Blueprint('ai_search', __name__, url_prefix='/api/ai-search')


@bp.post('')
@login_required(role='USER')
def search():
    """语义搜索：返回相关文件片段，可选生成 RAG 问答答案。"""
    payload = request.get_json(silent=True) or {}
    query = str(payload.get('query', '')).strip()
    with_answer = bool(payload.get('withAnswer', False))
    try:
        top_k = min(max(int(payload.get('topK', 8) or 8), 1), 20)
    except (TypeError, ValueError):
        top_k = 8

    if not query:
        return error(message='请输入搜索内容', code=400)

    try:
        results = semantic_search(g.current_identity['id'], query, top_k)
    except SemanticSearchError as exc:
        return error(message=exc.message, code=exc.code)

    answer = ''
    if with_answer and results:
        try:
            answer = rag_answer(g.current_identity['id'], query, results)
        except SemanticSearchError:
            answer = ''  # 问答失败不影响检索结果返回

    return success(
        message='语义搜索完成',
        data={'results': results, 'answer': answer},
    )


@bp.get('/status')
@login_required(role='USER')
def status():
    return success(message='获取索引状态成功', data=get_index_status(g.current_identity['id']))


@bp.post('/reindex')
@login_required(role='USER')
def reindex():
    """重建语义索引：传 nodeId 重建单个文件，不传则重建全部可解析文件。"""
    payload = request.get_json(silent=True) or {}
    node_id = payload.get('nodeId')
    user_id = g.current_identity['id']

    try:
        if node_id is not None:
            node = _get_user_node(user_id, int(node_id))
            if node.node_type != 'file':
                return error(message='只能对文件建立索引', code=400)
            if node.extension in IMAGE_ANALYSIS_EXTENSIONS:
                # 图片索引依赖视觉模型描述，提示走 AI 分析自动建立
                return error(message='图片文件请使用「AI 分析」生成内容描述后自动建立索引', code=400)
            text = extract_analysis_text(node.storage_rel_path, node.extension)
            if not text.strip():
                return error(message='该文件无法提取文本内容', code=400)
            count = index_file_text(user_id, node.id, text)
            return success(message='索引重建完成', data={'indexedFiles': 1, 'indexedChunks': count})

        # 全量重建：仅处理文本文档类
        from models import FileNode

        nodes = FileNode.query.filter_by(user_id=user_id, node_type='file').all()
        indexed_files = 0
        indexed_chunks = 0
        for node in nodes:
            if node.extension not in AI_DOCUMENT_EXTENSIONS or not node.storage_rel_path:
                continue
            text = extract_analysis_text(node.storage_rel_path, node.extension)
            if not text.strip():
                continue
            try:
                indexed_chunks += index_file_text(user_id, node.id, text)
                indexed_files += 1
            except SemanticSearchError:
                continue
        return success(
            message='全量索引重建完成',
            data={'indexedFiles': indexed_files, 'indexedChunks': indexed_chunks},
        )
    except (TypeError, ValueError):
        return error(message='参数格式错误', code=400)
    except FileManagerError as exc:
        return error(message=exc.message, code=exc.code)
    except SemanticSearchError as exc:
        return error(message=exc.message, code=exc.code)
