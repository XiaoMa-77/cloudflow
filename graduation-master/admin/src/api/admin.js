import http from './http'

export const fetchAdminOverviewApi = () => {
  return http.get('/admin/overview')
}

export const fetchAdminUsersApi = () => {
  return http.get('/admin/users')
}

export const updateAdminUserStatusApi = (userId, status) => {
  return http.patch(`/admin/users/${userId}/status`, { status })
}

export const updateAdminUserStorageApi = (userId, spaceLimitBytes) => {
  return http.patch(`/admin/users/${userId}/storage-limit`, { spaceLimitBytes })
}

export const deleteAdminUserApi = (userId) => {
  return http.delete(`/admin/users/${userId}`)
}

export const fetchAdminsApi = () => {
  return http.get('/admin/admins')
}

export const createAdminApi = (payload) => {
  return http.post('/admin/admins', payload)
}

export const deleteAdminApi = (adminId) => {
  return http.delete(`/admin/admins/${adminId}`)
}

export const updateAdminPasswordApi = (adminId, newPassword) => {
  return http.patch(`/admin/admins/${adminId}/password`, { newPassword })
}

export const fetchAdminProfileApi = () => {
  return http.get('/admin/profile')
}
