<template>
  <UserLayout title="密码本" description="安全管理您的所有账号密码" :items="userNavItems">
    <div class="password-book-container">
      <div class="password-header">
        <button class="add-password-btn" @click="showAddModal = true">
          <span class="btn-icon">+</span>
          <span>添加密码</span>
        </button>
      </div>
    
    <div class="password-search">
      <div class="search-container">
        <i class="search-icon">🔍</i>
        <input 
          type="text" 
          v-model="searchQuery"
          placeholder="搜索应用名称、账号..."
          class="search-input"
        >
        <button v-if="searchQuery" class="clear-search" @click="searchQuery = ''">×</button>
      </div>
    </div>
    
    <div class="password-grid">
      <div 
        v-for="(password, index) in filteredPasswords" 
        :key="password.id"
        class="password-card"
        :style="{ animationDelay: `${index * 0.05}s` }"
      >
        <div class="password-card-header">
          <div class="app-info">
            <div class="app-icon" :style="{ backgroundColor: getAppColor(password.app) }">
              {{ getAppIcon(password.app) }}
            </div>
            <h3 class="app-name">{{ password.app }}</h3>
          </div>
          <div class="card-actions">
            <button @click="editPassword(password)" class="action-btn edit" title="编辑">
              <i class="action-icon">✏️</i>
            </button>
            <button @click="deletePassword(password.id)" class="action-btn delete" title="删除">
              <i class="action-icon">🗑️</i>
            </button>
          </div>
        </div>
        
        <div class="password-card-body">
          <div class="credential-item">
            <label>账号</label>
            <div class="credential-value">
              <span>{{ password.username }}</span>
              <button class="copy-btn" @click="copyToClipboard(password.username)" title="复制账号">
                <i class="copy-icon">📋</i>
              </button>
            </div>
          </div>
          
          <div class="credential-item">
            <label>密码</label>
            <div class="credential-value">
              <span :class="{ 'password-hidden': !password.visible }">
                {{ password.visible ? password.password : '••••••••' }}
              </span>
              <div class="password-actions">
                <button class="toggle-btn" @click="password.visible = !password.visible" title="{{ password.visible ? '隐藏密码' : '显示密码' }}">
                  <i class="toggle-icon">{{ password.visible ? '👁️‍🗨️' : '👁️' }}</i>
                </button>
                <button class="copy-btn" @click="copyToClipboard(password.password)" title="复制密码">
                  <i class="copy-icon">📋</i>
                </button>
              </div>
            </div>
          </div>
          
          <div v-if="password.note" class="credential-item">
            <label>备注</label>
            <div class="credential-value note-value">
              {{ password.note }}
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="filteredPasswords.length === 0" class="empty-state">
        <div class="empty-icon">🔒</div>
        <h3>暂无密码</h3>
        <p>{{ getEmptyStateMessage() }}</p>
      </div>
    </div>
    
    <!-- 添加/编辑模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ editingPassword ? '编辑密码' : '添加密码' }}</h2>
          <button class="modal-close" @click="showAddModal = false">×</button>
        </div>
        <form @submit.prevent="savePassword">
          <div class="form-group">
            <label>应用名称</label>
            <input 
              type="text" 
              v-model="formData.app"
              required
              class="form-input"
            >
          </div>
          <div class="form-group">
            <label>账号</label>
            <input 
              type="text" 
              v-model="formData.username"
              required
              class="form-input"
            >
          </div>
          <div class="form-group">
            <label>密码</label>
            <div class="password-input-group">
              <input 
                :type="showPassword ? 'text' : 'password'"
                v-model="formData.password"
                required
                class="form-input"
              >
              <button 
                type="button" 
                class="toggle-password-btn"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? '隐藏' : '显示' }}
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>备注</label>
            <textarea v-model="formData.note" class="form-textarea"></textarea>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showAddModal = false">取消</button>
            <button type="submit" class="btn-primary">保存</button>
          </div>
        </form>
      </div>
    </div>
    </div>
  </UserLayout>
</template>

<script>
import UserLayout from '@/layouts/UserLayout.vue';
import { userNavItems } from '@/constants/userNavigation';
import http from '@/api/http';

export default {
  components: {
    UserLayout
  },
  data() {
    return {
      userNavItems,
      passwords: [],
      searchQuery: '',
      showAddModal: false,
      editingPassword: null,
      showPassword: false,
      formData: {
        app: '',
        username: '',
        password: '',
        note: ''
      },
      // 应用图标颜色映射
      appColors: {
        'GitHub': '#333',
        '微信': '#07C160',
        '支付宝': '#1677FF',
        'Gmail': '#EA4335',
        'Netflix': '#E50914',
        '京东': '#E1251B',
        '淘宝': '#FF4400',
        '百度': '#317EF3',
        '腾讯': '#00A870',
        '微博': '#E6162D'
      }
    }
  },
  computed: {
    filteredPasswords() {
      if (!this.searchQuery) {
        return this.passwords
      }
      const query = this.searchQuery.toLowerCase()
      return this.passwords.filter(password => 
        password.app.toLowerCase().includes(query) ||
        password.username.toLowerCase().includes(query) ||
        (password.note && password.note.toLowerCase().includes(query))
      )
    }
  },
  mounted() {
    this.fetchPasswords()
  },
  methods: {
    async fetchPasswords() {
      try {
        const data = await http.get('/user/passwords')
        this.passwords = data
        // 初始化密码可见性
        this.passwords.forEach(password => {
          password.visible = false
        })
      } catch (error) {
        console.error('获取密码失败:', error)
      }
    },
    async savePassword() {
      try {
        if (this.editingPassword) {
          await http.put(`/user/passwords/${this.editingPassword.id}`, this.formData)
        } else {
          await http.post('/user/passwords', this.formData)
        }
        this.showAddModal = false
        this.fetchPasswords()
        this.resetForm()
      } catch (error) {
        console.error('保存密码失败:', error)
      }
    },
    async deletePassword(id) {
      try {
        await http.delete(`/user/passwords/${id}`)
        this.fetchPasswords()
      } catch (error) {
        console.error('删除密码失败:', error)
      }
    },
    editPassword(password) {
      this.editingPassword = password
      this.formData = { ...password }
      this.showAddModal = true
    },
    resetForm() {
      this.editingPassword = null
      this.formData = {
        app: '',
        username: '',
        password: '',
        note: ''
      }
      this.showPassword = false
    },
    copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        // 显示更友好的复制成功提示
        this.showCopySuccess()
      }).catch(err => {
        console.error('复制失败:', err)
      })
    },
    showCopySuccess() {
      // 创建一个临时的成功提示元素
      const notification = document.createElement('div')
      notification.className = 'copy-success'
      notification.textContent = '复制成功！'
      document.body.appendChild(notification)
      
      // 添加动画效果
      setTimeout(() => {
        notification.remove()
      }, 2000)
    },
    getAppIcon(app) {
      const icons = {
        'GitHub': 'G',
        '微信': '微',
        '支付宝': '支',
        'Gmail': 'G',
        'Netflix': 'N',
        '京东': '京',
        '淘宝': '淘',
        '百度': '百',
        '腾讯': '腾',
        '微博': '微'
      }
      return icons[app] || app.charAt(0).toUpperCase()
    },
    getAppColor(app) {
      // 如果有预设颜色则使用，否则生成随机颜色
      if (this.appColors[app]) {
        return this.appColors[app]
      }
      // 生成基于应用名称的哈希颜色
      const hash = app.split('').reduce((acc, char) => {
        return acc + char.charCodeAt(0)
      }, 0)
      const hue = hash % 360
      return `hsl(${hue}, 70%, 50%)`
    },
    getEmptyStateMessage() {
      if (this.searchQuery) {
        return `没有找到与"${this.searchQuery}"相关的密码`
      }
      return '开始添加您的第一个密码吧'
    }
  }
}
</script>

<style scoped>
:root {
  --primary-color: #409eff;
  --success-color: #67c23a;
  --warning-color: #e6a23c;
  --danger-color: #f56c6c;
  --info-color: #909399;
  --light-color: #f5f7fa;
  --dark-color: #303133;
  --border-radius: 12px;
  --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  --transition: all 0.3s ease;
}

.password-book-container {
  padding: 20px;
  width: 100%;
}

.password-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 30px;
}

.add-password-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, var(--primary-color), #667eea);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 25px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  transition: var(--transition);
}

.add-password-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
}

.btn-icon {
  font-size: 20px;
  font-weight: bold;
}

.password-search {
  margin-bottom: 30px;
}

.search-container {
  position: relative;
  background: white;
  border-radius: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  transition: var(--transition);
}

.search-container:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.search-icon {
  position: absolute;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  color: #909399;
  font-size: 18px;
  transition: var(--transition);
}

.search-input {
  width: 100%;
  padding: 18px 20px 18px 56px;
  border: none;
  border-radius: 24px;
  font-size: 15px;
  transition: var(--transition);
  outline: none;
  background: transparent;
}

.search-input:focus {
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
}

.search-input:focus + .search-icon {
  color: #667eea;
  transform: translateY(-50%) scale(1.1);
}

.clear-search {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(144, 147, 153, 0.1);
  border: none;
  color: #909399;
  font-size: 16px;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
}

.clear-search:hover {
  background: rgba(102, 126, 234, 0.2);
  color: #667eea;
  transform: translateY(-50%) scale(1.1);
}

.password-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 24px;
}

.password-card {
  background: white;
  border-radius: 24px;
  box-shadow: var(--card-shadow);
  transition: var(--transition);
  animation: fadeInUp 0.4s ease-out;
  position: relative;
  overflow: hidden;
}

.password-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--primary-color);
  transform: scaleY(0);
  transition: var(--transition);
}

.password-card:hover::before {
  transform: scaleY(1);
}

.password-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.password-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 0 24px;
  margin-bottom: 20px;
}

.app-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  color: white;
  font-size: 20px;
  font-weight: bold;
  transition: var(--transition);
}

.app-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--dark-color);
  margin: 0;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 8px;
  border: 2px solid transparent;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  transition: var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
}

.action-btn.edit {
  color: var(--primary-color);
  border-color: rgba(64, 158, 255, 0.3);
  background-color: rgba(64, 158, 255, 0.1);
}

.action-btn.edit:hover {
  background-color: var(--primary-color);
  color: white;
  transform: scale(1.1);
}

.action-btn.delete {
  color: var(--danger-color);
  border-color: rgba(245, 108, 108, 0.3);
  background-color: rgba(245, 108, 108, 0.1);
}

.action-btn.delete:hover {
  background-color: var(--danger-color);
  color: white;
  transform: scale(1.1);
}

.password-card-body {
  padding: 0 24px 24px 24px;
}

.credential-item {
  margin-bottom: 20px;
}

.credential-item label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--info-color);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.credential-value {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f9f9f9;
  padding: 12px 16px;
  border-radius: 8px;
  transition: var(--transition);
}

.credential-value:hover {
  background: #f0f2f5;
}

.credential-value span {
  font-size: 14px;
  color: var(--dark-color);
  font-weight: 500;
  word-break: break-all;
}

.password-hidden {
  font-family: monospace;
  letter-spacing: 2px;
}

.password-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.copy-btn,
.toggle-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
}

.copy-btn:hover,
.toggle-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  transform: scale(1.1);
}

.copy-icon,
.toggle-icon {
  font-size: 16px;
  color: var(--info-color);
  transition: var(--transition);
}

.copy-btn:hover .copy-icon,
.toggle-btn:hover .toggle-icon {
  color: var(--primary-color);
}

.note-value {
  min-height: 60px;
  align-items: flex-start;
  padding: 16px;
}

.note-value span {
  font-style: italic;
  color: var(--info-color);
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 80px 40px;
  background: white;
  border-radius: var(--border-radius);
  box-shadow: var(--card-shadow);
  margin-top: 40px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 24px;
  opacity: 0.5;
}

.empty-state h3 {
  font-size: 20px;
  color: var(--dark-color);
  margin-bottom: 12px;
}

.empty-state p {
  font-size: 16px;
  color: var(--info-color);
  margin: 0;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease;
}

.modal-content {
  background: white;
  border-radius: var(--border-radius);
  width: 90%;
  max-width: 500px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  animation: slideInUp 0.4s ease;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #f0f0f0;
  background: linear-gradient(135deg, var(--primary-color), #667eea);
  color: white;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.modal-close {
  background: transparent;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: var(--transition);
}

.modal-close:hover {
  background: rgba(255, 255, 255, 0.2);
}

.modal-content form {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--dark-color);
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #f0f2f5;
  border-radius: 8px;
  font-size: 14px;
  transition: var(--transition);
  background: white;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 120px;
}

.password-input-group {
  display: flex;
  gap: 10px;
}

.password-input-group input {
  flex: 1;
}

.toggle-password-btn {
  padding: 0 20px;
  border: 2px solid #f0f2f5;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--info-color);
  transition: var(--transition);
}

.toggle-password-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.btn-secondary {
  padding: 10px 20px;
  border: 2px solid #f0f2f5;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--info-color);
  transition: var(--transition);
}

.btn-secondary:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.btn-primary {
  padding: 10px 24px;
  border: none;
  background: linear-gradient(135deg, var(--primary-color), #667eea);
  color: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: var(--transition);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
}

/* 复制成功提示 */
.copy-success {
  position: fixed;
  top: 20px;
  right: 20px;
  background: linear-gradient(135deg, var(--success-color), #85ce61);
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.3);
  font-size: 14px;
  font-weight: 500;
  animation: slideInRight 0.3s ease, fadeOut 2s ease 1.7s forwards;
  z-index: 10000;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes fadeOut {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}

@media (max-width: 768px) {
  .password-book-container {
    padding: 20px;
  }
  
  .password-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
  
  .add-password-btn {
    align-self: stretch;
  }
  
  .password-grid {
    grid-template-columns: 1fr;
  }
  
  .password-card {
    padding: 20px;
  }
  
  .password-card-header {
    padding: 0 0 16px 0;
  }
  
  .password-card-body {
    padding: 0;
  }
  
  .password-input-group {
    flex-direction: column;
  }
  
  .toggle-password-btn {
    padding: 12px;
  }
}
</style>