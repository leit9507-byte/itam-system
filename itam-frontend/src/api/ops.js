import request from '../utils/request'

export function getOpsHealth() {
  return request.get('/ops/health')
}

export function getOperationLogs(params = {}) {
  return request.get('/ops/logs', { params })
}

export async function exportOperationLogs(params = {}) {
  const blob = await request.get('/ops/logs/export', { params, responseType: 'blob' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
  link.href = url
  link.download = `operation-logs-${timestamp}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

export function getScheduledJobs() {
  return request.get('/ops/jobs')
}

export function getDatabaseConfig() {
  return request.get('/ops/database-config')
}

export function testDatabaseConfig(payload) {
  return request.post('/ops/database-config/test', payload)
}

export function saveDatabaseConfig(payload) {
  return request.put('/ops/database-config', payload)
}

export function getDatabaseStatus() {
  return request.get('/ops/database-status')
}

export function initDatabase(payload = {}, token = '') {
  return request.post('/ops/init-database', payload, {
    headers: token ? { 'X-Init-Token': token } : {}
  })
}
