# CloudFlow 智能云盘系统

基于 **Flask + Vue 3** 的智能云盘与个人协作空间，集成内容寻址去重存储、分片断点续传、RAG 语义搜索与多模态 AI 分析能力，AI 能力由 **Kimi（Moonshot）** 驱动。

## 核心特性

### 智能存储

| 特性 | 说明 |
| --- | --- |
| 内容寻址去重 | 文件按 SHA-256 指纹存储于 `uploads/blobs/`，相同内容只落盘一次，引用计数管理生命周期 |
| 秒传 | 客户端计算哈希后命中已有指纹，服务端直接建文件记录，零字节传输 |
| 分片上传 / 断点续传 | 4MB 分片（256KB–16MB 可配），`UploadSession` 记录已收分片，中断后可从断点继续，合并时流式计算哈希并去重 |

### 语义搜索与智能问答（RAG）

- 文档解析后按 700 字 / 80 字重叠滑窗分块，向量化存入 `embedding_chunk` 表
- 检索阶段对查询向量与全部分块做余弦相似度，按文件聚合返回 Top-K 片段
- 可选将 Top-K 片段作为上下文交给 Kimi 生成**带文件引用**的自然语言答案
- **向量化服务可插拔**：配置 `EMBEDDING_*` 即接入任意 OpenAI 兼容 `/embeddings` 服务；未配置时自动启用内置本地向量化（字符 n-gram 特征哈希，离线可用）
- 索引行记录向量来源标识（`model` 列），切换向量服务后旧索引自动隔离，重建即可

### 多模态 AI 分析

- **文档深度分析**：支持 `txt / md / csv / doc / docx / xls / xlsx / pdf`，输出结构化中文分析报告（执行摘要、核心解析、洞察结论、行动建议）
- **图片视觉理解**：`jpg / jpeg / png / gif / webp`，基于 kimi-k2.6 原生多模态能力，输出图片概述、视觉要素、OCR 文字识别与检索标签
- 分析任务走后台队列异步执行，完成后自动建立语义索引，沉淀为可检索知识

### 安全设计

- 密码 **pbkdf2:sha256** 哈希存储，历史明文密码在首次登录时自动升级
- 密码本条目 **Fernet 对称加密**（`enc:v1:` 前缀），主密钥仅存于 `backend/.env`
- AI API Key 只从环境变量 / `.env` 读取，`.gitignore` 已排除，不入库不入 Git
- AI 调用内置 429 限流自动重试，保障免费额度下的可用性

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 后端 | Python / Flask / SQLAlchemy / SQLite |
| 前端 | Vue 3 / Vite / Element Plus / Pinia |
| AI 服务 | Kimi `kimi-k2.6`（Moonshot OpenAI 兼容 API，对话 + 视觉多模态） |
| 向量化 | 内置 n-gram 特征哈希（默认）/ 任意 OpenAI 兼容 embeddings 服务（可选） |
| 安全 | hashlib.pbkdf2_hmac / cryptography.Fernet |

## 快速开始

### 环境要求

- Node.js 20.19+（或 22.12+）
- Python 3.10+（依赖见 `cloudflow/requirements.txt`）

### 配置 AI 服务

复制以下内容到 `cloudflow/backend/.env`（该文件已被 Git 排除）：

```ini
# Kimi (Moonshot) API Key，获取地址：https://platform.moonshot.cn/console/api-keys
MOONSHOT_API_KEY=sk-xxxxxxxx

# 对话与视觉模型（kimi-k2.6 为原生多模态，两者共用）
AI_MODEL=kimi-k2.6
AI_VISION_MODEL=kimi-k2.6

# 可选：外部向量服务（任意 OpenAI 兼容 /embeddings 接口），留空则使用内置本地向量化
# EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
# EMBEDDING_API_KEY=sk-xxxx
# AI_EMBEDDING_MODEL=BAAI/bge-m3

# 密码本静态加密主密钥（python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"）
PASSWORD_BOOK_KEY=your-fernet-key
```

> 说明：未配置 `MOONSHOT_API_KEY` 时，语义检索仍可离线工作（本地向量化），仅 AI 问答与分析不可用。

### 启动后端

```sh
cd cloudflow
python -m pip install -r requirements.txt
cd backend
python app.py          # 监听 http://localhost:8080
```

### 启动前端

```sh
cd cloudflow/admin
npm ci
npm run dev            # 开发模式
npm run build          # 生产构建，产物由 Flask 直接托管
```

后端同时托管 `admin/dist` 构建产物，健康检查端点为 `GET /api/health`。

## 核心接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/files/upload/check` | 秒传检查（提交 SHA-256 指纹） |
| POST | `/api/files/upload/init` | 初始化分片会话，返回已收分片（断点续传） |
| POST | `/api/files/upload/chunk` | 上传单个分片 |
| POST | `/api/files/upload/complete` | 合并分片，流式哈希去重落盘 |
| POST | `/api/ai-search` | 语义搜索（`query / withAnswer / topK`） |
| GET | `/api/ai-search/status` | 索引状态（文件数 / 分块数 / 向量模式） |
| POST | `/api/ai-search/reindex` | 重建语义索引（可传 `nodeId` 重建单个文件） |
| POST | `/api/ai-analysis/run` | 提交 AI 分析任务（文档 / 图片） |
| GET | `/api/ai-analysis` | 查询分析记录与结果 |

## 项目结构

```text
cloudflow/
├── admin/                        Vue 3 前端
│   └── src/
│       ├── api/uploader.js       智能上传（哈希 → 秒传 → 分片）
│       ├── api/aiSearch.js       语义搜索 API
│       └── views/user/           文件 / 智能搜索 / AI 分析等页面
└── backend/                      Flask 后端
    ├── config.py                 环境配置（.env 加载）
    ├── models/entities.py        ORM 模型（FileBlob / UploadSession / EmbeddingChunk …）
    ├── routes/                   REST 路由（files / ai_search / ai_analysis / auth …）
    └── services/
        ├── file_manager.py       内容寻址存储、秒传、引用计数
        ├── chunk_upload.py       分片上传会话管理
        ├── semantic_search.py    RAG：分块、向量化、检索、问答
        ├── ai_text_analysis.py   文档 / 图片多模态分析
        └── security.py           密码哈希、Fernet 加密
```

## 验证情况

以下链路均已通过端到端自动化测试（真实 Kimi API）：

- 登录鉴权（pbkdf2 哈希校验）与明文密码自动升级
- 秒传命中 / 未命中、分片上传合并、内容去重
- 语义检索召回（本地向量化模式，`embeddingMode: local`）
- RAG 问答：Kimi 基于检索片段生成带文件引用的准确答案
- 图片视觉分析：正确 OCR 图中文字并输出结构化描述
- 文档深度分析：生成结构化中文分析报告
- 无 Key 降级：检索照常工作，AI 功能返回友好提示
