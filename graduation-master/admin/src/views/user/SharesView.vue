<template>
  <UserLayout title="分享记录" description="查看分享状态、过期时间、访问方式与访问次数。" :items="userNavItems">
    <section class="summary-grid animate-fade-in">
      <article class="summary-card animate-slide-up">
        <div class="card-icon">
          <i class="icon-share"></i>
        </div>
        <small>分享总数</small>
        <strong>{{ totalCount }}</strong>
      </article>
      <article class="summary-card animate-slide-up" style="animation-delay: 0.1s;">
        <div class="card-icon">
          <i class="icon-active"></i>
        </div>
        <small>生效中</small>
        <strong>{{ activeCount }}</strong>
      </article>
      <article class="summary-card animate-slide-up" style="animation-delay: 0.2s;">
        <div class="card-icon">
          <i class="icon-expired"></i>
        </div>
        <small>已过期</small>
        <strong>{{ expiredCount }}</strong>
      </article>
      <article class="summary-card animate-slide-up" style="animation-delay: 0.3s;">
        <div class="card-icon">
          <i class="icon-visits"></i>
        </div>
        <small>访问总量</small>
        <strong>{{ totalVisits }}</strong>
      </article>
    </section>

    <section class="toolbar animate-fade-in" style="animation-delay: 0.4s;">
      <button type="button" :disabled="selectedIds.length === 0" @click="batchCancel" class="btn-primary">
        <i class="icon-batch"></i> 批量取消分享
      </button>
      <span>已选 {{ selectedIds.length }} 项</span>
    </section>

    <section v-if="loading" class="state-card animate-fade-in">
      <div class="loading-spinner"></div>
      <p>正在加载分享记录...</p>
    </section>

    <section v-else-if="errorText" class="state-card animate-fade-in">
      <div class="error-icon">
        <i class="icon-error"></i>
      </div>
      <h4>分享记录加载失败</h4>
      <p>{{ errorText }}</p>
      <button type="button" @click="loadShares" class="btn-primary">重新加载</button>
    </section>

    <section v-else-if="records.length === 0" class="state-card animate-fade-in">
      <div class="empty-icon">
        <i class="icon-empty"></i>
      </div>
      <h4>暂无分享记录</h4>
      <p>在文件管理中创建分享后，将在这里查看历史记录。</p>
    </section>

    <section v-else class="record-list">
      <article v-for="(record, index) in records" :key="record.id" class="record-card animate-slide-up" :style="{ 'animation-delay': `${0.1 * index}s` }">
        <label class="check-wrap">
          <input type="checkbox" :checked="selectedIds.includes(record.id)" @change="toggleSelect(record.id)" />
        </label>

        <div class="record-main">
          <h3>{{ record.fileName }}</h3>
          <p class="link">{{ record.link }}</p>
          <p class="meta">
            <span>分享状态：<strong>{{ record.status }}</strong></span>
            <span>过期时间：{{ record.expireAt }}</span>
            <span>访问方式：{{ record.accessMode }}</span>
            <span>访问次数：{{ record.visits }}</span>
          </p>
        </div>
        <div class="record-actions">
          <span class="status-tag" :class="statusClass(record.status)">{{ record.status }}</span>
          <button type="button" @click="copyLink(record.link)" class="btn-secondary">
            <i class="icon-copy"></i> 复制链接
          </button>
          <button
            type="button"
            class="btn-ghost"
            :disabled="record.status === '已取消'"
            @click="cancelShare(record.id)"
          >
            <i class="icon-cancel"></i> 取消分享
          </button>
          <button type="button" class="btn-danger" @click="removeShare(record.id)">
            <i class="icon-delete"></i> 删除记录
          </button>
        </div>
      </article>
    </section>
  </UserLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { batchCancelShareApi, cancelShareApi, deleteShareApi, fetchShareListApi } from '@/api/shares'
import UserLayout from '@/layouts/UserLayout.vue'
import { userNavItems } from '@/constants/userNavigation'

const records = ref([])
const totalCount = ref(0)
const loading = ref(false)
const errorText = ref('')
const selectedIds = ref([])

const activeCount = computed(() => records.value.filter((item) => item.status === '生效中').length)
const expiredCount = computed(() => records.value.filter((item) => item.status === '已过期').length)
const totalVisits = computed(() => records.value.reduce((sum, item) => sum + item.visits, 0))

const loadShares = async () => {
  loading.value = true
  errorText.value = ''

  try {
    const data = await fetchShareListApi({ page: 1, pageSize: 200 })
    records.value = data.items || []
    totalCount.value = data.total || records.value.length
    selectedIds.value = selectedIds.value.filter((id) => records.value.some((item) => item.id === id))
  } catch (error) {
    errorText.value = error?.message || '加载失败'
    records.value = []
    totalCount.value = 0
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

const batchCancel = async () => {
  if (selectedIds.value.length === 0) {
    return
  }

  try {
    await batchCancelShareApi(selectedIds.value)
    ElMessage.success('批量取消分享成功')
    selectedIds.value = []
    await loadShares()
  } catch (error) {
    ElMessage.warning(error?.message || '批量取消失败')
  }
}

const statusClass = (status) => {
  if (status === '生效中') {
    return 'active'
  }
  if (status === '已过期') {
    return 'expired'
  }
  return 'closed'
}

const copyLink = (link) => {
  navigator.clipboard?.writeText(link)
  ElMessage.success('分享链接已复制')
}

const cancelShare = async (shareId) => {
  try {
    await cancelShareApi(shareId)
    ElMessage.success('分享已取消')
    await loadShares()
  } catch (error) {
    ElMessage.warning(error?.message || '取消失败')
  }
}

const removeShare = async (shareId) => {
  try {
    await deleteShareApi(shareId)
    ElMessage.success('分享记录已删除')
    selectedIds.value = selectedIds.value.filter((id) => id !== shareId)
    await loadShares()
  } catch (error) {
    ElMessage.warning(error?.message || '删除失败')
  }
}

onMounted(() => {
  loadShares()
})
</script>

<style scoped>
.summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin-bottom: 16px;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

.summary-card,
.record-card,
.state-card {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 20px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
  transition: all 0.3s ease;
}

.summary-card {
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.summary-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #4f46e5, #8b5cf6);
}

.summary-card:hover {
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
}

.icon-share {
  color: #4f46e5;
}

.icon-share::before {
  content: '📤';
}

.icon-active {
  color: #10b981;
}

.icon-active::before {
  content: '✅';
}

.icon-expired {
  color: #ef4444;
}

.icon-expired::before {
  content: '⏰';
}

.icon-visits {
  color: #f59e0b;
}

.icon-visits::before {
  content: '👁️';
}

.card-icon {
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
}

.summary-card small {
  color: #64748b;
  display: block;
  font-size: 14px;
  margin-bottom: 8px;
}

.summary-card strong {
  display: block;
  font-size: 32px;
  color: #0f172a;
  font-weight: 700;
  transition: all 0.3s ease;
}

.summary-card:hover strong {
  transform: scale(1.05);
}

.toolbar {
  min-height: auto;
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
}

.state-card {
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 30px;
  margin-bottom: 20px;
}

.state-card h4 {
  margin: 16px 0 8px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 600;
}

.state-card p {
  margin: 0 0 20px;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.record-list {
  display: grid;
  gap: 16px;
}

.record-card {
  padding: 20px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 20px;
  position: relative;
}

.record-card:hover {
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
  accent-color: #4f46e5;
  cursor: pointer;
}

.record-main h3 {
  margin: 0 0 12px;
  color: #0f172a;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.record-card:hover h3 {
  color: #4f46e5;
}

.link {
  margin: 0 0 12px;
  color: #0284c7;
  font-size: 13px;
  word-break: break-all;
  transition: all 0.3s ease;
}

.link:hover {
  color: #0369a1;
  text-decoration: underline;
}

.meta {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: #64748b;
  font-size: 13px;
}

.meta strong {
  color: #0f172a;
  font-weight: 600;
}

.record-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.status-tag {
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.status-tag.active {
  background: #dcfce7;
  color: #166534;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
}

.status-tag.expired {
  background: #fee2e2;
  color: #991b1b;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
}

.status-tag.closed {
  background: #e2e8f0;
  color: #334155;
  box-shadow: 0 4px 12px rgba(148, 163, 184, 0.2);
}

.btn-primary,
.btn-secondary,
.btn-ghost,
.btn-danger {
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

.btn-primary {
  background: linear-gradient(135deg, #4f46e5, #8b5cf6);
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.4);
}

.btn-secondary {
  background: linear-gradient(135deg, #0ea5e9, #38bdf8);
  color: #ffffff;
}

.btn-secondary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(14, 165, 233, 0.4);
}

.btn-ghost {
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
  color: #334155;
  border: 1px solid #cbd5e1;
}

.btn-ghost:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(148, 163, 184, 0.3);
}

.btn-danger {
  background: linear-gradient(135deg, #ef4444, #f87171);
  color: #ffffff;
}

.btn-danger:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4);
}

.btn-primary:disabled,
.btn-secondary:disabled,
.btn-ghost:disabled,
.btn-danger:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f4f6;
  border-top: 3px solid #4f46e5;
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
  background: #e0e7ff;
  color: #4f46e5;
}

.icon-batch::before {
  content: '📦';
}

.icon-copy::before {
  content: '📋';
}

.icon-cancel::before {
  content: '❌';
}

.icon-delete::before {
  content: '🗑️';
}

.icon-error::before {
  content: '⚠️';
}

.icon-empty::before {
  content: '📤';
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

@media (max-width: 1180px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .record-card {
    grid-template-columns: 1fr;
  }

  .record-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 680px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .record-actions {
    gap: 8px;
  }

  .btn-primary,
  .btn-secondary,
  .btn-ghost,
  .btn-danger {
    padding: 8px 12px;
    font-size: 12px;
  }
}
</style>
