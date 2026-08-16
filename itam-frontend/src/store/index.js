import { defineStore } from 'pinia'
import { getCurrentPermissions } from '../api/user'
import { clearCache } from '../api/cache'
import { getStorageItem, getStorageJson, removeStorageItem, setStorageItem } from '../utils/storage'

const savedUser = getStorageJson('itam_user', null)
const savedReadableResources = getStorageJson('itam_readable_resources', [])

const guestUser = {
  name: '未登录用户',
  role: 'guest',
  username: '',
  source: 'none'
}

export const useAppStore = defineStore('app', {
  state: () => ({
    collapsed: false,
    user: savedUser || guestUser,
    token: getStorageItem('itam_token') || '',
    readableResources: savedReadableResources,
    permissionsLoaded: savedReadableResources.length > 0
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
      const token = getStorageItem('itam_token') || ''
      const rawUser = getStorageJson('itam_user', null)
      this.token = token
      this.user = rawUser || { ...guestUser }
      if (!token) {
        this.readableResources = []
        this.permissionsLoaded = false
        removeStorageItem('itam_readable_resources')
      }
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
      clearCache()
      setStorageItem('itam_token', this.token)
      setStorageItem('itam_user', JSON.stringify(nextUser))
    },
    async loadPermissions() {
      if (!this.token || this.permissionsLoaded) return
      if (this.user.role === 'admin') {
        this.readableResources = ['asset', 'purchase', 'repair', 'supplier', 'catalog', 'audit', 'identity', 'rbac', 'file', 'report', 'ops']
        this.permissionsLoaded = true
        setStorageItem('itam_readable_resources', JSON.stringify(this.readableResources))
        return
      }
      try {
        const result = await getCurrentPermissions()
        this.readableResources = Array.isArray(result?.resources) ? result.resources : []
        setStorageItem('itam_readable_resources', JSON.stringify(this.readableResources))
      } catch {
        this.readableResources = []
        removeStorageItem('itam_readable_resources')
      } finally {
        this.permissionsLoaded = true
      }
    },
    logout() {
      this.token = ''
      this.user = { ...guestUser }
      this.readableResources = []
      this.permissionsLoaded = false
      clearCache()
      removeStorageItem('itam_token')
      removeStorageItem('itam_user')
      removeStorageItem('itam_readable_resources')
    }
  }
})
