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
