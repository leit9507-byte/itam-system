import request from '../utils/request'

export function getApprovalConfigs(params = {}) {
  return request.get('/approval/configs', { params })
}

export function createApprovalConfig(payload) {
  return request.post('/approval/configs', payload)
}

export function updateApprovalConfig(id, payload) {
  return request.put(`/approval/configs/${id}`, payload)
}

export function deleteApprovalConfig(id) {
  return request.delete(`/approval/configs/${id}`)
}

export function evaluateApprovalConfig(params) {
  return request.get('/approval/evaluate', { params })
}

export function submitFeishuApproval(payload) {
  return request.post('/approval/feishu/submit', payload)
}

export function getApprovalInstances(params = {}) {
  return request.get('/approval/instances', { params })
}

export const getApprovalRules = getApprovalConfigs
export const createApprovalRule = createApprovalConfig
export const updateApprovalRule = updateApprovalConfig
export const deleteApprovalRule = deleteApprovalConfig
export const evaluateApprovalRules = evaluateApprovalConfig
