import request from '../utils/request'

async function downloadBlob(path, filename) {
  const blob = await request.get(path, { responseType: 'blob' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function downloadAssetCsv() {
  return downloadBlob('/reports/assets.csv', 'assets.csv')
}

export function downloadAssetPdf() {
  return downloadBlob('/reports/assets.pdf', 'assets.pdf')
}

export function downloadAuditReport() {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
  return downloadBlob('/audit/report', `audit-report-${timestamp}.html`)
}
