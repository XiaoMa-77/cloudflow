from routes.ai_analysis import bp as ai_analysis_bp
from routes.admin import bp as admin_bp
from routes.auth import bp as auth_bp
from routes.files import bp as files_bp
from routes.recycle import bp as recycle_bp
from routes.share_public import bp as share_public_bp
from routes.shares import bp as shares_bp
from routes.user import bp as user_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(shares_bp)
    app.register_blueprint(share_public_bp)
    app.register_blueprint(recycle_bp)
    app.register_blueprint(ai_analysis_bp)
