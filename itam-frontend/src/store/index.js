import { defineStore } from 'pinia'
import { getCurrentPermissions } from '../api/user'

const savedUser = localStorage.getItem('itam_user')

const guestUser = {
  name: '未登录用户',
  role: 'guest',
  username: '',
  source: 'none'
}

export const useAppStore = defineStore('app', {
  state: () => ({
    collapsed: false,
    user: savedUser ? JSON.parse(savedUser) : guestUser,
    token: localStorage.getItem('itam_token') || '',
    readableResources: [],
    permissionsLoaded: false
  }),
  getters: {
    isAuthenticated: state => Boolean(state.token),
    canReadResource: state => resource => {
      if (state.user.role === 'admin') return true
      return state.readableResources.includes(resource)
    }
  },
  actions: {
    syncSessionFromStorage() {
      const token = localStorage.getItem('itam_token') || ''
      const rawUser = localStorage.getItem('itam_user')
      this.token = token
      this.user = rawUser ? JSON.parse(rawUser) : { ...guestUser }
    },
    toggleSidebar() {
      this.collapsed = !this.collapsed
    },
    setSession(payload) {
      this.token = payload.access_token || ''
      const nextUser = {
        name: payload.user?.display_name || payload.user?.username || 'ITAM User',
        role: payload.user?.role || 'user',
        username: payload.user?.username || '',
        source: payload.user?.source || 'local'
      }
      this.user = nextUser
      this.readableResources = []
      this.permissionsLoaded = false
      localStorage.setItem('itam_token', this.token)
      localStorage.setItem('itam_user', JSON.stringify(nextUser))
    },
    async loadPermissions() {
      if (!this.token || this.permissionsLoaded) return
      if (this.user.role === 'admin') {
        this.readableResources = ['asset', 'purchase', 'repair', 'supplier', 'catalog', 'audit', 'identity', 'rbac', 'file', 'report', 'ops']
        this.permissionsLoaded = true
        return
      }
      try {
        const result = await getCurrentPermissions()
        this.readableResources = Array.isArray(result?.resources) ? result.resources : []
      } catch {
        this.readableResources = []
      } finally {
        this.permissionsLoaded = true
      }
    },
    logout() {
      this.token = ''
      this.user = { ...guestUser }
      this.readableResources = []
      this.permissionsLoaded = false
      localStorage.removeItem('itam_token')
      localStorage.removeItem('itam_user')
    }
  }
})
