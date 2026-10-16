<template>
  <AppShell title="管理员控制台" description="聚焦用户状态、空间资源与平台运行概览。" subtitle="管理端" :items="items">
    <section v-if="loading" class="state-card"><p>正在加载平台统计...</p></section>
    <section v-else-if="errorText" class="state-card">
      <h3>平台统计加载失败</h3>
      <p>{{ errorText }}</p>
      <button type="button" @click="loadOverview">重新加载</button>
    </section>

    <template v-else>
      <section class="admin-hero">
        <div class="admin-hero-card dark">
          <span class="badge light">平台概览</span>
          <h2>把用户、空间和权限管得清清楚楚</h2>
          <p>管理端聚焦账号状态、存储额度与平台数据统计，帮助运营快速定位风险与资源瓶颈。</p>
        </div>
        <div class="admin-hero-card stats">
          <div><span>注册用户</span><strong>{{ overview.totalUsers }}</strong></div>
          <div><span>平台已用</span><strong>{{ formatBytes(overview.totalUsedBytes) }}</strong></div>
          <div><span>可用空间</span><strong>{{ formatBytes(overview.remainingBytes) }}</strong></div>
        </div>
      </section>

      <div class="grid three dashboard-cards">
        <div class="card"><h3>用户状态</h3><strong>{{ overview.activeUsers }} / {{ overview.totalUsers }} 正常</strong><p>支持启用与禁用，快速处理异常账号。</p></div>
        <div class="card"><h3>管理员账号</h3><strong>{{ overview.totalAdmins }}</strong><p>可新增管理员、删除管理员与重置密码。</p></div>
        <div class="card"><h3>平台总额度</h3><strong>{{ formatBytes(overview.totalLimitBytes) }}</strong><p>支持按用户精细化调整存储上限。</p></div>
      </div>

      <div class="grid two dashboard-sections">
        <div class="card panel-card">
          <h3>管理入口</h3>
          <div class="quick-grid">
            <router-link to="/admin/users">用户管理</router-link>
            <router-link to="/admin/storage">存储管理</router-link>
            <router-link v-if="isSuperAdmin" to="/admin/admins">管理员管理</router-link>
            <router-link to="/admin/profile">个人中心</router-link>
          </div>
        </div>
        <div class="card panel-card">
          <h3>存储使用排行</h3>
          <ul class="activity-list">
            <li v-for="item in topUsers" :key="item.id">
              <span>{{ item.username }}</span>
              <small>{{ formatBytes(item.usedSpaceBytes) }} / {{ formatBytes(item.spaceLimitBytes) }}</small>
            </li>
            <li v-if="topUsers.length === 0"><span>暂无数据</span><small>--</small></li>
          </ul>
        </div>
      </div>
    </template>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { fetchAdminOverviewApi } from '@/api/admin'
import AppShell from '@/components/AppShell.vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const items = [
  { label: '首页', path: '/admin/home' },
  { label: '用户管理', path: '/admin/users' },
  { label: '存储管理', path: '/admin/storage' },
  { label: '管理员管理', path: '/admin/admins' },
  { label: '个人中心', path: '/admin/profile' },
]
const isSuperAdmin = computed(() => appStore.user?.account === 'admin')

const loading = ref(false)
const errorText = ref('')
const topUsers = ref([])
const overview = reactive({
  totalUsers: 0,
  activeUsers: 0,
  totalAdmins: 0,
  totalUsedBytes: 0,
  totalLimitBytes: 0,
  remainingBytes: 0,
})

const formatBytes = (bytes) => {
  if (!bytes || bytes < 0) {
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

const loadOverview = async () => {
  loading.value = true
  errorText.value = ''

  try {
    const data = await fetchAdminOverviewApi()
    Object.assign(overview, data.summary || {})
    topUsers.value = data.topUsers || []
  } catch (error) {
    errorText.value = error?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadOverview()
})
</script>

<style scoped>
.state-card {
  min-height: 220px;
  display: grid;
  place-items: center;
  text-align: center;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  padding: 20px;
}

.state-card h3 {
  margin: 0 0 8px;
  color: #0f172a;
}

.state-card p {
  margin: 0;
  color: #64748b;
}

.state-card button {
  margin-top: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 6px 12px;
  background: #fff;
  cursor: pointer;
}

.admin-hero { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 22px; margin-bottom: 22px; }
.admin-hero-card { border-radius: 24px; padding: 28px; }
.admin-hero-card.dark { background: linear-gradient(135deg,#0f172a,#1e293b); color: #fff; }
.admin-hero-card.dark h2 { margin: 16px 0 12px; font-size: 34px; }
.admin-hero-card.dark p { color: rgba(255,255,255,.76); line-height: 1.8; }
.badge.light { display: inline-flex; padding: 8px 12px; border-radius: 999px; background: rgba(255,255,255,.14); color: #e0f2fe; font-size: 12px; }
.admin-hero-card.stats { background: linear-gradient(135deg,#f8fafc,#eef2ff); display: grid; gap: 16px; }
.admin-hero-card.stats div { background: #fff; border-radius: 18px; padding: 20px; }
.admin-hero-card.stats span { display: block; color: #64748b; margin-bottom: 6px; }
.admin-hero-card.stats strong { font-size: 30px; color: #0f172a; }
.quick-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-top: 18px; }
.quick-grid a { text-decoration: none; padding: 18px; border-radius: 18px; background: #f8fafc; color: #0f172a; font-weight: 600; border: 1px solid #e2e8f0; }
.activity-list { list-style: none; padding: 0; margin: 18px 0 0; display: flex; flex-direction: column; gap: 14px; }
.activity-list li { display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-bottom: 1px solid #e2e8f0; }
.activity-list span { font-weight: 600; color: #0f172a; }
.activity-list small { color: #64748b; }
.dashboard-sections { margin-top: 20px; }

@media (max-width: 1180px) {
  .admin-hero,
  .dashboard-sections {
    grid-template-columns: 1fr;
  }
}
</style>
