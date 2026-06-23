import { defineStore } from 'pinia'

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
    token: localStorage.getItem('itam_token') || ''
  }),
  getters: {
    isAuthenticated: state => Boolean(state.token)
  },
  actions: {
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
      localStorage.setItem('itam_token', this.token)
      localStorage.setItem('itam_user', JSON.stringify(nextUser))
    },
    logout() {
      this.token = ''
      this.user = { ...guestUser }
      localStorage.removeItem('itam_token')
      localStorage.removeItem('itam_user')
    }
  }
})
