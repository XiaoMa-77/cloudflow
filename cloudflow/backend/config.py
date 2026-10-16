import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / 'instance'
UPLOAD_DIR = BASE_DIR / 'uploads'
DATABASE_PATH = INSTANCE_DIR / '2026030303.db'
ENV_FILE = BASE_DIR / '.env'


def _load_env_file() -> None:
    """从 backend/.env 读取配置，不覆盖已存在的环境变量。"""
    if not ENV_FILE.exists():
        return
    try:
        lines = ENV_FILE.read_text(encoding='utf-8').splitlines()
    except OSError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', '2026030303-dev-secret')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 单请求上限：普通上传走分片（每片 4MB），这里给直接上传留足余量
    MAX_CONTENT_LENGTH = 512 * 1024 * 1024
    UPLOAD_DIR = str(UPLOAD_DIR)

    # AI 服务配置（Kimi / Moonshot，密钥只从环境变量或 backend/.env 读取，禁止写入源码）
    # kimi-k2.6 为原生多模态模型，对话与视觉分析共用；账户限流约 3 RPM
    AI_BASE_URL = os.getenv('AI_BASE_URL', 'https://api.moonshot.cn/v1')
    AI_API_KEY = os.getenv('MOONSHOT_API_KEY', '')
    AI_MODEL = os.getenv('AI_MODEL', 'kimi-k2.6')
    AI_VISION_MODEL = os.getenv('AI_VISION_MODEL', 'kimi-k2.6')
    AI_TIMEOUT_SECONDS = int(os.getenv('AI_TIMEOUT_SECONDS', '180'))
    AI_MAX_INPUT_CHARS = int(os.getenv('AI_MAX_INPUT_CHARS', '12000'))

    # 向量服务（用于语义搜索）。未配置时自动使用内置本地向量化（特征哈希 n-gram），
    # 可接入任意 OpenAI 兼容 /embeddings 服务（如 SiliconFlow bge-m3）。
    EMBEDDING_BASE_URL = os.getenv('EMBEDDING_BASE_URL', '')
    EMBEDDING_API_KEY = os.getenv('EMBEDDING_API_KEY', '')
    AI_EMBEDDING_MODEL = os.getenv('AI_EMBEDDING_MODEL', '')
    # 向量服务协议：openai（OpenAI 兼容，默认）/ minimax（原生 texts 格式；embo-01 为非对称模型，入库 db / 检索 query）
    EMBEDDING_PROVIDER = os.getenv('EMBEDDING_PROVIDER', 'openai')

    # 分片上传
    UPLOAD_CHUNK_SIZE = int(os.getenv('UPLOAD_CHUNK_SIZE', str(4 * 1024 * 1024)))

    # 密码本静态加密主密钥（Fernet key，仅存于 .env）
    PASSWORD_BOOK_KEY = os.getenv('PASSWORD_BOOK_KEY', '')
