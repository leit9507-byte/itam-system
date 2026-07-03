import request from '../utils/request'

export function getOpsHealth() {
  return request.get('/ops/health')
}

export function getOperationLogs(params = {}) {
  return request.get('/ops/logs', { params })
}

export function getScheduledJobs() {
  return request.get('/ops/jobs')
}
