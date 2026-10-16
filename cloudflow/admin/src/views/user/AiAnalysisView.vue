<template>
  <UserLayout
    title="AI 分析"
    description="文档与图片的智能分析：文档输出结构化摘要，图片由视觉大模型识别内容与文字（OCR），分析后自动建立语义索引。"
    :items="userNavItems"
  >
    <section class="analysis-toolbar card animate-fade-in">
      <div class="limit-tip">
        <div class="tip-icon">
          <i class="icon-info"></i>
        </div>
        <p>
          支持格式：txt、doc、docx、md、csv、xls、xlsx、轻量文本型 pdf，以及 jpg、jpeg、png、gif、webp 图片。
          图片分析会调用视觉大模型识别场景与图内文字；分析完成后将自动纳入「智能搜索」语义索引。
        </p>
        <div class="status-overview">
          <span class="status-badge total">总任务 {{ records.length }}</span>
          <span class="status-badge running">分析中 {{ analyzingCount }}</span>
          <span class="status-badge done">已完成 {{ doneCount }}</span>
          <span class="status-badge failed">失败 {{ failedCount }}</span>
        </div>
      </div>

      <div class="launch-actions">
        <input ref="analysisUploadRef" type="file" class="hidden-input" @change="handleUploadAndAnalyze" />
        <button type="button" class="btn-primary" :disabled="launching" @click="openUploadDialog">
          <i class="icon-upload"></i> {{ launching ? '提交中...' : '上传文档并分析' }}
        </button>
        <button type="button" class="btn-ghost" :disabled="loading" @click="loadRecords">
          <i class="icon-refresh"></i> {{ loading ? '刷新中...' : '刷新列表' }}
        </button>
      </div>
    </section>

    <section v-if="loading" class="state-card card animate-fade-in">
      <div class="loading-spinner"></div>
      <p>正在加载 AI 分析记录...</p>
    </section>

    <section v-else-if="errorText" class="state-card card animate-fade-in">
      <div class="error-icon">
        <i class="icon-error"></i>
      </div>
      <h4>AI 分析记录加载失败</h4>
      <p>{{ errorText }}</p>
      <button type="button" class="btn-primary" @click="loadRecords">重新加载</button>
    </section>

    <section v-else-if="records.length === 0" class="state-card card animate-fade-in">
      <div class="empty-icon">
        <i class="icon-empty"></i>
      </div>
      <h4>暂无 AI 分析记录</h4>
      <p>在文件管理中对文档执行 AI 分析后，结果会在这里展示。</p>
    </section>

    <section v-else class="analysis-list card animate-fade-in">
      <header class="list-head">
        <span>文件</span>
        <span>摘要</span>
        <span>状态</span>
        <span>时间</span>
        <span>操作</span>
      </header>

      <article v-for="(item, index) in records" :key="item.id" class="analysis-row animate-slide-up" :style="{ 'animation-delay': `${0.1 * index}s` }">
        <div class="file-cell">
          <div class="file-icon">
            <i class="icon-file"></i>
          </div>
          <div class="file-info">
            <strong :title="item.fileName">{{ item.fileName }}</strong>
            <small>{{ item.type }}</small>
          </div>
        </div>

        <p class="summary" :title="summaryPreview(item.summary)">{{ summaryPreview(item.summary) }}</p>

        <span class="status" :class="statusClass(item.status)">{{ item.status }}</span>

        <span class="time">{{ item.analyzedAt }}</span>

        <div class="actions">
          <button type="button" class="btn-secondary" @click="openDetail(item)">
            <i class="icon-detail"></i> 查看详情
          </button>
          <button type="button" class="btn-ghost" :disabled="!item.fileNodeId" @click="rerun(item)">
            <i class="icon-rerun"></i> 重新分析
          </button>
        </div>
      </article>
    </section>

    <section v-if="detailVisible" class="detail-mask" @click.self="closeDetail">
      <article class="detail-dialog animate-fade-in">
        <header>
          <div>
            <h3>{{ detailRecord?.fileName }}</h3>
            <p>{{ detailRecord?.status }} · {{ detailRecord?.analyzedAt }}</p>
          </div>
          <button type="button" class="close-btn" @click="closeDetail">
            <i class="icon-close"></i>
          </button>
        </header>

        <div class="detail-content markdown-body" v-html="detailMarkdownHtml"></div>
      </article>
    </section>
  </UserLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'

import { fetchAiRecordsApi, runAiAnalysisApi } from '@/api/aiAnalysis'
import { smartUploadFile } from '@/api/uploader'
import UserLayout from '@/layouts/UserLayout.vue'
import { userNavItems } from '@/constants/userNavigation'

const SUPPORTED_EXTENSIONS = new Set(['txt', 'doc', 'docx', 'md', 'csv', 'xls', 'xlsx', 'pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp'])
const analysisUploadRef = ref(null)
const loading = ref(false)
const errorText = ref('')
const records = ref([])
const launching = ref(false)
const detailVisible = ref(false)
const detailRecord = ref(null)

marked.setOptions({
  breaks: true,
  gfm: true,
})

const doneCount = computed(() => records.value.filter((item) => item.status === '已完成').length)
const analyzingCount = computed(() => records.value.filter((item) => item.status === '分析中').length)
const failedCount = computed(() => records.value.filter((item) => item.status === '失败').length)

const detailMarkdownHtml = computed(() => {
  const content = detailRecord.value?.summary || ''
  if (!content.trim()) {
    return '<p>暂无详细内容</p>'
  }
  return marked.parse(content)
})

const loadRecords = async () => {
  loading.value = true
  errorText.value = ''

  try {
    const data = await fetchAiRecordsApi()
    records.value = data.items || []
  } catch (error) {
    errorText.value = error?.message || '加载失败'
    records.value = []
  } finally {
    loading.value = false
  }
}

const statusClass = (status) => {
  if (status === '已完成') {
    return 'done'
  }
  if (status === '失败') {
    return 'failed'
  }
  return 'running'
}

const summaryPreview = (content) => {
  const plain = String(content || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[(.*?)\]\(.*?\)/g, '$1')
    .replace(/[>#*_\-|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  if (!plain) {
    return '暂无摘要内容'
  }

  return plain.length > 90 ? `${plain.slice(0, 90)}...` : plain
}

const openDetail = (item) => {
  detailRecord.value = item
  detailVisible.value = true
}

const closeDetail = () => {
  detailVisible.value = false
  detailRecord.value = null
}

const rerun = async (item) => {
  if (!item.fileNodeId) {
    return
  }

  try {
    await runAiAnalysisApi(item.fileNodeId)
    ElMessage.success('分析任务已提交，请稍后刷新查看结果')
    await loadRecords()
  } catch (error) {
    ElMessage.warning(error?.message || '重新分析失败')
  }
}

const openUploadDialog = () => {
  analysisUploadRef.value?.click()
}

const handleUploadAndAnalyze = async (event) => {
  const file = event.target.files?.[0]
  if (!file) {
    return
  }

  const extension = (file.name.split('.').pop() || '').toLowerCase()
  if (!SUPPORTED_EXTENSIONS.has(extension)) {
    ElMessage.warning('当前文件类型不在 AI 分析支持范围内')
    event.target.value = ''
    return
  }

  launching.value = true
  try {
    const { entry, instant } = await smartUploadFile({ file, parentId: null })
    await runAiAnalysisApi(entry.id)
    ElMessage.success(instant ? '文件秒传成功，分析任务已提交' : '分析任务已提交，请稍后刷新查看结果')
    await loadRecords()
  } catch (error) {
    ElMessage.warning(error?.message || '上传并分析失败')
  } finally {
    launching.value = false
    event.target.value = ''
  }
}

onMounted(() => {
  loadRecords()
})
</script>

<style scoped>
.card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 16px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
  transition: all 0.3s ease;
}

.card:hover {
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.12);
}

.analysis-toolbar {
  padding: 20px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 20px;
  align-items: flex-start;
  margin-bottom: 20px;
  position: relative;
  overflow: hidden;
}

.analysis-toolbar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #10b981, #3b82f6);
}

.limit-tip {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tip-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #dcfce7, #bbf7d0);
  color: #166534;
  font-size: 16px;
  align-self: flex-start;
}

.limit-tip p {
  margin: 0;
  color: #334155;
  line-height: 1.65;
  font-size: 14px;
  background: #f8fafc;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.status-overview {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.status-badge {
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.status-badge.total {
  background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
  color: #4338ca;
}

.status-badge.running {
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  color: #1d4ed8;
}

.status-badge.done {
  background: linear-gradient(135deg, #dcfce7, #bbf7d0);
  color: #166534;
}

.status-badge.failed {
  background: linear-gradient(135deg, #fee2e2, #fecaca);
  color: #b91c1c;
}

.launch-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.hidden-input {
  display: none;
}

.btn-primary,
.btn-secondary,
.btn-ghost,
.close-btn {
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
  background: linear-gradient(135deg, #10b981, #059669);
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
}

.btn-secondary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #ffffff;
}

.btn-secondary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4);
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

.btn-primary:disabled,
.btn-secondary:disabled,
.btn-ghost:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.analysis-list {
  overflow: hidden;
  margin-bottom: 20px;
}

.list-head,
.analysis-row {
  display: grid;
  grid-template-columns: minmax(180px, 1.2fr) minmax(260px, 2fr) 90px 130px minmax(160px, 0.9fr);
  gap: 16px;
  align-items: center;
  padding: 12px 16px;
}

.list-head {
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
  border-bottom: 1px solid #e2e8f0;
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
}

.analysis-row {
  border-bottom: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.analysis-row:hover {
  background: #f8fafc;
  transform: translateX(4px);
}

.analysis-row:last-child {
  border-bottom: 0;
}

.file-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.file-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
  color: #4338ca;
  font-size: 16px;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-info strong {
  color: #0f172a;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
  transition: all 0.3s ease;
}

.analysis-row:hover .file-info strong {
  color: #3b82f6;
}

.file-info small {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
  display: block;
}

.summary,
.time {
  margin: 0;
  font-size: 13px;
  color: #334155;
}

.summary {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.status {
  width: fit-content;
  border-radius: 999px;
  font-size: 12px;
  padding: 6px 12px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.status.done {
  background: linear-gradient(135deg, #dcfce7, #bbf7d0);
  color: #166534;
}

.status.running {
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  color: #1d4ed8;
}

.status.failed {
  background: linear-gradient(135deg, #fee2e2, #fecaca);
  color: #b91c1c;
}

.actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
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

.detail-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 2000;
  display: grid;
  place-items: center;
  padding: 16px;
  backdrop-filter: blur(4px);
}

.detail-dialog {
  width: min(920px, calc(100vw - 32px));
  max-height: calc(100vh - 32px);
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 24px 68px rgba(15, 23, 42, 0.26);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s ease;
}

.detail-dialog:hover {
  box-shadow: 0 32px 80px rgba(15, 23, 42, 0.32);
}

.detail-dialog header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.detail-dialog h3 {
  margin: 0;
  color: #0f172a;
  font-size: 16px;
  font-weight: 600;
}

.detail-dialog header p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.close-btn {
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
  color: #64748b;
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: linear-gradient(135deg, #e2e8f0, #cbd5e1);
  transform: none;
}

.detail-content {
  padding: 24px;
  overflow: auto;
  color: #1e293b;
  line-height: 1.8;
  flex: 1;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  color: #0f172a;
  margin: 16px 0 8px;
  font-weight: 600;
}

.markdown-body :deep(p) {
  margin: 10px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 24px;
  margin: 10px 0;
}

.markdown-body :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

.markdown-body :deep(pre) {
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  overflow: auto;
  margin: 12px 0;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f4f6;
  border-top: 3px solid #10b981;
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
  background: #dcfce7;
  color: #10b981;
}

.icon-info::before {
  content: 'ℹ️';
}

.icon-upload::before {
  content: '📤';
}

.icon-refresh::before {
  content: '🔄';
}

.icon-file::before {
  content: '📄';
}

.icon-detail::before {
  content: '📋';
}

.icon-rerun::before {
  content: '🔁';
}

.icon-close::before {
  content: '✕';
}

.icon-error::before {
  content: '⚠️';
}

.icon-empty::before {
  content: '🤖';
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
  .analysis-toolbar {
    grid-template-columns: 1fr;
  }

  .launch-actions {
    justify-content: flex-start;
  }

  .list-head {
    display: none;
  }

  .analysis-row {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 16px;
  }

  .file-cell {
    justify-content: flex-start;
  }

  .actions {
    justify-content: flex-start;
  }
}

@media (max-width: 680px) {
  .analysis-toolbar {
    padding: 16px;
  }

  .launch-actions {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .btn-primary,
  .btn-secondary,
  .btn-ghost {
    padding: 8px 12px;
    font-size: 12px;
  }

  .detail-dialog {
    width: calc(100vw - 32px);
  }

  .detail-content {
    padding: 16px;
  }
}
</style>
