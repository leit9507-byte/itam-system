import request from '../utils/request'

export async function getPurchases(filters = {}) {
  const result = await request.get('/purchase/list', {
    params: {
      created_from: filters.created_from || undefined,
      created_to: filters.created_to || undefined,
      page: filters.page || undefined,
      page_size: filters.page_size ?? filters.pageSize ?? undefined
    }
  })
  const { rows, total } = normalizePagedResult(result)
  return { list: rows.map(mapBackendPurchase), total }
}

export async function createPurchase(payload) {
  const items = (payload.items || []).map(item => ({
    name: item.product_name || item.name,
    category: item.category,
    brand: item.brand,
    model: item.model,
    spec: item.spec || '',
    quantity: Number(item.quantity || 1),
    unit_price: Number(item.unit_price || 0),
    retirement_years: item.retirement_years ? Number(item.retirement_years) : null,
    purchase_reason: item.purchase_reason || payload.purchase_reason || '',
    location: item.warehouse || item.location,
    dept_id: item.dept || item.dept_id || payload.dept || ''
  }))
  const totalAmount = items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0)
  const row = await request.post('/purchase/create', {
    purchase_no: payload.purchase_no || payload.approval_no || `PO-${Date.now()}`,
    company: payload.company || '',
    approval_no: payload.approval_no || '',
    supplier_name: payload.supplier_name || '',
    purchase_reason: payload.purchase_reason || '',
    total_amount: totalAmount,
    status: payload.status || 'created',
    items
  })
  return mapBackendPurchase(row)
}

export async function approvePurchase(row) {
  return mapBackendPurchase(await request.post(`/purchase/${encodeURIComponent(row.purchase_no)}/approve`, {}))
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
    approval_submitted: '已提交飞书审批',
    rejected: '已驳回',
    pending_acceptance: '待验收',
    received: '已入库'
  }
  return {
    id: row.purchase_no,
    purchase_no: row.purchase_no,
    created_at: formatDateTime(row.created_at),
    company: row.company || '',
    approval_no: row.approval_no || '',
    supplier_name: row.supplier_name || '未指定供应商',
    purchase_reason: row.purchase_reason || purchaseReasonSummary(items),
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
      spec: item.spec || '',
      quantity: Number(item.quantity || 0),
      unit_price: Number(item.unit_price || 0),
      retirement_years: item.retirement_years ?? null,
      purchase_reason: item.purchase_reason || row.purchase_reason || '',
      total_amount: Number(item.quantity || 0) * Number(item.unit_price || 0),
      warehouse: item.location || '',
      location: item.location || '',
      dept: item.dept_id || '',
      dept_id: item.dept_id || '',
      warranty_years: '',
      supplier_name: row.supplier_name || '未指定供应商',
      purchase_no: row.purchase_no
    })),
    quantity: items.reduce((sum, item) => sum + Number(item.quantity || 0), 0)
  }
}

function formatDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function purchaseReasonSummary(items) {
  return [...new Set((items || []).map(item => item.purchase_reason).filter(Boolean))].join('；')
}

function normalizePagedResult(result) {
  if (Array.isArray(result)) return { rows: result, total: result.length }
  const rows = result?.list || result?.items || []
  return { rows, total: Number(result?.total ?? rows.length) }
}
