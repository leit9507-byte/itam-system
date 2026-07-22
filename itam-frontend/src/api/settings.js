import request from '../utils/request'

export function getAssetResidualConfig() {
  return request.get('/settings/asset-residual')
}

export function saveAssetResidualConfig(payload) {
  return request.put('/settings/asset-residual', payload)
}
