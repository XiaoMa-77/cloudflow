from datetime import datetime

from sqlalchemy import text

from extensions import db
from models import ActivityRecord, AdminUser, AiAnalysisRecord, FavoriteRecord, FileNode, FileRecord, RecycleRecord, ShareRecord, User, TodoItem, LongTermTask, PasswordEntry
from services.user_portal import recalculate_user_storage


def init_database():
    db.create_all()
    _patch_sqlite_schema()

    legacy_demo_user = User.query.filter_by(username='demo.user').first()
    demo_user = User.query.filter_by(username='user').first()
    if legacy_demo_user and not demo_user:
        legacy_demo_user.username = 'user'
        demo_user = legacy_demo_user

    if not demo_user:
        demo_user = User(
            username='user',
            password='123456',
            status='ACTIVE',
            used_space_bytes=6_800_000_000,
            space_limit_bytes=20 * 1024 * 1024 * 1024,
        )
        db.session.add(demo_user)
        db.session.flush()
    elif legacy_demo_user and legacy_demo_user.id != demo_user.id:
        legacy_demo_user.username = 'user.legacy'

    sample_accounts = [
        ('user.a', 3_200_000_000, 10 * 1024 * 1024 * 1024, 'ACTIVE'),
        ('user.b', 8_900_000_000, 20 * 1024 * 1024 * 1024, 'ACTIVE'),
        ('user.c', 1_200_000_000, 5 * 1024 * 1024 * 1024, 'DISABLED'),
    ]
    for username, used, limit, status in sample_accounts:
        if not User.query.filter_by(username=username).first():
            db.session.add(
                User(
                    username=username,
                    password='123456',
                    status=status,
                    used_space_bytes=used,
                    space_limit_bytes=limit,
                )
            )

    legacy_demo_admin = AdminUser.query.filter_by(username='demo.admin').first()
    demo_admin = AdminUser.query.filter_by(username='admin').first()
    if legacy_demo_admin and not demo_admin:
        legacy_demo_admin.username = 'admin'
        demo_admin = legacy_demo_admin

    if not demo_admin:
        demo_admin = AdminUser(username='admin', password='123456')
        db.session.add(demo_admin)
    elif legacy_demo_admin and legacy_demo_admin.id != demo_admin.id:
        db.session.delete(legacy_demo_admin)

    if FileRecord.query.filter_by(user_id=demo_user.id).count() == 0:
        file_rows = [
            FileRecord(
                user_id=demo_user.id,
                file_name='项目排期-2026Q1.xlsx',
                file_type='document',
                folder_name='项目管理',
                size_bytes=4_618_240,
                updated_at=datetime(2026, 3, 11, 9, 40),
            ),
            FileRecord(
                user_id=demo_user.id,
                file_name='发布会主视觉.psd',
                file_type='image',
                folder_name='市场素材',
                size_bytes=68_245_504,
                updated_at=datetime(2026, 3, 10, 18, 12),
            ),
            FileRecord(
                user_id=demo_user.id,
                file_name='客户访谈剪辑.mp4',
                file_type='video',
                folder_name='视频资料',
                size_bytes=95_420_416,
                updated_at=datetime(2026, 3, 10, 16, 25),
            ),
            FileRecord(
                user_id=demo_user.id,
                file_name='交付清单-v6.pdf',
                file_type='document',
                folder_name='交付文档',
                size_bytes=2_211_840,
                updated_at=datetime(2026, 3, 9, 21, 6),
            ),
            FileRecord(
                user_id=demo_user.id,
                file_name='原始照片合集.zip',
                file_type='archive',
                folder_name='历史归档',
                size_bytes=54_812_672,
                updated_at=datetime(2026, 3, 8, 12, 28),
            ),
        ]
        db.session.add_all(file_rows)

    if ShareRecord.query.filter_by(user_id=demo_user.id).count() == 0:
        share_rows = [
            ShareRecord(
                user_id=demo_user.id,
                file_name='交付清单-v6.pdf',
                share_url='http://localhost:8080/share/s-01',
                access_mode='提取码 7F2K',
                status='生效中',
                expires_at=datetime(2026, 3, 18, 23, 59),
                visit_count=18,
            ),
            ShareRecord(
                user_id=demo_user.id,
                file_name='客户访谈剪辑.mp4',
                share_url='http://localhost:8080/share/s-02',
                access_mode='公开访问',
                status='生效中',
                expires_at=datetime(2026, 3, 14, 12, 0),
                visit_count=74,
            ),
            ShareRecord(
                user_id=demo_user.id,
                file_name='品牌素材包.zip',
                share_url='http://localhost:8080/share/s-03',
                access_mode='提取码 X9P6',
                status='已过期',
                expires_at=datetime(2026, 3, 7, 10, 0),
                visit_count=9,
            ),
            ShareRecord(
                user_id=demo_user.id,
                file_name='预算清单.xlsx',
                share_url='http://localhost:8080/share/s-04',
                access_mode='公开访问',
                status='已取消',
                expires_at=datetime(2026, 3, 20, 23, 59),
                visit_count=3,
            ),
        ]
        db.session.add_all(share_rows)

    if RecycleRecord.query.filter_by(user_id=demo_user.id).count() == 0:
        recycle_rows = [
            RecycleRecord(
                user_id=demo_user.id,
                file_name='培训资料-旧版.pptx',
                file_type='document',
                extension='pptx',
                mime_type='application/vnd.ms-powerpoint',
                storage_rel_path='',
                size_bytes=12_845_056,
                deleted_at=datetime(2026, 3, 10, 8, 20),
                remaining_days=28,
            ),
            RecycleRecord(
                user_id=demo_user.id,
                file_name='上线录屏-初版.mp4',
                file_type='video',
                extension='mp4',
                mime_type='video/mp4',
                storage_rel_path='',
                size_bytes=76_546_048,
                deleted_at=datetime(2026, 3, 9, 14, 5),
                remaining_days=27,
            ),
            RecycleRecord(
                user_id=demo_user.id,
                file_name='需求草稿.txt',
                file_type='document',
                extension='txt',
                mime_type='text/plain',
                storage_rel_path='',
                size_bytes=96_768,
                deleted_at=datetime(2026, 3, 6, 22, 41),
                remaining_days=24,
            ),
        ]
        db.session.add_all(recycle_rows)

    if FileNode.query.filter_by(user_id=demo_user.id).count() == 0:
        root = FileNode(
            user_id=demo_user.id,
            parent_id=None,
            node_type='folder',
            name='我的文件',
            extension='',
            size_bytes=0,
            mime_type='',
            storage_rel_path='',
            updated_at=datetime(2026, 3, 12, 10, 15),
        )
        db.session.add(root)
        db.session.flush()

        project_folder = FileNode(
            user_id=demo_user.id,
            parent_id=root.id,
            node_type='folder',
            name='项目资料',
            extension='',
            size_bytes=0,
            mime_type='',
            storage_rel_path='',
            updated_at=datetime(2026, 3, 12, 9, 30),
        )
        media_folder = FileNode(
            user_id=demo_user.id,
            parent_id=root.id,
            node_type='folder',
            name='市场素材',
            extension='',
            size_bytes=0,
            mime_type='',
            storage_rel_path='',
            updated_at=datetime(2026, 3, 10, 18, 12),
        )
        knowledge_folder = FileNode(
            user_id=demo_user.id,
            parent_id=root.id,
            node_type='folder',
            name='知识库',
            extension='',
            size_bytes=0,
            mime_type='',
            storage_rel_path='',
            updated_at=datetime(2026, 3, 9, 20, 6),
        )
        readme_file = FileNode(
            user_id=demo_user.id,
            parent_id=root.id,
            node_type='file',
            name='使用说明.txt',
            extension='txt',
            size_bytes=24_651,
            mime_type='text/plain',
            storage_rel_path='',
            updated_at=datetime(2026, 3, 12, 10, 15),
        )
        db.session.add_all([project_folder, media_folder, knowledge_folder, readme_file])
        db.session.flush()

        contract_folder = FileNode(
            user_id=demo_user.id,
            parent_id=project_folder.id,
            node_type='folder',
            name='合同文档',
            extension='',
            size_bytes=0,
            mime_type='',
            storage_rel_path='',
            updated_at=datetime(2026, 3, 11, 17, 20),
        )
        db.session.add(contract_folder)
        db.session.flush()

        db.session.add_all(
            [
                FileNode(
                    user_id=demo_user.id,
                    parent_id=contract_folder.id,
                    node_type='file',
                    name='年度框架协议.pdf',
                    extension='pdf',
                    size_bytes=2_516_582,
                    mime_type='application/pdf',
                    storage_rel_path='',
                    updated_at=datetime(2026, 3, 11, 16, 45),
                ),
                FileNode(
                    user_id=demo_user.id,
                    parent_id=contract_folder.id,
                    node_type='file',
                    name='保密条款补充.docx',
                    extension='docx',
                    size_bytes=735_211,
                    mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    storage_rel_path='',
                    updated_at=datetime(2026, 3, 10, 15, 14),
                ),
                FileNode(
                    user_id=demo_user.id,
                    parent_id=project_folder.id,
                    node_type='file',
                    name='项目排期-2026Q1.xlsx',
                    extension='xlsx',
                    size_bytes=4_618_240,
                    mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    storage_rel_path='',
                    updated_at=datetime(2026, 3, 11, 9, 40),
                ),
                FileNode(
                    user_id=demo_user.id,
                    parent_id=project_folder.id,
                    node_type='file',
                    name='项目复盘会议纪要.txt',
                    extension='txt',
                    size_bytes=92_640,
                    mime_type='text/plain',
                    storage_rel_path='',
                    updated_at=datetime(2026, 3, 12, 8, 28),
                ),
                FileNode(
                    user_id=demo_user.id,
                    parent_id=media_folder.id,
                    node_type='file',
                    name='发布会主视觉.psd',
                    extension='psd',
                    size_bytes=68_245_504,
                    mime_type='image/vnd.adobe.photoshop',
                    storage_rel_path='',
                    updated_at=datetime(2026, 3, 10, 18, 12),
                ),
                FileNode(
                    user_id=demo_user.id,
                    parent_id=media_folder.id,
                    node_type='file',
                    name='客户访谈剪辑.mp4',
                    extension='mp4',
                    size_bytes=95_420_416,
                    mime_type='video/mp4',
                    storage_rel_path='',
                    updated_at=datetime(2026, 3, 10, 16, 25),
                ),
            ]
        )

        ai_folder = FileNode(
            user_id=demo_user.id,
            parent_id=knowledge_folder.id,
            node_type='folder',
            name='AI 可分析文档',
            extension='',
            size_bytes=0,
            mime_type='',
            storage_rel_path='',
            updated_at=datetime(2026, 3, 12, 9, 12),
        )
        db.session.add(ai_folder)
        db.session.flush()

        db.session.add_all(
            [
                FileNode(
                    user_id=demo_user.id,
                    parent_id=ai_folder.id,
                    node_type='file',
                    name='交付清单-v6.pdf',
                    extension='pdf',
                    size_bytes=2_211_840,
                    mime_type='application/pdf',
                    storage_rel_path='',
                    updated_at=datetime(2026, 3, 9, 21, 6),
                ),
                FileNode(
                    user_id=demo_user.id,
                    parent_id=ai_folder.id,
                    node_type='file',
                    name='需求规格说明书.doc',
                    extension='doc',
                    size_bytes=1_328_991,
                    mime_type='application/msword',
                    storage_rel_path='',
                    updated_at=datetime(2026, 3, 11, 11, 48),
                ),
            ]
        )

    if FavoriteRecord.query.filter_by(user_id=demo_user.id).count() == 0:
        favored_nodes = FileNode.query.filter_by(user_id=demo_user.id, node_type='file').limit(3).all()
        db.session.add_all([FavoriteRecord(user_id=demo_user.id, file_node_id=item.id) for item in favored_nodes])

    if AiAnalysisRecord.query.filter_by(user_id=demo_user.id).count() == 0:
        db.session.add_all(
            [
                AiAnalysisRecord(
                    user_id=demo_user.id,
                    file_name='交付清单-v6.pdf',
                    file_type='pdf',
                    summary='文档结构清晰，核心条款与交付节点已识别。',
                    status='已完成',
                    created_at=datetime(2026, 3, 11, 18, 24),
                ),
                AiAnalysisRecord(
                    user_id=demo_user.id,
                    file_name='项目复盘会议纪要.txt',
                    file_type='txt',
                    summary='已提取关键行动项与风险提醒。',
                    status='已完成',
                    created_at=datetime(2026, 3, 10, 9, 46),
                ),
            ]
        )

    if ActivityRecord.query.filter_by(user_id=demo_user.id).count() == 0:
        db.session.add_all(
            [
                ActivityRecord(
                    user_id=demo_user.id,
                    file_name='投标答疑记录.pdf',
                    action='完成 AI 分析',
                    created_at=datetime(2026, 3, 12, 9, 58),
                ),
                ActivityRecord(
                    user_id=demo_user.id,
                    file_name='品牌素材包.zip',
                    action='上传文件',
                    created_at=datetime(2026, 3, 12, 9, 42),
                ),
                ActivityRecord(
                    user_id=demo_user.id,
                    file_name='季度复盘.mp4',
                    action='创建分享链接',
                    created_at=datetime(2026, 3, 12, 9, 32),
                ),
                ActivityRecord(
                    user_id=demo_user.id,
                    file_name='预算清单.xlsx',
                    action='移动到财务目录',
                    created_at=datetime(2026, 3, 11, 20, 14),
                ),
            ]
        )

    recalculate_user_storage(demo_user.id)
    db.session.commit()


def _patch_sqlite_schema():
    _ensure_columns(
        'file_node',
        {
            'mime_type': "TEXT NOT NULL DEFAULT ''",
            'storage_rel_path': "TEXT NOT NULL DEFAULT ''",
        },
    )
    _ensure_columns(
        'recycle_record',
        {
            'extension': "TEXT NOT NULL DEFAULT ''",
            'mime_type': "TEXT NOT NULL DEFAULT ''",
            'storage_rel_path': "TEXT NOT NULL DEFAULT ''",
        },
    )


def _ensure_columns(table_name: str, column_definitions: dict):
    inspector_sql = text(f'PRAGMA table_info({table_name})')
    existing_rows = db.session.execute(inspector_sql).fetchall()
    existing_columns = {row[1] for row in existing_rows}

    for column_name, column_sql in column_definitions.items():
        if column_name in existing_columns:
            continue
        db.session.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}'))
    db.session.commit()
