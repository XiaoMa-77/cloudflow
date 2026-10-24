# 更新日志

本项目的显著变更记录于此，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-10-24

初始公开版本。

### 功能

- 文件管理：SHA-256 内容寻址存储、去重秒传、大文件分片上传与断点续传、分享、回收站、待办
- 语义检索：文档向量化入索引，自然语言检索（向量来源隔离与重建迁移）
- RAG 问答：基于检索片段生成带引用文件名的答案
- 多模态 AI 分析：文档深度解析（PDF/Office）+ 图片 OCR 与场景描述，结果回灌语义索引
- 安全：口令哈希升级、密码本加解密、密钥零硬编码

### 工程

- 前端 Vue 3 + Element Plus + Vite，后端 Flask + SQLAlchemy + SQLite
- CI（GitHub Actions）：后端依赖可安装、应用可导入、全量语法检查；前端生产构建
- MIT 许可证；`.idea/` 等本地 IDE 配置移出版本库
