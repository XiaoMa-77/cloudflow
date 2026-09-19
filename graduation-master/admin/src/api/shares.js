import http from './http'

export const fetchShareListApi = ({ page = 1, pageSize = 200 } = {}) => {
  return http.get('/shares', { params: { page, pageSize } })
}

export const cancelShareApi = (shareId) => {
  return http.patch(`/shares/${shareId}/cancel`)
}

export const batchCancelShareApi = (shareIds) => {
  return http.post('/shares/batch-cancel', { shareIds })
}

export const deleteShareApi = (shareId) => {
  return http.delete(`/shares/${shareId}`)
}
