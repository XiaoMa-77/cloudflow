"""cloudflow 后端测试夹具：真实 Flask 应用 + 临时 SQLite 与上传目录。

被测代码在多个模块里各自绑定 ``from config import UPLOAD_DIR``，
因此补丁必须逐模块覆盖，且在调用 create_app() 之前完成。
每个用例拿到独立的应用实例与全新数据库，互不串扰。
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def app(tmp_path):
    import config
    from extensions import db as _db

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    db_path = tmp_path / "test.db"

    config.Config.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    config.Config.UPLOAD_DIR = str(upload_dir)
    config.UPLOAD_DIR = upload_dir

    import app as app_module
    import routes.share_public as share_public
    import services.ai_text_analysis as ai_text_analysis
    import services.chunk_upload as chunk_upload
    import services.file_manager as file_manager
    import services.recycle_service as recycle_service

    for module in (app_module, share_public, ai_text_analysis,
                   recycle_service, chunk_upload):
        module.UPLOAD_DIR = upload_dir
    file_manager.UPLOAD_DIR = upload_dir
    file_manager.BLOB_DIR = upload_dir / "blobs"
    file_manager.CHUNK_TMP_DIR = upload_dir / ".chunks"

    application = app_module.create_app()
    yield application

    with application.app_context():
        _db.session.remove()
        _db.drop_all()
