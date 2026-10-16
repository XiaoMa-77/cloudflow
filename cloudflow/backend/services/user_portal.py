from __future__ import annotations

from datetime import datetime

from sqlalchemy import func

from extensions import db
from models import ActivityRecord, AiAnalysisRecord, FavoriteRecord, FileNode, RecycleRecord, ShareRecord, User
from services.ai_text_analysis import (
    analyze_document_text,
    analyze_image_file,
    extract_analysis_text,
)
from services.file_manager import AI_IMAGE_EXTENSIONS, AI_SUPPORTED_EXTENSIONS, FILE_TYPE_BY_EXTENSION, FileManagerError


def record_activity(user_id: int, file_name: str, action: str) -> None:
    if not file_name or not action:
        return

    db.session.add(ActivityRecord(user_id=user_id, file_name=file_name, action=action, created_at=datetime.utcnow()))

    # Keep recent activity records bounded per user.
    old_rows = (
        ActivityRecord.query.filter_by(user_id=user_id)
        .order_by(ActivityRecord.created_at.desc())
        .offset(200)
        .all()
    )
    if old_rows:
        stale_ids = [item.id for item in old_rows]
        ActivityRecord.query.filter(ActivityRecord.id.in_(stale_ids)).delete(synchronize_session=False)


def recalculate_user_storage(user_id: int) -> int:
    total = (
        db.session.query(func.coalesce(func.sum(FileNode.size_bytes), 0))
        .filter_by(user_id=user_id, node_type='file')
        .scalar()
    )
    user = User.query.filter_by(id=user_id).first()
    if user:
        user.used_space_bytes = int(total or 0)
    return int(total or 0)


def get_dashboard(user_id: int) -> dict:
    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise FileManagerError('用户不存在', code=404)

    recalculate_user_storage(user_id)
    total_files = FileNode.query.filter_by(user_id=user_id, node_type='file').count()
    active_shares = ShareRecord.query.filter_by(user_id=user_id, status='生效中').count()
    recycle_count = RecycleRecord.query.filter_by(user_id=user_id).count()

    recent_rows = (
        ActivityRecord.query.filter_by(user_id=user_id)
        .order_by(ActivityRecord.created_at.desc())
        .limit(8)
        .all()
    )

    return {
        'overview': {
            'usedSpaceBytes': user.used_space_bytes,
            'spaceLimitBytes': user.space_limit_bytes,
            'totalFiles': total_files,
            'activeShares': active_shares,
            'recycleCount': recycle_count,
        },
        'recentActivities': [_serialize_activity(item) for item in recent_rows],
    }


def list_favorites(user_id: int) -> dict:
    rows = (
        db.session.query(FavoriteRecord, FileNode)
        .join(FileNode, FavoriteRecord.file_node_id == FileNode.id)
        .filter(FavoriteRecord.user_id == user_id)
        .order_by(FavoriteRecord.created_at.desc())
        .all()
    )

    items = []
    for favorite, node in rows:
        items.append(
            {
                'id': favorite.id,
                'fileNodeId': node.id,
                'name': node.name,
                'type': _human_type(node),
                'sizeBytes': node.size_bytes,
                'favoritedAt': favorite.created_at.strftime('%Y-%m-%d %H:%M'),
            }
        )

    return {
        'items': items,
        'total': len(items),
    }


def toggle_favorite(user_id: int, node_id: int) -> dict:
    node = FileNode.query.filter_by(id=node_id, user_id=user_id).first()
    if not node or node.node_type != 'file':
        raise FileManagerError('目标文件不存在', code=404)

    favorite = FavoriteRecord.query.filter_by(user_id=user_id, file_node_id=node.id).first()
    if favorite:
        db.session.delete(favorite)
        record_activity(user_id=user_id, file_name=node.name, action='取消收藏')
        return {'favorited': False}

    db.session.add(FavoriteRecord(user_id=user_id, file_node_id=node.id))
    record_activity(user_id=user_id, file_name=node.name, action='加入收藏')
    return {'favorited': True}


def list_ai_records(user_id: int) -> dict:
    rows = (
        AiAnalysisRecord.query.filter_by(user_id=user_id)
        .order_by(AiAnalysisRecord.created_at.desc())
        .limit(100)
        .all()
    )

    return {
        'items': [
            {
                'id': item.id,
                'fileNodeId': item.file_node_id,
                'fileName': item.file_name,
                'type': item.file_type.upper() if item.file_type else '文件',
                'summary': item.summary,
                'status': item.status,
                'analyzedAt': item.created_at.strftime('%Y-%m-%d %H:%M'),
            }
            for item in rows
        ],
        'total': len(rows),
    }


def run_ai_analysis(user_id: int, node_id: int) -> dict:
    node = FileNode.query.filter_by(id=node_id, user_id=user_id).first()
    if not node or node.node_type != 'file':
        raise FileManagerError('目标文件不存在', code=404)

    extension = (node.extension or '').lower()
    if extension not in AI_SUPPORTED_EXTENSIONS:
        raise FileManagerError('AI 分析仅支持 txt、doc、docx、md、csv、xls、xlsx、pdf 及常见图片文件', code=409)

    record = AiAnalysisRecord(
        user_id=user_id,
        file_node_id=node.id,
        file_name=node.name,
        file_type=extension,
        summary='任务已加入分析队列，请稍候刷新查看结果。',
        status='分析中',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(record)
    db.session.flush()
    record_activity(user_id=user_id, file_name=node.name, action='提交 AI 分析任务')

    return {
        'id': record.id,
        'fileNodeId': node.id,
        'fileName': node.name,
        'summary': record.summary,
        'status': '分析中',
    }


def process_ai_analysis_task(record_id: int) -> None:
    record = AiAnalysisRecord.query.filter_by(id=record_id).first()
    if not record:
        return

    node = FileNode.query.filter_by(id=record.file_node_id, user_id=record.user_id).first()
    if not node or node.node_type != 'file':
        record.status = '失败'
        record.summary = '源文件不存在或不可访问，无法继续分析。'
        record.updated_at = datetime.utcnow()
        db.session.commit()
        return

    extension = (node.extension or '').lower()
    if extension not in AI_SUPPORTED_EXTENSIONS:
        record.status = '失败'
        record.summary = '当前文件类型不在 AI 分析支持范围内。'
        record.updated_at = datetime.utcnow()
        db.session.commit()
        return

    try:
        if extension in AI_IMAGE_EXTENSIONS:
            # 多模态：视觉大模型直接理解图片内容（含 OCR）
            summary = analyze_image_file(file_name=node.name, storage_rel_path=node.storage_rel_path)
            index_text = summary
        else:
            text = extract_analysis_text(storage_rel_path=node.storage_rel_path, extension=extension)
            summary = analyze_document_text(file_name=node.name, text=text)
            index_text = text

        record.status = '已完成'
        record.summary = summary
        record.updated_at = datetime.utcnow()
        record_activity(user_id=record.user_id, file_name=node.name, action='完成 AI 分析')

        # 顺带建立/刷新语义索引，供智能搜索使用
        try:
            from services.semantic_search import index_file_text

            index_file_text(record.user_id, node.id, index_text)
        except Exception:
            pass  # 索引失败不影响分析结果
    except FileManagerError as exc:
        record.status = '失败'
        record.summary = exc.message
        record.updated_at = datetime.utcnow()
        record_activity(user_id=record.user_id, file_name=node.name, action='AI 分析失败')
    except Exception:
        record.status = '失败'
        record.summary = 'AI 繁忙，请稍后重试'
        record.updated_at = datetime.utcnow()
        record_activity(user_id=record.user_id, file_name=node.name, action='AI 分析失败')

    db.session.commit()


def get_user_profile(user_id: int) -> dict:
    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise FileManagerError('用户不存在', code=404)

    return {
        'id': user.id,
        'account': user.username,
        'name': user.username,
        'role': 'USER',
        'status': user.status,
        'createdAt': user.created_at.strftime('%Y-%m-%d %H:%M'),
        'usedSpaceBytes': user.used_space_bytes,
        'spaceLimitBytes': user.space_limit_bytes,
    }


def _serialize_activity(item: ActivityRecord) -> dict:
    return {
        'id': item.id,
        'fileName': item.file_name,
        'action': item.action,
        'time': item.created_at.strftime('%Y-%m-%d %H:%M'),
    }


def _human_type(node: FileNode) -> str:
    if node.node_type == 'folder':
        return '文件夹'

    extension = (node.extension or '').lower()
    file_type = FILE_TYPE_BY_EXTENSION.get(extension, 'other')
    if file_type == 'document':
        return '文档'
    if file_type == 'image':
        return '图片'
    if file_type == 'video':
        return '视频'
    if file_type == 'archive':
        return '压缩包'
    return extension.upper() or '文件'
