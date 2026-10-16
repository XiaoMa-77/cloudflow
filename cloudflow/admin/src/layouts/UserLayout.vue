<template>
  <div class="user-layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">☁</div>
        <div>
          <div class="brand-title">CloudFlow</div>
          <div class="brand-subtitle">用户端</div>
        </div>
      </div>

      <div class="profile-card">
        <div class="avatar">{{ userInitial }}</div>
        <div class="profile-meta">
          <span>当前用户</span>
          <strong>{{ currentUserName }}</strong>
        </div>
      </div>

      <nav class="nav-list">
        <router-link v-for="item in items" :key="item.path" :to="item.path" class="nav-item">
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="storage-card">
        <small>存储空间</small>
        <strong>{{ sidebarUsagePercent }}%</strong>
        <div class="storage-meta">
          <span>已用 {{ sidebarUsedStorage }}</span>
          <span>总量 {{ sidebarTotalStorage }}</span>
        </div>
        <div class="progress">
          <span :style="{ width: `${sidebarUsagePercent}%` }"></span>
        </div>
        <p>容量信息：{{ sidebarUsedStorage }} / {{ sidebarTotalStorage }}</p>
      </div>
    </aside>

    <div class="main-panel">
      <header class="topbar">
        <div class="topbar-left">
          <div class="topbar-badge">CloudFlow · 用户工作区</div>
          <h1 class="topbar-title">{{ title }}</h1>
          <p class="topbar-description">{{ description }}</p>
        </div>
        <div class="topbar-right">
          <div class="user-info">
            <div class="user-avatar">{{ userInitial }}</div>
            <div class="user-details">
              <span class="user-label">当前用户</span>
              <strong class="user-name">{{ currentUserName }}</strong>
            </div>
          </div>
          <slot name="header-actions" />
          <button type="button" class="logout-btn" @click="handleLogout">
            <span class="logout-icon">↪</span>
            退出登录
          </button>
        </div>
      </header>

      <section class="content">
        <slot />
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'

const props = defineProps({
  title: {
    type: String,
    default: '',
  },
  description: {
    type: String,
    default: '',
  },
  items: {
    type: Array,
    default: () => [],
  },
  usedStorage: {
    type: String,
    default: '0GB',
  },
  totalStorage: {
    type: String,
    default: '0GB',
  },
  usagePercent: {
    type: Number,
    default: 0,
  },
})

const router = useRouter()
const appStore = useAppStore()

const currentUserName = computed(() => {
  if (appStore.user?.name) {
    return appStore.user.name
  }
  const raw = localStorage.getItem('auth_session')
  if (!raw) {
    return '未登录'
  }
  try {
    const parsed = JSON.parse(raw)
    return parsed?.name || '云盘用户'
  } catch (error) {
    return '云盘用户'
  }
})

const userInitial = computed(() => currentUserName.value?.trim()?.slice(0, 1) || 'U')

const sidebarUsedStorage = computed(() => (appStore.user ? appStore.usedStorageText : props.usedStorage))
const sidebarTotalStorage = computed(() => (appStore.user ? appStore.totalStorageText : props.totalStorage))
const sidebarUsagePercent = computed(() => (appStore.user ? appStore.usagePercent : props.usagePercent))

onMounted(() => {
  appStore.restoreSession().catch(() => {
    // Router guard will redirect on unauthorized state.
  })
})

const handleLogout = async () => {
  await appStore.logout()
  router.push('/login')
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

.user-layout {
  min-height: 100vh;
  display: flex;
  background: linear-gradient(-45deg, #f0f9ff, #e6f7ff, #f0f4ff, #eef2ff);
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
}

.sidebar {
  width: 256px;
  padding: 24px 18px;
  background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
  color: #334155;
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.brand-mark {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #409EFF, #667EEA);
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
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}

.brand-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(51, 65, 85, 0.72);
}

.profile-card {
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 16px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.2);
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 14px;
  font-weight: 700;
  color: #ffffff;
  background: linear-gradient(135deg, #0ea5e9, #3b82f6);
}

.profile-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.profile-meta span {
  font-size: 11px;
  color: rgba(51, 65, 85, 0.7);
}

.profile-meta strong {
  font-size: 14px;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  padding: 12px 16px;
  border-radius: 12px;
  color: rgba(51, 65, 85, 0.86);
  text-decoration: none;
  transition: 0.2s ease;
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-icon {
  font-size: 18px;
  transition: 0.2s ease;
}

.nav-label {
  font-size: 14px;
  font-weight: 500;
  transition: 0.2s ease;
}

.nav-item:hover {
  background: rgba(102, 126, 234, 0.1);
  color: #1e293b;
  transform: translateX(4px);
}

.nav-item:hover .nav-icon {
  transform: scale(1.1);
  color: #667eea;
}

.nav-item.router-link-active {
  color: #1e293b;
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.4), rgba(59, 130, 246, 0.28));
  border: 1px solid rgba(147, 197, 253, 0.3);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.nav-item.router-link-active .nav-icon {
  transform: scale(1.1);
  color: #667eea;
}

.storage-card {
  margin-top: auto;
  border-radius: 18px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.storage-card small {
  color: rgba(51, 65, 85, 0.76);
  font-size: 12px;
}

.storage-card strong {
  display: block;
  margin: 8px 0 10px;
  font-size: 18px;
  color: #1e293b;
}

.storage-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 12px;
  color: rgba(51, 65, 85, 0.8);
}

.progress {
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(148, 163, 184, 0.2);
}

.progress span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #0ea5e9, #38bdf8);
}

.storage-card p {
  margin: 10px 0 0;
  color: rgba(51, 65, 85, 0.76);
  line-height: 1.5;
  font-size: 12px;
}

.main-panel {
  flex: 1;
  padding: 24px;
}

.topbar {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 24px;
  padding: 24px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 30px;
  box-shadow: 0 16px 48px rgba(15, 23, 42, 0.1);
  backdrop-filter: blur(12px);
  transition: all 0.3s ease;
}

.topbar:hover {
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.12);
  transform: translateY(-2px);
}

.topbar-left {
  flex: 1;
}

.topbar-badge {
  display: inline-block;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 16px;
  margin-bottom: 12px;
  font-weight: 500;
}

.topbar-title {
  margin: 0 0 8px;
  font-size: 32px;
  font-weight: 700;
  color: #1a1a1a;
  letter-spacing: -0.5px;
}

.topbar-description {
  margin: 0;
  font-size: 16px;
  color: #666;
  line-height: 1.4;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 16px;
  border: 1px solid rgba(102, 126, 234, 0.2);
  transition: all 0.3s ease;
}

.user-info:hover {
  background: rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: white;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.user-details {
  display: flex;
  flex-direction: column;
}

.user-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 2px;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.logout-btn {
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  padding: 10px 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.logout-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
}

.logout-icon {
  font-size: 16px;
  transition: transform 0.3s ease;
}

.logout-btn:hover .logout-icon {
  transform: translateX(2px) rotate(90deg);
}

.content {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

@media (max-width: 1080px) {
  .user-layout {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
  }

  .topbar {
    flex-direction: column;
  }

  .topbar-right {
    justify-content: space-between;
  }

  .account {
    text-align: left;
  }
}

@media (max-width: 720px) {
  .main-panel {
    padding: 14px;
  }

  .topbar {
    padding: 16px;
  }

  .topbar h1 {
    font-size: 24px;
  }

  .topbar-right {
    flex-wrap: wrap;
  }
}
</style>
