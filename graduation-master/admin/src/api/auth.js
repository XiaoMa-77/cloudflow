import http from './http'

export const registerApi = (payload) => {
  return http.post('/auth/register', payload)
}

export const loginApi = (payload) => {
  return http.post('/auth/login', payload)
}

export const fetchMeApi = () => {
  return http.get('/auth/me')
}

export const logoutApi = () => {
  return http.post('/auth/logout')
}

export const changePasswordApi = (payload) => {
  return http.patch('/auth/password', payload)
}
