import http from './http'

export const fetchUserDashboardApi = () => {
  return http.get('/user/dashboard')
}

export const fetchFavoritesApi = () => {
  return http.get('/user/favorites')
}

export const fetchUserProfileApi = () => {
  return http.get('/user/profile')
}
