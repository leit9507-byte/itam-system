import request from '../utils/request'

export const inventoryTypes = [
  { label: '许可证', value: 'license' },
  { label: '耗材', value: 'consumable' },
  { label: '配件', value: 'accessory' },
  { label: '组件', value: 'component' }
]

export const inventoryActions = [
  { label: '入库', value: 'in' },
  { label: '出库调整', value: 'out' },
  { label: '分配给人员', value: 'assign' },
  { label: '耗用', value: 'consume' },
  { label: '归还', value: 'return' },
  { label: '装配到资产', value: 'install' },
  { label: '从资产拆卸', value: 'uninstall' },
  { label: '增加调整', value: 'adjust_add' },
  { label: '减少调整', value: 'adjust_sub' }
]

export async function getInventoryItems(params = {}) {
  const result = await request.get('/inventory/items', {
    params: {
      keyword: params.keyword || undefined,
      item_type: params.item_type || undefined,
      item_types: params.item_types || undefined,
      status: params.status || undefined,
      low_stock: params.low_stock || undefined,
      expiring_days: params.expiring_days ?? undefined,
      page: params.page || undefined,
      page_size: params.page_size ?? params.pageSize ?? undefined
    }
  })
  return {
    list: (result.list || []).map(mapInventoryItem),
    total: Number(result.total || 0),
    summary: result.summary || {}
  }
}

export function createInventoryItem(payload) {
  return request.post('/inventory/items', normalizeItem(payload))
}

export function updateInventoryItem(id, payload) {
  return request.put(`/inventory/items/${id}`, normalizeItem(payload))
}

export function operateInventoryItem(id, payload) {
  return request.post(`/inventory/items/${id}/ledger`, {
    action: payload.action,
    quantity: Number(payload.quantity || 1),
    assignee_user_id: payload.assignee_user_id || '',
    assignee_name: payload.assignee_name || '',
    dept_id: payload.dept_id || '',
    asset_id: payload.asset_id || '',
    location: payload.location || '',
    remark: payload.remark || ''
  })
}

export async function getInventoryLedger(id) {
  const rows = await request.get(`/inventory/items/${id}/ledger`)
  return (rows || []).map(row => ({
    ...row,
    action_label: actionLabel(row.action),
    created_at_text: formatDateTime(row.created_at)
  }))
}

export function typeLabel(value) {
  return inventoryTypes.find(item => item.value === value)?.label || value || '-'
}

export function actionLabel(value) {
  return inventoryActions.find(item => item.value === value)?.label || value || '-'
}

function normalizeItem(payload) {
  return {
    item_type: payload.item_type,
    code: payload.code,
    name: payload.name,
    brand: payload.brand || '',
    model: payload.model || '',
    spec: payload.spec || '',
    total_qty: Number(payload.total_qty || 0),
    available_qty: payload.available_qty === '' || payload.available_qty == null ? undefined : Number(payload.available_qty),
    min_qty: Number(payload.min_qty || 0),
    unit_cost: Number(payload.unit_cost || 0),
    license_key: payload.license_key || '',
    expire_date: payload.expire_date ? `${payload.expire_date}T00:00:00` : null,
    supplier: payload.supplier || '',
    dept_id: payload.dept_id || '',
    location: payload.location || '',
    status: payload.status || 'active',
    remark: payload.remark || ''
  }
}

function mapInventoryItem(row) {
  return {
    ...row,
    type_label: typeLabel(row.item_type),
    expire_date_text: formatDate(row.expire_date),
    low_stock: Number(row.available_qty || 0) <= Number(row.min_qty || 0)
  }
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toISOString().slice(0, 10)
}

function formatDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', { hour12: false })
}
