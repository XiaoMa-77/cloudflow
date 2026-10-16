import http from './http'
import axios from 'axios'

export const fetchWorkspaceApi = ({ folderId, keyword, sort } = {}) => {
  const params = {}
  if (folderId !== undefined && folderId !== null) {
    params.folderId = folderId
  }
  if (keyword) {
    params.keyword = keyword
  }
  if (sort) {
    params.sort = sort
  }
  return http.get('/files/workspace', { params })
}

export const renameNodeApi = (nodeId, name) => {
  return http.patch(`/files/nodes/${nodeId}/rename`, { name })
}

export const deleteNodeApi = (nodeId) => {
  return http.delete(`/files/nodes/${nodeId}`)
}

export const shareNodeApi = (nodeId, payload = {}) => {
  return http.post(`/files/nodes/${nodeId}/share`, payload)
}

export const pasteNodeApi = (payload) => {
  return http.post('/files/paste', payload)
}

export const toggleFavoriteApi = (nodeId) => {
  return http.post(`/files/nodes/${nodeId}/favorite`)
}

export const createFolderApi = (payload) => {
  return http.post('/files/folders', payload)
}

export const uploadFileApi = ({ file, parentId }) => {
  const formData = new FormData()
  formData.append('file', file)
  if (parentId !== undefined && parentId !== null) {
    formData.append('parentId', `${parentId}`)
  }
  return http.post('/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

// 秒传检查：客户端提供文件 SHA-256，命中内容指纹时服务端直接创建记录
export const checkInstantUploadApi = ({ fileName, fileSize, contentHash, parentId }) => {
  return http.post('/files/upload/check', {
    fileName,
    fileSize,
    contentHash,
    parentId: parentId === undefined || parentId === null ? null : parentId,
  })
}

// 初始化分片上传会话（返回已收分片索引，用于断点续传）
export const initChunkUploadApi = ({ fileName, fileSize, chunkSize, contentHash = '', parentId }) => {
  return http.post('/files/upload/init', {
    fileName,
    fileSize,
    chunkSize,
    contentHash,
    parentId: parentId === undefined || parentId === null ? null : parentId,
  })
}

// 上传单个分片
export const uploadChunkApi = ({ uploadId, chunkIndex, chunk }) => {
  const formData = new FormData()
  formData.append('uploadId', uploadId)
  formData.append('chunkIndex', `${chunkIndex}`)
  formData.append('chunk', chunk)
  return http.post('/files/upload/chunk', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 120000,
  })
}

// 合并分片完成上传
export const completeChunkUploadApi = ({ uploadId }) => {
  return http.post('/files/upload/complete', { uploadId })
}

export const batchDeleteNodesApi = (nodeIds) => {
  return http.post('/files/nodes/batch-delete', { nodeIds })
}

export const downloadNodeApi = async (nodeId) => {
  const sessionRaw = localStorage.getItem('auth_session')
  let token = ''
  try {
    token = JSON.parse(sessionRaw || '{}')?.token || ''
  } catch (error) {
    token = ''
  }

  const response = await axios.get(`/api/files/nodes/${nodeId}/download`, {
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  const disposition = response.headers['content-disposition'] || ''
  const match = disposition.match(/filename\\*=UTF-8''([^;]+)|filename=\"?([^\";]+)\"?/)
  const fileNameRaw = decodeURIComponent(match?.[1] || match?.[2] || `download-${nodeId}`)
  return {
    blob: response.data,
    fileName: fileNameRaw,
  }
}

export const previewNodeApi = async (nodeId) => {
  const sessionRaw = localStorage.getItem('auth_session')
  let token = ''
  try {
    token = JSON.parse(sessionRaw || '{}')?.token || ''
  } catch (error) {
    token = ''
  }

  const response = await axios.get(`/api/files/nodes/${nodeId}/preview`, {
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  return {
    blob: response.data,
    mimeType: response.headers['content-type'] || '',
  }
}
