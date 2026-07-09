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

export function downloadDepartmentAssetsCsv() {
  return downloadBlob('/reports/department-assets.csv', 'department-assets.csv')
}

export function downloadPersonHoldingsCsv() {
  return downloadBlob('/reports/person-holdings.csv', 'person-holdings.csv')
}

export function downloadOverdueBorrowingsCsv() {
  return downloadBlob('/reports/overdue-borrowings.csv', 'overdue-borrowings.csv')
}

export function downloadWarrantyExpiringCsv(days = 90) {
  return downloadBlob(`/reports/warranty-expiring.csv?days=${days}`, 'warranty-expiring.csv')
}

export function downloadScrapDisposalLedgerCsv() {
  return downloadBlob('/reports/scrap-disposal-ledger.csv', 'scrap-disposal-ledger.csv')
}

export function downloadAuditReport() {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
  return downloadBlob('/audit/report.pdf', `audit-report-${timestamp}.pdf`)
}

export function downloadAuditReportExcel() {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
  return downloadBlob('/reports/audit-report.xlsx', `audit-report-${timestamp}.xlsx`)
}

export function getReportAnalytics() {
  return request.get('/reports/analytics')
}
