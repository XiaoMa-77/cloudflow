from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from config import Config, INSTANCE_DIR, UPLOAD_DIR
from extensions import cors, db
from routes import register_blueprints
from services.ai_task_queue import start_ai_worker
from services import init_database

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = PROJECT_ROOT / 'admin' / 'dist'
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / 'index.html'


def create_app():
    app = Flask(__name__, static_folder=str(FRONTEND_DIST_DIR), static_url_path='')
    app.config.from_object(Config)

    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    cors.init_app(app, resources={r'/api/*': {'origins': '*'}})
    register_blueprints(app)

    with app.app_context():
        init_database()
    start_ai_worker(app)

    @app.get('/api/health')
    def health():
        return jsonify({'code': 200, 'message': 'ok', 'data': {'service': 'cloudflow'}})

    @app.get('/')
    def index():
        if FRONTEND_INDEX_FILE.exists():
            return app.send_static_file('index.html')
        return jsonify({'code': 200, 'message': '前端构建产物不存在，请先执行 admin/npm run build', 'data': None})

    @app.get('/<path:path>')
    def frontend(path):
        if path.startswith('api/'):
            return jsonify({'code': 404, 'message': 'API 路径不存在', 'data': None}), 404

        target = FRONTEND_DIST_DIR / path
        if target.exists() and target.is_file():
            return send_from_directory(FRONTEND_DIST_DIR, path)

        if FRONTEND_INDEX_FILE.exists():
            return app.send_static_file('index.html')
        return jsonify({'code': 404, 'message': '前端构建产物不存在，请先执行 admin/npm run build', 'data': None}), 404

    return app


app = create_app()

if __name__ == '__main__':
    # exclude_patterns: 排除所有 site-packages，避免第三方包文件变化触发 reload 中断 AI 分析任务
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True,
        exclude_patterns=['*site-packages*'],
    )
