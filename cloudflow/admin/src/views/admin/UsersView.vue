<template>
  <AppShell title="用户管理" description="查看用户状态并执行启用、禁用或删除操作。" subtitle="管理端" :items="items">
    <section v-if="loading" class="state-card"><p>正在加载用户列表...</p></section>
    <section v-else-if="errorText" class="state-card">
      <h3>用户列表加载失败</h3>
      <p>{{ errorText }}</p>
      <button type="button" @click="loadUsers">重新加载</button>
    </section>

    <section v-else class="table-card">
      <table>
        <thead>
          <tr>
            <th>账号</th>
            <th>状态</th>
            <th>注册时间</th>
            <th>已用空间</th>
            <th>上限</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in users" :key="item.id">
            <td>{{ item.username }}</td>
            <td>
              <span class="status" :class="item.status === 'ACTIVE' ? 'active' : 'disabled'">
                {{ item.status === 'ACTIVE' ? '正常' : '已禁用' }}
              </span>
            </td>
            <td>{{ item.createdAt }}</td>
            <td>{{ formatBytes(item.usedSpaceBytes) }}</td>
            <td>{{ formatBytes(item.spaceLimitBytes) }}</td>
            <td>
              <div class="actions">
                <button
                  type="button"
                  class="status-btn"
                  @click="toggleStatus(item)"
                >
                  {{ item.status === 'ACTIVE' ? '禁用' : '启用' }}
                </button>
                <button
                  type="button"
                  class="danger-btn"
                  @click="deleteUser(item)"
                >
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { fetchAdminUsersApi, updateAdminUserStatusApi, deleteAdminUserApi } from '@/api/admin'
import AppShell from '@/components/AppShell.vue'

const items = [
  { label: '首页', path: '/admin/home' },
  { label: '用户管理', path: '/admin/users' },
  { label: '存储管理', path: '/admin/storage' },
  { label: '管理员管理', path: '/admin/admins' },
  { label: '个人中心', path: '/admin/profile' },
]

const users = ref([])
const loading = ref(false)
const errorText = ref('')

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
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
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

const toggleStatus = async (item) => {
  const nextStatus = item.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
  try {
    await updateAdminUserStatusApi(item.id, nextStatus)
    ElMessage.success('用户状态更新成功')
    await loadUsers()
  } catch (error) {
    ElMessage.warning(error?.message || '更新失败')
  }
}

const deleteUser = async (item) => {
  try {
    await ElMessageBox.confirm(`确认删除用户 ${item.username} 吗？`, '删除用户', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (error) {
    return
  }

  try {
    await deleteAdminUserApi(item.id)
    ElMessage.success('用户已删除')
    await loadUsers()
  } catch (error) {
    ElMessage.warning(error?.message || '删除失败')
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

.status {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
}

.status.active {
  background: #dcfce7;
  color: #166534;
}

.status.disabled {
  background: #fee2e2;
  color: #991b1b;
}

.actions {
  display: flex;
  gap: 8px;
}

.status-btn {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
  background: #ffffff;
  transition: all 0.2s ease;
}

.status-btn:hover {
  border-color: #94a3b8;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.danger-btn {
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
  background: #ffffff;
  color: #b91c1c;
  transition: all 0.2s ease;
}

.danger-btn:hover {
  background: #fee2e2;
  box-shadow: 0 2px 4px rgba(185, 28, 28, 0.1);
}
</style>
