<template>
  <UserLayout title="用户首页" description="集中查看存储空间、近期动态与文件主链路入口。" :items="userNavItems">
    <!-- 欢迎卡片 -->
    <section class="hero-section animate-fade-in" style="animation-delay: 0.1s;">
      <div class="hero-card">
        <div class="hero-content">
          <span class="hero-badge">智能云盘工作台</span>
          <h2>Hi, {{ appStore.user?.username || '用户' }}!</h2>
          <p>欢迎使用智能云盘系统，在这里统一管理文件、分享与回收站，快速完成日常存储与协作操作。</p>
          <div class="hero-actions">
            <router-link to="/user/files" class="hero-btn primary">
              <span class="btn-icon">📁</span>
              管理文件
            </router-link>
            <router-link to="/user/todo" class="hero-btn secondary">
              <span class="btn-icon">✅</span>
              待办事项
            </router-link>
          </div>
        </div>
        <div class="hero-visual animate-float">
          <div class="cloud-icon">☁️</div>
          <div class="floating-elements">
            <div class="float-item" style="animation-delay: 0s;">📄</div>
            <div class="float-item" style="animation-delay: 0.5s;">📊</div>
            <div class="float-item" style="animation-delay: 1s;">🔒</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 数据概览 -->
    <section class="stats-section">
      <div class="stats-grid">
        <div class="stat-card animate-fade-in" style="animation-delay: 0.2s;">
          <div class="stat-icon storage-icon">💾</div>
          <div class="stat-content">
            <div class="stat-label">存储使用</div>
            <div class="stat-value">{{ usedStorageText }}</div>
            <div class="stat-progress">
              <div class="progress-bar" :style="{ width: `${usagePercent}%` }"></div>
            </div>
            <div class="stat-detail">{{ usagePercent }}% of {{ totalStorageText }}</div>
          </div>
        </div>
        <div class="stat-card animate-fade-in" style="animation-delay: 0.3s;">
          <div class="stat-icon files-icon">📁</div>
          <div class="stat-content">
            <div class="stat-label">总文件数</div>
            <div class="stat-value">{{ overview.totalFiles }}</div>
            <div class="stat-detail">覆盖文档、图片、视频与压缩包</div>
          </div>
        </div>
        <div class="stat-card animate-fade-in" style="animation-delay: 0.4s;">
          <div class="stat-icon shares-icon">📤</div>
          <div class="stat-content">
            <div class="stat-label">有效分享</div>
            <div class="stat-value">{{ overview.activeShares }}</div>
            <div class="stat-detail">可在分享记录中管理有效期</div>
          </div>
        </div>
        <div class="stat-card animate-fade-in" style="animation-delay: 0.5s;">
          <div class="stat-icon recycle-icon">🗑️</div>
          <div class="stat-content">
            <div class="stat-label">回收站文件</div>
            <div class="stat-value">{{ overview.recycleCount }}</div>
            <div class="stat-detail">支持恢复与彻底删除操作</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 功能快捷入口 -->
    <section class="features-section animate-fade-in" style="animation-delay: 0.6s;">
      <h3 class="section-title">快捷功能</h3>
      <div class="features-grid">
        <router-link to="/user/files" class="feature-card">
          <div class="feature-icon file-manager-icon">📂</div>
          <h4>文件管理</h4>
          <p>上传、下载、整理和管理您的所有文件</p>
        </router-link>
        <router-link to="/user/todo" class="feature-card">
          <div class="feature-icon todo-icon">✅</div>
          <h4>待办事项</h4>
          <p>创建、跟踪和完成您的日常任务</p>
        </router-link>
        <router-link to="/user/long-term-tasks" class="feature-card">
          <div class="feature-icon long-task-icon">📅</div>
          <h4>长期任务</h4>
          <p>管理和跟踪您的长期项目进度</p>
        </router-link>
        <router-link to="/user/passwords" class="feature-card">
          <div class="feature-icon password-icon">🔒</div>
          <h4>密码本</h4>
          <p>安全存储和管理您的密码信息</p>
        </router-link>
        <router-link to="/user/share" class="feature-card">
          <div class="feature-icon share-icon">🔗</div>
          <h4>分享记录</h4>
          <p>查看和管理您的文件分享</p>
        </router-link>
        <router-link to="/user/ai-analysis" class="feature-card">
          <div class="feature-icon ai-icon">🤖</div>
          <h4>AI 分析</h4>
          <p>利用AI分析您的文件内容</p>
        </router-link>
      </div>
    </section>

    <!-- 最近动态 -->
    <section class="activity-section animate-fade-in" style="animation-delay: 0.7s;">
      <h3 class="section-title">最近动态</h3>
      <div class="activity-card">
        <div v-if="loading" class="activity-state">
          <div class="loading-spinner"></div>
          <p>正在加载动态...</p>
        </div>
        <div v-else-if="errorText" class="activity-state error">
          <div class="error-icon">⚠️</div>
          <p>{{ errorText }}</p>
          <button type="button" class="retry-btn" @click="loadDashboard">重新加载</button>
        </div>
        <ul v-else-if="recentActivities.length > 0" class="activity-list">
          <li 
            v-for="(item, index) in recentActivities" 
            :key="item.id" 
            class="activity-item"
            :style="{ animationDelay: `${0.8 + index * 0.1}s` }"
          >
            <div class="activity-icon">
              <span v-if="item.action.includes('上传')">📤</span>
              <span v-else-if="item.action.includes('删除')">🗑️</span>
              <span v-else-if="item.action.includes('分享')">🔗</span>
              <span v-else>📄</span>
            </div>
            <div class="activity-content">
              <strong>{{ item.fileName }}</strong>
              <p>{{ item.action }}</p>
            </div>
            <span class="activity-time">{{ item.time }}</span>
          </li>
        </ul>
        <div v-else class="activity-state">
          <div class="empty-icon">📋</div>
          <p>暂无动态记录</p>
        </div>
      </div>
    </section>
  </UserLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { fetchUserDashboardApi } from '@/api/user'
import UserLayout from '@/layouts/UserLayout.vue'
import { useAppStore } from '@/stores/app'
import { userNavItems } from '@/constants/userNavigation'

const appStore = useAppStore()

const loading = ref(false)
const errorText = ref('')
const recentActivities = ref([])
const overview = reactive({
  usedSpaceBytes: 0,
  spaceLimitBytes: 0,
  totalFiles: 0,
  activeShares: 0,
  recycleCount: 0,
})

const formatBytes = (bytes) => {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return '0 B'
  }
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

const usedStorageText = computed(() => formatBytes(overview.usedSpaceBytes))
const totalStorageText = computed(() => formatBytes(overview.spaceLimitBytes))
const usagePercent = computed(() => {
  if (!overview.spaceLimitBytes) {
    return 0
  }
  return Math.min(100, Math.round((overview.usedSpaceBytes / overview.spaceLimitBytes) * 100))
})

const loadDashboard = async () => {
  loading.value = true
  errorText.value = ''

  try {
    const data = await fetchUserDashboardApi()
    Object.assign(overview, data.overview || {})
    recentActivities.value = data.recentActivities || []

    appStore.user = {
      ...(appStore.user || {}),
      usedSpaceBytes: overview.usedSpaceBytes || 0,
      spaceLimitBytes: overview.spaceLimitBytes || 0,
    }
    appStore.persistSession()
  } catch (error) {
    errorText.value = error?.message || '首页信息加载失败'
    recentActivities.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.hero-section {
  margin-bottom: 40px;
}

.hero-card {
  background: linear-gradient(135deg, #f0f9ff 0%, #ffffff 100%);
  border-radius: 32px;
  padding: 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 40px;
  box-shadow: 0 20px 48px rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.1);
  position: relative;
  overflow: hidden;
}

.hero-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-primary);
}

.hero-content {
  flex: 1;
  animation: slideIn 0.5s ease-out forwards;
  animation-delay: 0.2s;
  opacity: 0;
}

.hero-badge {
  display: inline-flex;
  padding: 10px 20px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.1);
  color: var(--primary-color);
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 20px;
  transition: all 0.3s ease;
}

.hero-badge:hover {
  background: rgba(59, 130, 246, 0.2);
  transform: scale(1.05);
}

.hero-card h2 {
  margin: 0 0 16px;
  color: var(--text-primary);
  font-size: 36px;
  font-weight: 700;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-card p {
  margin: 0 0 32px;
  color: var(--text-secondary);
  line-height: 1.75;
  font-size: 16px;
  max-width: 600px;
}

.hero-actions {
  display: flex;
  gap: 16px;
}

.hero-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 24px;
  border-radius: 16px;
  font-weight: 600;
  transition: all 0.3s ease;
  text-decoration: none;
  border: 2px solid transparent;
}

.hero-btn.primary {
  background: var(--gradient-primary);
  color: white;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3);
}

.hero-btn.secondary {
  background: white;
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.hero-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(59, 130, 246, 0.4);
}

.btn-icon {
  font-size: 18px;
}

.hero-visual {
  position: relative;
  width: 200px;
  height: 200px;
  animation: fadeIn 0.6s ease-out forwards;
  animation-delay: 0.4s;
  opacity: 0;
}

.cloud-icon {
  font-size: 120px;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1;
}

.floating-elements {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2;
}

.float-item {
  position: absolute;
  font-size: 24px;
  animation: float 3s ease-in-out infinite;
}

.float-item:nth-child(1) {
  top: 20%;
  left: 20%;
}

.float-item:nth-child(2) {
  top: 60%;
  right: 10%;
}

.float-item:nth-child(3) {
  bottom: 10%;
  left: 30%;
}

.stats-section {
  margin-bottom: 40px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.stat-card {
  background: var(--card-bg);
  border-radius: 24px;
  padding: 28px;
  box-shadow: var(--shadow-soft);
  transition: all var(--transition-normal);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-4px);
  border-color: rgba(59, 130, 246, 0.2);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-size: 28px;
  flex-shrink: 0;
}

.storage-icon {
  background: rgba(59, 130, 246, 0.1);
  color: var(--primary-color);
}

.files-icon {
  background: rgba(16, 185, 129, 0.1);
  color: var(--accent-color);
}

.shares-icon {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.recycle-icon {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.stat-progress {
  height: 8px;
  border-radius: 999px;
  background: #f1f5f9;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar {
  height: 100%;
  border-radius: 999px;
  background: var(--gradient-primary);
  transition: width 1s ease-out;
}

.stat-detail {
  font-size: 12px;
  color: var(--text-light);
}

.features-section {
  margin-bottom: 40px;
}

.section-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title::before {
  content: '';
  width: 4px;
  height: 24px;
  background: var(--gradient-primary);
  border-radius: 2px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.feature-card {
  background: var(--card-bg);
  border-radius: 24px;
  padding: 32px;
  box-shadow: var(--shadow-soft);
  transition: all var(--transition-normal);
  border: 1px solid var(--border-color);
  text-align: center;
  text-decoration: none;
  color: var(--text-primary);
  position: relative;
  overflow: hidden;
}

.feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-primary);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform var(--transition-normal);
}

.feature-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-4px);
  border-color: rgba(59, 130, 246, 0.2);
}

.feature-card:hover::before {
  transform: scaleX(1);
}

.feature-icon {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  display: grid;
  place-items: center;
  font-size: 32px;
  margin: 0 auto 20px;
  transition: all var(--transition-normal);
}

.file-manager-icon {
  background: rgba(59, 130, 246, 0.1);
  color: var(--primary-color);
}

.todo-icon {
  background: rgba(16, 185, 129, 0.1);
  color: var(--accent-color);
}

.long-task-icon {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.password-icon {
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}

.share-icon {
  background: rgba(236, 72, 153, 0.1);
  color: #ec4899;
}

.ai-icon {
  background: rgba(6, 182, 212, 0.1);
  color: var(--secondary-color);
}

.feature-card:hover .feature-icon {
  transform: scale(1.1);
}

.feature-card h4 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--text-primary);
}

.feature-card p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

.activity-section {
  margin-bottom: 40px;
}

.activity-card {
  background: var(--card-bg);
  border-radius: 24px;
  padding: 32px;
  box-shadow: var(--shadow-soft);
  border: 1px solid var(--border-color);
}

.activity-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-height: 400px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.5);
  transition: all var(--transition-normal);
  animation: fadeIn 0.4s ease-out forwards;
  opacity: 0;
}

.activity-item:hover {
  background: rgba(240, 249, 255, 0.8);
  transform: translateX(8px);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.1);
}

.activity-item .activity-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 18px;
  flex-shrink: 0;
  background: rgba(59, 130, 246, 0.1);
  color: var(--primary-color);
}

.activity-content {
  flex: 1;
}

.activity-content strong {
  color: var(--text-primary);
  font-weight: 600;
  display: block;
  margin-bottom: 4px;
  font-size: 15px;
}

.activity-content p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
}

.activity-time {
  color: var(--text-light);
  font-size: 13px;
  white-space: nowrap;
  flex-shrink: 0;
  margin-top: 4px;
}

.activity-state {
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  text-align: center;
  padding: 60px 20px;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f1f5f9;
  border-top: 4px solid var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

.error-icon {
  font-size: 40px;
  margin-bottom: 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.5;
}

.retry-btn {
  margin-top: 20px;
  border: 2px solid var(--primary-color);
  border-radius: 12px;
  padding: 10px 24px;
  background: var(--primary-color);
  color: white;
  cursor: pointer;
  font-weight: 600;
  transition: all var(--transition-normal);
}

.retry-btn:hover {
  background: #2563eb;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
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

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .hero-card {
    flex-direction: column;
    text-align: center;
    gap: 32px;
  }
  
  .hero-actions {
    justify-content: center;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .hero-card {
    padding: 32px 24px;
  }
  
  .hero-card h2 {
    font-size: 28px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
  
  .feature-card {
    padding: 24px;
  }
  
  .activity-card {
    padding: 24px;
  }
}
</style>
