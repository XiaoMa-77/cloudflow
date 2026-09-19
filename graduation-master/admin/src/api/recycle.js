import http from './http'

export const fetchRecycleListApi = ({ page = 1, pageSize = 200 } = {}) => {
  return http.get('/recycle', { params: { page, pageSize } })
}

export const restoreRecycleApi = (recycleId) => {
  return http.post(`/recycle/${recycleId}/restore`)
}

export const deleteRecycleApi = (recycleId) => {
  return http.delete(`/recycle/${recycleId}`)
}

export const batchRestoreRecycleApi = (recycleIds) => {
  return http.post('/recycle/batch-restore', { recycleIds })
}

export const clearRecycleApi = () => {
  return http.delete('/recycle/clear')
}
