<template>
  <AppShell title="个人中心" description="查看管理员账号信息并维护登录安全。" subtitle="管理端" :items="items">
    <section class="profile-grid">
      <article class="card">
        <h3>账号信息</h3>
        <div v-if="loading" class="state">正在加载资料...</div>
        <div v-else-if="errorText" class="state error">
          <p>{{ errorText }}</p>
          <button type="button" @click="loadProfile">重新加载</button>
        </div>
        <ul v-else>
          <li><span>账号</span><strong>{{ profile.username }}</strong></li>
          <li><span>角色</span><strong>ADMIN</strong></li>
          <li><span>创建时间</span><strong>{{ profile.createdAt }}</strong></li>
        </ul>
      </article>

      <article class="card">
        <h3>修改登录密码</h3>
        <form class="form" @submit.prevent="changePassword">
          <label>
            <span>原密码</span>
            <input v-model.trim="form.oldPassword" type="password" placeholder="请输入原密码" />
          </label>
          <label>
            <span>新密码</span>
            <input v-model.trim="form.newPassword" type="password" placeholder="请输入新密码（至少 6 位）" />
          </label>
          <label>
            <span>确认新密码</span>
            <input v-model.trim="form.confirmPassword" type="password" placeholder="请再次输入新密码" />
          </label>
          <button type="submit" :disabled="submitting">{{ submitting ? '提交中...' : '保存新密码' }}</button>
        </form>
      </article>
    </section>
  </AppShell>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchAdminProfileApi } from '@/api/admin'
import { changePasswordApi } from '@/api/auth'
import AppShell from '@/components/AppShell.vue'

const items = [
  { label: '首页', path: '/admin/home' },
  { label: '用户管理', path: '/admin/users' },
  { label: '存储管理', path: '/admin/storage' },
  { label: '管理员管理', path: '/admin/admins' },
  { label: '个人中心', path: '/admin/profile' },
]

const loading = ref(false)
const errorText = ref('')
const submitting = ref(false)
const profile = ref({ username: '--', createdAt: '--' })

const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const resetForm = () => {
  form.oldPassword = ''
  form.newPassword = ''
  form.confirmPassword = ''
}

const loadProfile = async () => {
  loading.value = true
  errorText.value = ''

  try {
    const data = await fetchAdminProfileApi()
    profile.value = {
      username: data.username,
      createdAt: data.createdAt,
    }
  } catch (error) {
    errorText.value = error?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const changePassword = async () => {
  if (!form.oldPassword || !form.newPassword || !form.confirmPassword) {
    ElMessage.warning('请填写完整密码信息')
    return
  }

  if (form.newPassword.length < 6) {
    ElMessage.warning('新密码长度不能少于 6 位')
    return
  }

  if (form.newPassword !== form.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }

  submitting.value = true
  try {
    await changePasswordApi({
      oldPassword: form.oldPassword,
      newPassword: form.newPassword,
    })
    ElMessage.success('密码修改成功')
    resetForm()
  } catch (error) {
    ElMessage.warning(error?.message || '修改失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.card {
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  background: #fff;
  padding: 20px;
}

.card h3 {
  margin: 0 0 14px;
  color: #0f172a;
}

.card ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.card li {
  display: flex;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px solid #e2e8f0;
}

.card span {
  color: #64748b;
}

.card strong {
  color: #0f172a;
}

.state {
  min-height: 120px;
  display: grid;
  place-items: center;
  color: #64748b;
}

.state.error {
  text-align: center;
}

.state button {
  margin-top: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 6px 12px;
  background: #fff;
  cursor: pointer;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form label {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form input {
  height: 40px;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  padding: 0 10px;
}

.form button {
  height: 40px;
  border: 0;
  border-radius: 10px;
  background: #0f172a;
  color: #fff;
  cursor: pointer;
}

.form button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

@media (max-width: 980px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
