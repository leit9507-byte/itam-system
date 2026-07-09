import request from '../utils/request'

export async function getTodoItems() {
  return normalizeBackendTodos(await request.get('/todo/list'))
}

function normalizeBackendTodos(rows) {
  return (Array.isArray(rows) ? rows : []).map(item => ({
    ...item,
    created_at: formatTodoDate(item.created_at)
  }))
}

function formatTodoDate(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}
