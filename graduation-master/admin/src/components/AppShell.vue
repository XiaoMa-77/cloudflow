<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">☁</div>
        <div>
          <div class="brand-title">智能云盘系统</div>
          <div class="brand-subtitle">{{ subtitle }}</div>
        </div>
      </div>
      <div class="nav-group">
        <router-link 
          v-for="(item, index) in visibleItems" 
          :key="item.path" 
          :to="item.path" 
          class="nav-item"
          :style="{ animationDelay: `${index * 0.1}s` }"
        >
          <span class="nav-item-icon">{{ getItemIcon(item.label) }}</span>
          <span class="nav-item-text">{{ item.label }}</span>
          <span class="nav-item-indicator"></span>
        </router-link>
      </div>
      <div class="user-info">
        <div class="user-avatar">
          {{ getUserInitials() }}
        </div>
        <div class="user-details">
          <div class="user-name">{{ appStore.user?.username || '用户' }}</div>
          <div class="user-role">{{ appStore.role === 'ADMIN' ? '管理员' : '用户' }}</div>
        </div>
        <button type="button" class="logout-btn" @click="handleLogout">
          <span class="logout-icon">↪</span>
        </button>
      </div>
    </aside>
    <main class="content">
      <header class="header">
        <div class="header-content">
          <h1 class="header-title">{{ title }}</h1>
          <p class="header-description">{{ description }}</p>
        </div>
        <div class="header-actions">
        </div>
      </header>
      <section class="page-body">
        <slot />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useAppStore } from '@/stores/app'

const props = defineProps({
  title: String,
  description: String,
  subtitle: String,
  items: Array,
})

const appStore = useAppStore()
const router = useRouter()

const visibleItems = computed(() => {
  const navItems = Array.isArray(props.items) ? props.items : []
  if (appStore.user?.account === 'admin') {
    return navItems
  }
  return navItems.filter((item) => item.path !== '/admin/admins')
})

const handleLogout = async () => {
  await appStore.logout()
  router.replace('/login')
}

const getItemIcon = (label) => {
  const icons = {
    '首页': '🏠',
    '待办事项': '✅',
    '长期任务': '📅',
    '密码本': '🔒',
    '文件管理': '📁',
    '我的分享': '📤',
    '我的收藏': '⭐',
    '回收站': '🗑️',
    'AI 分析': '🤖',
    '个人中心': '👤',
    '用户管理': '👥',
    '存储管理': '💾',
    '管理员管理': '🛠️'
  }
  return icons[label] || '📄'
}

const getUserInitials = () => {
  if (appStore.user?.username) {
    return appStore.user.username.charAt(0).toUpperCase()
  }
  return 'U'
}
</script>

<style scoped>
@keyframes gradientShift {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

.shell { 
  display: flex; 
  min-height: 100vh; 
  background: linear-gradient(-45deg, #f0f9ff, #e6f7ff, #f0f4ff, #eef2ff);
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
  overflow: hidden;
}

.sidebar { 
  width: 260px; 
  background: linear-gradient(135deg, #f8fafc, #ffffff); 
  color: var(--text-primary); 
  padding: 24px 20px; 
  position: relative;
  box-shadow: 0 0 32px rgba(15, 23, 42, 0.08);
  z-index: 100;
  animation: slideIn 0.5s ease-out forwards;
  border-right: 1px solid var(--border-color);
}

.sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 1px;
  height: 100%;
  background: linear-gradient(to bottom, transparent, var(--border-color), transparent);
}

.brand { 
  display: flex; 
  gap: 12px; 
  align-items: center; 
  margin-bottom: 32px; 
  animation: fadeIn 0.6s ease-out forwards;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.brand-mark { 
  width: 48px; 
  height: 48px; 
  border-radius: 16px; 
  display: grid; 
  place-items: center; 
  background: var(--gradient-primary); 
  font-size: 24px; 
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  color: white;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3);
}

.brand-mark::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  transition: left 0.6s ease;
}

.brand-mark:hover::before {
  left: 100%;
}

.brand-mark:hover {
  transform: scale(1.05);
  box-shadow: 0 12px 32px rgba(59, 130, 246, 0.4);
}

.brand-title { 
  font-size: 20px; 
  font-weight: 700; 
  position: relative;
  overflow: hidden;
  color: var(--text-primary);
}

.brand-subtitle { 
  font-size: 12px; 
  color: var(--text-secondary); 
  margin-top: 4px; 
  transition: color 0.3s ease;
}

.brand:hover .brand-subtitle {
  color: var(--text-primary);
}

.nav-group { 
  display: flex; 
  flex-direction: column; 
  gap: 8px; 
  margin-bottom: auto;
}

.nav-item { 
  color: var(--text-secondary); 
  text-decoration: none; 
  padding: 14px 18px; 
  border-radius: 16px; 
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 12px;
  animation: fadeIn 0.4s ease-out forwards;
  background: transparent;
  border: 2px solid transparent;
}

.nav-item:hover {
  background: rgba(59, 130, 246, 0.05);
  color: var(--primary-color);
  transform: translateX(4px);
  border-color: rgba(59, 130, 246, 0.2);
}

.nav-item.router-link-active {
  background: rgba(59, 130, 246, 0.1);
  color: var(--primary-color);
  font-weight: 600;
  border-color: var(--primary-color);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.15);
}

.nav-item-icon {
  font-size: 18px;
  width: 24px;
  text-align: center;
}

.nav-item-text {
  flex: 1;
}

.nav-item-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: transparent;
  transition: all 0.3s ease;
}

.nav-item:hover .nav-item-indicator {
  background: var(--primary-color);
  transform: scale(1.2);
}

.nav-item.router-link-active .nav-item-indicator {
  background: var(--primary-color);
  transform: scale(1.4);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
  margin-top: 32px;
  animation: fadeIn 0.6s ease-out forwards;
  animation-delay: 0.6s;
  opacity: 0;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--gradient-primary);
  color: white;
  display: grid;
  place-items: center;
  font-weight: 600;
  font-size: 16px;
}

.user-details {
  flex: 1;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.user-role {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.logout-btn {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
  border: none;
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all 0.3s ease;
  font-size: 16px;
}

.logout-btn:hover {
  background: var(--danger-color);
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.content { 
  flex: 1; 
  padding: 32px;
  animation: fadeIn 0.6s ease-out forwards;
  animation-delay: 0.2s;
  opacity: 0;
  overflow-y: auto;
}

.header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  gap: 24px; 
  margin-bottom: 32px;
  position: relative;
}

.header::after {
  content: '';
  position: absolute;
  bottom: -16px;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-color), transparent);
}

.header-content {
  animation: slideIn 0.5s ease-out forwards;
  animation-delay: 0.3s;
  opacity: 0;
}

.header-title { 
  margin: 0; 
  font-size: 32px; 
  font-weight: 700;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  position: relative;
}

.header-description { 
  margin: 8px 0 0; 
  color: var(--text-secondary); 
  font-size: 14px;
  transition: color 0.3s ease;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  animation: fadeIn 0.5s ease-out forwards;
  animation-delay: 0.4s;
  opacity: 0;
}

.search-bar {
  position: relative;
  width: 300px;
}

.search-input {
  width: 100%;
  padding: 12px 40px 12px 16px;
  border: 2px solid var(--border-color);
  border-radius: 16px;
  font-size: 14px;
  transition: all 0.3s ease;
  background: white;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.search-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-light);
  font-size: 16px;
}

.notification-btn {
  position: relative;
  width: 44px;
  height: 44px;
  border-radius: 16px;
  background: white;
  border: 2px solid var(--border-color);
  color: var(--text-secondary);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all 0.3s ease;
  font-size: 18px;
}

.notification-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.notification-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--danger-color);
  color: white;
  font-size: 12px;
  font-weight: 600;
  display: grid;
  place-items: center;
}

.page-body { 
  margin-top: 24px;
  animation: fadeIn 0.6s ease-out forwards;
  animation-delay: 0.5s;
  opacity: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 220px;
    padding: 20px 16px;
  }
  
  .brand-title {
    font-size: 18px;
  }
  
  .nav-item {
    padding: 12px 14px;
  }
  
  .content {
    padding: 24px;
  }
  
  .header-title {
    font-size: 28px;
  }
  
  .search-bar {
    width: 200px;
  }
}

/* 动画定义 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
