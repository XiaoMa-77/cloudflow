"""RAG 语义搜索服务。

- 文本切片后向量化存入 ``embedding_chunk`` 表：配置了 ``EMBEDDING_*`` 时走外部
  OpenAI 兼容 /embeddings 服务，否则使用内置本地向量化（特征哈希 n-gram，离线可用）；
- 检索时对查询向量与全部分块做余弦相似度，取 Top-K 片段；
- 可选将 Top-K 片段作为上下文交给对话模型（Kimi/Moonshot）生成自然语言答案；
- 索引行记录向量来源标识（model 列），切换向量服务后旧索引自动失效，重建即可。
"""
from __future__ import annotations

import hashlib
import time

import requests

from config import Config
from extensions import db
from models import EmbeddingChunk, FileNode

_EMBED_BATCH_SIZE = 16
_CHUNK_SIZE = 700
_CHUNK_OVERLAP = 80
_MAX_CONTEXT_CHARS = 6000
_LOCAL_EMBED_DIM = 512
_LOCAL_EMBED_MODEL_ID = 'local:ngram-v1'


class SemanticSearchError(Exception):
    def __init__(self, message: str, code: int = 502):
        super().__init__(message)
        self.message = message
        self.code = code


def _remote_embedding_enabled() -> bool:
    return bool(Config.EMBEDDING_BASE_URL and Config.EMBEDDING_API_KEY and Config.AI_EMBEDDING_MODEL)


def current_embedding_model_id() -> str:
    """当前生效的向量来源标识，用于索引隔离。"""
    if _remote_embedding_enabled():
        return f'api:{Config.AI_EMBEDDING_MODEL}'
    return _LOCAL_EMBED_MODEL_ID


def embed_texts(texts: list[str], kind: str = 'db') -> list[list[float]]:
    """向量化入口：优先外部 API，未配置时使用内置本地向量化。

    kind: 'db'（索引入库）/ 'query'（检索查询），
    仅 MiniMax embo-01 这类非对称向量模型区分，OpenAI 兼容服务忽略该参数。
    """
    if _remote_embedding_enabled():
        return _request_remote_embeddings(texts, kind)
    return [_local_embed_text(text) for text in texts]


def _request_remote_embeddings(texts: list[str], kind: str) -> list[list[float]]:
    is_minimax = Config.EMBEDDING_PROVIDER == 'minimax'
    vectors: list[list[float]] = []
    for start in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = [text[:4000] for text in texts[start:start + _EMBED_BATCH_SIZE]]
        if is_minimax:
            body = {'model': Config.AI_EMBEDDING_MODEL, 'texts': batch, 'type': kind}
        else:
            body = {'model': Config.AI_EMBEDDING_MODEL, 'input': batch}
        try:
            response = requests.post(
                f'{Config.EMBEDDING_BASE_URL.rstrip("/")}/embeddings',
                headers={'Authorization': f'Bearer {Config.EMBEDDING_API_KEY}'},
                json=body,
                timeout=Config.AI_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            raise SemanticSearchError('向量服务连接失败，请稍后重试')

        if response.status_code != 200:
            raise SemanticSearchError(f'向量化失败（HTTP {response.status_code}）')

        payload = response.json()
        if is_minimax:
            # MiniMax 业务错误也返回 HTTP 200，需检查 base_resp
            base_resp = payload.get('base_resp') or {}
            if base_resp.get('status_code'):
                raise SemanticSearchError(f"向量化失败：{base_resp.get('status_msg') or '服务返回错误'}")
            batch_vectors = payload.get('vectors') or []
        else:
            items = payload.get('data') or []
            ordered = sorted(items, key=lambda item: item.get('index', 0))
            batch_vectors = [item['embedding'] for item in ordered]
        vectors.extend(batch_vectors)

    if len(vectors) != len(texts):
        raise SemanticSearchError('向量化返回数量不匹配')
    return vectors


def _local_embed_text(text: str) -> list[float]:
    """内置本地向量化：字符 n-gram 特征哈希（feature hashing）。

    中文按单字 + 二元组、英文按词切分，哈希到固定维度后 L2 归一化。
    无需联网与外部依赖，效果弱于专业向量模型，但可离线支撑语义检索演示。
    """
    import numpy as np

    text = (text or '').strip()
    vector = np.zeros(_LOCAL_EMBED_DIM, dtype='float32')
    if not text:
        return vector.tolist()

    tokens: set[str] = set()
    for i, char in enumerate(text):
        tokens.add(char)
        if i + 1 < len(text):
            tokens.add(text[i:i + 2])
    for word in text.split():
        if word:
            tokens.add(word)

    for token in tokens:
        digest = hashlib.md5(token.encode('utf-8')).digest()
        slot = int.from_bytes(digest[:4], 'little') % _LOCAL_EMBED_DIM
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[slot] += sign

    norm = float(np.linalg.norm(vector))
    if norm > 0:
        vector /= norm
    return vector.tolist()


def chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """按段落聚合切分，超出 chunk_size 的长段落按字符滑窗切。"""
    normalized = (text or '').strip()
    if not normalized:
        return []

    paragraphs = [p.strip() for p in normalized.split('\n') if p.strip()]
    chunks: list[str] = []
    buffer = ''

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if buffer:
                chunks.append(buffer)
                buffer = ''
            step = max(chunk_size - overlap, 1)
            for start in range(0, len(paragraph), step):
                piece = paragraph[start:start + chunk_size]
                if piece:
                    chunks.append(piece)
            continue

        if len(buffer) + len(paragraph) + 1 > chunk_size and buffer:
            chunks.append(buffer)
            buffer = buffer[-overlap:] + '\n' + paragraph if overlap else paragraph
        else:
            buffer = f'{buffer}\n{paragraph}' if buffer else paragraph

    if buffer:
        chunks.append(buffer)
    return chunks


def index_file_text(user_id: int, node_id: int, text: str) -> int:
    """为文件建立/重建语义索引，返回分块数量。"""
    EmbeddingChunk.query.filter_by(user_id=user_id, file_node_id=node_id).delete(synchronize_session=False)
    db.session.commit()

    chunks = chunk_text(text)
    if not chunks:
        return 0

    model_id = current_embedding_model_id()
    vectors = embed_texts(chunks, kind='db')
    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        db.session.add(
            EmbeddingChunk(
                user_id=user_id,
                file_node_id=node_id,
                chunk_index=index,
                chunk_text=chunk,
                embedding=_pack_vector(vector),
                dim=len(vector),
                model=model_id,
            )
        )
    db.session.commit()
    return len(chunks)


def delete_file_index(user_id: int, node_id: int) -> None:
    EmbeddingChunk.query.filter_by(user_id=user_id, file_node_id=node_id).delete(synchronize_session=False)
    db.session.commit()


def semantic_search(user_id: int, query: str, top_k: int = 8) -> list[dict]:
    """全库余弦相似度检索，按文件聚合返回最相关片段（仅比较同向量来源的索引）。"""
    query = (query or '').strip()
    if not query:
        raise SemanticSearchError('请输入搜索内容', code=400)

    model_id = current_embedding_model_id()
    rows = (
        EmbeddingChunk.query
        .join(FileNode, FileNode.id == EmbeddingChunk.file_node_id)
        .filter(EmbeddingChunk.user_id == user_id, EmbeddingChunk.model == model_id)
        .add_columns(FileNode.id, FileNode.name, FileNode.extension, FileNode.size_bytes, FileNode.updated_at)
        .all()
    )
    if not rows:
        return []

    query_vector = embed_texts([query], kind='query')[0]

    try:
        import numpy as np

        query_matrix = np.asarray(query_vector, dtype='float32')
        query_norm = np.linalg.norm(query_matrix)
        if query_norm == 0:
            return []

        scored = []
        seen_files: set[int] = set()
        for row, node_id, name, extension, size_bytes, updated_at in rows:
            vector = _unpack_vector(row.embedding, row.dim)
            if not vector:
                continue
            candidate = np.asarray(vector, dtype='float32')
            norm = np.linalg.norm(candidate)
            if norm == 0:
                continue
            score = float(np.dot(query_matrix, candidate) / (query_norm * norm))
            scored.append((score, row, node_id, name, extension, size_bytes, updated_at))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, row, node_id, name, extension, size_bytes, updated_at in scored:
            if node_id in seen_files:
                continue  # 每个文件只保留最相关片段
            seen_files.add(node_id)
            results.append(
                {
                    'fileId': node_id,
                    'fileName': name,
                    'extension': extension or '',
                    'sizeBytes': size_bytes,
                    'updatedAt': updated_at.strftime('%Y-%m-%d %H:%M') if updated_at else '',
                    'snippet': row.chunk_text[:300],
                    'score': round(score, 4),
                }
            )
            if len(results) >= top_k:
                break
        return results
    except ImportError:
        raise SemanticSearchError('服务器缺少 numpy 依赖，无法进行语义检索', code=500)


def rag_answer(user_id: int, query: str, results: list[dict]) -> str:
    """基于检索片段生成自然语言答案（Kimi / Moonshot 对话模型）。"""
    if not results:
        return ''

    if not Config.AI_API_KEY:
        raise SemanticSearchError('AI 服务未配置，请在 backend/.env 中设置 MOONSHOT_API_KEY', code=503)

    context_blocks = []
    used_chars = 0
    for result in results:
        block = f"【{result['fileName']}】\n{result['snippet']}"
        if used_chars + len(block) > _MAX_CONTEXT_CHARS:
            break
        context_blocks.append(block)
        used_chars += len(block)

    prompt = (
        '你是云盘文件的智能助手。请仅依据下面给出的云盘文件片段，用简体中文回答用户的问题。'
        '如果片段不足以回答，请直接说明没有找到相关内容。回答末尾请列出引用的文件名。\n\n'
        f'文件片段：\n{"\n\n".join(context_blocks)}\n\n'
        f'用户问题：{query}'
    )

    try:
        response = None
        for attempt in range(2):
            response = requests.post(
                f'{Config.AI_BASE_URL.rstrip("/")}/chat/completions',
                headers={'Authorization': f'Bearer {Config.AI_API_KEY}'},
                json={
                    'model': Config.AI_MODEL,
                    'messages': [
                        {'role': 'system', 'content': '你是一个严谨的云盘内容检索助手，只依据给定材料回答。'},
                        {'role': 'user', 'content': prompt},
                    ],
                    'max_tokens': 4000,  # 需覆盖思维链与回答（kimi-k2.6 为思考型模型）
                },
                timeout=Config.AI_TIMEOUT_SECONDS,
            )
            if response.status_code != 429 or attempt == 1:
                break
            time.sleep(10)  # Kimi 免费档限流约 3 次/分钟
    except requests.RequestException:
        raise SemanticSearchError('AI 服务连接失败，请稍后重试')

    if response is None or response.status_code != 200:
        if response is not None and response.status_code == 429:
            raise SemanticSearchError('AI 问答限流（约 3 次/分钟），请稍后再试')
        raise SemanticSearchError(f'AI 问答失败（HTTP {response.status_code if response is not None else 0}）')

    data = response.json()
    choices = data.get('choices') or []
    if not choices:
        raise SemanticSearchError('AI 未返回有效回答')
    return (choices[0].get('message') or {}).get('content', '').strip()


def get_index_status(user_id: int) -> dict:
    model_id = current_embedding_model_id()
    base_query = EmbeddingChunk.query.filter_by(user_id=user_id, model=model_id)
    chunk_count = base_query.count()
    file_count = (
        base_query
        .with_entities(EmbeddingChunk.file_node_id)
        .distinct()
        .count()
    )
    return {
        'indexedFiles': file_count,
        'indexedChunks': chunk_count,
        'embeddingMode': 'api' if _remote_embedding_enabled() else 'local',
    }


def _pack_vector(vector: list[float]) -> bytes:
    import numpy as np

    return np.asarray(vector, dtype='float32').tobytes()


def _unpack_vector(blob: bytes, dim: int) -> list[float]:
    if not blob or dim <= 0:
        return []
    import numpy as np

    if len(blob) != dim * 4:
        return []
    return np.frombuffer(blob, dtype='float32').tolist()
