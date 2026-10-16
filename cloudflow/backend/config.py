import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / 'instance'
UPLOAD_DIR = BASE_DIR / 'uploads'
DATABASE_PATH = INSTANCE_DIR / '2026030303.db'


class Config:
    SECRET_KEY = '2026030303-dev-secret'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    UPLOAD_DIR = str(UPLOAD_DIR)
    AI_BASE_URL = os.getenv('AI_BASE_URL', 'https://api.siliconflow.cn/v1')
    AI_API_KEY = os.getenv('SILICONFLOW_API_KEY', 'sk-venqnuaopzopqsmzsygsgiovkbncrhuaxvphyleabphyifmw')
    AI_MODEL = os.getenv('AI_MODEL', 'Qwen/Qwen2.5-7B-Instruct')
    AI_TIMEOUT_SECONDS = int(os.getenv('AI_TIMEOUT_SECONDS', '30'))
    AI_MAX_INPUT_CHARS = int(os.getenv('AI_MAX_INPUT_CHARS', '12000'))
