<template>
  <UserLayout title="我的收藏" description="集中查看已标记文件，支持快速跳转和后续处理。" :items="userNavItems">
    <section class="summary-grid animate-fade-in">
      <article class="summary-card animate-slide-up">
        <div class="card-icon">
          <i class="icon-total"></i>
        </div>
        <small>收藏总数</small>
        <strong>{{ favoriteList.length }}</strong>
      </article>
      <article class="summary-card animate-slide-up" style="animation-delay: 0.1s;">
        <div class="card-icon">
          <i class="icon-document"></i>
        </div>
        <small>文档类</small>
        <strong>{{ documentCount }}</strong>
      </article>
      <article class="summary-card animate-slide-up" style="animation-delay: 0.2s;">
        <div class="card-icon">
          <i class="icon-recent"></i>
        </div>
        <small>最近收藏</small>
        <strong>{{ favoriteList[0]?.favoritedAt || '无记录' }}</strong>
      </article>
    </section>

    <section v-if="loading" class="state-card animate-fade-in">
      <div class="loading-spinner"></div>
      <p>正在加载收藏列表...</p>
    </section>

    <section v-else-if="errorText" class="state-card animate-fade-in">
      <div class="error-icon">
        <i class="icon-error"></i>
      </div>
      <h4>收藏列表加载失败</h4>
      <p>{{ errorText }}</p>
      <button type="button" @click="loadFavorites" class="btn-primary">重新加载</button>
    </section>

    <section v-else-if="favoriteList.length === 0" class="state-card animate-fade-in">
      <div class="empty-icon">
        <i class="icon-empty"></i>
      </div>
      <h4>暂无收藏文件</h4>
      <p>在文件管理中添加收藏后，将在这里快速访问。</p>
    </section>

    <section v-else class="list-wrap">
      <article v-for="(item, index) in favoriteList" :key="item.id" class="favorite-card animate-slide-up" :style="{ 'animation-delay': `${0.1 * index}s` }">
        <div class="favorite-icon">
          <i class="icon-file"></i>
        </div>
        <div class="favorite-info">
          <h3>{{ item.name }}</h3>
          <p class="meta">
            <span>类型：{{ item.type }}</span>
            <span>容量：{{ formatBytes(item.sizeBytes || 0) }}</span>
            <span>收藏时间：{{ item.favoritedAt }}</span>
          </p>
        </div>
        <router-link class="btn-primary" to="/user/files">
          <i class="icon-open"></i> 打开文件管理
        </router-link>
      </article>
    </section>
  </UserLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import UserLayout from '@/layouts/UserLayout.vue'
import { fetchFavoritesApi } from '@/api/user'
import { userNavItems } from '@/constants/userNavigation'

const loading = ref(false)
const errorText = ref('')
const favoriteList = ref([])

const documentCount = computed(() => favoriteList.value.filter((item) => ['文档', 'PDF', 'Word', 'txt'].includes(item.type)).length)

const formatBytes = (bytes) => {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const loadFavorites = async () => {
  loading.value = true
  errorText.value = ''

  try {
    const data = await fetchFavoritesApi()
    favoriteList.value = data.items || []
  } catch (error) {
    errorText.value = error?.message || '加载失败'
    favoriteList.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadFavorites()
})
</script>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.summary-card,
.favorite-card,
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
  background: linear-gradient(90deg, #ec4899, #8b5cf6);
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
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
}

.icon-total {
  color: #ec4899;
}

.icon-total::before {
  content: '❤️';
}

.icon-document {
  color: #3b82f6;
}

.icon-document::before {
  content: '📄';
}

.icon-recent {
  color: #10b981;
}

.icon-recent::before {
  content: '🕒';
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

.list-wrap {
  display: grid;
  gap: 16px;
}

.favorite-card {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  position: relative;
}

.favorite-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.12);
}

.favorite-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background: linear-gradient(135deg, #f0abfc, #c084fc);
  color: #ffffff;
  flex-shrink: 0;
}

.favorite-info {
  flex: 1;
}

.favorite-info h3 {
  margin: 0 0 12px;
  color: #0f172a;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.favorite-card:hover h3 {
  color: #ec4899;
}

.meta {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: #64748b;
  font-size: 13px;
}

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
  background: linear-gradient(135deg, #ec4899, #8b5cf6);
  color: #ffffff;
  text-decoration: none;
  flex-shrink: 0;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(236, 72, 153, 0.4);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f4f6;
  border-top: 3px solid #ec4899;
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
  background: #fce7f3;
  color: #ec4899;
}

.icon-file::before {
  content: '📁';
}

.icon-open::before {
  content: '📂';
}

.icon-error::before {
  content: '⚠️';
}

.icon-empty::before {
  content: '❤️';
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
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .favorite-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .btn-primary {
    align-self: flex-end;
  }
}

@media (max-width: 680px) {
  .favorite-icon {
    width: 48px;
    height: 48px;
    font-size: 18px;
  }

  .btn-primary {
    padding: 8px 12px;
    font-size: 12px;
  }
}
</style>
