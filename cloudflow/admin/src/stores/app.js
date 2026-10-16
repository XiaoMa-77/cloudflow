import { defineStore } from 'pinia'

import { fetchMeApi, loginApi, logoutApi } from '@/api/auth'

const SESSION_KEY = 'auth_session'

const formatBytes = (bytes) => {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return '0B'
  }
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

export const useAppStore = defineStore('app', {
  state: () => ({
    role: null,
    token: null,
    user: null,
    hydrated: false,
    profileLoaded: false,
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    usedStorageText: (state) => formatBytes(state.user?.usedSpaceBytes || 0),
    totalStorageText: (state) => formatBytes(state.user?.spaceLimitBytes || 0),
    usagePercent: (state) => {
      const used = state.user?.usedSpaceBytes || 0
      const total = state.user?.spaceLimitBytes || 0
      if (!total) {
        return 0
      }
      return Math.min(100, Math.max(0, Math.round((used / total) * 100)))
    },
  },
  actions: {
    hydrateFromStorage() {
      if (this.hydrated) {
        return
      }

      const raw = localStorage.getItem(SESSION_KEY)
      if (!raw) {
        this.hydrated = true
        return
      }

      try {
        const parsed = JSON.parse(raw)
        this.token = parsed?.token || null
        this.role = parsed?.role || null
        this.user = parsed
          ? {
              account: parsed.account || '',
              name: parsed.name || '',
              role: parsed.role || null,
              usedSpaceBytes: parsed.usedSpaceBytes || 0,
              spaceLimitBytes: parsed.spaceLimitBytes || 0,
              loginAt: parsed.loginAt || '',
            }
          : null
      } catch (error) {
        this.clearSession()
      }

      this.hydrated = true
    },

    persistSession() {
      if (!this.token || !this.role) {
        localStorage.removeItem(SESSION_KEY)
        return
      }

      localStorage.setItem(
        SESSION_KEY,
        JSON.stringify({
          token: this.token,
          role: this.role,
          account: this.user?.account || '',
          name: this.user?.name || '',
          usedSpaceBytes: this.user?.usedSpaceBytes || 0,
          spaceLimitBytes: this.user?.spaceLimitBytes || 0,
          loginAt: this.user?.loginAt || '',
        }),
      )
    },

    applySession(payload) {
      this.token = payload.token
      this.role = payload.role
      this.user = {
        account: payload.account,
        name: payload.name,
        role: payload.role,
        usedSpaceBytes: payload.usedSpaceBytes || 0,
        spaceLimitBytes: payload.spaceLimitBytes || 0,
        loginAt: payload.loginAt || new Date().toISOString(),
      }
      this.persistSession()
    },

    clearSession() {
      this.token = null
      this.role = null
      this.user = null
      this.profileLoaded = false
      localStorage.removeItem(SESSION_KEY)
    },

    async login(account, password, captcha) {
      const data = await loginApi({ account, password, captcha })
      this.applySession({
        ...data,
        loginAt: new Date().toISOString(),
      })
      await this.fetchCurrentUser({ force: true })
      return data
    },

    async fetchCurrentUser({ force = false } = {}) {
      this.hydrateFromStorage()
      if (!this.token) {
        return null
      }
      if (this.profileLoaded && !force) {
        return this.user
      }

      const profile = await fetchMeApi()
      this.role = profile.role
      this.user = {
        account: profile.account,
        name: profile.name,
        role: profile.role,
        usedSpaceBytes: profile.usedSpaceBytes || 0,
        spaceLimitBytes: profile.spaceLimitBytes || 0,
        loginAt: this.user?.loginAt || new Date().toISOString(),
      }
      this.profileLoaded = true
      this.persistSession()
      return this.user
    },

    async restoreSession() {
      this.hydrateFromStorage()
      if (!this.token) {
        return null
      }

      try {
        return await this.fetchCurrentUser()
      } catch (error) {
        this.clearSession()
        throw error
      }
    },

    async logout() {
      if (this.token) {
        try {
          await logoutApi()
        } catch (error) {
          // Ignore remote logout errors and clear local session anyway.
        }
      }
      this.clearSession()
    },
  },
})
