import axios from 'axios'

const SESSION_KEY = 'auth_session'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const raw = localStorage.getItem(SESSION_KEY)
  if (!raw) {
    return config
  }

  try {
    const session = JSON.parse(raw)
    if (session?.token) {
      config.headers.Authorization = `Bearer ${session.token}`
    }
  } catch (error) {
    // Ignore malformed session data.
  }

  return config
})

http.interceptors.response.use(
  (response) => {
    const payload = response.data

    if (payload && typeof payload === 'object' && Object.hasOwn(payload, 'code')) {
      if (payload.code === 200) {
        return payload.data
      }

      const businessError = new Error(payload.message || '请求失败')
      businessError.code = payload.code
      businessError.payload = payload.data
      throw businessError
    }

    return payload
  },
  (axiosError) => {
    const responseData = axiosError?.response?.data
    if (responseData && typeof responseData === 'object') {
      const requestError = new Error(responseData.message || '请求失败')
      requestError.code = responseData.code || axiosError.response?.status
      requestError.payload = responseData.data
      throw requestError
    }

    if (axiosError?.code === 'ECONNABORTED') {
      throw new Error('请求超时，请稍后重试')
    }

    throw new Error('网络异常，请检查服务是否可用')
  },
)

export default http
