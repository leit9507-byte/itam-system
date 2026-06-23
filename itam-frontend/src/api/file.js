import request from '../utils/request'

export function uploadAssetFile(assetId, file) {
  const form = new FormData()
  form.append('file', file)
  return request.post(`/files/asset/${assetId}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function listAssetFiles(assetId) {
  return request.get(`/files/asset/${assetId}`)
}

export function assetQrCodeUrl(assetId) {
  const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
  return `${base}/files/asset/${encodeURIComponent(assetId)}/qrcode`
}

export function fileDownloadUrl(fileId) {
  const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
  return `${base}/files/${fileId}/download`
}

export async function loadAssetQrCode(assetId) {
  const blob = await request.get(`/files/asset/${assetId}/qrcode`, { responseType: 'blob' })
  return URL.createObjectURL(blob)
}

export async function downloadAssetFile(row) {
  const blob = await request.get(`/files/${row.id}/download`, { responseType: 'blob' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = row.filename || `attachment-${row.id}`
  link.click()
  URL.revokeObjectURL(url)
}
