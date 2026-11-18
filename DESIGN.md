# 📐 CloudFlow · 设计文档

> 版本：v0.1 · 更新：2026-11-18
> 本文描述 `cloudflow` 的设计背景、架构、接口、数据流与边界/异常场景。
> 事实性内容（接口、字段、常量、流程）均以本仓库实际代码为准，关键实现标注到 `文件:行号` 便于核对；
> 无法从仓库内代码确认的部分统一在文末「假设与待确认」中显式列出。

---

## 1. 背景与目标

### 1.1 问题

个人与团队在网盘中累积的文档/图片 rapidly 增长，传统网盘有三类痛点：

1. **存储浪费**：同一份文件多人、多次重复上传，占用多份空间，上传耗时；
2. **找得到文件名、找不到内容**：只能按文件名检索，无法用自然语言描述定位文档，更无法直接得到答案；
3. **内容不可读**：PDF / Office / 图片里的信息无法被系统理解与复用，需要人工逐份翻阅。

### 1.2 目标

- **去重秒传与断点续传**：SHA-256 内容寻址，相同内容只落一份物理文件；大文件分片上传、网络中断可续传。
- **语义检索与 RAG 问答**：文档分块向量化后支持自然语言检索，并可基于检索片段生成带引用的答案。
- **多模态 AI 分析**：文档结构化解析 + 图片视觉理解（含 OCR），分析结果自动回灌语义索引。
- **完整网盘能力**：用户/管理员体系、文件夹树、收藏、分享、回收站、待办、长期任务、密码本。
- **可验证**：核心逻辑（去重、分片、鉴权边界等）有离线自动化测试守门。

### 1.3 非目标

- 不实现文件实时协同编辑、不承诺第三方 AI 模型 100% 可用；
- 不内置分布式存储/对象存储，物理块落在本地 `uploads/blobs/`（见「待确认」的部署形态）。

---

## 2. 总体架构

系统为「Vue 3 SPA 前端 + Flask 单体后端 + SQLite/本地块存储 + 外部 AI 服务」的分层结构：

```
┌────────────────────────── 前端 · Vue 3 SPA (admin/) ──────────────────────────┐
│  路由/页面(views)  │  api/ 封装(axios)  │  stores/app(Pinia)  │  uploader.js  │
│  文件/搜索/AI分析/密码本/管理端        │  Bearer 令牌        │  SHA-256/分片 │
└──────────────────────────────┬────────────────────────────────────────────────┘
                               │ HTTP /api/*（开发期 Vite 5173 → 后端 8080 代理）
                               v
┌────────────────────────── 后端 · Flask (backend/) ───────────────────────────┐
│  app.py 应用入口 / 静态托管 dist                                             │
│  routes/  认证·文件·分享·回收站·AI分析·AI搜索·用户门户·管理端                │
│  utils/   auth(Bearer 鉴权) · response(统一封装)                             │
│  services/ file_manager·chunk_upload·semantic_search·ai_text_analysis        │
│            security·user_portal·recycle_service·ai_task_queue·admin_service  │
│  models/   17 张 SQLAlchemy 实体                                             │
└───────┬───────────────────────────┬──────────────────────────┬────────────────┘
        │ 读写                       │ 异步分析                 │ 向量/对话/视觉
        v                           v                          v
┌──────────────────┐      ┌────────────────────┐    ┌──────────────────────────┐
│ SQLite 元数据     │      │ AI 任务队列         │    │ 外部 AI 服务（可缺省）    │
│ instance/*.db    │      │ Queue+daemon Thread │    │ Kimi/Moonshot 对话+视觉   │
│ 文件树/blob 索引  │      │ 单worker串行消费     │    │ OpenAI兼容/MiniMax 向量化 │
│ 向量/会话/审计    │      │                     │    │ 未配置→本地 n-gram 兜底   │
└──────────────────┘      └────────────────────┘    └──────────────────────────┘
        │
        v
┌────────────────────────────────────────────┐
│ 本地块存储 uploads/                        │
│  blobs/<hash前2位>/<hash>  内容寻址物理文件 │
│  .chunks/<token>/<i>.part  分片临时文件     │
└────────────────────────────────────────────┘
```

说明：
- 后端是单体 Flask 应用，`create_app()` 完成 DB 初始化、CORS、蓝图注册、AI worker 启动，并托管前端 `admin/dist`（`backend/app.py:16-54`）。
- 鉴权请求头支持 `Authorization: Bearer <token>` 与 `X-Auth-Token`（`backend/utils/auth.py:9-13`）。
- `MAX_CONTENT_LENGTH` 为 512MB（`backend/config.py:35`）；分片上传单文件上限 2GB（`backend/services/chunk_upload.py:33`）。

### 2.1 模块职责表

| 模块 | 文件 | 职责 |
|---|---|---|
| 应用入口 | `backend/app.py` | 组装应用、托管前端静态产物、`/api/health`、前端兜底路由 |
| 配置 | `backend/config.py` | 加载 `backend/.env`，集中定义 DB/AI/向量/分片/加密配置 |
| 扩展 | `backend/extensions.py` | 全局 `db`（Flask-SQLAlchemy）与 `cors` |
| 鉴权工具 | `backend/utils/auth.py` | 令牌提取、`get_current_identity`、`login_required(role)` 装饰器 |
| 响应封装 | `backend/utils/response.py` | `success` / `list_success` / `error`（业务 `code` 与 HTTP 状态对齐） |
| 路由层 | `backend/routes/*.py` | 认证 / 文件 / 分享 / 公开分享 / 回收站 / AI 分析 / AI 搜索 / 用户门户 / 管理端 |
| 文件管理 | `backend/services/file_manager.py` | 文件夹树、内容寻址落盘、去重、秒传、分享创建、删除入回收站、复制/移动、预览/下载 |
| 分片上传 | `backend/services/chunk_upload.py` | 会话创建/复用、分片落盘、合并校验、流式 SHA-256、去重、配额复查 |
| 语义检索 | `backend/services/semantic_search.py` | 分块、向量化（本地/远程）、Top-K 检索、RAG 问答、索引状态 |
| AI 文本分析 | `backend/services/ai_text_analysis.py` | 多格式文本抽取 + 文档/图片模型调用与提示词 |
| 安全 | `backend/services/security.py` | pbkdf2 口令哈希、历史明文校验、Fernet 密码本加解密 |
| 用户门户 | `backend/services/user_portal.py` | 工作台、收藏、AI 记录、分析任务处理、存储重算、活动记录 |
| 回收站 | `backend/services/recycle_service.py` | 恢复、彻底删除、批量恢复、清空，引用释放 |
| AI 任务队列 | `backend/services/ai_task_queue.py` | 内存 Queue + daemon 线程串行消费分析任务 |
| 管理端服务 | `backend/services/admin_service.py` | 用户/管理员管理、配额与状态、概览统计 |
| 数据初始化 | `backend/services/data_initializer.py` | 建表、轻量 schema 补丁、明文口令升级、演示数据播种 |
| 前端 SPA | `admin/src/` | Vue 3 页面 + api 封装 + Pinia store + 智能上传器 |

### 2.2 技术栈（取自实际依赖）

| 层 | 技术 |
|---|---|
| 后端 | Python 3.10+ / Flask ≥3.0 / Flask-SQLAlchemy ≥3.1 / SQLite / Werkzeug / numpy / cryptography（`backend/requirements.txt`） |
| 前端 | Vue 3 / Vite 7 / Element Plus / Pinia / vue-router(hash 模式) / axios（`admin/package.json`） |
| AI 服务 | Kimi/Moonshot `kimi-k2.6`（对话 + 视觉，默认）；向量化 OpenAI 兼容或 MiniMax `embo-01`，未配置时用本地 n-gram |
| 安全 | `pbkdf2:sha256`（werkzeug）/ Fernet（cryptography） |

---

## 3. 数据模型

核心实体（`backend/models/entities.py`），按职责分组：

| 实体 | 关键字段 | 说明 |
|---|---|---|
| `User` / `AdminUser` | username, password, status, used_space_bytes, space_limit_bytes | 用户/管理员账号；口令 pbkdf2 哈希 |
| `AuthSession` | token, role(USER/ADMIN), user_id / admin_user_id | 登录令牌与角色绑定 |
| `FileNode` | user_id, parent_id, node_type, name, extension, storage_rel_path, content_hash | 文件夹树节点（自关联 parent_id），文件本体 |
| `FileBlob` | content_hash(**unique**), size_bytes, storage_rel_path, ref_count | 内容指纹表，去重/秒传的核心 |
| `UploadSession` | upload_token, total_bytes/chunks, received_chunks, status | 分片会话，支撑断点续传 |
| `EmbeddingChunk` | user_id, file_node_id, chunk_index, embedding(BLOB), dim, model | 语义索引分块；`model` 用于向量来源隔离 |
| `RecycleRecord` | storage_rel_path, content_hash, remaining_days(30) | 软删除记录，恢复/彻底删除依据 |
| `ShareRecord` | share_url, access_mode, status(生效中/已取消), expires_at, visit_count | 分享链接 |
| `AiAnalysisRecord` | file_node_id, summary, status(分析中/已完成/失败) | AI 分析任务与结果 |
| `FavoriteRecord` / `ActivityRecord` | user_id, file_node_id / action | 收藏与审计（活动记录每用户保留最近 200 条，`user_portal.py:23-32`） |
| `FileRecord` | file_name, file_type, folder_name, is_deleted | 旧版扁平文件列表（`/api/files` 使用，见「待确认」） |
| `TodoItem` / `LongTermTask` / `PasswordEntry` | user_id, ... | 待办 / 长期任务 / 密码本（密码字段 Fernet 加密） |

要点：
- `FileBlob.content_hash` 唯一约束 + `ref_count` 是去重的语义核心（`entities.py:71-82`）。
- `EmbeddingChunk.model` 记录向量来源；检索时只比较同来源索引，实现切换向量服务后的自动隔离（`semantic_search.py:202-208`）。

---

## 4. 接口设计

统一响应：`{code, message, data}`；`code=200` 为成功，失败时 `code` 与 HTTP 状态码一致（`utils/response.py`）。前端 axios 拦截器对 `code==200` 自动解包 `data`，否则抛出带 `code` 的错误（`admin/src/api/http.js:28-44`）。

### 4.1 认证与鉴权

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/auth/captcha` | 无 | 生成 4 位图形验证码，明文存入 Flask session；Pillow 不可用时退化为文本验证码（`routes/auth.py:94-104`） |
| POST | `/api/auth/register` | 无 | 账号 3–32 位、密码 ≥6 位，排除与管理员重名（`auth.py:107-140`） |
| POST | `/api/auth/login` | 无 | 校验验证码 + 口令，签发 24 字节 urlsafe token；历史明文口令登录成功后升级为哈希（`auth.py:143-209`） |
| GET | `/api/auth/me` | 登录 | 返回当前身份 |
| POST | `/api/auth/logout` | 登录 | 删除 AuthSession |
| PATCH | `/api/auth/password` | 登录 | 修改口令（校验原口令） |

- `login_required(role)` 未登录返回 401，角色不符返回 403（`utils/auth.py:55-71`）。
- 管理端「管理员管理」额外要求账号名为 `admin`（超级管理员），否则 403（`routes/admin.py:22-25`）。

### 4.2 文件与上传

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/files` | 旧版文件列表（FileRecord），支持 keyword/type/sort/分页（`routes/files.py:40-73`） |
| GET | `/api/files/workspace` | 文件夹树目录内容，返回 currentFolder/breadcrumbs/items（`files.py:76-88`） |
| POST | `/api/files/folders` | 新建文件夹，同级重名 409 |
| PATCH | `/api/files/nodes/<id>/rename` | 重命名；根目录禁止 |
| DELETE | `/api/files/nodes/<id>` | 删除（软删除到回收站） |
| POST | `/api/files/nodes/batch-delete` | 批量删除 |
| POST | `/api/files/paste` | 复制/移动（mode=copy/move），含子树与防环校验 |
| POST | `/api/files/nodes/<id>/favorite` | 收藏/取消收藏 |
| POST | `/api/files/upload` | 整文件上传（小文件直传路径） |
| POST | `/api/files/upload/check` | 秒传检测（SHA-256 命中直接建记录） |
| POST | `/api/files/upload/init` | 初始化/复用分片会话，返回已收分片索引 |
| POST | `/api/files/upload/chunk` | 上传单个分片（multipart：uploadId/chunkIndex/chunk） |
| POST | `/api/files/upload/complete` | 合并分片 + 流式 SHA-256 去重 + 建节点 |
| GET | `/api/files/nodes/<id>/download` | 下载（物理文件缺失时生成说明文本兜底，`file_manager.py:347-368`） |
| GET | `/api/files/nodes/<id>/preview` | 图片/视频在线预览，不支持类型 409 |

### 4.3 分享与回收站

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/files/nodes/<id>/share` | 创建分享，有效期 1–30 天，生成 `/share/u{uid}-n{nid}-{ts}`（`file_manager.py:490-523`） |
| GET | `/api/shares` | 我的分享列表（分页） |
| PATCH | `/api/shares/<id>/cancel` | 取消分享（幂等） |
| POST | `/api/shares/batch-cancel` | 批量取消（仅本人记录） |
| DELETE | `/api/shares/<id>` | 删除分享记录 |
| GET | `/share/<token>` | 公开下载：解析 token → 校验状态/过期/归属/文件存在 → 计数 +1（`routes/share_public.py:25-64`） |
| GET | `/api/recycle` | 回收站列表（分页） |
| POST | `/api/recycle/<id>/restore` | 恢复到根目录，重名加 `-恢复N` 后缀 |
| POST | `/api/recycle/batch-restore` | 批量恢复 |
| DELETE | `/api/recycle/<id>` | 彻底删除（无其他引用时才释放物理文件） |
| DELETE | `/api/recycle/clear` | 清空回收站 |

### 4.4 AI 分析 / 语义搜索 / 用户 / 管理端

| 分组 | 主要接口 | 说明 |
|---|---|---|
| AI 分析 | `GET /api/ai-analysis`、`POST /api/ai-analysis/run` | 提交分析任务入队（异步），返回「分析中」记录（`routes/ai_analysis.py`） |
| AI 搜索 | `POST /api/ai-search`、`GET /api/ai-search/status`、`POST /api/ai-search/reindex` | 语义检索（topK 1–20）、可选 RAG 问答、索引状态、单文件/全量重建（`routes/ai_search.py`） |
| 用户门户 | `/api/user/dashboard`、`/favorites`、`/profile`、`/todos`、`/long-term-tasks`、`/passwords` | 工作台、收藏、待办/长期任务/密码本 CRUD（`routes/user.py`） |
| 管理端 | `/api/admin/overview`、`/users`、`/users/<id>/status`、`/users/<id>/storage-limit`、`/admins` 等 | 用户/管理员管理、配额与状态、统计（`routes/admin.py`） |
| 系统 | `GET /api/health` | 健康检查，返回 `{service: 'cloudflow'}`（`app.py:31-33`） |

---

## 5. 数据流

### 5.1 上传 → 内容寻址 → 去重（`uploader.js` + `file_manager` + `chunk_upload`）

```
前端 smartUploadFile(file):
  1) file.size ≤ 64MB 且浏览器支持 → Web Crypto 计算整文件 SHA-256
  2) POST /upload/check（fileName/fileSize/contentHash）
     ├─ 命中(FileBlob 存在 + 物理文件在 + 配额够) → 秒传：ref_count+1，直接建节点，结束
     └─ 未命中 ↓
  3) file.size ≤ 8MB → POST /upload 整文件直传
     └─ _store_blob_from_bytes：sha256 → 命中复用/新建 blobs/<xx>/<hash>，ref_count+1
  4) 否则 → 分片：
     init → 逐个 POST /chunk（失败重试 3 次，退避 600ms×n）→ complete
     └─ 合并流式 sha256 → 去重复用或 _promote_merged_file → 建节点 → 删会话
  进度阶段：hashing → instant | uploading → merging → done
```

要点：
- 客户端仅对 ≤64MB 文件计算整文件哈希；更大文件跳过秒传，由服务端合并后去重（`admin/src/api/uploader.js:9-11,17-30`）。
- 分片大小默认 4MB，服务端接受范围 256KB–16MB，单文件上限 2GB（`chunk_upload.py:31-33,48-53`）。
- 去重判定同时检查 `FileBlob` 记录与物理文件是否存在，避免“有记录无文件”的假命中（`file_manager.py:274-279`、`chunk_upload.py:162-169`）。

### 5.2 断点续传

```
init(user, fileName, fileSize, chunkSize, totalChunks, parentId)
  → 查同用户 + 同名 + 同大小的 UPLOADING 会话
  → 复用则返回 {uploadId, chunkSize, totalChunks, uploadedChunks:[已收索引]}
  → 否则新建会话
前端仅上传 uploadedChunks 中缺失的片
complete:
  → received 数 == total_chunks？否则 409「缺少 N 片」
  → 顺序合并 .part（缺片 409）→ 流式 sha256 → 校验 merged_size==total_bytes
  → 去重 → 配额复查 → 建节点 → 会话置 COMPLETED 并删除
```

`received_chunks` 以逗号分隔的整数存储，`_parse_received` 去重、排序并容忍脏数据（`chunk_upload.py:245-253`）。

### 5.3 索引 → 检索 → RAG 问答

```
AI 分析完成 / reindex:
  → extract_analysis_text(按扩展名分发抽取，截断 AI_MAX_INPUT_CHARS=12000)
  → index_file_text:
       删除该 node 旧分块 → chunk_text(700 字 / 80 重叠，按段落聚合)
       → embed_texts(chunks, kind='db')
          ├─ 配了 EMBEDDING_* → OpenAI兼容/MiniMax 远程向量（MiniMax 区分 db/query）
          └─ 未配置 → 本地 n-gram 特征哈希(512 维, local:ngram-v1)
       → 写入 EmbeddingChunk(embedding=float32 bytes, model=来源ID)

POST /api/ai-search(query, withAnswer, topK):
  → semantic_search:
       取同 model 的全部分块 → 查询向量(kind='query') → 余弦相似度
       → 按文件聚合(每文件仅保留最相关片段) → Top-K
  → withAnswer 且有结果 → rag_answer(上下文≤6000字, 生成带引用答案；失败不影响检索结果)
```

- 向量来源标识：远程为 `api:<模型名>`，本地为 `local:ngram-v1`（`semantic_search.py:39-44`）。
- RAG 问答要求配置 `MOONSHOT_API_KEY`（503 提示），429 限流等待 10s 重试一次（`semantic_search.py:260-316`）。

### 5.4 AI 分析任务（异步）

```
POST /api/ai-analysis/run(nodeId)
  → run_ai_analysis: 校验节点归属/类型 → 写 AiAnalysisRecord(status='分析中')
  → enqueue_ai_task(record_id) → 内存 Queue
daemon worker(_worker_loop):
  → process_ai_analysis_task:
       图片 → analyze_image_file(base64 data URI, ≤10MB, 视觉模型含 OCR)
       文档 → extract_analysis_text → analyze_document_text(结构化报告)
       成功 → status='已完成' + summary，并尝试 index_file_text(失败不影响分析)
       FileManagerError/其他异常 → status='失败' + 摘要，记录活动
  → 异常不会终止 worker（ai_task_queue.py:34-36）
```

### 5.5 删除 / 恢复 / 引用释放

```
delete_node:
  收集子树 → 文件写入 RecycleRecord(remaining_days=30)
  → 删除对应 FavoriteRecord / EmbeddingChunk / FileNode
  → 重算存储 + 活动记录
restore:  RecycleRecord → 根目录 FileNode（重名 -恢复N），删回收站记录
彻底删除/清空: 先删记录再 release_storage_reference
  → 仅当无 FileNode / RecycleRecord 引用同一 storage_rel_path 时才删除物理文件与 FileBlob
```

---

## 6. 边界与异常场景

| # | 场景 | 处理策略（依据代码） |
|---|---|---|
| 1 | 重复文件（同内容不同名） | `_store_blob_from_bytes` / 合并路径命中 `content_hash` 且物理文件存在 → 复用、仅 `ref_count+1`，不新增物理文件（`file_manager.py:269-298`） |
| 2 | 秒传指纹合法但无记录 / 文件被外部删除 | `check_instant_upload` 校验 hash 长度=64、`FileBlob` 与物理文件均存在，否则 `instant=False` 回退正常上传（`file_manager.py:223-266`） |
| 3 | 分块中断后续传 | `init` 复用同名同大小 UPLOADING 会话，`uploadedChunks` 告知已收索引，前端跳过（`chunk_upload.py:66-98`） |
| 4 | 分片不完整就合并 | received 数不足 → 409「缺少 N 片」；合并时缺 `.part` → 409；合并后大小不符 → 会话置 FAILED 并清理（`chunk_upload.py:126-157`） |
| 5 | 分片大小/文件过大 | 分片需 256KB–16MB（400），单文件 >2GB（400），整请求 >512MB 由 Flask 413（`chunk_upload.py:31,48-51`） |
| 6 | 存储配额不足 | 上传整文件/init/complete 三处校验 `used+size > limit` → 409；complete 复查后失败置 FAILED（`file_manager.py:198-199`、`chunk_upload.py:63-64,184-188`） |
| 7 | 越权访问他人文件 | `_get_user_node` 按 `user_id+id` 查询，命中不到一律 404，不泄漏存在性（`file_manager.py:670-674`） |
| 8 | 角色不符 / 未登录 | `login_required(role)`：无令牌 401，角色不符 403（`utils/auth.py:55-71`） |
| 9 | 非 admin 访问管理员管理 | `_require_super_admin` 账号名非 `admin` → 403（`routes/admin.py:22-25`） |
| 10 | 公开分享非法/失效 token | token 正则不符 404；`status≠生效中` / 已过期 / 归属不符 / 文件不存在均返回对应 4xx（`share_public.py:25-64`） |
| 11 | 分享有效期参数非法 | 非数字 → 400；不在 1–30 天 → 400（`files.py:114-133`、`file_manager.py:492-493`） |
| 12 | 软删除恢复 | 删除写入 RecycleRecord 并清索引/收藏；恢复回根目录，重名 `-恢复N`；物理文件在“无任何引用”时才释放（`recycle_service.py`） |
| 13 | AI 服务未配置 / 调用失败 | 未配置 key 抛 503；429 限流等待 10s 重试一次；分析任务失败落 `status='失败'` 摘要，不中断 worker（`ai_text_analysis.py:86-100`、`user_portal.py:177-231`） |
| 14 | 图片过大 | >10MB 图片拒绝视觉分析（409）（`ai_text_analysis.py:31,204-205`） |
| 15 | 文件无法提取文本 | 规范化后文本 <10 字 → 409；PDF/Office 解析失败按类型给提示（`ai_text_analysis.py:77-83`） |
| 16 | RAG 问答失败 | `rag_answer` 异常被吞掉，仍返回检索结果、`answer=''`（`routes/ai_search.py:42-47`） |
| 17 | 向量来源切换 | 旧索引 `model` 不匹配新来源 → 检索自动忽略；前端“重建索引”迁移（`semantic_search.py:202-208`） |
| 18 | 物理文件缺失 | 下载生成说明文本兜底（`file_manager.py:362-368`）；预览/分享/AI 分析返回 404 提示重新上传 |
| 19 | 根目录操作 | 根目录禁止重命名/删除、禁止移动（`file_manager.py:419-420,443-444,538-539`） |
| 20 | 循环/自移动 | 移动到自身或子目录 → 409（`file_manager.py:540-546`） |
| 21 | 密码本无密钥/密钥轮换 | 无密钥降级明文存取；旧密文解不开返回空串（fail-closed），不泄露密文（`security.py:56-77`） |
| 22 | 数据库并发建表 | `create_all` 遇到 `already exists` 重试最多 3 次（`data_initializer.py:12-21`） |

---

## 7. 安全与隐私

- **口令**：`pbkdf2:sha256` 哈希（`security.py:22-23`）；历史明文登录成功后自动升级（`auth.py:173-176`、初始化时批量升级）。
- **会话**：令牌为 `secrets.token_urlsafe(24)`，存于 `AuthSession`；登出即删除。前端存 `localStorage` 的 `auth_session`（`admin/src/api/http.js:3-25`）。
- **密钥隔离**：AI / 向量 / Fernet 密钥仅从环境变量或 `backend/.env` 读取，`.env` 已 `.gitignore`；源码无硬编码业务密钥。
- **密码本**：Fernet 静态加密，密文带 `enc:v1:` 前缀；无密钥降级明文（演示环境）、解密失败 fail-closed。
- **越权防护**：所有资源查询带 `user_id` 过滤；管理端角色与超级管理员双重校验。
- **CORS**：当前对 `/api/*` 放开 `origins='*'`（`app.py:24`）——见「待确认」的公网部署风险。

---

## 8. 测试策略

所有测试离线运行，使用 Flask `test_client` + 临时 SQLite + 临时上传目录，网络/AI/真实外部服务均不参与（`backend/tests/conftest.py`）。

| 层次 | 文件 | 覆盖 |
|---|---|---|
| API 冒烟 | `tests/test_api_smoke.py` | 健康检查、未知 API 404、未登录拦截、演示账号口令可验证 |
| 分片上传 | `tests/test_chunk_upload.py` | 合并建 Blob/节点、SHA-256 去重与引用计数、分片不完整拒绝、断点续传会话复用、超大文件拒绝、`_parse_received` 归一化 |
| 安全 | `tests/test_security.py` | 口令哈希 roundtrip、历史明文兼容、密码本加解密 roundtrip、无密钥降级、坏密钥 fail-closed |
| 补充集成 | `tests/test_file_dedup_and_permissions.py` | 整文件直传去重、秒传命中/未命中、跨用户越权、角色隔离、超级管理员限制、无令牌拒绝、公开分享校验（非法/取消/过期）、软删除恢复 roundtrip |
| CI | `.github/workflows/ci.yml` | push(master)/PR：后端全量语法检查 + pytest + 应用可导入；前端 `npm ci` + 生产构建 |

运行方式（详见根 README）：

```bash
cd cloudflow/backend
pip install -r requirements.txt pytest
python -m pytest tests -q
```

前端当前无测试框架（`admin/package.json` 无 `test` 脚本），本轮不强行引入；其正确性由生产构建与后端集成测试间接守门。

---

## 9. 假设与待确认

以下内容无法仅凭仓库内代码确认，或属于当前实现的有意简化，标注为假设/待确认：

1. **`FileRecord` 与 `FileNode` 双轨**：`/api/files` 使用旧版扁平 `FileRecord`，`workspace` 使用树形 `FileNode`；两者是否计划统一、演示数据是否为唯一来源，待确认（`data_initializer.py` 同时播种两者）。
2. **AI 模型名与可用性**：`kimi-k2.6`、`embo-01` 及 `AI_BASE_URL` 默认值来自 README/配置，实际以开放平台账户可用模型与配额为准；仓库内无法验证。
3. **向量服务协议**：MiniMax 走 `texts/type` 原生协议、OpenAI 兼容走 `input`，为代码事实；具体服务的向量维度/计费/限流以服务商为准。
4. **分享 `access_mode`**：种子数据含「提取码 7F2K」等，但公开下载路由仅校验 token 状态/过期/归属，**未实现提取码校验**；提取码是待实现功能还是已放弃的设计，待确认。
5. **分享 token 中的时间戳**：token 形如 `u{uid}-n{nid}-{ts}`，`_parse_token` 只解析 uid/nid 与 ts 格式，过期判断以 `ShareRecord.expires_at` 为准，ts 本身未参与校验——属于实现简化。
6. **CORS 与部署形态**：`origins='*'` + Bearer 令牌存 localStorage，公网部署存在令牌泄露/CSRF 风险；是否置于内网或加白名单/HttpOnly Cookie，待确认。
7. **默认密钥**：`SECRET_KEY` 默认 `2026030303-dev-secret`、DB 文件名 `2026030303.db` 为开发默认值；生产应通过 `.env` 覆盖，仓库内无生产配置。
8. **回收站自动清理**：`RecycleRecord.remaining_days=30` 为字段默认值，但未检索到按 `deleted_at + remaining_days` 定时物理清理的任务；30 天到期自动清除是待实现还是人工处理，待确认。
9. **AI 任务队列持久化**：队列为进程内 `Queue`，重启后未完成任务丢失；单机单 worker 是明确设计，多实例部署需外部队列，待确认。
10. **测试覆盖范围**：本轮补齐的是与需求直接相关、可离线运行的核心边界；语义检索/RAG 问答的完整单元测试与前端组件测试仍未覆盖（前者可通过 mock `requests` 补充，后者需引入测试框架，本轮未引入）。
