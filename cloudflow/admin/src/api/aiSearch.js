import http from './http'

// 语义搜索：返回相关文件片段，可选生成 RAG 问答答案
export const semanticSearchApi = ({ query, withAnswer = false, topK = 8 }) => {
  return http.post('/ai-search', { query, withAnswer, topK })
}

// 语义索引概览（已索引文件数 / 分块数）
export const fetchSearchIndexStatusApi = () => {
  return http.get('/ai-search/status')
}

// 重建语义索引：传 nodeId 重建单个文件，不传则全量重建（文档类）
export const reindexSearchApi = ({ nodeId } = {}) => {
  return http.post('/ai-search/reindex', nodeId ? { nodeId } : {})
}
