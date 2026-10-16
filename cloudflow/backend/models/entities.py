from datetime import datetime

from extensions import db


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(16), nullable=False, default='ACTIVE')
    used_space_bytes = db.Column(db.Integer, nullable=False, default=0)
    space_limit_bytes = db.Column(db.Integer, nullable=False, default=20 * 1024 * 1024 * 1024)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdminUser(db.Model):
    __tablename__ = 'admin_user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuthSession(db.Model):
    __tablename__ = 'auth_session'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    role = db.Column(db.String(16), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('admin_user.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class FileRecord(db.Model):
    __tablename__ = 'file_record'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(32), nullable=False, default='other', index=True)
    folder_name = db.Column(db.String(128), nullable=False, default='根目录')
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class FileNode(db.Model):
    __tablename__ = 'file_node'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('file_node.id'), nullable=True, index=True)
    node_type = db.Column(db.String(16), nullable=False, default='file', index=True)
    name = db.Column(db.String(255), nullable=False)
    extension = db.Column(db.String(32), nullable=False, default='')
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    mime_type = db.Column(db.String(128), nullable=False, default='')
    storage_rel_path = db.Column(db.String(512), nullable=False, default='')
    content_hash = db.Column(db.String(64), nullable=False, default='', index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class FileBlob(db.Model):
    """文件内容指纹表：相同内容只落一份物理文件，支撑秒传与去重。"""

    __tablename__ = 'file_blob'

    id = db.Column(db.Integer, primary_key=True)
    content_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    storage_rel_path = db.Column(db.String(512), nullable=False, default='')
    ref_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmbeddingChunk(db.Model):
    """语义索引分块：文档/图片描述切分后向量化存储，支撑 RAG 检索。"""

    __tablename__ = 'embedding_chunk'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    file_node_id = db.Column(db.Integer, db.ForeignKey('file_node.id'), nullable=False, index=True)
    chunk_index = db.Column(db.Integer, nullable=False, default=0)
    chunk_text = db.Column(db.Text, nullable=False, default='')
    embedding = db.Column(db.LargeBinary, nullable=False, default=b'')
    dim = db.Column(db.Integer, nullable=False, default=0)
    model = db.Column(db.String(64), nullable=False, default='', index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class UploadSession(db.Model):
    """分片上传会话：记录分片接收进度，支撑断点续传。"""

    __tablename__ = 'upload_session'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    upload_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    parent_id = db.Column(db.Integer, nullable=True)
    total_bytes = db.Column(db.Integer, nullable=False, default=0)
    chunk_size = db.Column(db.Integer, nullable=False, default=0)
    total_chunks = db.Column(db.Integer, nullable=False, default=0)
    received_chunks = db.Column(db.Text, nullable=False, default='')
    status = db.Column(db.String(16), nullable=False, default='UPLOADING', index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class FavoriteRecord(db.Model):
    __tablename__ = 'favorite_record'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    file_node_id = db.Column(db.Integer, db.ForeignKey('file_node.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AiAnalysisRecord(db.Model):
    __tablename__ = 'ai_analysis_record'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    file_node_id = db.Column(db.Integer, db.ForeignKey('file_node.id'), nullable=True, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(32), nullable=False, default='other')
    summary = db.Column(db.Text, nullable=False, default='')
    status = db.Column(db.String(24), nullable=False, default='已完成', index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityRecord(db.Model):
    __tablename__ = 'activity_record'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    action = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class ShareRecord(db.Model):
    __tablename__ = 'share_record'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    file_record_id = db.Column(db.Integer, db.ForeignKey('file_record.id'), nullable=True)
    file_name = db.Column(db.String(255), nullable=False)
    share_url = db.Column(db.String(255), nullable=False)
    access_mode = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(16), nullable=False, default='生效中', index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    visit_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RecycleRecord(db.Model):
    __tablename__ = 'recycle_record'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(32), nullable=False, default='other')
    extension = db.Column(db.String(32), nullable=False, default='')
    mime_type = db.Column(db.String(128), nullable=False, default='')
    storage_rel_path = db.Column(db.String(512), nullable=False, default='')
    content_hash = db.Column(db.String(64), nullable=False, default='')
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    deleted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    remaining_days = db.Column(db.Integer, nullable=False, default=30)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class TodoItem(db.Model):
    __tablename__ = 'todo_item'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.String(16), nullable=False, default='medium')
    completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class LongTermTask(db.Model):
    __tablename__ = 'long_term_task'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    progress = db.Column(db.Integer, nullable=False, default=0)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(16), nullable=False, default='进行中')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PasswordEntry(db.Model):
    __tablename__ = 'password_entry'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    app = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    note = db.Column(db.Text, nullable=False, default='')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
