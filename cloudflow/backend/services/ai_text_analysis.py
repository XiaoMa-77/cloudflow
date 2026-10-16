from __future__ import annotations

import base64
import csv
import re
import time
import zipfile
from io import StringIO
from pathlib import Path
from typing import List
from xml.etree import ElementTree

import requests

from config import Config, UPLOAD_DIR
from services.file_manager import FileManagerError

# ==============================================================================
# 常量定义与配置
# ==============================================================================

SUPPORTED_ANALYSIS_EXTENSIONS = {'txt', 'doc', 'docx', 'md', 'csv', 'xls', 'xlsx', 'pdf'}
IMAGE_ANALYSIS_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
_IMAGE_MIME_BY_EXTENSION = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_PUNCTUATION = r",.;:!?/\-_@#%&*+=|(){}\[\]<>，。！？；：（）《》【】、‘’"
_TEXT_SEGMENT_RE = re.compile(rf'[\u4e00-\u9fffA-Za-z0-9][\u4e00-\u9fffA-Za-z0-9\s{_PUNCTUATION}]{{5,}}')


# ==============================================================================
# 核心业务逻辑
# ==============================================================================

def extract_analysis_text(storage_rel_path: str, extension: str) -> str:
    """
    提取文件中的可分析文本内容。
    支持多种格式自动解析，并进行文本标准化处理。

    :param storage_rel_path: 文件相对存储路径
    :param extension: 文件扩展名
    :return: 标准化后的文本内容
    :raises FileManagerError: 当文件不支持、不存在或内容过少时抛出
    """
    ext = (extension or '').lower()
    if ext not in SUPPORTED_ANALYSIS_EXTENSIONS:
        raise FileManagerError('AI 分析仅支持 txt、doc、docx、md、csv、xls、xlsx、pdf 文件', code=409)

    if not storage_rel_path:
        raise FileManagerError('该文件缺少可分析内容，请上传后重试', code=409)

    absolute_path = UPLOAD_DIR / Path(storage_rel_path)
    if not absolute_path.exists() or not absolute_path.is_file():
        raise FileManagerError('未找到文件内容，请重新上传后再分析', code=404)

    # 根据扩展名分发提取逻辑
    if ext in {'txt', 'md'}:
        text = _extract_text_file(absolute_path)
    elif ext == 'csv':
        text = _extract_csv_text(absolute_path)
    elif ext == 'docx':
        text = _extract_docx_text(absolute_path)
    elif ext == 'xlsx':
        text = _extract_xlsx_text(absolute_path)
    elif ext == 'xls':
        text = _extract_xls_text(absolute_path)
    elif ext == 'doc':
        text = _extract_doc_text(absolute_path)
    else:
        text = _extract_pdf_text(absolute_path)

    # 文本标准化与长度校验
    normalized = _normalize_text(text)
    if len(normalized) < 10:
        raise FileManagerError('当前文件无法稳定提取文本内容，暂不支持内容分析', code=409)

    # 截断至配置允许的最大输入长度
    return normalized[: Config.AI_MAX_INPUT_CHARS]


def _request_chat_completion(payload: dict) -> dict:
    """调用对话接口；Kimi 免费档限流约 3 次/分钟，429 时等待后自动重试一次。"""
    endpoint = f"{Config.AI_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        'Authorization': f'Bearer {Config.AI_API_KEY}',
        'Content-Type': 'application/json',
    }
    response = None
    for attempt in range(2):
        response = requests.post(endpoint, json=payload, headers=headers, timeout=Config.AI_TIMEOUT_SECONDS)
        if response.status_code != 429 or attempt == 1:
            break
        time.sleep(10)
    response.raise_for_status()
    return response.json()


def analyze_document_text(file_name: str, text: str) -> str:
    """
    调用 AI 接口对文档内容进行深度分析与结构化摘要。
    采用高级提示词策略，输出专业级分析报告。

    :param file_name: 文件名称
    :param text: 待分析的文本内容
    :return: AI 生成的分析摘要
    :raises FileManagerError: 当 AI 服务不可用或请求失败时抛出
    """
    if not Config.AI_API_KEY:
        raise FileManagerError('AI 服务未配置或繁忙，请稍后重试', code=503)

    # --------------------------------------------------------------------------
    # 高级提示词工程 (Prompt Engineering)
    # --------------------------------------------------------------------------
    system_prompt = (
        "你是一位资深文档分析专家，具备跨学科的知识架构能力。"
        "你的任务是对提供的文档内容进行深度解析，输出专业、结构化、逻辑严密的中文分析报告。"
        "请遵循以下原则：\n"
        "1. 客观中立：基于事实陈述，避免主观臆断。\n"
        "2. 结构清晰：使用 Markdown 格式，层级分明。\n"
        "3. 深度洞察：不仅总结表面信息，还要提炼核心逻辑与潜在价值。\n"
        "4. 术语规范：正确使用领域专业术语。"
    )

    user_prompt = (
        f"请对文档《{file_name}》进行深度分析，并严格按照以下结构输出报告：\n\n"
        "## 📌 执行摘要\n"
        "- 用 100 字左右概括文档的核心价值与主旨。\n\n"
        "## 🔍 核心内容解析\n"
        "- **背景与目的**：文档产生的背景及试图解决的问题。\n"
        "- **关键论点/数据**：提取 3-5 个核心观点或关键数据支撑。\n"
        "- **逻辑架构**：简述文档的论证逻辑或内容组织方式。\n\n"
        "## 💡 洞察与结论\n"
        "- 基于内容得出的主要结论或发现。\n"
        "- 文档的局限性或潜在风险（如有）。\n\n"
        "## 🚀 行动建议\n"
        "- 基于文档内容，给出 1-3 条可落地的后续建议或决策参考。\n\n"
        "---\n"
        "文档内容如下：\n"
        f"{text}"
    )
    # --------------------------------------------------------------------------

    payload = {
        'model': Config.AI_MODEL,
        'max_tokens': 8000,  # 需覆盖思维链与报告两部分（kimi-k2.6 为思考型模型）
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
    }

    try:
        data = _request_chat_completion(payload)

        content = (
            data.get('choices', [{}])[0]
            .get('message', {})
            .get('content', '')
            .strip()
        )

        if content:
            return content
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 0
        if status_code == 429:
            raise FileManagerError('AI 服务限流（约 3 次/分钟），请稍后重试', code=503) from exc
        raise FileManagerError('AI 服务响应异常，请稍后重试', code=503) from exc
    except Exception as exc:
        raise FileManagerError('AI 服务响应异常，请稍后重试', code=503) from exc

    raise FileManagerError('AI 未返回有效内容，请稍后重试', code=503)


# ==============================================================================
# 多模态图片分析（视觉大模型）
# ==============================================================================

def analyze_image_file(file_name: str, storage_rel_path: str) -> str:
    """
    调用视觉大模型对图片进行内容理解与 OCR，输出结构化中文描述。

    :param file_name: 文件名称
    :param storage_rel_path: 图片相对存储路径
    :return: 结构化的图片内容描述（Markdown）
    :raises FileManagerError: 当文件不支持、过大或视觉服务异常时抛出
    """
    if not Config.AI_API_KEY:
        raise FileManagerError('AI 服务未配置或繁忙，请稍后重试', code=503)

    if not storage_rel_path:
        raise FileManagerError('该文件缺少可分析内容，请上传后重试', code=409)

    absolute_path = UPLOAD_DIR / Path(storage_rel_path)
    if not absolute_path.exists() or not absolute_path.is_file():
        raise FileManagerError('未找到文件内容，请重新上传后再分析', code=404)

    image_bytes = absolute_path.read_bytes()
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise FileManagerError('图片过大（超过 10MB），暂不支持 AI 分析', code=409)

    extension = Path(file_name).suffix.lstrip('.').lower() or 'png'
    mime_type = _IMAGE_MIME_BY_EXTENSION.get(extension, 'image/png')
    data_uri = f'data:{mime_type};base64,{base64.b64encode(image_bytes).decode("ascii")}'

    payload = {
        'model': Config.AI_VISION_MODEL,
        'max_tokens': 8000,  # 需覆盖思维链与回答两部分（kimi-k2.6 为思考型模型）
        'messages': [
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'image_url',
                        'image_url': {'url': data_uri},
                    },
                    {
                        'type': 'text',
                        'text': (
                            f'请对图片《{file_name}》进行多模态分析，用简体中文按以下结构输出 Markdown：\n\n'
                            '## 📌 图片概述\n'
                            '- 用一两句话概括图片内容与场景。\n\n'
                            '## 🔍 视觉要素\n'
                            '- 主体对象、人物动作、环境背景等关键要素。\n\n'
                            '## 📝 文字识别（OCR）\n'
                            '- 逐条列出图片中出现的所有文字；没有文字则写「无文字内容」。\n\n'
                            '## 🏷️ 标签建议\n'
                            '- 给出 5-8 个便于检索的中文标签，用顿号分隔。'
                        ),
                    },
                ],
            },
        ],
    }

    try:
        data = _request_chat_completion(payload)
        content = (
            data.get('choices', [{}])[0]
            .get('message', {})
            .get('content', '')
            .strip()
        )
        if content:
            return content
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 0
        if status_code == 429:
            raise FileManagerError('视觉 AI 服务限流（约 3 次/分钟），请稍后重试', code=503) from exc
        if status_code == 403:
            raise FileManagerError(
                '视觉模型不可用：当前 Kimi API Key 无权访问视觉模型，'
                '请在 Kimi 开放平台检查账户余额与模型权限后重试',
                code=503,
            ) from exc
        if status_code == 404:
            raise FileManagerError(
                '视觉模型不存在：请确认 AI_VISION_MODEL 配置的模型名在 Kimi 平台可用',
                code=503,
            ) from exc
        raise FileManagerError('视觉 AI 服务响应异常，请稍后重试', code=503) from exc
    except Exception as exc:
        raise FileManagerError('视觉 AI 服务响应异常，请稍后重试', code=503) from exc

    raise FileManagerError('AI 未返回有效内容，请稍后重试', code=503)


# ==============================================================================
# 文件提取辅助函数 (保持原有功能逻辑不变)
# ==============================================================================

def _extract_text_file(path: Path) -> str:
    """提取纯文本文件内容，兼容多种编码格式。"""
    raw = path.read_bytes()
    for encoding in ('utf-8-sig', 'utf-8', 'gb18030'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode('latin-1', errors='ignore')


def _extract_csv_text(path: Path) -> str:
    """提取 CSV 文件内容，限制行数以防过载。"""
    text = _extract_text_file(path)
    reader = csv.reader(StringIO(text))

    rows: List[str] = []
    for index, row in enumerate(reader):
        if index >= 600:
            break
        rows.append(', '.join(cell.strip() for cell in row))

    return '\n'.join(rows)


def _extract_docx_text(path: Path) -> str:
    """解析 DOCX 文件内部 XML 提取文本。"""
    try:
        with zipfile.ZipFile(path, 'r') as archive:
            xml_bytes = archive.read('word/document.xml')
    except Exception as exc:
        raise FileManagerError('docx 文件读取失败，请确认文件格式正确', code=409) from exc

    try:
        root = ElementTree.fromstring(xml_bytes)
    except Exception as exc:
        raise FileManagerError('docx 内容解析失败，请重新上传后重试', code=409) from exc

    texts = []
    for node in root.iter():
        if node.tag.endswith('}t') and node.text:
            value = node.text.strip()
            if value:
                texts.append(value)
    return '\n'.join(texts)


def _extract_xlsx_text(path: Path) -> str:
    """解析 XLSX 文件内部 XML 提取文本，包含共享字符串处理。"""
    try:
        with zipfile.ZipFile(path, 'r') as archive:
            shared_strings = _read_xlsx_shared_strings(archive)
            sheet_names = sorted(
                [name for name in archive.namelist() if
                 name.startswith('xl/worksheets/sheet') and name.endswith('.xml')]
            )
            chunks = []
            for sheet_name in sheet_names[:8]:
                sheet_xml = archive.read(sheet_name)
                rows = _read_xlsx_sheet_text(sheet_xml, shared_strings)
                chunks.extend(rows)
                if len(chunks) >= 1000:
                    break
    except FileManagerError:
        raise
    except Exception as exc:
        raise FileManagerError('xlsx 文件读取失败，请确认文件格式正确', code=409) from exc

    return '\n'.join(chunks[:1000])


def _read_xlsx_shared_strings(archive: zipfile.ZipFile) -> List[str]:
    """读取 XLSX 共享字符串表。"""
    if 'xl/sharedStrings.xml' not in archive.namelist():
        return []

    try:
        root = ElementTree.fromstring(archive.read('xl/sharedStrings.xml'))
    except Exception as exc:
        raise FileManagerError('xlsx 共享字符串解析失败', code=409) from exc

    values = []
    for item in root.iter():
        if item.tag.endswith('}t') and item.text:
            values.append(item.text.strip())
    return values


def _read_xlsx_sheet_text(sheet_xml: bytes, shared_strings: List[str]) -> List[str]:
    """解析 XLSX 工作表 XML 内容。"""
    try:
        root = ElementTree.fromstring(sheet_xml)
    except Exception as exc:
        raise FileManagerError('xlsx 工作表解析失败', code=409) from exc

    rows = []
    for row_node in root.iter():
        if not row_node.tag.endswith('}row'):
            continue

        cells = []
        for cell in row_node:
            if not cell.tag.endswith('}c'):
                continue

            cell_type = cell.attrib.get('t', '')
            value_node = None
            for child in cell:
                if child.tag.endswith('}v'):
                    value_node = child
                    break
            if value_node is None or value_node.text is None:
                continue

            raw = value_node.text.strip()
            if not raw:
                continue

            if cell_type == 's':
                try:
                    index = int(raw)
                    cells.append(shared_strings[index] if 0 <= index < len(shared_strings) else raw)
                except Exception:
                    cells.append(raw)
            else:
                cells.append(raw)

        if cells:
            rows.append('\t'.join(cells))
        if len(rows) >= 200:
            break
    return rows


def _extract_xls_text(path: Path) -> str:
    """解析旧版 XLS 文件，含依赖缺失降级处理。"""
    try:
        import xlrd
    except Exception as exc:
        raise FileManagerError('当前环境缺少 xls 解析依赖，暂不支持内容分析', code=500) from exc

    try:
        workbook = xlrd.open_workbook(str(path), on_demand=True)
    except Exception:
        # 降级方案：尝试从二进制中提取可读文本段
        segments = _extract_text_segments_from_binary(path.read_bytes())
        if segments:
            return '\n'.join(segments[:1500])
        raise FileManagerError('当前 xls 未能稳定提取纯文本，暂不支持内容分析', code=409)

    rows = []
    try:
        for sheet in workbook.sheets()[:8]:
            for row_idx in range(min(sheet.nrows, 300)):
                values = []
                row_values = sheet.row_values(row_idx)
                for value in row_values:
                    text = str(value).strip()
                    if text:
                        values.append(text)
                if values:
                    rows.append('\t'.join(values))
                if len(rows) >= 1200:
                    break
            if len(rows) >= 1200:
                break
    finally:
        workbook.release_resources()

    return '\n'.join(rows)


def _extract_doc_text(path: Path) -> str:
    """解析旧版 DOC 文件，含 OLE 结构处理。"""
    payloads = [path.read_bytes()]
    try:
        import olefile

        if olefile.isOleFile(str(path)):
            with olefile.OleFileIO(str(path)) as ole:
                for stream_name in ('WordDocument', '1Table', '0Table'):
                    if ole.exists(stream_name):
                        payloads.append(ole.openstream(stream_name).read())
    except Exception:
        # 继续尝试原始字节提取
        pass

    collected = []
    for payload in payloads:
        collected.extend(_extract_text_segments_from_binary(payload))

    return '\n'.join(collected[:1500])


def _extract_pdf_text(path: Path) -> str:
    """解析 PDF 文件文本内容。"""
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise FileManagerError('当前环境缺少 pdf 解析依赖，暂不支持内容分析', code=500) from exc

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise FileManagerError('pdf 文件读取失败，请确认文件格式正确', code=409) from exc

    rows = []
    for page in reader.pages[:80]:
        text = (page.extract_text() or '').strip()
        if text:
            rows.append(text)

    if not rows:
        raise FileManagerError('当前 pdf 未能稳定提取纯文本，暂不支持内容分析', code=409)

    return '\n\n'.join(rows)


def _extract_text_segments_from_binary(payload: bytes) -> List[str]:
    """从二进制数据中提取可读文本段（降级方案）。"""
    segments = []
    ascii_text = payload.decode('latin-1', errors='ignore')
    utf16_text = payload.decode('utf-16le', errors='ignore')

    for candidate in (ascii_text, utf16_text):
        for match in _TEXT_SEGMENT_RE.findall(candidate):
            normalized = re.sub(r'\s+', ' ', match).strip()
            if len(normalized) >= 8:
                segments.append(normalized)

    unique = []
    seen = set()
    for item in segments:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _normalize_text(text: str) -> str:
    """标准化文本格式，去除多余空白与控制字符。"""
    value = text.replace('\x00', ' ')
    value = re.sub(r'\r\n?', '\n', value)
    value = re.sub(r'[ \t]+', ' ', value)
    value = re.sub(r'\n{3,}', '\n\n', value)
    return value.strip()