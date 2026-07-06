import request from '../utils/request'

export const assetStatuses = [
  { label: '待采购', value: 'pending_purchase', type: 'info' },
  { label: '待验收', value: 'pending_acceptance', type: 'info' },
  { label: '在库', value: 'in_stock', type: 'primary' },
  { label: '在用', value: 'in_use', type: 'success' },
  { label: '闲置', value: 'idle', type: 'warning' },
  { label: '借出', value: 'borrowed', type: 'warning' },
  { label: '维修中', value: 'repair', type: 'danger' },
  { label: '已出库', value: 'out_stock', type: 'info' },
  { label: '待报废', value: 'ready_scrap', type: 'warning' },
  { label: '已提交报废审批', value: 'pending_scrap', type: 'danger' },
  { label: '已报废', value: 'scrapped', type: 'info' }
]

export const statusMap = Object.fromEntries(assetStatuses.map(item => [item.value, item]))
export const editableAssetStatuses = assetStatuses.filter(item => !['pending_purchase', 'pending_acceptance', 'pending_scrap', 'scrapped'].includes(item.value))
const DETAIL_CONTEXT_LIMIT = 500

export const lifecycleActionMap = {
  CREATE: '资产建档',
  BATCH_IMPORT: '批量导入',
  ASSET_UPDATE: '资产信息更新',
  STATUS_CHANGE: '状态变更',
  PURCHASE: '采购入库',
  PURCHASE_ACCEPTANCE: '采购验收入库',
  REPAIR_CREATE: '创建维修单',
  REPAIR_FINISH: '维修完成',
  SCRAP_REQUEST: '提交报废审批',
  SCRAP_APPROVE: '报废审批通过',
  SCRAP_REJECT: '报废审批驳回'
}

export async function getAssets(params = {}) {
  const result = await request.get('/asset/list', {
    params: {
      keyword: params.keyword || undefined,
      status: params.status || undefined,
      category: params.category || undefined,
      company: params.company || undefined,
      supplier: params.supplier || undefined,
      page: params.page || undefined,
      page_size: params.page_size ?? params.pageSize ?? undefined
    }
  })
  const { rows, total } = normalizePagedResult(result)
  const list = rows.map(mapBackendAsset)
  return { list, total }
}

export function getAssetSummary() {
  return request.get('/asset/summary')
}

export async function importAssetsFromText(content, operator = 'asset-import') {
  const result = await request.post('/asset/import/text', { content, operator })
  return normalizeImportResult(result)
}

export async function importAssetsFromExcel(file, operator = 'asset-excel-import') {
  const form = new FormData()
  form.append('file', file)
  const result = await request.post(`/asset/import/excel?operator=${encodeURIComponent(operator)}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return normalizeImportResult(result)
}

export async function previewAssetsFromExcel(file) {
  const form = new FormData()
  form.append('file', file)
  return normalizeImportPreview(await request.post('/asset/import/excel/preview', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }))
}

export async function previewAssetsFromText(content, operator = 'asset-import') {
  return normalizeImportPreview(await request.post('/asset/import/text/preview', { content, operator }))
}

export async function downloadAssetImportTemplate() {
  const blob = await request.get('/asset/import/template', { responseType: 'blob' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'asset_import_template.xlsx'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function importAssets(items, operator = 'asset-import') {
  const result = await request.post('/asset/import', { items, operator })
  return normalizeImportResult(result)
}

function normalizeImportPreview(result) {
  return {
    total: Number(result.total || 0),
    valid: Number(result.valid || 0),
    errors: result.errors || [],
    items: (result.items || []).map(item => ({
      row: item.row,
      valid: item.valid,
      data: item.data || {}
    }))
  }
}

export async function updateAsset(assetId, payload) {
  const warrantyYears = payload.warranty_years === '' || payload.warranty_years == null ? null : Number(payload.warranty_years)
  const warrantyMonths = warrantyYears == null ? null : warrantyYears * 12
  const warrantyExpireDate = warrantyYears && payload.purchase_date ? addYears(payload.purchase_date, warrantyYears) : payload.warranty_expire_date
  const row = await request.put(`/asset/${assetId}`, {
    asset_id: payload.asset_id,
    asset_no: payload.asset_no || '',
    name: payload.name,
    company: payload.company || '',
    category: payload.category,
    brand: payload.brand,
    model: payload.model,
    sn: payload.sn,
    config: {
      spec: payload.spec || '',
      retirement_years: payload.retirement_years === '' || payload.retirement_years == null ? null : Number(payload.retirement_years)
    },
    purchase_price: Number(payload.price || payload.purchase_price || 0),
    purchase_date: dateToApi(payload.purchase_date),
    purchase_approval_no: payload.purchase_approval_no || '',
    purchase_supplier_name: payload.purchase_supplier_name || '',
    warranty_expire_date: dateToApi(warrantyExpireDate),
    warranty_months: warrantyMonths,
    status: payload.status,
    owner_user_id: payload.owner_user_id || '',
    dept_id: payload.dept_id || '',
    location: payload.location || '',
    remark: payload.remark || ''
  })
  return mapBackendAsset(row)
}

export async function batchUpdateAssets(rows, payload) {
  const updated = []
  for (const row of rows) {
    updated.push(await updateAsset(row.asset_id, { ...row, ...payload }))
  }
  return updated
}

export async function getAssetDetail(assetId) {
  const { list } = await getAssets({})
  const asset = list.find(item => item.asset_id === assetId) || list[0]
  const lifecycleResult = await getLifecycleList({ page: 1, page_size: DETAIL_CONTEXT_LIMIT }).catch(() => ({ list: [] }))
  const changes = await getAssetChanges(assetId).catch(() => [])
  const lifecycles = lifecycleResult.list.filter(item => item.asset_id === assetId)
  return {
    asset,
    lifecycles,
    changes,
    usageRecords: [
      { user: asset?.owner_name || asset?.owner || '未分配', dept: asset?.dept_name || asset?.dept || '未绑定', from: asset?.created_at || '-', to: '至今' }
    ],
    inventoryRecords: lifecycles.filter(item => item.category === 'daily_inventory').map(mapInventoryLifecycle),
    risks: buildAssetRisks(asset)
  }
}

export function getAssetChanges(assetId) {
  return request.get(`/asset/${assetId}/changes`)
}

export async function getLifecycleList(params = {}) {
  const result = await request.get('/lifecycle/list', { params })
  const { rows, total } = normalizePagedResult(result)
  return { list: rows.map(mapLifecycle), total }
}

export async function getInventoryRecords() {
  const result = await getLifecycleList({ operation_type: 'daily_inventory', page: 1, page_size: DETAIL_CONTEXT_LIMIT })
  return result.list.map(mapInventoryLifecycle)
}

export async function changeAssetStatus(assetId, status, payload = {}) {
  const asset = await request.post(`/asset/${assetId}/status`, {
    to_status: status,
    operator: payload.operator || '资产管理员',
    owner_user_id: payload.owner_user_id,
    dept_id: payload.dept_id,
    location: payload.location,
    remark: payload.remark || ''
  })
  return mapBackendAsset(asset)
}

export async function inboundAsset(assetId, payload = {}) {
  const inboundAddress = payload.location || ''
  const asset = await changeAssetStatus(assetId, 'in_stock', {
    ...payload,
    owner_user_id: '',
    dept_id: '',
    location: inboundAddress,
    action: '入库',
    remark: payload.remark || '资产入库'
  })
  return asset
}

export async function submitReclaimApproval(assetId, payload = {}) {
  return request.post(`/asset/${assetId}/reclaim-approval`, {
    location: payload.location || '',
    remark: payload.remark || '资产回收审批',
    user_id: payload.user_id || '',
    open_id: payload.open_id || ''
  })
}

export async function outboundAsset(assetId, payload = {}) {
  const status = payload.toStatus || 'in_use'
  const isPublicLocation = payload.outboundTarget === 'location'
  const asset = await changeAssetStatus(assetId, status, {
    ...payload,
    owner_user_id: isPublicLocation ? '' : payload.owner_user_id,
    dept_id: isPublicLocation ? '' : payload.dept_id,
    location: payload.location,
    action: '出库',
    remark: payload.remark || (isPublicLocation ? `公用设备：${payload.location || ''}` : '资产出库')
  })
  return asset
}

export async function createScrapRequest(assetId, payload = {}) {
  return mapScrapRequest(await request.post(`/scrap/${assetId}/create`, { ...payload, operator: payload.operator || '资产管理员' }))
}

export async function getScrapRequests(params = {}) {
  const result = await request.get('/scrap/list', {
    params: {
      status: params.status || undefined,
      created_from: params.created_from || undefined,
      created_to: params.created_to || undefined,
      page: params.page || undefined,
      page_size: params.page_size ?? params.pageSize ?? undefined
    }
  })
  const { rows, total } = normalizePagedResult(result)
  return { list: rows.map(mapScrapRequest), total }
}

export async function approveScrapRequest(requestId, approver = '资产负责人') {
  return mapScrapRequest(await request.post(`/scrap/${requestId}/approve`, { approver }))
}

export async function rejectScrapRequest(requestId, approver = '资产负责人') {
  return mapScrapRequest(await request.post(`/scrap/${requestId}/reject`, { approver }))
}

export async function addAcceptedAssets(product, serialNumbers = []) {
  const created = []
  for (const sn of serialNumbers) {
    const asset = await request.post('/asset/create', {
      name: product.product_name,
      category: product.category,
      brand: product.brand,
      model: product.model,
    sn,
      config: { spec: product.spec, retirement_years: product.retirement_years || null },
      purchase_price: Number(product.unit_price || 0),
      purchase_date: dateToApi(product.purchase_date),
      purchase_approval_no: product.purchase_no || product.approval_no || '',
      purchase_supplier_name: product.supplier_name || '',
      warranty_expire_date: dateToApi(product.warranty_expire_date),
      warranty_months: product.warranty_months || null,
      status: 'in_stock',
      dept_id: product.dept || '',
      location: product.warehouse || '待分配仓库',
      remark: product.remark || ''
    })
    created.push(mapBackendAsset(asset))
  }
  return created
}

export async function getDashboardStats() {
  const { list } = await getAssets({})
  const inUse = list.filter(item => item.status === 'in_use').length
  const idle = list.filter(item => item.status === 'idle').length
  const risk = list.filter(item => !item.owner || !item.dept || ['idle', 'repair', 'ready_scrap', 'pending_scrap', 'scrapped'].includes(item.status)).length
  return {
    total: list.length,
    inUse,
    idle,
    risk,
    utilization: [62, 66, 71, 69, 74, 78, 81],
    deptDistribution: groupBy(list, 'dept', '未绑定')
  }
}

function normalizeImportResult(result) {
  return {
    ...result,
    assets: (result.assets || []).map(mapBackendAsset)
  }
}

function mapBackendAsset(row) {
  const config = row.config || {}
  const ownerName = row.owner_display_name || row.owner_name || ''
  const deptName = row.dept_name || ''
  const purchaseDate = formatDate(row.purchase_date)
  const retirementYears = config.retirement_years || ''
  return {
    asset_id: row.asset_id,
    asset_no: row.asset_no || '',
    config,
    company: row.company || '',
    name: row.name,
    category: row.category,
    owner: row.owner_user_id || '',
    owner_user_id: row.owner_user_id || '',
    owner_name: ownerName,
    owner_username: row.owner_username || '',
    dept: row.dept_id || '',
    dept_id: row.dept_id || '',
    dept_name: deptName,
    status: row.status || 'in_stock',
    price: Number(row.purchase_price || 0),
    purchase_price: Number(row.purchase_price || 0),
    purchase_date: purchaseDate,
    purchase_approval_no: row.purchase_approval_no || '',
    purchase_supplier_name: row.purchase_supplier_name || '',
    warranty_expire_date: formatDate(row.warranty_expire_date),
    warranty_months: row.warranty_months ?? '',
    warranty_years: row.warranty_months ? Math.round(Number(row.warranty_months) / 12) : '',
    retirement_years: retirementYears,
    retirement_date: addYears(purchaseDate, Number(retirementYears)),
    brand: row.brand || '',
    model: row.model || '',
    spec: config.spec || '',
    location: row.location || '',
    remark: row.remark || '',
    sn: row.sn || '',
    created_at: formatDate(row.created_at)
  }
}

function mapScrapRequest(row) {
  return {
    id: row.id,
    request_no: row.request_no || `SC-${row.id}`,
    asset_id: row.asset_id,
    asset_name: row.asset_name,
    sn: row.asset_sn || '',
    company: row.company || '',
    category: row.category || '',
    brand: row.brand || '',
    model: row.model || '',
    owner_user_id: row.owner_user_id || '',
    dept_id: row.dept_id || '',
    location: row.location || '',
    purchase_price: Number(row.purchase_price || 0),
    purchase_date: formatDate(row.purchase_date),
    purchase_approval_no: row.purchase_approval_no || '',
    purchase_supplier_name: row.purchase_supplier_name || '',
    applicant: row.applicant || '',
    reason: row.reason || '',
    disposal_method: row.disposal_method || '',
    estimated_residual_value: Number(row.estimated_residual_value || 0),
    status: row.status,
    created_at: formatDate(row.created_at),
    approver: row.approver || '',
    approved_at: formatDate(row.approved_at)
  }
}

function mapLifecycle(row) {
  const fromStatusLabel = statusLabel(row.from_status)
  const toStatusLabel = statusLabel(row.to_status)
  const category = lifecycleCategory(row)
  const responsibleLabel = lifecycleResponsibleLabel(row, category)
  return {
    ...row,
    time_value: row.time,
    time: formatDateTime(row.time),
    category,
    category_label: category === 'daily_inventory' ? '日常出入库' : '其他操作',
    responsible_label: responsibleLabel,
    type_label: lifecycleActionLabel(row),
    from_status_label: fromStatusLabel,
    to_status_label: toStatusLabel,
    status_change_label: statusChangeLabel(fromStatusLabel, toStatusLabel),
    description: lifecycleDescription(row, fromStatusLabel, toStatusLabel)
  }
}

function lifecycleCategory(row) {
  if (row.type !== 'STATUS_CHANGE') return 'other'
  return ['in_stock', 'in_use', 'borrowed', 'out_stock'].includes(row.to_status) ? 'daily_inventory' : 'other'
}

function lifecycleActionLabel(row) {
  if (row.type === 'STATUS_CHANGE') {
    if (row.to_status === 'in_stock') return '入库回收'
    if (['in_use', 'borrowed', 'out_stock'].includes(row.to_status)) return `出库-${statusLabel(row.to_status)}`
  }
  return lifecycleActionMap[row.type] || row.type || '-'
}

function lifecycleResponsibleLabel(row, category) {
  if (category !== 'daily_inventory') return '-'
  const text = String(row.description || '')
  const match = text.match(/(?:领用人|借用人|出库责任人|退回人)[:：]\s*([^;；]+)/)
  return match?.[1]?.trim() || '-'
}

function statusLabel(status) {
  return status ? statusMap[status]?.label || status : ''
}

function statusChangeLabel(fromStatus, toStatus) {
  if (fromStatus && toStatus) return `${fromStatus} -> ${toStatus}`
  if (toStatus) return `更新为 ${toStatus}`
  if (fromStatus) return `原状态 ${fromStatus}`
  return '-'
}

function lifecycleDescription(row, fromStatus, toStatus) {
  const remark = row.description && !String(row.description).includes('->') ? row.description : ''
  const statusText = statusChangeLabel(fromStatus, toStatus)
  const action = lifecycleActionMap[row.type] || row.type || '生命周期记录'
  const base = {
    CREATE: `新建资产，初始状态为 ${toStatus || '-'}`,
    BATCH_IMPORT: `批量导入资产，初始状态为 ${toStatus || '-'}`,
    ASSET_UPDATE: fromStatus !== toStatus && toStatus ? `更新资产信息，状态从 ${fromStatus || '-'} 调整为 ${toStatus}` : '更新资产信息',
    STATUS_CHANGE: `资产状态从 ${fromStatus || '-'} 调整为 ${toStatus || '-'}`,
    PURCHASE: `采购完成并入库，状态为 ${toStatus || '-'}`,
    PURCHASE_ACCEPTANCE: `采购验收完成并入库，状态为 ${toStatus || '-'}`,
    REPAIR_CREATE: `创建维修单，状态从 ${fromStatus || '-'} 调整为 ${toStatus || '-'}`,
    REPAIR_FINISH: `维修完成，状态从 ${fromStatus || '-'} 调整为 ${toStatus || '-'}`,
    SCRAP_REQUEST: `提交报废审批，状态从 ${fromStatus || '-'} 调整为 ${toStatus || '-'}`,
    SCRAP_APPROVE: `报废审批通过，状态从 ${fromStatus || '-'} 调整为 ${toStatus || '-'}`,
    SCRAP_REJECT: `报废审批驳回，状态从 ${fromStatus || '-'} 调整为 ${toStatus || '-'}`
  }[row.type] || `${action}，${statusText}`
  return remark ? `${base}；备注：${remark}` : base
}

function groupBy(list, key, emptyLabel) {
  const map = {}
  list.forEach(item => {
    const name = item[key] || emptyLabel
    map[name] = (map[name] || 0) + 1
  })
  return Object.entries(map).map(([name, value]) => ({ name, value }))
}

function mapInventoryLifecycle(row) {
  const isInbound = row.to_status === 'in_stock'
  return {
    id: row.id,
    asset_id: row.asset_id,
    type: isInbound ? '入库' : '出库',
    operator: row.operator || '',
    target: row.responsible_label && row.responsible_label !== '-' ? row.responsible_label : row.to_status_label || row.to_status || '-',
    time: row.time,
    remark: row.description || ''
  }
}

function buildAssetRisks(asset) {
  if (!asset) return []
  const risks = []
  if (!asset.owner && asset.status === 'in_use') risks.push({ level: 'high', message: '在用资产未绑定责任人' })
  if (!asset.dept && asset.price >= 50000) risks.push({ level: 'high', message: '高价值资产未绑定部门' })
  if (asset.status === 'idle') risks.push({ level: 'medium', message: '资产处于闲置状态，建议调拨复用' })
  if (asset.status === 'repair') risks.push({ level: 'medium', message: '资产维修中，请关注维修周期' })
  if (asset.status === 'ready_scrap') risks.push({ level: 'medium', message: '资产已标记待报废，可提交报废审批' })
  if (asset.status === 'pending_scrap') risks.push({ level: 'medium', message: '资产已提交报废审批，请关注审批结果' })
  if (asset.status === 'scrapped') risks.push({ level: 'low', message: '资产已报废，等待处置归档' })
  if (asset.warranty_expire_date && new Date(asset.warranty_expire_date) < new Date()) risks.push({ level: 'medium', message: '资产质保已过期' })
  return risks.length ? risks : [{ level: 'low', message: '暂无显著风险' }]
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

function dateToApi(value) {
  if (!value) return null
  return `${value}T00:00:00`
}

function addYears(value, years) {
  if (!value || !years) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  date.setFullYear(date.getFullYear() + Number(years))
  return date.toISOString().slice(0, 10)
}

function normalizePagedResult(result) {
  if (Array.isArray(result)) return { rows: result, total: result.length }
  const rows = result?.list || result?.items || []
  return { rows, total: Number(result?.total ?? rows.length) }
}
