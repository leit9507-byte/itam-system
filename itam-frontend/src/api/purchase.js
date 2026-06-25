import request from '../utils/request'

export async function getPurchases() {
  const rows = await request.get('/purchase/list')
  return rows.map(mapBackendPurchase)
}

export async function createPurchase(payload) {
  const items = (payload.items || []).map(item => ({
    name: item.product_name || item.name,
    category: item.category,
    brand: item.brand,
    model: item.model,
    quantity: Number(item.quantity || 1),
    unit_price: Number(item.unit_price || 0),
    retirement_years: item.retirement_years ? Number(item.retirement_years) : null,
    location: item.warehouse || item.location,
    dept_id: item.dept || item.dept_id
  }))
  const totalAmount = items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0)
  const row = await request.post('/purchase/create', {
    purchase_no: payload.purchase_no || payload.approval_no || `PO-${Date.now()}`,
    supplier_name: payload.supplier_name || '',
    total_amount: totalAmount,
    status: payload.status || 'created',
    items
  })
  return mapBackendPurchase(row)
}

export function approvePurchase(row) {
  row.status = 'pending_acceptance'
  row.status_label = '待验收'
  return Promise.resolve(row)
}

export async function acceptPurchase(purchaseNo, acceptances) {
  const result = await request.post(`/purchase/accept?purchase_no=${encodeURIComponent(purchaseNo)}`, {
    operator: '采购验收员',
    acceptances: acceptances.map(item => ({
      ...item,
      assets: (item.assets || []).map(asset => ({
        ...asset,
        warranty_months: asset.warranty_years ? Number(asset.warranty_years) * 12 : asset.warranty_months || null
      }))
    }))
  })
  return {
    purchase: mapBackendPurchase(result.purchase),
    generated_assets: result.assets?.length || 0,
    assets: result.assets || []
  }
}

export async function receivePurchase(purchaseNo) {
  const result = await request.post(`/purchase/receive?purchase_no=${encodeURIComponent(purchaseNo)}`, {
    operator: '采购验收员'
  })
  return {
    purchase: mapBackendPurchase(result.purchase),
    generated_assets: result.assets?.length || 0,
    assets: result.assets || []
  }
}

function mapBackendPurchase(row) {
  const items = row.items || []
  const statusLabelMap = {
    created: '审批中',
    pending_acceptance: '待验收',
    received: '已入库'
  }
  return {
    id: row.purchase_no,
    purchase_no: row.purchase_no,
    approval_no: row.purchase_no,
    supplier_name: row.supplier_name || '未指定供应商',
    total_amount: Number(row.total_amount || 0),
    status: row.status || 'created',
    status_label: statusLabelMap[row.status] || row.status || '审批中',
    items: items.map(item => ({
      id: item.id,
      product_name: item.name,
      name: item.name,
      category: item.category,
      brand: item.brand || '',
      model: item.model || '',
      quantity: Number(item.quantity || 0),
      unit_price: Number(item.unit_price || 0),
      retirement_years: item.retirement_years ?? null,
      total_amount: Number(item.quantity || 0) * Number(item.unit_price || 0),
      warehouse: item.location || '',
      location: item.location || '',
      dept: item.dept_id || '',
      dept_id: item.dept_id || '',
      spec: '',
      warranty_years: '',
      supplier_name: row.supplier_name || '未指定供应商',
      purchase_no: row.purchase_no
    })),
    quantity: items.reduce((sum, item) => sum + Number(item.quantity || 0), 0)
  }
}
