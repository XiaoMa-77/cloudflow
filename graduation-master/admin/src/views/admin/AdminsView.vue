<template>
  <AppShell title="管理员管理" description="管理管理员账号，支持新增、删除和密码重置。" subtitle="管理端" :items="items">
    <section class="toolbar card">
      <button type="button" @click="createAdmin">新增管理员</button>
    </section>

    <section v-if="loading" class="state-card"><p>正在加载管理员列表...</p></section>
    <section v-else-if="errorText" class="state-card">
      <h3>管理员列表加载失败</h3>
      <p>{{ errorText }}</p>
      <button type="button" @click="loadAdmins">重新加载</button>
    </section>

    <section v-else class="table-card">
      <table>
        <thead>
          <tr>
            <th>账号</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in admins" :key="item.id">
            <td>{{ item.username }}</td>
            <td>{{ item.createdAt }}</td>
            <td>
              <div class="actions">
                <button type="button" :disabled="isProtectedAdmin(item)" @click="resetPassword(item)">重置密码</button>
                <button type="button" class="danger" :disabled="isProtectedAdmin(item)" @click="removeAdmin(item)">删除</button>
                <small v-if="isProtectedAdmin(item)" class="protected-tip">超级管理员</small>
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

import { createAdminApi, deleteAdminApi, fetchAdminsApi, updateAdminPasswordApi } from '@/api/admin'
import AppShell from '@/components/AppShell.vue'

const items = [
  { label: '首页', path: '/admin/home' },
  { label: '用户管理', path: '/admin/users' },
  { label: '存储管理', path: '/admin/storage' },
  { label: '管理员管理', path: '/admin/admins' },
  { label: '个人中心', path: '/admin/profile' },
]

const admins = ref([])
const loading = ref(false)
const errorText = ref('')

const isProtectedAdmin = (item) => item.username === 'admin'

const loadAdmins = async () => {
  loading.value = true
  errorText.value = ''

  try {
    const data = await fetchAdminsApi()
    admins.value = data.items || []
  } catch (error) {
    errorText.value = error?.message || '加载失败'
    admins.value = []
  } finally {
    loading.value = false
  }
}

const createAdmin = async () => {
  try {
    const { value: account } = await ElMessageBox.prompt('请输入管理员账号', '新增管理员', {
      inputValidator: (input) => Boolean(input?.trim()),
      inputErrorMessage: '账号不能为空',
      confirmButtonText: '下一步',
      cancelButtonText: '取消',
    })

    const { value: password } = await ElMessageBox.prompt('请输入初始密码（至少 6 位）', '新增管理员', {
      inputType: 'password',
      inputValidator: (input) => Boolean(input?.trim() && input.trim().length >= 6),
      inputErrorMessage: '密码至少 6 位',
      confirmButtonText: '创建',
      cancelButtonText: '取消',
    })

    await createAdminApi({ username: account.trim(), password: password.trim() })
    ElMessage.success('管理员创建成功')
    await loadAdmins()
  } catch (error) {
    if (error === 'cancel' || error?.message === 'cancel') {
      return
    }
    ElMessage.warning(error?.message || '创建失败')
  }
}

const resetPassword = async (item) => {
  if (isProtectedAdmin(item)) {
    ElMessage.warning('admin 账号禁止重置密码')
    return
  }

  try {
    const { value } = await ElMessageBox.prompt(`请输入 ${item.username} 的新密码`, '重置密码', {
      inputType: 'password',
      inputValidator: (input) => Boolean(input?.trim() && input.trim().length >= 6),
      inputErrorMessage: '密码至少 6 位',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })

    await updateAdminPasswordApi(item.id, value.trim())
    ElMessage.success('密码重置成功')
  } catch (error) {
    if (error === 'cancel' || error?.message === 'cancel') {
      return
    }
    ElMessage.warning(error?.message || '重置失败')
  }
}

const removeAdmin = async (item) => {
  if (isProtectedAdmin(item)) {
    ElMessage.warning('admin 账号禁止删除')
    return
  }

  try {
    await ElMessageBox.confirm(`确认删除管理员 ${item.username} 吗？`, '删除管理员', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (error) {
    return
  }

  try {
    await deleteAdminApi(item.id)
    ElMessage.success('管理员已删除')
    await loadAdmins()
  } catch (error) {
    ElMessage.warning(error?.message || '删除失败')
  }
}

onMounted(() => {
  loadAdmins()
})
</script>

<style scoped>
.card,
.table-card,
.state-card {
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
}

.toolbar {
  padding: 14px;
}

.toolbar button {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 8px 12px;
  background: #0f172a;
  color: #f8fafc;
  cursor: pointer;
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
}

.actions {
  display: flex;
  gap: 8px;
}

.actions button {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 10px;
  background: #fff;
  cursor: pointer;
}

.actions button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.actions .danger {
  border-color: #fecaca;
  color: #b91c1c;
}

.protected-tip {
  color: #475569;
  font-size: 12px;
  line-height: 1;
  align-self: center;
}
</style>
