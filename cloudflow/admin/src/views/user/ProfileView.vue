<template>
  <UserLayout title="个人中心" description="查看账号基础信息与安全设置。" :items="userNavItems">
    <section class="profile-grid animate-fade-in">
      <article class="profile-card animate-slide-up">
        <div class="card-header">
          <div class="header-icon">
            <i class="icon-user"></i>
          </div>
          <h3>基础信息</h3>
        </div>

        <div v-if="loading" class="state-text">
          <div class="loading-spinner"></div>
          <p>正在加载资料...</p>
        </div>
        <div v-else-if="errorText" class="state-text error">
          <div class="error-icon">
            <i class="icon-error"></i>
          </div>
          <p>{{ errorText }}</p>
          <button type="button" class="btn-primary" @click="loadProfile">重新加载</button>
        </div>
        <ul v-else class="info-list">
          <li class="info-item animate-slide-up" style="animation-delay: 0.1s;">
            <div class="item-icon">
              <i class="icon-name"></i>
            </div>
            <span>用户名</span>
            <strong>{{ profile.name }}</strong>
          </li>
          <li class="info-item animate-slide-up" style="animation-delay: 0.2s;">
            <div class="item-icon">
              <i class="icon-account"></i>
            </div>
            <span>账号</span>
            <strong>{{ profile.account }}</strong>
          </li>
          <li class="info-item animate-slide-up" style="animation-delay: 0.3s;">
            <div class="item-icon">
              <i class="icon-role"></i>
            </div>
            <span>角色</span>
            <strong>{{ profile.role }}</strong>
          </li>
          <li class="info-item animate-slide-up" style="animation-delay: 0.4s;">
            <div class="item-icon">
              <i class="icon-status"></i>
            </div>
            <span>账号状态</span>
            <strong :class="profile.status === 'ACTIVE' ? 'status-active' : 'status-disabled'">{{ profile.status === 'ACTIVE' ? '正常' : '已禁用' }}</strong>
          </li>
          <li class="info-item animate-slide-up" style="animation-delay: 0.5s;">
            <div class="item-icon">
              <i class="icon-time"></i>
            </div>
            <span>注册时间</span>
            <strong>{{ profile.createdAt }}</strong>
          </li>
        </ul>
      </article>

      <article class="profile-card animate-slide-up" style="animation-delay: 0.2s;">
        <div class="card-header">
          <div class="header-icon">
            <i class="icon-password"></i>
          </div>
          <h3>密码修改</h3>
        </div>
        <form class="password-form" @submit.prevent="changePassword">
          <div class="form-group animate-slide-up" style="animation-delay: 0.3s;">
            <label>
              <span>原密码</span>
              <div class="input-wrapper">
                <i class="icon-lock"></i>
                <input v-model.trim="form.oldPassword" type="password" placeholder="请输入原密码" />
              </div>
            </label>
          </div>
          <div class="form-group animate-slide-up" style="animation-delay: 0.4s;">
            <label>
              <span>新密码</span>
              <div class="input-wrapper">
                <i class="icon-lock"></i>
                <input v-model.trim="form.newPassword" type="password" placeholder="请输入新密码（至少 6 位）" />
              </div>
            </label>
          </div>
          <div class="form-group animate-slide-up" style="animation-delay: 0.5s;">
            <label>
              <span>确认新密码</span>
              <div class="input-wrapper">
                <i class="icon-lock"></i>
                <input v-model.trim="form.confirmPassword" type="password" placeholder="请再次输入新密码" />
              </div>
            </label>
          </div>
          <button type="submit" class="btn-primary animate-slide-up" style="animation-delay: 0.6s;" :disabled="submitting">
            <i class="icon-save"></i> {{ submitting ? '提交中...' : '保存新密码' }}
          </button>
        </form>
      </article>
    </section>
  </UserLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { changePasswordApi } from '@/api/auth'
import { fetchUserProfileApi } from '@/api/user'
import UserLayout from '@/layouts/UserLayout.vue'
import { useAppStore } from '@/stores/app'
import { userNavItems } from '@/constants/userNavigation'

const appStore = useAppStore()

const loading = ref(false)
const errorText = ref('')
const submitting = ref(false)
const profile = ref({
  name: '--',
  account: '--',
  role: 'USER',
  status: 'ACTIVE',
  createdAt: '--',
})

const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const loadProfile = async () => {
  loading.value = true
  errorText.value = ''

  try {
    const data = await fetchUserProfileApi()
    profile.value = {
      name: data.name,
      account: data.account,
      role: data.role,
      status: data.status,
      createdAt: data.createdAt,
    }

    appStore.user = {
      ...(appStore.user || {}),
      name: data.name,
      account: data.account,
      role: data.role,
      usedSpaceBytes: data.usedSpaceBytes || appStore.user?.usedSpaceBytes || 0,
      spaceLimitBytes: data.spaceLimitBytes || appStore.user?.spaceLimitBytes || 0,
    }
    appStore.persistSession()
  } catch (error) {
    errorText.value = error?.message || '资料加载失败'
  } finally {
    loading.value = false
  }
}

const resetPasswordForm = () => {
  form.oldPassword = ''
  form.newPassword = ''
  form.confirmPassword = ''
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
    resetPasswordForm()
  } catch (error) {
    ElMessage.warning(error?.message || '密码修改失败')
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
  gap: 20px;
}

.profile-card {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 20px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
  padding: 24px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.profile-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #8b5cf6, #ec4899);
}

.profile-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.12);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.header-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0abfc, #c084fc);
  color: #ffffff;
  font-size: 20px;
  flex-shrink: 0;
}

.profile-card h3 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
  font-weight: 600;
}

.info-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.info-item:hover {
  background: #f8fafc;
  padding-left: 8px;
  border-radius: 8px;
}

.item-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
  color: #4338ca;
  font-size: 14px;
  flex-shrink: 0;
}

.info-item span {
  color: #64748b;
  font-size: 14px;
  flex: 1;
}

.info-item strong {
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.status-active {
  color: #166534 !important;
  background: #dcfce7;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px !important;
}

.status-disabled {
  color: #991b1b !important;
  background: #fee2e2;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px !important;
}

.state-text {
  color: #64748b;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  text-align: center;
}

.state-text.error {
  color: #ef4444;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f4f6;
  border-top: 3px solid #8b5cf6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fee2e2;
  color: #ef4444;
  font-size: 24px;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  transition: all 0.3s ease;
}

.form-group:hover {
  transform: translateX(4px);
}

.password-form label {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.password-form label span {
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrapper i {
  position: absolute;
  left: 12px;
  color: #94a3b8;
  font-size: 16px;
}

.password-form input {
  height: 48px;
  border-radius: 12px;
  border: 1px solid #cbd5e1;
  padding: 0 12px 0 40px;
  outline: none;
  font-size: 14px;
  transition: all 0.3s ease;
  background: #ffffff;
}

.password-form input:focus {
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
  transform: translateY(-2px);
}

.btn-primary {
  border: 0;
  border-radius: 12px;
  height: 48px;
  background: linear-gradient(135deg, #8b5cf6, #ec4899);
  color: #ffffff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
  margin-top: 8px;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4);
}

.btn-primary:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.icon-user::before {
  content: '👤';
}

.icon-password::before {
  content: '🔒';
}

.icon-name::before {
  content: '📛';
}

.icon-account::before {
  content: '📧';
}

.icon-role::before {
  content: '🎭';
}

.icon-status::before {
  content: '📊';
}

.icon-time::before {
  content: '⏰';
}

.icon-lock::before {
  content: '🔐';
}

.icon-save::before {
  content: '💾';
}

.icon-error::before {
  content: '⚠️';
}

.animate-fade-in {
  animation: fadeIn 0.6s ease-in-out;
}

.animate-slide-up {
  animation: slideUp 0.6s ease-out;
}

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

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 980px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .profile-card {
    padding: 20px;
  }

  .card-header {
    margin-bottom: 16px;
  }

  .header-icon {
    width: 40px;
    height: 40px;
    font-size: 16px;
  }

  .profile-card h3 {
    font-size: 16px;
  }

  .info-item {
    gap: 12px;
    padding: 10px 0;
  }

  .item-icon {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }

  .password-form input {
    height: 44px;
  }

  .btn-primary {
    height: 44px;
  }
}
</style>
