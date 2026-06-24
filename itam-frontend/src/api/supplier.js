import request from '../utils/request'

export async function getSuppliers(filters = {}) {
  const rows = await request.get('/supplier/list', { params: { keyword: filters.keyword || '' } })
  return rows.map(mapSupplier)
}

export async function getSupplierPurchaseDevices(supplierName) {
  const rows = await request.get(`/supplier/${encodeURIComponent(supplierName)}/devices`)
  return rows.map(item => ({
    supplier_name: item.supplier_name,
    purchase_no: item.purchase_no,
    status: item.status,
    product_name: item.product_name,
    category: item.category,
    brand: item.brand || '',
    model: item.model || '',
    quantity: Number(item.quantity || 0),
    unit_price: Number(item.unit_price || 0),
    total_amount: Number(item.total_amount || 0),
    warehouse: item.warehouse || '',
    dept: item.dept || ''
  }))
}

export async function saveSupplier(payload) {
  const body = {
    name: payload.name,
    contact: payload.contact || '',
    phone: payload.phone || '',
    level: payload.level || '普通',
    status: payload.status || '启用'
  }
  const row = payload.id ? await request.put(`/supplier/${payload.id}`, body) : await request.post('/supplier/save', body)
  return mapSupplier(row)
}

function mapSupplier(row) {
  return {
    id: row.id,
    supplier_no: row.supplier_no,
    name: row.name,
    contact: row.contact || '',
    phone: row.phone || '',
    level: row.level || '普通',
    status: row.status || '启用',
    purchase_count: Number(row.purchase_count || 0),
    device_count: Number(row.device_count || 0),
    total_amount: Number(row.total_amount || 0),
    last_purchase_no: row.last_purchase_no || ''
  }
}
