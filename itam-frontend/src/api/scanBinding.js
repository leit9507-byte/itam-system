import request from '../utils/request'

export function resolveScanBinding(scanRaw) {
  return request.post('/scan-bindings/resolve', { scan_raw: scanRaw }, { silentError: true })
}

export function getAssetScanBindings(assetId) {
  return request.get(`/scan-bindings/asset/${encodeURIComponent(assetId)}`)
}

export function bindAssetScanCode(assetId, payload) {
  return request.post(`/scan-bindings/asset/${encodeURIComponent(assetId)}`, {
    scan_raw: payload.scan_raw,
    scan_type: payload.scan_type || 'generic',
    remark: payload.remark || '',
    force: Boolean(payload.force)
  })
}

export function deleteAssetScanBinding(bindingId) {
  return request.post(`/scan-bindings/${bindingId}/unbind`)
}
