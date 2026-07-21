import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/backend',
  timeout: Number(import.meta.env.VITE_API_TIMEOUT_MS || 30000)
})

request.interceptors.request.use(config => {
  const token = localStorage.getItem('itam_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  response => response.data,
  error => {
    const message = normalizeErrorMessage(error)
    error.userMessage = message
    const isLoginRequest = (error.config?.url || '').includes('/auth/login')
    if (error.response?.status === 401 && !isLoginRequest) {
      // 会话过期：清理凭证并回到登录页
      localStorage.removeItem('itam_token')
      localStorage.removeItem('itam_user')
      if (window.location.pathname !== '/login') {
        ElMessage.error('登录状态已过期，请重新登录')
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`
      }
    } else if (!error.config?.silentError) {
      // 登录接口本身的 401（密码错误等）走正常错误提示
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

function normalizeErrorMessage(error) {
  if (error.code === 'ECONNABORTED') return '请求超时，请稍后重试'
  if (!error.response) return '网络连接失败，请检查服务是否正常'
  const status = error.response.status
  const detail = error.response.data?.detail
  const serverMessage = Array.isArray(detail) ? '' : detail
  if (serverMessage) return serverMessage
  if (status === 400) return '请求内容不正确，请检查输入'
  if (status === 401) return '用户名或密码错误'
  if (status === 423) return '账号已被锁定，请稍后再试'
  if (status === 403) return '没有权限执行该操作'
  if (status === 404) return '数据不存在或已被删除'
  if (status === 409) return '数据冲突，请刷新后重试'
  if (status === 413) return '上传文件过大'
  if (status === 422) return '请求参数不正确，请检查后重试'
  if (status >= 500) return '服务器内部错误，请联系管理员'
  return `请求失败 (${status})`
}

export default request
