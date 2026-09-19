<template>
  <div class="login-page">
    <div class="background">
      <div class="gradient-overlay"></div>
      <div class="floating-shapes">
        <div class="shape shape-1"></div>
        <div class="shape shape-2"></div>
        <div class="shape shape-3"></div>
      </div>
      <div class="ripple-container">
        <div class="ripple"></div>
        <div class="ripple" style="animation-delay: 2s;"></div>
        <div class="ripple" style="animation-delay: 4s;"></div>
      </div>
      <div class="geometric-shapes">
        <div class="geo-shape geo-1"></div>
        <div class="geo-shape geo-2"></div>
        <div class="geo-shape geo-3"></div>
      </div>
      <div class="light-effects">
        <div class="light-beam"></div>
        <div class="light-beam" style="animation-delay: 3s;"></div>
      </div>
      <div class="particles">
        <div v-for="n in 20" :key="n" class="particle" :style="{ animationDelay: `${n * 0.2}s` }"></div>
      </div>
    </div>
    
    <div class="content">
      <div class="brand-section">
        <div class="brand-logo">
          <div class="logo-mark">☁</div>
          <h1 class="brand-title">CloudFlow</h1>
        </div>
        <h2 class="brand-subtitle">智能云盘系统</h2>
        <p class="brand-description">
          高效管理文件，无缝协作分享，智能 AI 分析，为您的工作流程赋能。
        </p>
        <div class="brand-features">
          <div class="feature">
            <div class="feature-icon">📁</div>
            <span>文件管理</span>
          </div>
          <div class="feature">
            <div class="feature-icon">🔗</div>
            <span>分享协作</span>
          </div>
          <div class="feature">
            <div class="feature-icon">🤖</div>
            <span>AI 分析</span>
          </div>
        </div>
      </div>

      <div class="form-section">
        <div class="form-container">
          <h3 class="form-title">登录</h3>
          <p class="form-subtitle">请输入您的账号信息</p>
          
          <form @submit.prevent="handleLogin">
            <div class="form-field">
              <label class="field-label">账号</label>
              <div class="input-container">
                <span class="input-icon">👤</span>
                <input 
                  v-model.trim="form.account" 
                  type="text" 
                  placeholder="请输入账号" 
                  class="form-input"
                  @focus="handleInputFocus"
                  @blur="handleInputBlur"
                />
              </div>
            </div>

            <div class="form-field">
              <label class="field-label">密码</label>
              <div class="input-container">
                <span class="input-icon">🔒</span>
                <input 
                  v-model.trim="form.password" 
                  type="password" 
                  placeholder="请输入密码" 
                  class="form-input"
                  @focus="handleInputFocus"
                  @blur="handleInputBlur"
                />
              </div>
            </div>

            <div class="form-field">
              <label class="field-label">验证码</label>
              <div class="captcha-wrapper">
                <div class="input-container">
                  <span class="input-icon">🔍</span>
                  <input 
                    v-model.trim="form.captcha" 
                    type="text" 
                    placeholder="请输入验证码" 
                    class="form-input captcha-input"
                    @focus="handleInputFocus"
                    @blur="handleInputBlur"
                  />
                </div>
                <img 
                  :src="captchaUrl" 
                  @click="refreshCaptcha" 
                  class="captcha-image"
                  alt="验证码"
                />
              </div>
            </div>
            
            <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
            
            <button 
              type="submit" 
              class="submit-button" 
              :disabled="submitting"
              :class="{ 'loading': submitting }"
            >
              <span v-if="!submitting">登录</span>
              <div v-else class="button-loading">
                <div class="spinner"></div>
                <span>登录中...</span>
              </div>
            </button>
            
            <div class="form-footer">
              <router-link to="/register" class="register-link">
                创建账号
              </router-link>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
  import { reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { useAppStore } from '@/stores/app'

  const router = useRouter()
  const appStore = useAppStore()

  const form = reactive({
    account: '',
    password: '',
    captcha: '',
  })

  const captchaUrl = ref('/api/auth/captcha?' + Date.now())
  const captchaHover = ref(false)

  const refreshCaptcha = () => {
    captchaUrl.value = '/api/auth/captcha?' + Date.now()
  }

  const errorMessage = ref('')
  const submitting = ref(false)

  const handleInputFocus = (event) => {
    const inputWrapper = event.target.closest('.input-wrapper')
    inputWrapper.classList.add('focused')
  }

  const handleInputBlur = (event) => {
    const inputWrapper = event.target.closest('.input-wrapper')
    inputWrapper.classList.remove('focused')
  }

  const handleCaptchaHover = (isHovering) => {
    captchaHover.value = isHovering
  }

  const handleLogin = async () => {
    errorMessage.value = ''

    if (!form.account || !form.password) {
      errorMessage.value = '请输入账号和密码'
      return
    }

    if (!form.captcha) {
      errorMessage.value = '请输入验证码'
      return
    }

    submitting.value = true
    try {
      await appStore.login(form.account, form.password, form.captcha)
      if (appStore.role === 'ADMIN') {
        router.push('/admin/home')
        return
      }
      router.push('/user/home')
    } catch (error) {
      errorMessage.value = error?.message || '登录失败，请稍后重试'
      // 验证码错误时刷新验证码
      if (error?.message?.includes('验证码')) {
        refreshCaptcha()
      }
    } finally {
      submitting.value = false
    }
  }
</script>

<style scoped>
  /* 全局动画定义 */
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(30px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateX(30px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  @keyframes float {
    0%, 100% {
      transform: translateY(0) rotate(0deg);
    }
    50% {
      transform: translateY(-20px) rotate(5deg);
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

  @keyframes shimmer {
    0% {
      background-position: -200% 0;
    }
    100% {
      background-position: 200% 0;
    }
  }

  /* 渐变动画 */
  @keyframes gradientShift {
    0% {
      background-position: 0% 50%;
    }
    50% {
      background-position: 100% 50%;
    }
    100% {
      background-position: 0% 50%;
    }
  }

  /* 波纹效果 */
  @keyframes ripple {
    0% {
      transform: scale(0);
      opacity: 1;
    }
    100% {
      transform: scale(4);
      opacity: 0;
    }
  }

  /* 几何图形动画 */
  @keyframes shapeTransform {
    0% {
      transform: rotate(0deg) scale(1);
      border-radius: 60% 40% 30% 70%/60% 30% 70% 40%;
    }
    25% {
      border-radius: 30% 60% 70% 40%/50% 60% 30% 60%;
    }
    50% {
      transform: rotate(180deg) scale(1.1);
      border-radius: 40% 60% 60% 40%/60% 30% 70% 40%;
    }
    75% {
      border-radius: 70% 30% 40% 60%/30% 60% 70% 60%;
    }
    100% {
      transform: rotate(360deg) scale(1);
      border-radius: 60% 40% 30% 70%/60% 30% 70% 40%;
    }
  }

  /* 光效动画 */
  @keyframes lightEffect {
    0% {
      transform: translateX(-100%) rotate(0deg);
      opacity: 0;
    }
    50% {
      opacity: 1;
    }
    100% {
      transform: translateX(100%) rotate(180deg);
      opacity: 0;
    }
  }

  /* 粒子动画 */
  @keyframes particleFloat {
    0%, 100% {
      transform: translateY(0) translateX(0) rotate(0deg);
      opacity: 0;
    }
    50% {
      opacity: 1;
    }
    100% {
      transform: translateY(-100px) translateX(50px) rotate(360deg);
      opacity: 0;
    }
  }

  /* 基础样式 */
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  .login-page {
    min-height: 100vh;
    position: relative;
    overflow: hidden;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  /* 背景 */
  .background {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 0;
  }

  .gradient-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
  }

  .floating-shapes {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }

  .shape {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.2;
    animation: float 15s ease-in-out infinite;
  }

  .shape-1 {
    width: 400px;
    height: 400px;
    background: #667eea;
    top: -100px;
    left: -100px;
  }

  .shape-2 {
    width: 300px;
    height: 300px;
    background: #764ba2;
    bottom: -100px;
    right: -100px;
    animation-delay: 3s;
  }

  .shape-3 {
    width: 250px;
    height: 250px;
    background: #f093fb;
    top: 50%;
    right: 10%;
    animation-delay: 6s;
  }

  /* 波纹效果 */
  .ripple-container {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 200px;
    height: 200px;
  }

  .ripple {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 100px;
    height: 100px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    animation: ripple 6s infinite;
  }

  /* 几何图形动画 */
  .geometric-shapes {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
  }

  .geo-shape {
    position: absolute;
    background: rgba(255, 255, 255, 0.1);
    animation: shapeTransform 10s ease-in-out infinite;
  }

  .geo-1 {
    width: 100px;
    height: 100px;
    top: 10%;
    right: 10%;
  }

  .geo-2 {
    width: 150px;
    height: 150px;
    bottom: 10%;
    left: 10%;
    animation-delay: 2s;
  }

  .geo-3 {
    width: 80px;
    height: 80px;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    animation-delay: 4s;
  }

  /* 光效动画 */
  .light-effects {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
  }

  .light-beam {
    position: absolute;
    top: 50%;
    left: 0;
    width: 200px;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.8), transparent);
    transform: translateY(-50%);
    animation: lightEffect 6s ease-in-out infinite;
  }

  /* 粒子动画 */
  .particles {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }

  .particle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: rgba(255, 255, 255, 0.8);
    border-radius: 50%;
    animation: particleFloat 6s ease-in-out infinite;
  }

  /* 为粒子设置随机位置 */
  .particle:nth-child(1) { top: 10%; left: 20%; }
  .particle:nth-child(2) { top: 20%; left: 80%; }
  .particle:nth-child(3) { top: 30%; left: 40%; }
  .particle:nth-child(4) { top: 40%; left: 60%; }
  .particle:nth-child(5) { top: 50%; left: 10%; }
  .particle:nth-child(6) { top: 60%; left: 90%; }
  .particle:nth-child(7) { top: 70%; left: 30%; }
  .particle:nth-child(8) { top: 80%; left: 70%; }
  .particle:nth-child(9) { top: 90%; left: 50%; }
  .particle:nth-child(10) { top: 5%; left: 50%; }
  .particle:nth-child(11) { top: 15%; left: 70%; }
  .particle:nth-child(12) { top: 25%; left: 30%; }
  .particle:nth-child(13) { top: 35%; left: 90%; }
  .particle:nth-child(14) { top: 45%; left: 20%; }
  .particle:nth-child(15) { top: 55%; left: 80%; }
  .particle:nth-child(16) { top: 65%; left: 40%; }
  .particle:nth-child(17) { top: 75%; left: 10%; }
  .particle:nth-child(18) { top: 85%; left: 60%; }
  .particle:nth-child(19) { top: 95%; left: 30%; }
  .particle:nth-child(20) { top: 50%; left: 70%; }

  /* 内容区域 */
  .content {
    position: relative;
    z-index: 1;
    min-height: 100vh;
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: center;
    padding: 0 60px;
  }

  /* 品牌区域 */
  .brand-section {
    padding-right: 40px;
    animation: fadeIn 0.8s ease-out 0.2s both;
  }

  .brand-logo {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 40px;
  }

  .logo-mark {
    width: 60px;
    height: 60px;
    border-radius: 16px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    color: white;
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
  }

  .brand-title {
    font-size: 32px;
    font-weight: 800;
    color: #1a1a1a;
    letter-spacing: -0.5px;
  }

  .brand-subtitle {
    font-size: 48px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 24px;
    line-height: 1.2;
  }

  .brand-description {
    font-size: 24px;
    font-weight: 600;
    line-height: 1.4;
    color: #333;
    margin-bottom: 40px;
    max-width: 100%;
    white-space: nowrap;
  }

  .brand-features {
    display: flex;
    gap: 24px;
  }

  .feature {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 16px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    transition: all 0.3s ease;
  }

  .feature:hover {
    transform: translateY(-8px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  }

  .feature-icon {
    font-size: 28px;
  }

  .feature span {
    font-size: 14px;
    font-weight: 600;
    color: #333;
  }

  /* 表单区域 */
  .form-section {
    animation: slideIn 0.8s ease-out 0.4s both;
  }

  .form-container {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(20px);
    border-radius: 24px;
    padding: 60px 40px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
    max-width: 450px;
    width: 100%;
  }

  .form-title {
    font-size: 32px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 8px;
  }

  .form-subtitle {
    font-size: 16px;
    color: #666;
    margin-bottom: 40px;
  }

  /* 表单字段 */
  .form-field {
    margin-bottom: 24px;
  }

  .field-label {
    display: block;
    font-size: 14px;
    font-weight: 600;
    color: #333;
    margin-bottom: 8px;
  }

  .input-container {
    position: relative;
  }

  .form-input {
    width: 100%;
    height: 56px;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 0 20px 0 56px;
    font-size: 16px;
    outline: none;
    transition: all 0.3s ease;
    background: #f9f9f9;
  }

  .form-input:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
    background: white;
    transform: translateY(-2px);
  }

  .input-icon {
    position: absolute;
    left: 20px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 18px;
    color: #999;
    transition: all 0.3s ease;
  }

  .form-input:focus + .input-icon {
    color: #667eea;
  }

  /* 验证码 */
  .captcha-wrapper {
    display: flex;
    gap: 16px;
    align-items: center;
  }

  .captcha-input {
    flex: 1;
  }

  .captcha-image {
    width: 120px;
    height: 56px;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    border: 1px solid #eaeaea;
  }

  .captcha-image:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  /* 错误信息 */
  .error-message {
    margin: 16px 0;
    padding: 16px;
    background: #fee;
    border: 1px solid #fcc;
    border-radius: 12px;
    color: #c33;
    font-size: 14px;
    animation: fadeIn 0.3s ease-out;
  }

  /* 提交按钮 */
  .submit-button {
    width: 100%;
    height: 56px;
    border: none;
    border-radius: 12px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
    margin-top: 16px;
  }

  .submit-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    animation: shimmer 1.5s infinite;
  }

  .submit-button:hover:not(:disabled) {
    transform: translateY(-3px);
    box-shadow: 0 12px 32px rgba(102, 126, 234, 0.4);
  }

  .submit-button:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 6px 16px rgba(102, 126, 234, 0.3);
  }

  .submit-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .button-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top: 2px solid white;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  /* 表单底部 */
  .form-footer {
    margin-top: 24px;
    text-align: center;
  }

  .register-link {
    color: #667eea;
    font-size: 14px;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.3s ease;
  }

  .register-link:hover {
    color: #764ba2;
    text-decoration: underline;
  }

  /* 响应式设计 */
  @media (max-width: 1024px) {
    .content {
      grid-template-columns: 1fr;
      padding: 60px 40px;
      text-align: center;
    }

    .brand-section {
      padding-right: 0;
      margin-bottom: 60px;
    }

    .brand-features {
      justify-content: center;
    }

    .form-container {
      margin: 0 auto;
    }
  }

  @media (max-width: 768px) {
    .content {
      padding: 40px 20px;
    }

    .brand-subtitle {
      font-size: 36px;
    }

    .form-container {
      padding: 40px 24px;
    }

    .brand-features {
      flex-direction: column;
      align-items: center;
    }

    .feature {
      width: 100%;
      max-width: 300px;
      flex-direction: row;
      justify-content: center;
      gap: 16px;
    }
  }

  @media (max-width: 480px) {
    .brand-title {
      font-size: 24px;
    }

    .brand-subtitle {
      font-size: 28px;
    }

    .form-container {
      padding: 32px 20px;
    }

    .form-input {
      height: 48px;
    }

    .submit-button {
      height: 48px;
    }
  }
</style>
