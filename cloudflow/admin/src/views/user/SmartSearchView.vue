<template>
  <UserLayout
    title="智能搜索"
    description="基于向量语义检索的全文搜索与 RAG 问答：用自然语言描述即可找到云盘里的文档与图片内容。"
    :items="userNavItems"
  >
    <section class="search-toolbar card animate-fade-in">
      <div class="search-form" @keyup.enter="runSearch">
        <div class="search-input-wrapper">
          <input
            v-model.trim="queryInput"
            type="text"
            class="search-input"
            placeholder="试试：包含报销流程的文档 / 描述项目排期的表格 / 出现二维码的图片"
            :disabled="searching"
          />
          <button type="button" class="search-btn" :disabled="searching || !queryInput" @click="runSearch">
            <i class="icon-search"></i> {{ searching ? '检索中...' : '语义搜索' }}
          </button>
        </div>

        <div class="search-options">
          <label class="option-item">
            <input v-model="withAnswer" type="checkbox" />
            <span>同时生成 AI 问答答案（RAG）</span>
          </label>
          <div class="option-item">
            <span>返回条数</span>
            <select v-model="topK" class="topk-select">
              <option :value="5">5</option>
              <option :value="8">8</option>
              <option :value="12">12</option>
              <option :value="20">20</option>
            </select>
          </div>
        </div>
      </div>

      <div class="index-panel">
        <div class="index-stats">
          <span class="status-badge files">已索引文件 {{ indexStatus.indexedFiles }}</span>
          <span class="status-badge chunks">语义分块 {{ indexStatus.indexedChunks }}</span>
        </div>
        <button type="button" class="btn-ghost" :disabled="reindexing" @click="rebuildIndex">
          <i class="icon-refresh"></i> {{ reindexing ? '重建中...' : '重建全部索引' }}
        </button>
        <p class="index-tip">
          文档在「AI 分析」完成后会自动建立索引；图片分析生成的文字描述同样可被检索。
        </p>
      </div>
    </section>

    <section v-if="answer" class="answer-card card animate-fade-in">
      <header class="answer-head">
        <div class="answer-title">
          <i class="icon-ai"></i>
          <div>
            <h4>AI 问答</h4>
            <p>基于检索到的 {{ results.length }} 个文件片段生成</p>
          </div>
        </div>
        <span class="answer-query">“{{ lastQuery }}”</span>
      </header>
      <div class="answer-body markdown-body" v-html="answerHtml"></div>
    </section>

    <section v-if="searched && !searching && results.length === 0" class="state-card card animate-fade-in">
      <div class="empty-icon">
        <i class="icon-empty"></i>
      </div>
      <h4>未找到相关内容</h4>
      <p>换个描述方式试试，或点击「重建全部索引」为云盘文件建立语义索引。</p>
    </section>

    <section v-if="results.length > 0" class="result-list card animate-fade-in">
      <header class="list-head">
        <span>文件</span>
        <span>匹配片段</span>
        <span>相关度</span>
        <span>更新时间</span>
      </header>

      <article
        v-for="(item, index) in results"
        :key="item.fileId"
        class="result-row animate-slide-up"
        :style="{ 'animation-delay': `${0.06 * index}s` }"
      >
        <div class="file-cell">
          <div class="file-icon" :class="iconClass(item.extension)">
            <i :class="iconClass(item.extension) === 'image' ? 'icon-image' : 'icon-file'"></i>
          </div>
          <div class="file-info">
            <strong :title="item.fileName">{{ item.fileName }}</strong>
            <small>{{ (item.extension || 'file').toUpperCase() }} · {{ formatSize(item.sizeBytes) }}</small>
          </div>
        </div>

        <p class="snippet">{{ item.snippet }}</p>

        <div class="score-cell">
          <div class="score-bar">
            <div class="score-fill" :style="{ width: `${scorePercent(item.score)}%` }"></div>
          </div>
          <small>{{ (item.score * 100).toFixed(1) }}%</small>
        </div>

        <span class="time">{{ item.updatedAt || '-' }}</span>
      </article>
    </section>
  </UserLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'

import { fetchSearchIndexStatusApi, reindexSearchApi, semanticSearchApi } from '@/api/aiSearch'
import UserLayout from '@/layouts/UserLayout.vue'
import { userNavItems } from '@/constants/userNavigation'

marked.setOptions({ breaks: true, gfm: true })

const queryInput = ref('')
const lastQuery = ref('')
const withAnswer = ref(true)
const topK = ref(8)
const searching = ref(false)
const searched = ref(false)
const results = ref([])
const answer = ref('')
const indexStatus = ref({ indexedFiles: 0, indexedChunks: 0 })
const reindexing = ref(false)

const answerHtml = computed(() => {
  if (!answer.value.trim()) {
    return '<p>AI 未生成答案，可尝试仅检索模式。</p>'
  }
  return marked.parse(answer.value)
})

const loadStatus = async () => {
  try {
    indexStatus.value = await fetchSearchIndexStatusApi()
  } catch (error) {
    // 状态加载失败不打断页面
  }
}

const runSearch = async () => {
  const query = queryInput.value.trim()
  if (!query || searching.value) {
    return
  }

  searching.value = true
  searched.value = true
  try {
    const data = await semanticSearchApi({ query, withAnswer: withAnswer.value, topK: topK.value })
    results.value = data.results || []
    answer.value = data.answer || ''
    lastQuery.value = query
    if (results.value.length === 0 && !answer.value) {
      ElMessage.info('未找到相关内容，可尝试重建索引')
    }
  } catch (error) {
    ElMessage.warning(error?.message || '语义搜索失败')
    results.value = []
    answer.value = ''
  } finally {
    searching.value = false
  }
}

const rebuildIndex = async () => {
  if (reindexing.value) {
    return
  }
  reindexing.value = true
  try {
    const data = await reindexSearchApi()
    ElMessage.success(`索引重建完成：${data.indexedFiles} 个文件，${data.indexedChunks} 个语义分块`)
    await loadStatus()
  } catch (error) {
    ElMessage.warning(error?.message || '索引重建失败')
  } finally {
    reindexing.value = false
  }
}

const iconClass = (extension) => {
  const ext = (extension || '').toLowerCase()
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
    return 'image'
  }
  return 'document'
}

const scorePercent = (score) => {
  return Math.max(4, Math.min(100, Math.round(Math.max(0, score) * 100)))
}

const formatSize = (bytes) => {
  const value = Number(bytes || 0)
  if (value < 1024) {
    return `${value} B`
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

onMounted(() => {
  loadStatus()
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

.search-toolbar {
  padding: 20px;
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(240px, 1fr);
  gap: 24px;
  margin-bottom: 20px;
  position: relative;
  overflow: hidden;
}

.search-toolbar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #8b5cf6, #3b82f6);
}

.search-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.search-input-wrapper {
  display: flex;
  gap: 10px;
}

.search-input {
  flex: 1;
  min-width: 0;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 14px;
  color: #0f172a;
  transition: all 0.3s ease;
  outline: none;
}

.search-input:focus {
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15);
}

.search-btn {
  border: 0;
  border-radius: 12px;
  padding: 0 20px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  background: linear-gradient(135deg, #8b5cf6, #6d28d9);
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  transition: all 0.3s ease;
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.35);
}

.search-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(139, 92, 246, 0.45);
}

.search-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
}

.search-options {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #475569;
  font-size: 13px;
}

.option-item input[type='checkbox'] {
  accent-color: #8b5cf6;
}

.topk-select {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 13px;
  color: #334155;
  outline: none;
}

.index-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
}

.index-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-badge {
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.status-badge.files {
  background: linear-gradient(135deg, #ede9fe, #ddd6fe);
  color: #5b21b6;
}

.status-badge.chunks {
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  color: #1d4ed8;
}

.btn-ghost {
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  background: linear-gradient(135deg, #ffffff, #f1f5f9);
  color: #334155;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s ease;
}

.btn-ghost:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(148, 163, 184, 0.35);
}

.btn-ghost:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
}

.index-tip {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}

.answer-card {
  margin-bottom: 20px;
  overflow: hidden;
}

.answer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 20px;
  background: linear-gradient(135deg, #f5f3ff, #ede9fe);
  border-bottom: 1px solid #e2e8f0;
}

.answer-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.answer-title i {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #8b5cf6, #6d28d9);
  color: #ffffff;
  font-size: 16px;
  font-style: normal;
}

.answer-title h4 {
  margin: 0;
  color: #0f172a;
  font-size: 15px;
  font-weight: 600;
}

.answer-title p {
  margin: 2px 0 0;
  color: #64748b;
  font-size: 12px;
}

.answer-query {
  color: #5b21b6;
  font-size: 13px;
  font-weight: 500;
  max-width: 40%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.answer-body {
  padding: 18px 20px;
  color: #1e293b;
  line-height: 1.8;
  max-height: 420px;
  overflow: auto;
}

.result-list {
  overflow: hidden;
  margin-bottom: 20px;
}

.list-head,
.result-row {
  display: grid;
  grid-template-columns: minmax(200px, 1fr) minmax(280px, 2fr) 140px 120px;
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

.result-row {
  border-bottom: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.result-row:hover {
  background: #f8fafc;
  transform: translateX(4px);
}

.result-row:last-child {
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
  font-size: 16px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
  color: #4338ca;
}

.file-icon.image {
  background: linear-gradient(135deg, #dcfce7, #bbf7d0);
  color: #166534;
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
}

.result-row:hover .file-info strong {
  color: #8b5cf6;
}

.file-info small {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
  display: block;
}

.snippet {
  margin: 0;
  font-size: 13px;
  color: #334155;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.score-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-cell small {
  color: #64748b;
  font-size: 12px;
  min-width: 46px;
}

.score-bar {
  flex: 1;
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #8b5cf6, #3b82f6);
  transition: width 0.5s ease;
}

.time {
  font-size: 13px;
  color: #334155;
}

.state-card {
  min-height: 260px;
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
  margin: 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.empty-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ede9fe;
  color: #8b5cf6;
  font-size: 24px;
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

.icon-search::before {
  content: '🔍';
}

.icon-refresh::before {
  content: '🔄';
}

.icon-ai::before {
  content: '🤖';
}

.icon-file::before {
  content: '📄';
}

.icon-image::before {
  content: '🖼️';
}

.icon-empty::before {
  content: '🔎';
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
  .search-toolbar {
    grid-template-columns: 1fr;
  }

  .list-head {
    display: none;
  }

  .result-row {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 16px;
  }

  .answer-query {
    display: none;
  }
}

@media (max-width: 680px) {
  .search-toolbar {
    padding: 16px;
  }

  .search-input-wrapper {
    flex-direction: column;
  }

  .search-btn {
    justify-content: center;
    padding: 12px;
  }

  .search-options {
    gap: 10px;
  }
}
</style>
