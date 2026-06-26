import request from '../utils/request'

export async function getCompanies() {
  const rows = await request.get('/company/list')
  return rows.map(row => ({
    ...row,
    asset_count: Number(row.asset_count || 0),
    total_original_value: Number(row.total_original_value || 0),
    in_use_count: Number(row.in_use_count || 0),
    in_stock_count: Number(row.in_stock_count || 0),
    idle_count: Number(row.idle_count || 0),
    repair_count: Number(row.repair_count || 0),
    scrapped_count: Number(row.scrapped_count || 0),
    pending_scrap_count: Number(row.pending_scrap_count || 0),
    assets: row.assets || []
  }))
}

export function createCompany(payload) {
  return request.post('/company/save', payload)
}

export function updateCompany(id, payload) {
  return request.put(`/company/${id}`, payload)
}

export function deleteCompany(id) {
  return request.delete(`/company/${id}`)
}
