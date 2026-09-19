<template>
  <AppShell title="存储管理" description="查看用户存储使用情况并调整额度上限。" subtitle="管理端" :items="items">
    <section v-if="loading" class="state-card"><p>正在加载存储列表...</p></section>
    <section v-else-if="errorText" class="state-card">
      <h3>存储列表加载失败</h3>
      <p>{{ errorText }}</p>
      <button type="button" @click="loadUsers">重新加载</button>
    </section>

    <section v-else class="table-card">
      <table>
        <thead>
          <tr>
            <th>账号</th>
            <th>已用空间</th>
            <th>当前上限</th>
            <th>使用率</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in users" :key="item.id">
            <td>{{ item.username }}</td>
            <td>{{ formatBytes(item.usedSpaceBytes) }}</td>
            <td>{{ formatBytes(item.spaceLimitBytes) }}</td>
            <td>{{ usagePercent(item) }}%</td>
            <td>
              <button type="button" class="limit-btn" @click="openLimitDialog(item)">调整上限</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="limitDialog.visible" class="dialog-mask" @click.self="closeLimitDialog">
      <article class="dialog-card">
        <h3>调整存储上限</h3>
        <p>账号：{{ limitDialog.username }}</p>

        <label>
          <span>容量数值</span>
          <input v-model="limitDialog.amount" type="number" min="1" step="1" placeholder="请输入容量数值" />
        </label>

        <label>
          <span>容量单位</span>
          <select v-model="limitDialog.unit">
            <option value="MB">MB</option>
            <option value="GB">GB</option>
            <option value="TB">TB</option>
          </select>
        </label>

        <div class="dialog-actions">
          <button type="button" class="ghost" @click="closeLimitDialog">取消</button>
          <button type="button" @click="submitLimit" :disabled="savingLimit">
            {{ savingLimit ? '保存中...' : '保存' }}
          </button>
        </div>
      </article>
    </section>
  </AppShell>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchAdminUsersApi, updateAdminUserStorageApi } from '@/api/admin'
import AppShell from '@/components/AppShell.vue'

const items = [
  { label: '首页', path: '/admin/home' },
  { label: '用户管理', path: '/admin/users' },
  { label: '存储管理', path: '/admin/storage' },
  { label: '管理员管理', path: '/admin/admins' },
  { label: '个人中心', path: '/admin/profile' },
]

const UNIT_BYTES = {
  MB: 1024 * 1024,
  GB: 1024 * 1024 * 1024,
  TB: 1024 * 1024 * 1024 * 1024,
}

const users = ref([])
const loading = ref(false)
const errorText = ref('')
const savingLimit = ref(false)
const limitDialog = reactive({
  visible: false,
  userId: null,
  username: '',
  amount: '',
  unit: 'GB',
})

const formatBytes = (bytes) => {
  if (!bytes || bytes < 0) {
    return '0 B'
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  if (bytes < 1024 * 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }
  return `${(bytes / (1024 * 1024 * 1024 * 1024)).toFixed(1)} TB`
}

const usagePercent = (item) => {
  if (!item.spaceLimitBytes) {
    return 0
  }
  return Math.min(100, Math.round((item.usedSpaceBytes / item.spaceLimitBytes) * 100))
}

const normalizeDialogLimit = (spaceLimitBytes) => {
  if (spaceLimitBytes >= UNIT_BYTES.TB && spaceLimitBytes % UNIT_BYTES.TB === 0) {
    return { amount: String(spaceLimitBytes / UNIT_BYTES.TB), unit: 'TB' }
  }
  if (spaceLimitBytes >= UNIT_BYTES.GB) {
    return { amount: String(Math.max(1, Math.round(spaceLimitBytes / UNIT_BYTES.GB))), unit: 'GB' }
  }
  return { amount: String(Math.max(1, Math.round(spaceLimitBytes / UNIT_BYTES.MB))), unit: 'MB' }
}

const loadUsers = async () => {
  loading.value = true
  errorText.value = ''

  try {
    const data = await fetchAdminUsersApi()
    users.value = data.items || []
  } catch (error) {
    errorText.value = error?.message || '加载失败'
    users.value = []
  } finally {
    loading.value = false
  }
}

const openLimitDialog = (item) => {
  const normalized = normalizeDialogLimit(item.spaceLimitBytes || UNIT_BYTES.GB)
  limitDialog.visible = true
  limitDialog.userId = item.id
  limitDialog.username = item.username
  limitDialog.amount = normalized.amount
  limitDialog.unit = normalized.unit
}

const closeLimitDialog = () => {
  limitDialog.visible = false
  limitDialog.userId = null
  limitDialog.username = ''
  limitDialog.amount = ''
  limitDialog.unit = 'GB'
  savingLimit.value = false
}

const submitLimit = async () => {
  const amount = Number(limitDialog.amount)
  if (!Number.isFinite(amount) || amount <= 0) {
    ElMessage.warning('请输入大于 0 的容量数值')
    return
  }

  const unitBytes = UNIT_BYTES[limitDialog.unit]
  const nextLimit = Math.floor(amount * unitBytes)
  if (!nextLimit) {
    ElMessage.warning('容量上限无效')
    return
  }

  savingLimit.value = true
  try {
    await updateAdminUserStorageApi(limitDialog.userId, nextLimit)
    ElMessage.success('存储上限已更新')
    closeLimitDialog()
    await loadUsers()
  } catch (error) {
    ElMessage.warning(error?.message || '更新失败')
    savingLimit.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.state-card,
.table-card {
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
}

.state-card {
  min-height: 220px;
  display: grid;
  place-items: center;
  text-align: center;
  padding: 20px;
}

.state-card button {
  margin-top: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 6px 12px;
  background: #fff;
  cursor: pointer;
}

.table-card {
  padding: 16px;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  text-align: left;
  padding: 10px;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

th {
  color: #64748b;
  font-size: 13px;
}

td {
  color: #0f172a;
  font-size: 14px;
}

.limit-btn {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
  background: #ffffff;
}

.dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 2000;
  display: grid;
  place-items: center;
  padding: 16px;
}

.dialog-card {
  width: min(420px, calc(100vw - 32px));
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 24px 68px rgba(15, 23, 42, 0.26);
  padding: 18px;
}

.dialog-card h3 {
  margin: 0;
  color: #0f172a;
}

.dialog-card > p {
  margin: 10px 0 14px;
  color: #64748b;
  font-size: 13px;
}

.dialog-card label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.dialog-card span {
  color: #334155;
  font-size: 13px;
}

.dialog-card input,
.dialog-card select {
  height: 38px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 10px;
  font-size: 14px;
  background: #ffffff;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.dialog-actions button {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 12px;
  background: #ffffff;
  cursor: pointer;
}

.dialog-actions button.ghost {
  background: #f8fafc;
}

.dialog-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
</style>
