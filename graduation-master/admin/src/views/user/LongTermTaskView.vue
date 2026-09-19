<template>
  <UserLayout title="长期任务" description="追踪您的长期项目，实现更大的目标" :items="userNavItems">
    <div class="long-term-task-container">
      <div class="task-header">
        <button class="add-task-btn" @click="showAddModal = true">
          <span class="btn-icon">+</span>
          <span>新建项目</span>
        </button>
      </div>
      
      <div class="task-stats">
        <div class="stat-card" v-for="(stat, index) in stats" :key="index" :style="{ animationDelay: `${index * 0.1}s` }">
          <div class="stat-icon" :class="stat.iconClass">{{ stat.icon }}</div>
          <div class="stat-number">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </div>
      
      <div class="task-filters">
        <button 
          v-for="filter in filters" 
          :key="filter.value"
          :class="{ active: currentFilter === filter.value }"
          @click="currentFilter = filter.value"
        >
          {{ filter.label }}
        </button>
      </div>
      
      <div class="task-grid">
        <div 
          v-for="(project, index) in filteredProjects" 
          :key="project.id"
          class="project-card"
          :style="{ animationDelay: `${index * 0.05}s` }"
        >
          <div class="project-header">
            <h3>{{ project.title }}</h3>
            <div class="project-actions">
              <button @click="editProject(project)" class="action-btn edit" title="编辑">
                <i class="action-icon">✏️</i>
              </button>
              <button @click="deleteProject(project.id)" class="action-btn delete" title="删除">
                <i class="action-icon">🗑️</i>
              </button>
            </div>
          </div>
          <p class="project-description">{{ project.description }}</p>
          <div class="project-progress">
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: project.progress + '%', backgroundColor: getProgressColor(project.progress) }"
              ></div>
            </div>
            <div class="progress-text">{{ project.progress }}%</div>
          </div>
          <div class="project-meta">
            <span class="project-status" :class="getStatusClass(project.status)">
              <i class="status-icon">{{ getStatusIcon(project.status) }}</i>
              {{ project.status }}
            </span>
            <span class="project-days">
              <i class="days-icon">⏰</i>
              {{ project.days_left }} 天
            </span>
          </div>
        </div>
        <div v-if="filteredProjects.length === 0" class="empty-state">
          <div class="empty-icon">📊</div>
          <h3>暂无项目</h3>
          <p>{{ getEmptyStateMessage() }}</p>
        </div>
      </div>
      
      <!-- 添加/编辑模态框 -->
      <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h2>{{ editingProject ? '编辑项目' : '新建项目' }}</h2>
            <button class="modal-close" @click="showAddModal = false">×</button>
          </div>
          <form @submit.prevent="saveProject">
            <div class="form-group">
              <label>项目名称</label>
              <input 
                type="text" 
                v-model="formData.title"
                required
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label>项目描述</label>
              <textarea v-model="formData.description" class="form-textarea"></textarea>
            </div>
            <div class="form-group">
              <label>目标进度</label>
              <div class="progress-input-group">
                <input 
                  type="range" 
                  v-model="formData.progress"
                  min="0"
                  max="100"
                  class="progress-slider"
                >
                <span class="progress-value">{{ formData.progress }}%</span>
              </div>
              <input 
                type="number" 
                v-model="formData.progress"
                min="0"
                max="100"
                required
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label>截止日期</label>
              <input 
                type="date" 
                v-model="formData.end_date"
                required
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label>状态</label>
              <select v-model="formData.status" class="form-select">
                <option value="进行中">进行中</option>
                <option value="已暂停">已暂停</option>
                <option value="已完成">已完成</option>
              </select>
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
      projects: [],
      currentFilter: 'all',
      showAddModal: false,
      editingProject: null,
      formData: {
        title: '',
        description: '',
        progress: 0,
        end_date: '',
        status: '进行中'
      },
      filters: [
        { label: '全部', value: 'all' },
        { label: '进行中', value: 'in_progress' },
        { label: '已暂停', value: 'paused' },
        { label: '已完成', value: 'completed' }
      ]
    }
  },
  computed: {
    totalProjects() {
      return this.projects.length
    },
    inProgressProjects() {
      return this.projects.filter(project => project.status === '进行中').length
    },
    completedProjects() {
      return this.projects.filter(project => project.status === '已完成').length
    },
    filteredProjects() {
      if (this.currentFilter === 'all') {
        return this.projects
      } else if (this.currentFilter === 'in_progress') {
        return this.projects.filter(project => project.status === '进行中')
      } else if (this.currentFilter === 'paused') {
        return this.projects.filter(project => project.status === '已暂停')
      } else {
        return this.projects.filter(project => project.status === '已完成')
      }
    },
    stats() {
      return [
        {
          icon: '📊',
          iconClass: 'stat-icon-all',
          value: this.totalProjects,
          label: '全部项目'
        },
        {
          icon: '🚀',
          iconClass: 'stat-icon-in-progress',
          value: this.inProgressProjects,
          label: '进行中'
        },
        {
          icon: '✅',
          iconClass: 'stat-icon-completed',
          value: this.completedProjects,
          label: '已完成'
        }
      ]
    }
  },
  mounted() {
    this.fetchProjects()
  },
  methods: {
    async fetchProjects() {
      try {
        const data = await http.get('/user/long-term-tasks')
        this.projects = data
      } catch (error) {
        console.error('获取长期任务失败:', error)
      }
    },
    async saveProject() {
      // 表单验证
      if (!this.formData.title) {
        alert('请填写项目名称')
        return
      }
      if (!this.formData.end_date) {
        alert('请填写截止日期')
        return
      }
      
      try {
        if (this.editingProject) {
          await http.put(`/user/long-term-tasks/${this.editingProject.id}`, this.formData)
        } else {
          await http.post('/user/long-term-tasks', this.formData)
        }
        this.showAddModal = false
        this.fetchProjects()
        this.resetForm()
      } catch (error) {
        console.error('保存长期任务失败:', error)
        alert('保存失败: ' + error.message)
      }
    },
    async deleteProject(id) {
      try {
        await http.delete(`/user/long-term-tasks/${id}`)
        this.fetchProjects()
      } catch (error) {
        console.error('删除长期任务失败:', error)
      }
    },
    editProject(project) {
      this.editingProject = project
      this.formData = { ...project }
      this.showAddModal = true
    },
    resetForm() {
      this.editingProject = null
      this.formData = {
        title: '',
        description: '',
        progress: 0,
        end_date: '',
        status: '进行中'
      }
    },
    getProgressColor(progress) {
      if (progress >= 100) {
        return '#67c23a' // 成功色
      } else if (progress >= 70) {
        return '#409eff' // 主要色
      } else if (progress >= 40) {
        return '#e6a23c' // 警告色
      } else {
        return '#f56c6c' // 危险色
      }
    },
    getStatusClass(status) {
      switch (status) {
        case '进行中':
          return 'status-in-progress'
        case '已暂停':
          return 'status-paused'
        case '已完成':
          return 'status-completed'
        default:
          return ''
      }
    },
    getStatusIcon(status) {
      switch (status) {
        case '进行中':
          return '🚀'
        case '已暂停':
          return '⏸️'
        case '已完成':
          return '✅'
        default:
          return '📌'
      }
    },
    getEmptyStateMessage() {
      switch (this.currentFilter) {
        case 'in_progress':
          return '暂无进行中的项目'
        case 'paused':
          return '暂无已暂停的项目'
        case 'completed':
          return '暂无已完成的项目'
        default:
          return '开始创建您的第一个长期项目吧'
      }
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
  --border-radius: 20px;
  --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  --transition: all 0.3s ease;
}

.long-term-task-container {
  padding: 20px;
  width: 100%;
}

.task-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 30px;
}

.add-task-btn {
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

.add-task-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
}

.btn-icon {
  font-size: 20px;
  font-weight: bold;
}

.task-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  flex: 1;
  background: white;
  padding: 24px;
  border-radius: 24px;
  text-align: center;
  box-shadow: var(--card-shadow);
  transition: var(--transition);
  animation: fadeInUp 0.6s ease-out;
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--primary-color), #667eea);
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.stat-icon {
  font-size: 32px;
  margin-bottom: 12px;
  display: block;
}

.stat-icon-all {
  color: var(--primary-color);
}

.stat-icon-in-progress {
  color: var(--warning-color);
}

.stat-icon-completed {
  color: var(--success-color);
}

.stat-number {
  font-size: 28px;
  font-weight: bold;
  color: var(--dark-color);
  margin-bottom: 6px;
  font-family: 'Arial', sans-serif;
}

.stat-label {
  font-size: 12px;
  color: var(--info-color);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.task-filters {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
  background: white;
  padding: 10px;
  border-radius: 24px;
  box-shadow: var(--card-shadow);
}

.task-filters button {
  padding: 8px 16px;
  border: 2px solid transparent;
  background: transparent;
  border-radius: 25px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--info-color);
  transition: var(--transition);
  flex: 1;
  text-align: center;
}

.task-filters button:hover {
  background: rgba(64, 158, 255, 0.1);
  color: var(--primary-color);
}

.task-filters button.active {
  background: linear-gradient(135deg, var(--primary-color), #667eea);
  color: white;
  border-color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.project-card {
  background: white;
  border-radius: 24px;
  box-shadow: var(--card-shadow);
  padding: 24px;
  transition: var(--transition);
  animation: fadeInUp 0.4s ease-out;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.project-card::before {
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

.project-card:hover::before {
  transform: scaleY(1);
}

.project-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}

.project-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--dark-color);
  margin: 0 0 6px 0;
  flex: 1;
  line-height: 1.3;
}

.project-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 6px;
  border: 2px solid transparent;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
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

.project-description {
  font-size: 14px;
  color: var(--info-color);
  margin-bottom: 16px;
  line-height: 1.5;
  flex: 1;
}

.project-progress {
  margin-bottom: 16px;
}

.progress-bar {
  width: 100%;
  height: 12px;
  background-color: #f0f2f5;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 12px;
  position: relative;
}

.progress-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.5s ease, background-color 0.3s ease;
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.3) 50%, rgba(255,255,255,0) 100%);
  animation: shimmer 2s infinite;
}

.progress-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--dark-color);
  text-align: right;
}

.project-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.project-status {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  transition: var(--transition);
  gap: 6px;
}

.status-icon {
  font-size: 14px;
}

.status-in-progress {
  background-color: rgba(64, 158, 255, 0.1);
  color: var(--primary-color);
}

.status-paused {
  background-color: rgba(144, 147, 153, 0.1);
  color: var(--info-color);
}

.status-completed {
  background-color: rgba(103, 194, 58, 0.1);
  color: var(--success-color);
}

.project-days {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--info-color);
  font-weight: 500;
}

.days-icon {
  font-size: 14px;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 30px;
  background: white;
  border-radius: var(--border-radius);
  box-shadow: var(--card-shadow);
  margin-top: 30px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-state h3 {
  font-size: 18px;
  color: var(--dark-color);
  margin-bottom: 10px;
}

.empty-state p {
  font-size: 14px;
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
.form-textarea,
.form-select {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #f0f2f5;
  border-radius: 8px;
  font-size: 14px;
  transition: var(--transition);
  background: white;
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 120px;
}

.progress-input-group {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.progress-slider {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #f0f2f5;
  border-radius: 3px;
  outline: none;
  transition: var(--transition);
}

.progress-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-color), #667eea);
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.3);
  transition: var(--transition);
}

.progress-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

.progress-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  min-width: 60px;
  text-align: right;
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

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

@media (max-width: 768px) {
  .long-term-task-container {
    padding: 20px;
  }
  
  .task-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
  
  .add-task-btn {
    align-self: stretch;
  }
  
  .task-stats {
    flex-direction: column;
    gap: 16px;
  }
  
  .task-grid {
    grid-template-columns: 1fr;
  }
  
  .project-card {
    padding: 20px;
  }
  
  .progress-input-group {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .progress-value {
    text-align: center;
  }
}
</style>