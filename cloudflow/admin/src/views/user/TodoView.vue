<template>
  <UserLayout title="待办事项" description="管理您的日常任务，提高工作效率" :items="userNavItems">
    <div class="todo-container">
      <div class="todo-header">
        <button class="add-todo-btn" @click="showAddModal = true">
          <span class="btn-icon">+</span>
          <span>添加待办</span>
        </button>
      </div>
      
      <div class="todo-stats">
        <div class="stat-card">
          <div class="stat-icon stat-icon-all">📋</div>
          <div class="stat-number">{{ todos.length }}</div>
          <div class="stat-label">全部任务</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon stat-icon-pending">⏳</div>
          <div class="stat-number">{{ pendingTodos.length }}</div>
          <div class="stat-label">未完成</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon stat-icon-completed">✅</div>
          <div class="stat-number">{{ completedTodos.length }}</div>
          <div class="stat-label">已完成</div>
        </div>
      </div>
      
      <div class="todo-filters">
        <button 
          v-for="filter in filters" 
          :key="filter.value"
          :class="{ active: currentFilter === filter.value }"
          @click="currentFilter = filter.value"
        >
          {{ filter.label }}
        </button>
      </div>
      
      <div class="todo-list">
        <div 
          v-for="(todo, index) in filteredTodos" 
          :key="todo.id"
          class="todo-item"
          :style="{ animationDelay: `${index * 0.05}s` }"
        >
          <div class="todo-content">
            <div class="checkbox-container">
              <input 
                type="checkbox" 
                :checked="todo.completed"
                @change="toggleTodo(todo.id)"
                class="todo-checkbox"
              >
              <span class="checkbox-indicator"></span>
            </div>
            <div class="todo-info">
              <h3 :class="{ 'completed': todo.completed }">{{ todo.title }}</h3>
              <p>{{ todo.description }}</p>
              <div class="todo-meta">
                <span class="due-date">
                  <i class="meta-icon">📅</i>
                  {{ formatDate(todo.due_date) }}
                </span>
                <span :class="['priority', todo.priority]">
                  <i class="meta-icon">{{ getPriorityIcon(todo.priority) }}</i>
                  {{ getPriorityText(todo.priority) }}
                </span>
              </div>
            </div>
          </div>
          <div class="todo-actions">
            <button @click="editTodo(todo)" class="action-btn edit" title="编辑">
              <i class="action-icon">✏️</i>
            </button>
            <button @click="deleteTodo(todo.id)" class="action-btn delete" title="删除">
              <i class="action-icon">🗑️</i>
            </button>
          </div>
        </div>
        <div v-if="filteredTodos.length === 0" class="empty-state">
          <div class="empty-icon">📋</div>
          <h3>暂无待办事项</h3>
          <p>{{ getEmptyStateMessage() }}</p>
        </div>
      </div>
      
      <!-- 添加/编辑模态框 -->
      <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h2>{{ editingTodo ? '编辑待办' : '添加待办' }}</h2>
            <button class="modal-close" @click="showAddModal = false">×</button>
          </div>
          <form @submit.prevent="saveTodo">
            <div class="form-group">
              <label>标题</label>
              <input 
                type="text" 
                v-model="formData.title"
                required
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label>描述</label>
              <textarea v-model="formData.description" class="form-textarea"></textarea>
            </div>
            <div class="form-group">
              <label>截止日期</label>
              <input 
                type="date" 
                v-model="formData.due_date"
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label>优先级</label>
              <select v-model="formData.priority" class="form-select">
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
              </select>
            </div>
            <div class="form-group">
              <label>状态</label>
              <select v-model="formData.completed" class="form-select">
                <option :value="false">未完成</option>
                <option :value="true">已完成</option>
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
import UserLayout from '@/layouts/UserLayout.vue'
import { userNavItems } from '@/constants/userNavigation'
import http from '@/api/http'

export default {
  components: {
    UserLayout
  },
  data() {
    return {
      userNavItems,
      todos: [],
      showAddModal: false,
      editingTodo: null,
      formData: {
        title: '',
        description: '',
        due_date: '',
        priority: 'medium',
        completed: false
      },
      currentFilter: 'all',
      filters: [
        { label: '全部', value: 'all' },
        { label: '未完成', value: 'pending' },
        { label: '已完成', value: 'completed' }
      ]
    }
  },
  computed: {
    pendingTodos() {
      return this.todos.filter(todo => !todo.completed)
    },
    completedTodos() {
      return this.todos.filter(todo => todo.completed)
    },
    filteredTodos() {
      if (this.currentFilter === 'all') {
        return this.todos
      } else if (this.currentFilter === 'pending') {
        return this.pendingTodos
      } else if (this.currentFilter === 'completed') {
        return this.completedTodos
      }
      return this.todos
    }
  },
  mounted() {
    this.fetchTodos()
  },
  methods: {
    async fetchTodos() {
      try {
        const data = await http.get('/user/todos')
        this.todos = data
      } catch (error) {
        console.error('获取待办事项失败:', error)
      }
    },
    async saveTodo() {
      // 表单验证
      if (!this.formData.title) {
        alert('请填写标题')
        return
      }
      
      try {
        if (this.editingTodo) {
          await http.put(`/user/todos/${this.editingTodo.id}`, this.formData)
        } else {
          await http.post('/user/todos', this.formData)
        }
        this.showAddModal = false
        this.fetchTodos()
        this.resetForm()
      } catch (error) {
        console.error('保存待办事项失败:', error)
        alert('保存失败: ' + error.message)
      }
    },
    async toggleTodo(id) {
      try {
        const todo = this.todos.find(t => t.id === id)
        await http.put(`/user/todos/${id}`, { completed: !todo.completed })
        this.fetchTodos()
      } catch (error) {
        console.error('更新待办事项失败:', error)
      }
    },
    async deleteTodo(id) {
      try {
        await http.delete(`/user/todos/${id}`)
        this.fetchTodos()
      } catch (error) {
        console.error('删除待办事项失败:', error)
      }
    },
    editTodo(todo) {
      this.editingTodo = todo
      this.formData = { ...todo }
      this.showAddModal = true
    },
    resetForm() {
      this.editingTodo = null
      this.formData = {
        title: '',
        description: '',
        due_date: '',
        priority: 'medium',
        completed: false
      }
    },
    formatDate(dateString) {
      if (!dateString) return '无截止日期'
      const date = new Date(dateString)
      return date.toLocaleDateString('zh-CN')
    },
    getPriorityIcon(priority) {
      switch (priority) {
        case 'high':
          return '🔥'
        case 'medium':
          return '⚠️'
        case 'low':
          return '💡'
        default:
          return '📌'
      }
    },
    getPriorityText(priority) {
      switch (priority) {
        case 'high':
          return '高优先级'
        case 'medium':
          return '中优先级'
        case 'low':
          return '低优先级'
        default:
          return priority
      }
    },
    getEmptyStateMessage() {
      switch (this.currentFilter) {
        case 'pending':
          return '所有任务都已完成，真棒！'
        case 'completed':
          return '还没有已完成的任务'
        default:
          return '开始添加您的第一个待办事项吧'
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

.todo-container {
  padding: 20px;
  width: 100%;
}

.todo-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 30px;
}

.add-todo-btn {
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

.add-todo-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
}

.btn-icon {
  font-size: 20px;
  font-weight: bold;
}

.todo-stats {
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

.stat-icon-pending {
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

.todo-filters {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
  background: white;
  padding: 10px;
  border-radius: 24px;
  box-shadow: var(--card-shadow);
}

.todo-filters button {
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

.todo-filters button:hover {
  background: rgba(64, 158, 255, 0.1);
  color: var(--primary-color);
}

.todo-filters button.active {
  background: linear-gradient(135deg, var(--primary-color), #667eea);
  color: white;
  border-color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

.todo-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.todo-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: white;
  padding: 20px;
  border-radius: 24px;
  box-shadow: var(--card-shadow);
  transition: var(--transition);
  animation: fadeInUp 0.4s ease-out;
  position: relative;
  overflow: hidden;
}

.todo-item::before {
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

.todo-item:hover::before {
  transform: scaleY(1);
}

.todo-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.todo-content {
  display: flex;
  gap: 16px;
  flex: 1;
}

.checkbox-container {
  position: relative;
  margin-top: 4px;
}

.todo-checkbox {
  position: absolute;
  opacity: 0;
  cursor: pointer;
  height: 0;
  width: 0;
}

.checkbox-indicator {
  position: relative;
  height: 24px;
  width: 24px;
  background-color: #f0f2f5;
  border-radius: 50%;
  transition: var(--transition);
  cursor: pointer;
}

.checkbox-container:hover .checkbox-indicator {
  background-color: #e4e7eb;
}

.todo-checkbox:checked ~ .checkbox-indicator {
  background: linear-gradient(135deg, var(--success-color), #85ce61);
}

.checkbox-indicator::after {
  content: '';
  position: absolute;
  display: none;
  left: 8px;
  top: 4px;
  width: 6px;
  height: 12px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.todo-checkbox:checked ~ .checkbox-indicator::after {
  display: block;
}

.todo-info {
  flex: 1;
}

.todo-info h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--dark-color);
  margin-bottom: 8px;
  transition: var(--transition);
}

.todo-info h3.completed {
  text-decoration: line-through;
  color: var(--info-color);
  opacity: 0.7;
}

.todo-info p {
  font-size: 14px;
  color: var(--info-color);
  margin-bottom: 12px;
  line-height: 1.5;
}

.todo-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  align-items: center;
}

.meta-icon {
  margin-right: 4px;
}

.due-date {
  color: var(--info-color);
  display: flex;
  align-items: center;
}

.priority {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  transition: var(--transition);
}

.priority.low {
  background-color: rgba(103, 194, 58, 0.1);
  color: var(--success-color);
}

.priority.medium {
  background-color: rgba(230, 162, 60, 0.1);
  color: var(--warning-color);
}

.priority.high {
  background-color: rgba(245, 108, 108, 0.1);
  color: var(--danger-color);
}

.todo-actions {
  display: flex;
  gap: 8px;
  align-items: flex-start;
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

.empty-state {
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

@media (max-width: 768px) {
  .todo-container {
    padding: 16px;
  }
  
  .todo-header {
    justify-content: center;
  }
  
  .add-todo-btn {
    width: 100%;
    justify-content: center;
  }
  
  .todo-stats {
    flex-direction: column;
    gap: 14px;
  }
  
  .todo-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
  }
  
  .todo-actions {
    align-self: stretch;
    justify-content: flex-end;
  }
}
</style>