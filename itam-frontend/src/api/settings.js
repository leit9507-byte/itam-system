import request from '../utils/request'

export function getAssetResidualConfig() {
  return request.get('/settings/asset-residual')
}

export function saveAssetResidualConfig(payload) {
  return request.put('/settings/asset-residual', payload)
}

export function getFeishuConfig() {
  return request.get('/settings/feishu')
}

export function saveFeishuConfig(payload) {
  return request.put('/settings/feishu', payload)
}

export function testFeishuConfig() {
  return request.post('/settings/feishu/test')
}
