import http from './http'

export const fetchAiRecordsApi = () => {
  return http.get('/ai-analysis')
}

export const runAiAnalysisApi = (nodeId) => {
  return http.post('/ai-analysis/run', { nodeId })
}
