<template>
  <UserLayout title="回收站" description="查看待处理文件并执行恢复或彻底删除操作。" :items="userNavItems">
    <section class="overview animate-fade-in">
      <article class="overview-card animate-slide-up">
        <div class="card-icon">
          <i class="icon-files"></i>
        </div>
        <small>回收站文件数</small>
        <strong>{{ recycleList.length }}</strong>
      </article>
      <article class="overview-card animate-slide-up" style="animation-delay: 0.1s;">
        <div class="card-icon">
          <i class="icon-size"></i>
        </div>
        <small>预计可释放容量</small>
        <strong>{{ formatBytes(totalRecycleSize) }}</strong>
      </article>
      <article class="overview-card animate-slide-up" style="animation-delay: 0.2s;">
        <div class="card-icon">
          <i class="icon-expiry"></i>
        </div>
        <small>最近到期</small>
        <strong>{{ nearestExpiryText }}</strong>
      </article>
    </section>

    <section class="toolbar animate-fade-in" style="animation-delay: 0.3s;">
      <button type="button" class="btn-restore" :disabled="selectedIds.length === 0" @click="batchRestore">
        <i class="icon-restore"></i> 批量恢复
      </button>
      <button type="button" class="btn-danger" :disabled="recycleList.length === 0" @click="clearAll">
        <i class="icon-clear"></i> 清空回收站
      </button>
      <span>已选 {{ selectedIds.length }} 项</span>
    </section>

    <section v-if="loading" class="empty-state animate-fade-in">
      <div class="loading-spinner"></div>
      <div>
        <h4>正在加载回收站</h4>
        <p>请稍候...</p>
      </div>
    </section>

    <section v-else-if="errorText" class="empty-state animate-fade-in">
      <div class="error-icon">
        <i class="icon-error"></i>
      </div>
      <div>
        <h4>回收站加载失败</h4>
        <p>{{ errorText }}</p>
        <button type="button" class="btn-primary" @click="loadRecycleList">重新加载</button>
      </div>
    </section>

    <section v-else class="list-wrap">
      <article v-for="(item, index) in recycleList" :key="item.id" class="recycle-card animate-slide-up" :style="{ 'animation-delay': `${0.1 * index}s` }">
        <label class="check-wrap">
          <input type="checkbox" :checked="selectedIds.includes(item.id)" @change="toggleSelect(item.id)" />
        </label>
        <div class="recycle-icon">
          <i class="icon-recycle"></i>
        </div>
        <div class="left">
          <h3>{{ item.fileName }}</h3>
          <p class="meta">
            <span>类型：{{ item.typeLabel }}</span>
            <span>容量：{{ formatBytes(item.sizeBytes) }}</span>
            <span>删除时间：{{ item.deletedAt }}</span>
            <span>剩余保留：{{ item.remainingDays }} 天</span>
          </p>
        </div>
        <div class="actions">
          <button type="button" class="btn-restore" @click="restoreItem(item.id)">
            <i class="icon-restore"></i> 恢复
          </button>
          <button type="button" class="btn-danger" @click="deleteForever(item.id)">
            <i class="icon-delete"></i> 彻底删除
          </button>
        </div>
      </article>

      <div v-if="recycleList.length === 0" class="empty-state animate-fade-in">
        <div class="empty-icon">
          <i class="icon-empty"></i>
        </div>
        <div>
          <h4>回收站为空</h4>
          <p>你已经清理完全部待处理文件。</p>
        </div>
      </div>
    </section>
  </UserLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { batchRestoreRecycleApi, clearRecycleApi, deleteRecycleApi, fetchRecycleListApi, restoreRecycleApi } from '@/api/recycle'
import UserLayout from '@/layouts/UserLayout.vue'
import { userNavItems } from '@/constants/userNavigation'

const recycleList = ref([])
const selectedIds = ref([])
const loading = ref(false)
const errorText = ref('')

const totalRecycleSize = computed(() => recycleList.value.reduce((sum, item) => sum + item.sizeBytes, 0))

const nearestExpiryText = computed(() => {
  if (recycleList.value.length === 0) {
    return '无'
  }
  const nearest = [...recycleList.value].sort((a, b) => a.remainingDays - b.remainingDays)[0]
  return `${nearest.remainingDays} 天`
})

const loadRecycleList = async () => {
  loading.value = true
  errorText.value = ''

  try {
    const data = await fetchRecycleListApi({ page: 1, pageSize: 200 })
    recycleList.value = data.items || []
    selectedIds.value = selectedIds.value.filter((id) => recycleList.value.some((item) => item.id === id))
  } catch (error) {
    errorText.value = error?.message || '加载失败'
    recycleList.value = []
    selectedIds.value = []
  } finally {
    loading.value = false
  }
}

const toggleSelect = (id) => {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter((itemId) => itemId !== id)
    return
  }
  selectedIds.value = [...selectedIds.value, id]
}

const formatBytes = (bytes) => {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const restoreItem = async (id) => {
  try {
    await restoreRecycleApi(id)
    ElMessage.success('文件已恢复')
    selectedIds.value = selectedIds.value.filter((itemId) => itemId !== id)
    await loadRecycleList()
  } catch (error) {
    ElMessage.warning(error?.message || '恢复失败')
  }
}

const deleteForever = async (id) => {
  try {
    await deleteRecycleApi(id)
    ElMessage.warning('文件已彻底删除')
    selectedIds.value = selectedIds.value.filter((itemId) => itemId !== id)
    await loadRecycleList()
  } catch (error) {
    ElMessage.warning(error?.message || '删除失败')
  }
}

const batchRestore = async () => {
  if (selectedIds.value.length === 0) {
    return
  }

  try {
    await batchRestoreRecycleApi(selectedIds.value)
    ElMessage.success('批量恢复成功')
    selectedIds.value = []
    await loadRecycleList()
  } catch (error) {
    ElMessage.warning(error?.message || '批量恢复失败')
  }
}

const clearAll = async () => {
  if (recycleList.value.length === 0) {
    return
  }

  try {
    await clearRecycleApi()
    ElMessage.success('回收站已清空')
    selectedIds.value = []
    await loadRecycleList()
  } catch (error) {
    ElMessage.warning(error?.message || '清空失败')
  }
}

onMounted(() => {
  loadRecycleList()
})
</script>

<style scoped>
.overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.overview-card,
.recycle-card,
.empty-state,
.toolbar {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 20px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
  transition: all 0.3s ease;
}

.overview-card {
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.overview-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #f59e0b, #ef4444);
}

.overview-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.12);
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  font-size: 20px;
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
}

.icon-files {
  color: #f59e0b;
}

.icon-files::before {
  content: '📁';
}

.icon-size {
  color: #3b82f6;
}

.icon-size::before {
  content: '💾';
}

.icon-expiry {
  color: #ef4444;
}

.icon-expiry::before {
  content: '⏰';
}

.overview-card small {
  color: #64748b;
  display: block;
  font-size: 14px;
  margin-bottom: 8px;
}

.overview-card strong {
  display: block;
  font-size: 32px;
  color: #0f172a;
  font-weight: 700;
  transition: all 0.3s ease;
}

.overview-card:hover strong {
  transform: scale(1.05);
}

.toolbar {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.toolbar span {
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  margin-left: auto;
}

.list-wrap {
  display: grid;
  gap: 16px;
}

.recycle-card {
  padding: 20px;
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  gap: 20px;
  align-items: center;
  position: relative;
}

.recycle-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.12);
}

.check-wrap {
  display: flex;
  align-items: start;
  padding-top: 4px;
}

.check-wrap input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: #f59e0b;
  cursor: pointer;
}

.recycle-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  color: #f59e0b;
  flex-shrink: 0;
}

.left h3 {
  margin: 0 0 12px;
  color: #0f172a;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.recycle-card:hover h3 {
  color: #f59e0b;
}

.meta {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: #64748b;
  font-size: 13px;
}

.actions {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.btn-restore,
.btn-danger,
.btn-primary {
  border: 0;
  border-radius: 12px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.btn-restore {
  background: linear-gradient(135deg, #0ea5e9, #38bdf8);
  color: #ffffff;
}

.btn-restore:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(14, 165, 233, 0.4);
}

.btn-danger {
  background: linear-gradient(135deg, #ef4444, #f87171);
  color: #ffffff;
}

.btn-danger:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4);
}

.btn-primary {
  background: linear-gradient(135deg, #4f46e5, #8b5cf6);
  color: #ffffff;
  margin-top: 16px;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.4);
}

.btn-restore:disabled,
.btn-danger:disabled,
.btn-primary:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.empty-state {
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 30px;
  margin-bottom: 20px;
}

.empty-state h4 {
  margin: 16px 0 8px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 600;
}

.empty-state p {
  margin: 0 0 20px;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f4f6;
  border-top: 3px solid #f59e0b;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon,
.empty-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  font-size: 24px;
}

.error-icon {
  background: #fee2e2;
  color: #ef4444;
}

.empty-icon {
  background: #fef3c7;
  color: #f59e0b;
}

.icon-restore::before {
  content: '↩️';
}

.icon-clear::before {
  content: '🗑️';
}

.icon-delete::before {
  content: '💥';
}

.icon-recycle::before {
  content: '♻️';
}

.icon-error::before {
  content: '⚠️';
}

.icon-empty::before {
  content: '📭';
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

@media (max-width: 1100px) {
  .overview {
    grid-template-columns: 1fr;
  }

  .recycle-card {
    grid-template-columns: 1fr;
    align-items: flex-start;
  }

  .actions {
    align-self: flex-end;
  }
}

@media (max-width: 680px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .toolbar span {
    margin-left: 0;
    align-self: flex-start;
  }

  .recycle-icon {
    width: 40px;
    height: 40px;
    font-size: 16px;
  }

  .actions {
    width: 100%;
    gap: 8px;
  }

  .btn-restore,
  .btn-danger,
  .btn-primary {
    flex: 1;
    padding: 8px 12px;
    font-size: 12px;
  }
}
</style>
