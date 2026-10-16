import { createRouter, createWebHashHistory } from 'vue-router'
import { useAppStore } from '@/stores/app'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: () => import('@/views/user/LoginView.vue') },
  { path: '/register', component: () => import('@/views/user/RegisterView.vue') },
  { path: '/user/home', component: () => import('@/views/user/HomeView.vue'), meta: { role: 'USER' } },
  { path: '/user/files', component: () => import('@/views/user/FilesView.vue'), meta: { role: 'USER' } },
  { path: '/user/files/folder/:id', component: () => import('@/views/user/FilesView.vue'), meta: { role: 'USER' } },
  { path: '/user/share', component: () => import('@/views/user/SharesView.vue'), meta: { role: 'USER' } },
  { path: '/user/shares', redirect: '/user/share' },
  { path: '/user/favorites', component: () => import('@/views/user/FavoritesView.vue'), meta: { role: 'USER' } },
  { path: '/user/recycle', component: () => import('@/views/user/RecycleView.vue'), meta: { role: 'USER' } },
  { path: '/user/ai-analysis', component: () => import('@/views/user/AiAnalysisView.vue'), meta: { role: 'USER' } },
  { path: '/user/smart-search', component: () => import('@/views/user/SmartSearchView.vue'), meta: { role: 'USER' } },
  { path: '/user/todo', component: () => import('@/views/user/TodoView.vue'), meta: { role: 'USER' } },
  { path: '/user/long-term-tasks', component: () => import('@/views/user/LongTermTaskView.vue'), meta: { role: 'USER' } },
  { path: '/user/passwords', component: () => import('@/views/user/PasswordBookView.vue'), meta: { role: 'USER' } },
  { path: '/user/profile', component: () => import('@/views/user/ProfileView.vue'), meta: { role: 'USER' } },
  { path: '/admin/home', component: () => import('@/views/admin/HomeView.vue'), meta: { role: 'ADMIN' } },
  { path: '/admin/users', component: () => import('@/views/admin/UsersView.vue'), meta: { role: 'ADMIN' } },
  { path: '/admin/storage', component: () => import('@/views/admin/StorageView.vue'), meta: { role: 'ADMIN' } },

  { path: '/admin/admins', component: () => import('@/views/admin/AdminsView.vue'), meta: { role: 'ADMIN' } },
  { path: '/admin/profile', component: () => import('@/views/admin/ProfileView.vue'), meta: { role: 'ADMIN' } },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const appStore = useAppStore()
  appStore.hydrateFromStorage()

  if (to.path === '/login' || to.path === '/register') {
    if (appStore.token && appStore.role) {
      return appStore.role === 'ADMIN' ? '/admin/home' : '/user/home'
    }
    return true
  }

  if (!appStore.token || !appStore.role) {
    return '/login'
  }

  try {
    await appStore.restoreSession()
  } catch (error) {
    return '/login'
  }

  if (to.meta?.role && to.meta.role !== appStore.role) {
    return appStore.role === 'ADMIN' ? '/admin/home' : '/user/home'
  }

  if (to.path === '/admin/admins' && appStore.role === 'ADMIN' && appStore.user?.account !== 'admin') {
    return '/admin/home'
  }

  return true
})

export default router
