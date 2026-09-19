<template>
  <UserLayout
    title="文件管理"
    description="统一管理目录、文件操作与 AI 分析入口（支持 txt、doc、docx、md、csv、xls、xlsx、轻量文本型 pdf）。"
    :items="userNavItems"
  >
    <section class="manager-toolbar card">
      <div class="path-block">
        <div class="top-actions">
          <button type="button" class="back-btn" :disabled="!canGoBack" @click="goBack">返回上级</button>
          <button type="button" class="plain-btn" @click="openUploadDialog">上传文件</button>
          <button type="button" class="plain-btn" @click="createFolder">新建文件夹</button>
          <button type="button" class="plain-btn" :disabled="!selectedSingleFile" @click="downloadSelected">
            下载选中文件
          </button>
          <button type="button" class="plain-btn" :disabled="!selectedSingleFile" @click="toggleFavoriteSelected">
            {{ selectedSingleFile?.isFavorite ? '取消收藏' : '收藏文件' }}
          </button>
          <button type="button" class="plain-btn" :disabled="selectedNodeIds.length === 0" @click="batchDeleteSelected">
            批量删除（{{ selectedNodeIds.length }}）
          </button>
        </div>

        <input ref="uploadInputRef" type="file" class="hidden-input" @change="handleUploadChange" />

        <div class="breadcrumbs">
          <template v-for="(crumb, index) in breadcrumbs" :key="crumb.id">
            <button type="button" class="crumb" :disabled="index === breadcrumbs.length - 1" @click="navigateByCrumb(index)">
              {{ crumb.name }}
            </button>
            <span v-if="index < breadcrumbs.length - 1" class="separator">/</span>
          </template>
        </div>
        <div class="query-tools">
          <div class="search-box">
            <input v-model.trim="keywordInput" type="text" class="search-input" placeholder="搜索当前目录文件名" @keyup.enter="applySearch" />
            <button type="button" class="search-btn" @click="applySearch">
              <span class="btn-icon">🔍</span>
            </button>
            <button type="button" class="clear-btn" :disabled="!keyword" @click="clearSearch">
              <span class="btn-icon">✕</span>
            </button>
          </div>
          <div class="filter-group">
            <div class="filter-item">
              <span class="filter-label">类型</span>
              <select v-model="typeFilter" class="filter-select" @change="onFilterChange">
                <option value="all">全部</option>
                <option value="document">文档</option>
                <option value="image">图片</option>
                <option value="video">视频</option>
                <option value="archive">压缩包</option>
                <option value="other">其他</option>
              </select>
            </div>
            <div class="filter-item">
              <span class="filter-label">收藏</span>
              <select v-model="favoriteFilter" class="filter-select" @change="onFilterChange">
                <option value="all">全部</option>
                <option value="favorite">仅收藏</option>
                <option value="unfavorite">未收藏</option>
              </select>
            </div>
            <div class="filter-item">
              <span class="filter-label">排序</span>
              <select v-model="sortValue" class="filter-select" @change="changeSort">
                <option value="name_asc">名称升序</option>
                <option value="name_desc">名称降序</option>
                <option value="updated_desc">时间降序</option>
                <option value="updated_asc">时间升序</option>
                <option value="size_desc">大小降序</option>
                <option value="size_asc">大小升序</option>
              </select>
            </div>
          </div>
        </div>
        <p class="path-text">当前目录：{{ currentPathText }}</p>
      </div>

      <div class="toolbar-actions">
        <button type="button" class="paste-btn" :disabled="!canPasteInCurrent" @click="pasteToCurrent">
          粘贴到当前目录
        </button>
        <p v-if="clipboard" class="clipboard-tip">
          剪贴板：{{ clipboard.mode === 'copy' ? '复制' : '剪切' }} {{ clipboard.name }}
        </p>
        <p v-else class="clipboard-tip">剪贴板为空</p>
      </div>
    </section>

    <section class="manager-list card">
      <header class="list-header">
        <h3>文件与文件夹</h3>
        <span>{{ filteredEntries.length }} / {{ entries.length }} 项</span>
      </header>

      <div v-if="isLoading" class="loading-state">
        <p>正在加载目录内容...</p>
      </div>

      <div v-else-if="loadError" class="error-state">
        <h4>目录加载失败</h4>
        <p>{{ loadError }}</p>
        <button type="button" @click="reloadCurrent">重新加载</button>
      </div>

      <div v-else-if="filteredEntries.length > 0" class="list-grid">
        <div class="grid-head">
          <span class="checkbox-col">
            <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
          </span>
          <span>名称</span>
          <span>类型</span>
          <span>大小 / 子项</span>
          <span>更新时间</span>
          <span>操作</span>
        </div>

        <article
          v-for="item in filteredEntries"
          :key="item.id"
          class="grid-row"
          :class="{ selected: selectedId === item.id, 'drag-over': dragOverId === item.id, 'dragging': draggingId === item.id }"
          @click="selectEntry(item.id)"
          @dragstart="onDragStart($event, item)"
          @dragend="onDragEnd"
          @dragover.prevent="onDragOver($event, item)"
          @dragenter.prevent="onDragEnter($event, item)"
          @dragleave.prevent="onDragLeave"
          @drop.prevent="onDrop($event, item)"
          :draggable="item.type === 'file'"
        >
          <span class="checkbox-col" @click.stop>
            <input type="checkbox" :checked="selectedNodeIds.includes(item.id)" @change="toggleRowSelection(item.id)" />
          </span>

          <button type="button" class="name-cell" @dblclick.stop="openEntry(item)">
            <span class="entry-icon" :class="item.type">{{ item.type === 'folder' ? 'DIR' : 'FILE' }}</span>
            <strong>{{ item.name }}</strong>
          </button>

          <span>{{ getTypeLabel(item) }}</span>
          <span>{{ getSizeLabel(item) }}</span>
          <span>{{ item.updatedAt }}</span>

          <div class="actions">
            <button type="button" @click.stop="renameEntry(item)">重命名</button>
            <button type="button" @click.stop="copyEntry(item)">复制</button>
            <button type="button" @click.stop="cutEntry(item)">剪切</button>
            <button type="button" @click.stop="shareEntry(item)">分享</button>
            <button type="button" class="danger" @click.stop="deleteEntry(item)">删除</button>
            <button v-if="isAiSupported(item)" type="button" class="ai-btn" @click.stop="runAiAnalysis(item)">
              AI 分析
            </button>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        <h4>{{ keyword || typeFilter !== 'all' || favoriteFilter !== 'all' ? '未找到匹配文件' : '目录为空' }}</h4>
        <p>
          {{
            keyword || typeFilter !== 'all' || favoriteFilter !== 'all'
              ? '请调整搜索或筛选条件后重试。'
              : '可返回上级目录，或上传新文件到当前目录。'
          }}
        </p>
      </div>
    </section>

    <section v-if="preview.visible" class="preview-mask" @click.self="closePreview">
      <article class="preview-card">
        <header>
          <h4>{{ preview.fileName }}</h4>
          <button type="button" @click="closePreview">关闭</button>
        </header>
        <div class="preview-content">
          <img v-if="preview.type === 'image'" :src="preview.url" :alt="preview.fileName" />
          <video v-else controls :src="preview.url"></video>
        </div>
      </article>
    </section>
  </UserLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { runAiAnalysisApi } from '@/api/aiAnalysis'
import {
  batchDeleteNodesApi,
  createFolderApi,
  deleteNodeApi,
  downloadNodeApi,
  fetchWorkspaceApi,
  pasteNodeApi,
  previewNodeApi,
  renameNodeApi,
  shareNodeApi,
  toggleFavoriteApi,
  uploadFileApi,
} from '@/api/files'
import UserLayout from '@/layouts/UserLayout.vue'
import { userNavItems } from '@/constants/userNavigation'

const AI_SUPPORTED_EXTENSIONS = new Set(['txt', 'doc', 'docx', 'md', 'csv', 'xls', 'xlsx', 'pdf'])
const route = useRoute()

const uploadInputRef = ref(null)
const currentFolderId = ref(null)
const entries = ref([])
const breadcrumbs = ref([])
const selectedId = ref('')
const selectedNodeIds = ref([])
const clipboard = ref(null)
const isLoading = ref(false)
const loadError = ref('')
const keywordInput = ref('')
const keyword = ref('')
const typeFilter = ref('all')
const favoriteFilter = ref('all')
const sortValue = ref('name_asc')
const preview = ref({
  visible: false,
  type: '',
  url: '',
  fileName: '',
})

// 拖动相关状态
const draggingId = ref('')
const dragOverId = ref('')

const canGoBack = computed(() => breadcrumbs.value.length > 1)
const currentPathText = computed(() => breadcrumbs.value.map((item) => item.name).join(' / ') || '我的文件')
const canPasteInCurrent = computed(() => canPasteToFolder(currentFolderId.value))
const filteredEntries = computed(() =>
  entries.value.filter((item) => {
    if (item.type === 'folder') {
      return typeFilter.value === 'all' && favoriteFilter.value === 'all'
    }

    if (typeFilter.value !== 'all' && getFileCategory(item) !== typeFilter.value) {
      return false
    }
    if (favoriteFilter.value === 'favorite' && !item.isFavorite) {
      return false
    }
    if (favoriteFilter.value === 'unfavorite' && item.isFavorite) {
      return false
    }
    return true
  }),
)
const isAllSelected = computed(
  () => filteredEntries.value.length > 0 && selectedNodeIds.value.length === filteredEntries.value.length,
)
const selectedSingleFile = computed(() => {
  if (selectedNodeIds.value.length !== 1) {
    return null
  }
  const selected = entries.value.find((item) => item.id === selectedNodeIds.value[0])
  if (!selected || selected.type !== 'file') {
    return null
  }
  return selected
})

const loadWorkspace = async (folderId) => {
  isLoading.value = true
  loadError.value = ''

  try {
    const data = await fetchWorkspaceApi({
      folderId,
      keyword: keyword.value,
      sort: sortValue.value,
    })
    currentFolderId.value = data.currentFolder.id
    entries.value = data.items || []
    breadcrumbs.value = data.breadcrumbs || []
    keywordInput.value = data.keyword || keyword.value
    keyword.value = data.keyword || keyword.value
    sortValue.value = data.sort || sortValue.value

    selectedNodeIds.value = selectedNodeIds.value.filter((id) => entries.value.some((item) => item.id === id))
    if (!entries.value.some((item) => item.id === selectedId.value)) {
      selectedId.value = ''
    }
    onFilterChange()
  } catch (error) {
    loadError.value = error?.message || '目录加载失败'
    entries.value = []
    selectedNodeIds.value = []
  } finally {
    isLoading.value = false
  }
}

const reloadCurrent = () => {
  if (currentFolderId.value) {
    loadWorkspace(currentFolderId.value)
    return
  }
  loadWorkspace(undefined)
}

const selectEntry = (id) => {
  selectedId.value = id
}

const toggleRowSelection = (id) => {
  if (selectedNodeIds.value.includes(id)) {
    selectedNodeIds.value = selectedNodeIds.value.filter((nodeId) => nodeId !== id)
    return
  }
  selectedNodeIds.value = [...selectedNodeIds.value, id]
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedNodeIds.value = []
    return
  }
  selectedNodeIds.value = filteredEntries.value.map((item) => item.id)
}

const navigateByCrumb = (index) => {
  const target = breadcrumbs.value[index]
  if (!target || target.id === currentFolderId.value) {
    return
  }
  loadWorkspace(target.id)
}

const openEntry = (item) => {
  if (item.type === 'folder') {
    loadWorkspace(item.id)
    return
  }
  if (item.previewType) {
    openPreview(item)
    return
  }
  ElMessage.info('当前文件暂不支持在线预览，可使用下载功能')
}

const goBack = () => {
  if (!canGoBack.value) {
    return
  }

  const parent = breadcrumbs.value[breadcrumbs.value.length - 2]
  if (parent) {
    loadWorkspace(parent.id)
  }
}

const openUploadDialog = () => {
  uploadInputRef.value?.click()
}

const applySearch = () => {
  keyword.value = keywordInput.value.trim()
  loadWorkspace(currentFolderId.value)
}

const clearSearch = () => {
  keywordInput.value = ''
  keyword.value = ''
  loadWorkspace(currentFolderId.value)
}

const onFilterChange = () => {
  const visibleIds = new Set(filteredEntries.value.map((item) => item.id))
  selectedNodeIds.value = selectedNodeIds.value.filter((id) => visibleIds.has(id))
  if (selectedId.value && !visibleIds.has(selectedId.value)) {
    selectedId.value = ''
  }
}

const changeSort = () => {
  loadWorkspace(currentFolderId.value)
}

const handleUploadChange = async (event) => {
  const file = event.target.files?.[0]
  if (!file) {
    return
  }

  try {
    await uploadFileApi({
      file,
      parentId: currentFolderId.value,
    })
    ElMessage.success('文件上传成功')
    await loadWorkspace(currentFolderId.value)
  } catch (error) {
    ElMessage.warning(error?.message || '文件上传失败')
  } finally {
    event.target.value = ''
  }
}

const createFolder = async () => {
  try {
    const { value } = await ElMessageBox.prompt('请输入文件夹名称', '新建文件夹', {
      inputValue: '新建文件夹',
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputValidator: (input) => Boolean(input?.trim()),
      inputErrorMessage: '名称不能为空',
    })

    await createFolderApi({
      parentId: currentFolderId.value,
      name: value.trim(),
    })
    ElMessage.success('文件夹创建成功')
    await loadWorkspace(currentFolderId.value)
  } catch (error) {
    if (error === 'cancel' || error?.message === 'cancel') {
      return
    }
    ElMessage.warning(error?.message || '创建失败')
  }
}

const renameEntry = async (item) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入新名称', '重命名', {
      inputValue: item.name,
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputValidator: (input) => Boolean(input?.trim()),
      inputErrorMessage: '名称不能为空',
    })

    await renameNodeApi(item.id, value.trim())
    ElMessage.success('重命名成功')
    await loadWorkspace(currentFolderId.value)
  } catch (error) {
    if (error === 'cancel' || error?.message === 'cancel') {
      return
    }
    ElMessage.warning(error?.message || '重命名失败')
  }
}

const downloadEntry = async (item) => {
  try {
    const data = await downloadNodeApi(item.id)
    const url = URL.createObjectURL(data.blob)
    const link = document.createElement('a')
    link.href = url
    link.download = data.fileName
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    ElMessage.success('下载已开始')
  } catch (error) {
    ElMessage.warning(error?.message || '下载失败')
  }
}

const downloadSelected = async () => {
  if (!selectedSingleFile.value) {
    return
  }
  await downloadEntry(selectedSingleFile.value)
}

const openPreview = async (item) => {
  try {
    const data = await previewNodeApi(item.id)
    const url = URL.createObjectURL(data.blob)
    closePreview()
    preview.value = {
      visible: true,
      type: item.previewType || (data.mimeType.startsWith('video/') ? 'video' : 'image'),
      url,
      fileName: item.name,
    }
  } catch (error) {
    ElMessage.warning(error?.message || '预览失败')
  }
}

const closePreview = () => {
  if (preview.value.url) {
    URL.revokeObjectURL(preview.value.url)
  }
  preview.value = {
    visible: false,
    type: '',
    url: '',
    fileName: '',
  }
}

const copyEntry = (item) => {
  clipboard.value = {
    mode: 'copy',
    sourceId: item.id,
    name: item.name,
  }
  ElMessage.success(`已复制 ${item.name}`)
}

const cutEntry = (item) => {
  clipboard.value = {
    mode: 'move',
    sourceId: item.id,
    name: item.name,
  }
  ElMessage.success(`已剪切 ${item.name}`)
}

const pasteToCurrent = () => {
  pasteIntoFolder(currentFolderId.value)
}

const pasteIntoFolder = async (targetFolderId) => {
  if (!canPasteToFolder(targetFolderId)) {
    ElMessage.warning('当前不可执行粘贴')
    return
  }

  try {
    await pasteNodeApi({
      sourceId: clipboard.value.sourceId,
      targetFolderId,
      mode: clipboard.value.mode,
    })

    const message = clipboard.value.mode === 'copy' ? '复制并粘贴成功' : '剪切并粘贴成功'
    if (clipboard.value.mode === 'move') {
      clipboard.value = null
    }

    ElMessage.success(message)
    await loadWorkspace(currentFolderId.value)
  } catch (error) {
    ElMessage.warning(error?.message || '粘贴失败')
  }
}

const deleteEntry = async (item) => {
  try {
    await ElMessageBox.confirm(`确认删除 ${item.name} 吗？`, '删除文件', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (error) {
    return
  }

  try {
    await deleteNodeApi(item.id)
    ElMessage.success('删除成功')
    selectedNodeIds.value = selectedNodeIds.value.filter((id) => id !== item.id)
    if (selectedId.value === item.id) {
      selectedId.value = ''
    }
    await loadWorkspace(currentFolderId.value)
  } catch (error) {
    ElMessage.warning(error?.message || '删除失败')
  }
}

const batchDeleteSelected = async () => {
  if (selectedNodeIds.value.length === 0) {
    return
  }

  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedNodeIds.value.length} 项吗？`, '批量删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (error) {
    return
  }

  try {
    await batchDeleteNodesApi(selectedNodeIds.value)
    ElMessage.success('批量删除成功')
    selectedNodeIds.value = []
    await loadWorkspace(currentFolderId.value)
  } catch (error) {
    ElMessage.warning(error?.message || '批量删除失败')
  }
}

const shareEntry = async (item) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入分享有效期（1-30 天）', '创建分享', {
      inputValue: '7',
      confirmButtonText: '创建链接',
      cancelButtonText: '取消',
      inputValidator: (input) => {
        const days = Number(input)
        return Number.isInteger(days) && days >= 1 && days <= 30
      },
      inputErrorMessage: '请输入 1 到 30 之间的整数',
    })

    const data = await shareNodeApi(item.id, { expireDays: Number(value) })
    if (data?.link) {
      navigator.clipboard?.writeText(data.link)
    }
    ElMessage.success(`分享链接已创建（到期：${data?.expireAt || '--'}）`)
  } catch (error) {
    if (error === 'cancel' || error?.message === 'cancel') {
      return
    }
    ElMessage.warning(error?.message || '分享失败')
  }
}

const runAiAnalysis = (item) => {
  runAiAnalysisApi(item.id)
    .then(() => {
      ElMessage.success('AI 分析任务已提交，请前往 AI 分析页查看进度')
    })
    .catch((error) => {
      ElMessage.warning(error?.message || 'AI 分析失败')
    })
}

const toggleFavorite = async (item) => {
  try {
    const data = await toggleFavoriteApi(item.id)
    item.isFavorite = Boolean(data.favorited)
    ElMessage.success(data.favorited ? '已加入收藏' : '已取消收藏')
  } catch (error) {
    ElMessage.warning(error?.message || '收藏操作失败')
  }
}

const toggleFavoriteSelected = async () => {
  if (!selectedSingleFile.value) {
    return
  }
  await toggleFavorite(selectedSingleFile.value)
}

const canPasteToFolder = (targetFolderId) => {
  if (!clipboard.value || !targetFolderId) {
    return false
  }
  if (clipboard.value.mode === 'move' && clipboard.value.sourceId === targetFolderId) {
    return false
  }
  return true
}

const isAiSupported = (item) => {
  if (item.type !== 'file') {
    return false
  }
  if (item.canAiAnalyze !== undefined) {
    return item.canAiAnalyze
  }
  return AI_SUPPORTED_EXTENSIONS.has((item.extension || '').toLowerCase())
}

const getTypeLabel = (item) => {
  if (item.type === 'folder') {
    return '文件夹'
  }

  const extension = (item.extension || '').toUpperCase()
  return extension || '文件'
}

const getFileCategory = (item) => {
  const extension = (item.extension || '').toLowerCase()
  if (['txt', 'doc', 'docx', 'md', 'csv', 'xls', 'xlsx', 'pdf', 'ppt', 'pptx'].includes(extension)) {
    return 'document'
  }
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(extension)) {
    return 'image'
  }
  if (['mp4', 'webm'].includes(extension)) {
    return 'video'
  }
  if (['zip', 'rar', '7z'].includes(extension)) {
    return 'archive'
  }
  return 'other'
}

const getSizeLabel = (item) => {
  if (item.type === 'folder') {
    return `${item.childrenCount || 0} 项`
  }
  return formatBytes(item.sizeBytes || 0)
}

const formatBytes = (bytes) => {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

onMounted(() => {
  const folderId = parseFolderId(route.params.id)
  loadWorkspace(folderId)
})

onBeforeUnmount(() => {
  closePreview()
})

watch(
  () => route.params.id,
  (value, previous) => {
    if (value === previous) {
      return
    }
    const folderId = parseFolderId(value)
    loadWorkspace(folderId)
  },
)

const parseFolderId = (value) => {
  const parsed = Number(value)
  if (Number.isInteger(parsed) && parsed > 0) {
    return parsed
  }
  return undefined
}

const getFileIcon = (item) => {
  const extension = (item.extension || '').toLowerCase()
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(extension)) {
    return '🖼️'
  }
  if (['txt', 'doc', 'docx', 'md', 'pdf'].includes(extension)) {
    return '📄'
  }
  if (['xls', 'xlsx', 'csv'].includes(extension)) {
    return '📊'
  }
  if (['zip', 'rar', '7z'].includes(extension)) {
    return '📦'
  }
  if (['mp4', 'webm'].includes(extension)) {
    return '🎬'
  }
  return '📄'
}

// 拖动相关方法
const onDragStart = (event, item) => {
  if (item.type === 'file') {
    draggingId.value = item.id
    event.dataTransfer.setData('text/plain', item.id)
    // 添加拖动效果
    event.target.style.opacity = '0.5'
  }
}

const onDragEnd = (event) => {
  draggingId.value = ''
  dragOverId.value = ''
  event.target.style.opacity = '1'
}

const onDragOver = (event, item) => {
  if (item.type === 'folder' && draggingId.value !== '') {
    event.preventDefault()
  }
}

const onDragEnter = (event, item) => {
  if (item.type === 'folder' && draggingId.value !== '') {
    event.preventDefault()
    dragOverId.value = item.id
  }
}

const onDragLeave = () => {
  dragOverId.value = ''
}

const onDrop = async (event, item) => {
  if (item.type === 'folder' && draggingId.value !== '') {
    event.preventDefault()
    dragOverId.value = ''
    
    try {
      await pasteNodeApi({
        sourceId: draggingId.value,
        targetFolderId: item.id,
        mode: 'move'
      })
      
      ElMessage.success('文件已移动到文件夹')
      await loadWorkspace(currentFolderId.value)
    } catch (error) {
      ElMessage.warning(error?.message || '移动文件失败')
    }
  }
}
</script>

<style scoped>
/* 动画定义 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.animate-fade-in {
  animation: fadeIn 0.6s ease-out forwards;
  opacity: 0;
}

.animate-slide-in {
  animation: slideIn 0.6s ease-out forwards;
  opacity: 0;
}

.card {
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #3b82f6, #0ea5e9);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease;
}

.card:hover::before {
  transform: scaleX(1);
}

.card:hover {
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
  transform: translateY(-2px);
}

.manager-toolbar {
  padding: 20px;
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.path-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.top-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.back-btn,
.paste-btn,
.crumb,
.plain-btn {
  width: fit-content;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  background: #ffffff;
  color: #111827;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 1.2;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.back-btn:hover,
.paste-btn:hover,
.crumb:hover,
.plain-btn:hover {
  background: #f8fafc;
  border-color: #94a3b8;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.back-btn:disabled,
.paste-btn:disabled,
.crumb:disabled,
.plain-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.back-btn.danger,
.plain-btn.danger {
  border-color: #fecaca;
  color: #b91c1c;
}

.back-btn.danger:hover,
.plain-btn.danger:hover {
  background: #fef2f2;
  border-color: #fca5a5;
}

.btn-icon {
  font-size: 14px;
}

.hidden-input {
  display: none;
}

.breadcrumbs {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.crumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 8px;
}

.crumb-icon {
  font-size: 14px;
}

.separator {
  color: #64748b;
  font-size: 14px;
  font-weight: 600;
}

.query-tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

.query-tools:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 280px;
}

.search-input {
  width: 100%;
  height: 44px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 16px;
  padding: 0 56px 0 20px;
  font-size: 14px;
  outline: none;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.05);
}

.search-input::placeholder {
  color: #94a3b8;
  font-size: 14px;
}

.search-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1), inset 0 1px 2px rgba(0, 0, 0, 0.05);
  transform: translateY(-1px);
  background: #ffffff;
}

.search-btn,
.clear-btn {
  position: absolute;
  right: 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 8px;
  border-radius: 12px;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
}

.search-btn {
  right: 52px;
}

.search-btn:hover,
.clear-btn:hover {
  background: #f1f5f9;
  color: #334155;
  transform: scale(1.1);
}

.search-btn:active,
.clear-btn:active {
  transform: scale(0.95);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #475569;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.7);
  padding: 8px 16px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  transition: all 0.3s ease;
}

.filter-item:hover {
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  transform: translateY(-1px);
}

.filter-label {
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
}

.filter-select {
  height: 36px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 10px;
  padding: 0 16px;
  background: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  transition: all 0.3s ease;
  outline: none;
  cursor: pointer;
  min-width: 120px;
}

.filter-select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
  transform: translateY(-1px);
  background: #ffffff;
}

.filter-select option {
  padding: 12px;
  font-size: 13px;
  background: #ffffff;
  color: #334155;
}

.filter-select option:hover {
  background: #f1f5f9;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .query-tools {
    flex-direction: column;
    align-items: stretch;
    padding: 12px;
  }
  
  .search-box {
    min-width: auto;
  }
  
  .filter-group {
    justify-content: space-between;
  }
  
  .filter-item {
    flex: 1;
    justify-content: space-between;
    padding: 6px 12px;
  }
  
  .filter-select {
    min-width: 100px;
  }
}

.path-text,
.clipboard-tip {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.toolbar-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 8px;
}

.paste-btn {
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
}

.manager-list {
  padding: 20px;
  margin-bottom: 20px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.list-header h3 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
  font-weight: 700;
}

.list-header span {
  color: #64748b;
  font-size: 13px;
  background: #f1f5f9;
  padding: 4px 12px;
  border-radius: 16px;
}

.list-grid {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.grid-head,
.grid-row {
  display: grid;
  grid-template-columns: 40px 1.3fr 0.6fr 0.7fr 0.8fr 2fr;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
}

.grid-head {
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  border-bottom: 1px solid #e2e8f0;
}

.grid-row {
  border-bottom: 1px solid #f1f5f9;
  min-height: 48px;
  font-size: 13px;
  color: #334155;
  transition: all 0.3s ease;
}

.grid-row:last-child {
  border-bottom: 0;
}

.grid-row.selected {
  background: #eaf2ff;
  border-left: 4px solid #3b82f6;
}

.grid-row:hover {
  background: #f8fafc;
  transform: translateX(4px);
}

/* 拖动相关样式 */
.grid-row.dragging {
  opacity: 0.5;
  transform: scale(0.98);
  transition: all 0.2s ease;
}

.grid-row.drag-over {
  background: #e0f2fe;
  border-left: 4px solid #0ea5e9;
  transform: translateX(8px);
  transition: all 0.2s ease;
}

.grid-row.drag-over .entry-icon.folder {
  background: #dbeafe;
  color: #3b82f6;
  transform: scale(1.1);
  transition: all 0.2s ease;
}

/* 拖动动画 */
@keyframes drag {}

/* 确保拖动时的光标样式 */
[draggable="true"] {
  cursor: grab;
}

[draggable="true"]:active {
  cursor: grabbing;
}

.checkbox-col {
  display: flex;
  align-items: center;
  justify-content: center;
}

.checkbox-col input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: #3b82f6;
  cursor: pointer;
}

.name-cell {
  border: 0;
  background: transparent;
  padding: 0;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  min-width: 0;
  transition: all 0.3s ease;
}

.name-cell:hover {
  transform: translateX(4px);
}

.entry-icon {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.entry-icon.folder {
  background: #fef3c7;
  color: #f59e0b;
}

.entry-icon.file {
  background: #dbeafe;
  color: #3b82f6;
}

.name-cell strong {
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  font-weight: 500;
}

.favorite-badge {
  font-size: 14px;
  margin-left: 6px;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.2);
  }
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.action-btn {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  padding: 6px 10px;
  font-size: 12px;
  line-height: 1.2;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-btn:hover {
  background: #f8fafc;
  border-color: #94a3b8;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
  box-shadow: none;
}

.action-btn.danger {
  border-color: #fecaca;
  color: #b91c1c;
}

.action-btn.danger:hover {
  background: #fef2f2;
  border-color: #fca5a5;
}

.action-btn.ai-btn {
  border-color: #bfdbfe;
  color: #1d4ed8;
}

.action-btn.ai-btn:hover {
  background: #eff6ff;
  border-color: #93c5fd;
}

.loading-state,
.error-state,
.empty-state {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f1f5f9;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.error-state h4,
.empty-state h4 {
  margin: 0 0 12px;
  color: #0f172a;
  font-size: 18px;
}

.loading-state p,
.error-state p,
.empty-state p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
}

.retry-btn {
  margin-top: 20px;
  border: 1px solid #3b82f6;
  border-radius: 12px;
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.retry-btn:hover {
  background: #2563eb;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.preview-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: grid;
  place-items: center;
  z-index: 1000;
  backdrop-filter: blur(8px);
}

.preview-card {
  width: min(860px, calc(100vw - 28px));
  max-height: calc(100vh - 28px);
  background: #ffffff;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.3);
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.3s ease-out forwards;
}

.preview-card header {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  background: #f8fafc;
}

.preview-card h4 {
  margin: 0;
  font-size: 16px;
  color: #0f172a;
  font-weight: 600;
}

.close-btn {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  font-size: 14px;
  padding: 8px 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 4px;
}

.close-btn:hover {
  background: #f8fafc;
  border-color: #94a3b8;
  transform: translateY(-1px);
}

.preview-content {
  padding: 20px;
  overflow: auto;
  display: grid;
  place-items: center;
  flex: 1;
}

.preview-content img,
.preview-content video {
  max-width: 100%;
  max-height: calc(100vh - 180px);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.preview-content img:hover,
.preview-content video:hover {
  transform: scale(1.02);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
}

@media (max-width: 1320px) {
  .manager-toolbar {
    grid-template-columns: 1fr;
  }

  .grid-head {
    display: none;
  }

  .grid-row {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 16px;
  }

  .checkbox-col {
    justify-content: flex-start;
  }

  .actions {
    justify-content: flex-start;
  }
}

@media (max-width: 768px) {
  .manager-toolbar,
  .manager-list {
    padding: 16px;
  }

  .top-actions {
    gap: 6px;
  }

  .back-btn,
  .paste-btn,
  .crumb,
  .plain-btn {
    padding: 6px 10px;
    font-size: 11px;
  }

  .search-input {
    width: 100%;
    height: 36px;
  }

  .filter-group {
    gap: 8px;
  }

  .filter-item {
    font-size: 11px;
  }

  .filter-select {
    height: 28px;
    padding: 0 8px;
    font-size: 11px;
  }
}
</style>
