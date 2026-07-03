import request from '../utils/request'

export function getApprovalRules(params = {}) {
  return request.get('/approval/rules', { params })
}

export function createApprovalRule(payload) {
  return request.post('/approval/rules', payload)
}

export function updateApprovalRule(id, payload) {
  return request.put(`/approval/rules/${id}`, payload)
}

export function deleteApprovalRule(id) {
  return request.delete(`/approval/rules/${id}`)
}

export function evaluateApprovalRules(params) {
  return request.get('/approval/evaluate', { params })
}
