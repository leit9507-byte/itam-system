import request from '../utils/request'

export const assetStatuses = [
  { label: '待验收', value: 'pending_acceptance', type: 'info' },
  { label: '在库', value: 'in_stock', type: 'primary' },
  { label: '在用', value: 'in_use', type: 'success' },
  { label: '闲置', value: 'idle', type: 'warning' },
  { label: '借出', value: 'borrowed', type: 'warning' },
  { label: '维修中', value: 'repair', type: 'danger' },
  { label: '已出库', value: 'out_stock', type: 'info' },
  { label: '待报废', value: 'ready_scrap', type: 'warning' },
  { label: '待处置登记', value: 'pending_scrap', type: 'danger' },
  { label: '已报废', value: 'scrapped', type: 'info' },
  { label: '已处置', value: 'disposed', type: 'info' },
  { label: '已丢失', value: 'lost', type: 'danger' }
]

export const statusMap = Object.fromEntries(assetStatuses.map(item => [item.value, item]))
export const editableAssetStatuses = assetStatuses.filter(item => !['pending_acceptance', 'pending_scrap', 'scrapped', 'disposed', 'lost'].includes(item.value))
const DETAIL_CONTEXT_LIMIT = 500
const IMPORT_TIMEOUT_MS = 180000

export const lifecycleActionMap = {
  CREATE: '资产建档',
  BATCH_IMPORT: '批量导入',
  ASSET_UPDATE: '资产信息更新',
  STATUS_CHANGE: '状态变更',
  PURCHASE: '采购入库',
  PURCHASE_ACCEPTANCE: '采购验收入库',
  REPAIR_CREATE: '创建维修单',
  REPAIR_FINISH: '维修完成',
  SCRAP_REQUEST: '提交报废处置登记',
  SCRAP_APPROVE: '报废登记确认',
  SCRAP_REJECT: '报废登记取消',
  SCRAP_DISPOSE: '报废处置归档'
}

export async function getAssets(params = {}) {
  const result = await request.get('/asset/list', {
    params: {
      keyword: params.keyword || undefined,
      status: params.status || undefined,
      category: params.category || undefined,
      company: params.company || undefined,
      supplier: params.supplier || undefined,
      risk_filter: params.risk_filter || undefined,
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

export async function getAssetById(assetId) {
  return mapBackendAsset(await request.get(`/asset/${assetId}`))
}

export async function importAssetsFromText(content, operator = 'asset-import', overwrite = false) {
  const result = await request.post('/asset/import/text', { content, operator, overwrite }, { timeout: IMPORT_TIMEOUT_MS })
  return normalizeImportResult(result)
}

export async function importAssetsFromExcel(file, operator = 'asset-excel-import', overwrite = false) {
  const form = new FormData()
  form.append('file', file)
  const result = await request.post(`/asset/import/excel?operator=${encodeURIComponent(operator)}&overwrite=${overwrite ? 'true' : 'false'}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: IMPORT_TIMEOUT_MS
  })
  return normalizeImportResult(result)
}

export async function previewAssetsFromExcel(file, overwrite = false) {
  const form = new FormData()
  form.append('file', file)
  return normalizeImportPreview(await request.post(`/asset/import/excel/preview?overwrite=${overwrite ? 'true' : 'false'}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: IMPORT_TIMEOUT_MS
  }))
}

export async function previewAssetsFromText(content, operator = 'asset-import', overwrite = false) {
  return normalizeImportPreview(await request.post('/asset/import/text/preview', { content, operator, overwrite }, { timeout: IMPORT_TIMEOUT_MS }))
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

export async function importAssets(items, operator = 'asset-import', overwrite = false) {
  const result = await request.post('/asset/import', { items, operator, overwrite }, { timeout: IMPORT_TIMEOUT_MS })
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
    asset_no: payload.asset_no || payload.asset_id || '',
    name: payload.name,
    company: payload.company || '',
    category: payload.category,
    brand: payload.brand,
    model: payload.model,
    sn: payload.sn,
    config: {
      ...(payload.config || {}),
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
  return request.post('/asset/batch-update', {
    asset_ids: rows.map(row => row.asset_id),
    updates: payload
  })
}

export async function getAssetDetail(assetId) {
  const [asset, lifecycleResult, changes, checkouts, scrapResult] = await Promise.all([
    getAssetById(assetId),
    getLifecycleList({ asset_id: assetId, page: 1, page_size: DETAIL_CONTEXT_LIMIT }).catch(() => ({ list: [] })),
    getAssetChanges(assetId).catch(() => []),
    getAssetCheckouts(assetId).catch(() => []),
    getScrapRequests({ asset_id: assetId, page: 1, page_size: 5 }).catch(() => ({ list: [] }))
  ])
  const lifecycles = lifecycleResult.list
  const scrapRequests = scrapResult.list || []
  const inventoryRecords = lifecycles.filter(item => item.category === 'daily_inventory').map(mapInventoryLifecycle)
  return {
    asset,
    scrapInfo: scrapRequests[0] || null,
    scrapRequests,
    lifecycles,
    changes,
    checkouts,
    timeline: buildAssetTimeline(asset, lifecycles, changes, checkouts),
    usageRecords: [
      { user: asset?.owner_name || asset?.owner || '未分配', dept: asset?.dept_name || asset?.dept || '未绑定', from: asset?.created_at || '-', to: '至今' }
    ],
    inventoryRecords,
    risks: buildAssetRisksV2(asset)
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
    borrow_due_date: payload.borrow_due_date || '',
    remark: payload.remark || ''
  })
  return mapBackendAsset(asset)
}

export async function getAssetCheckouts(assetId, limit = 200) {
  const rows = await request.get(`/asset/${assetId}/checkouts`, { params: { limit } })
  return (Array.isArray(rows) ? rows : []).map(mapAssetCheckout)
}

export async function getCheckoutRecords(params = {}) {
  const result = await request.get('/asset/checkouts/list', {
    params: {
      keyword: params.keyword || undefined,
      status: params.status || undefined,
      checkout_type: params.checkout_type || undefined,
      assignee_user_id: params.assignee_user_id || undefined,
      dept_id: params.dept_id || undefined,
      date_from: params.date_from || undefined,
      date_to: params.date_to || undefined,
      due_from: params.due_from || undefined,
      due_to: params.due_to || undefined,
      due_days: params.due_days ?? undefined,
      page: params.page || undefined,
      page_size: params.page_size ?? params.pageSize ?? undefined
    }
  })
  const { rows, total } = normalizePagedResult(result)
  return { list: rows.map(mapAssetCheckout), total, summary: result.summary || {} }
}

export async function checkoutAsset(assetId, payload = {}) {
  const asset = await request.post(`/asset/${assetId}/checkout`, {
    checkout_type: payload.toStatus || payload.checkout_type || 'in_use',
    owner_user_id: payload.owner_user_id,
    dept_id: payload.dept_id,
    location: payload.location,
    due_date: payload.borrow_due_date || payload.due_date || '',
    remark: payload.remark || ''
  })
  return mapBackendAsset(asset)
}

export async function batchCheckoutAssets(assetIds, payload = {}) {
  return request.post('/asset/batch-outbound', {
    asset_ids: assetIds,
    checkout_type: payload.toStatus || payload.checkout_type || 'in_use',
    owner_user_id: payload.owner_user_id,
    dept_id: payload.dept_id,
    location: payload.location,
    due_date: payload.borrow_due_date || payload.due_date || '',
    remark: payload.remark || ''
  })
}

export async function checkinAsset(assetId, payload = {}) {
  const asset = await request.post(`/asset/${assetId}/checkin`, {
    location: payload.location,
    remark: payload.remark || '资产归还入库'
  })
  return mapBackendAsset(asset)
}

export async function batchCheckinAssets(assetIds, payload = {}) {
  return request.post('/asset/batch-inbound', {
    asset_ids: assetIds,
    location: payload.location,
    remark: payload.remark || '资产批量归还入库'
  })
}

export async function inboundAsset(assetId, payload = {}) {
  const inboundAddress = payload.location || ''
  const asset = await checkinAsset(assetId, { ...payload, location: inboundAddress, remark: payload.remark || '资产入库' })
  return asset
}

export async function outboundAsset(assetId, payload = {}) {
  const status = payload.toStatus || 'in_use'
  const isPublicLocation = status === 'out_stock' && payload.outboundTarget === 'location'
  const borrowDueDateText = status === 'borrowed' && payload.borrow_due_date ? `借用到期时间：${payload.borrow_due_date}` : ''
  const remark = [payload.remark || (isPublicLocation ? `出库到地址：${payload.location || ''}` : '资产出库'), borrowDueDateText].filter(Boolean).join('；')
  const asset = await checkoutAsset(assetId, {
    ...payload,
    toStatus: status,
    outboundTarget: isPublicLocation ? 'location' : 'user',
    owner_user_id: isPublicLocation ? '' : payload.owner_user_id,
    dept_id: isPublicLocation ? '' : payload.dept_id,
    location: payload.location,
    action: '出库',
    remark
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
      disposal_method: params.disposal_method || undefined,
      asset_id: params.asset_id || undefined,
      created_from: params.created_from || undefined,
      created_to: params.created_to || undefined,
      page: params.page || undefined,
      page_size: params.page_size ?? params.pageSize ?? undefined
    }
  })
  const { rows, total } = normalizePagedResult(result)
  return { list: rows.map(mapScrapRequest), total }
}

export async function disposeScrapRequest(requestId, payload = {}) {
  return mapScrapRequest(await request.post(`/scrap/${requestId}/dispose`, {
    final_residual_value: Number(payload.final_residual_value || 0),
    disposal_method: payload.disposal_method || '',
    retirement_date: dateToApi(payload.retirement_date),
    retirement_approval_no: payload.retirement_approval_no || '',
    retirement_flow_no: payload.retirement_flow_no || '',
    dispose_recipient_user_id: payload.dispose_recipient_user_id || '',
    dispose_recipient_name: payload.dispose_recipient_name || '',
    disposal_remark: payload.disposal_remark || ''
  }))
}

export async function batchDisposeScrapRequests(requestIds, payload = {}) {
  const result = await request.post('/scrap/batch-dispose', {
    request_ids: requestIds,
    final_residual_value: Number(payload.final_residual_value || 0),
    disposal_method: payload.disposal_method || '',
    final_residual_value_mode: payload.final_residual_value_mode || '',
    retirement_date: dateToApi(payload.retirement_date),
    retirement_approval_no: payload.retirement_approval_no || '',
    retirement_flow_no: payload.retirement_flow_no || '',
    dispose_recipient_user_id: payload.dispose_recipient_user_id || '',
    dispose_recipient_name: payload.dispose_recipient_name || '',
    disposal_remark: payload.disposal_remark || ''
  })
  return {
    success: Number(result.success || 0),
    failed: Number(result.failed || 0),
    list: (result.list || []).map(mapScrapRequest),
    errors: result.errors || []
  }
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
  const risk = list.filter(item => !item.owner || !item.dept || ['idle', 'repair', 'ready_scrap', 'pending_scrap', 'scrapped', 'lost'].includes(item.status)).length
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
    created: Number(result.created || 0),
    updated: Number(result.updated || 0),
    skipped: Number(result.skipped || 0),
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
    display_id: row.display_id ?? '',
    asset_id: row.asset_id,
    asset_no: row.asset_no || '',
    config,
    borrow_due_date: config.borrow_due_date || '',
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
    current_residual_value: Number(row.current_residual_value || 0),
    purchase_date: purchaseDate,
    purchase_approval_no: row.purchase_approval_no || '',
    purchase_supplier_name: row.purchase_supplier_name || '',
    payment_time: config.payment_time || '',
    payment_no: config.payment_no || '',
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
  const requestNo = row.request_no || `SC-${row.id}`
  const retirementFlowNo = row.retirement_flow_no || ''
  return {
    id: row.id,
    request_no: requestNo,
    registration_no: row.registration_no || requestNo,
    retirement_flow_no: retirementFlowNo,
    flow_no: row.flow_no || retirementFlowNo || requestNo,
    asset_id: row.asset_id,
    asset_no: row.asset_no || '',
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
    retirement_date: formatDate(row.retirement_date),
    retirement_approval_no: row.retirement_approval_no || '',
    estimated_residual_value: Number(row.estimated_residual_value || 0),
    final_residual_value: Number(row.final_residual_value || 0),
    disposal_remark: row.disposal_remark || '',
    dispose_recipient_user_id: row.dispose_recipient_user_id || '',
    dispose_recipient_name: row.dispose_recipient_name || '',
    disposed_by: row.disposed_by || '',
    disposed_at: formatDate(row.disposed_at),
    disposal_status: row.status === '已处置' ? '已处置' : '未处置',
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
    SCRAP_REQUEST: `提交报废处置登记，状态从 ${fromStatus || '-'} 调整为 ${toStatus || '-'}`,
    SCRAP_APPROVE: `报废登记确认，状态从 ${fromStatus || '-'} 调整为 ${toStatus || '-'}`,
    SCRAP_REJECT: `报废登记取消，状态从 ${fromStatus || '-'} 调整为 ${toStatus || '-'}`,
    SCRAP_DISPOSE: `报废资产完成处置归档，状态从 ${fromStatus || '-'} 调整为 ${toStatus || '-'}`
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

function mapAssetCheckout(row) {
  return {
    id: row.id,
    asset_id: row.asset_id,
    asset_no: row.asset_no || '',
    asset_name: row.asset_name || '',
    asset_category: row.asset_category || '',
    asset_status: row.asset_status || '',
    asset_status_label: statusLabel(row.asset_status),
    checkout_type: row.checkout_type,
    checkout_type_label: row.checkout_type === 'borrowed' ? '借用' : statusLabel(row.checkout_type),
    assignee_user_id: row.assignee_user_id || '',
    assignee_name: row.assignee_name || row.assignee_user_id || '',
    dept_id: row.dept_id || '',
    location: row.location || '',
    due_date: formatDate(row.due_date),
    status: row.status,
    status_label: row.status === 'open' ? '借用中' : '已归还',
    is_overdue: Boolean(row.is_overdue),
    days_overdue: Number(row.days_overdue || 0),
    checked_out_at: formatDateTime(row.checked_out_at),
    checked_out_by: row.checked_out_by || '',
    checked_in_at: formatDateTime(row.checked_in_at),
    checked_in_by: row.checked_in_by || '',
    checkin_location: row.checkin_location || '',
    remark: row.remark || '',
    checkin_remark: row.checkin_remark || ''
  }
}

function buildAssetTimeline(asset, lifecycles = [], changes = [], checkouts = []) {
  const rows = [
    ...(asset?.created_at ? [assetCreatedTimeline(asset)] : []),
    ...lifecycles.map(lifecycleTimeline),
    ...changes.map(changeTimeline),
    ...checkouts.flatMap(checkoutTimeline)
  ]
  const deduped = new Map()
  rows.filter(Boolean).forEach(item => {
    const key = `${item.source}:${item.source_id}:${item.event}:${item.raw_time || item.time}`
    if (!deduped.has(key)) deduped.set(key, item)
  })
  return [...deduped.values()].sort((a, b) => dateValue(b.raw_time || b.time) - dateValue(a.raw_time || a.time))
}

function assetCreatedTimeline(asset) {
  return {
    source: 'asset',
    source_id: asset.asset_id,
    event: 'created',
    group: 'basic',
    type: '建档',
    title: '资产建档',
    description: `${asset.name || asset.asset_id} 已创建，初始状态：${statusLabel(asset.status) || '-'}`,
    operator: '-',
    time: formatDateTime(asset.created_at),
    raw_time: asset.created_at,
    tone: 'primary',
    meta: [asset.category, asset.company].filter(Boolean)
  }
}

function lifecycleTimeline(row) {
  return {
    source: 'lifecycle',
    source_id: row.id,
    event: row.type,
    group: lifecycleGroup(row),
    type: row.type_label || lifecycleActionMap[row.type] || row.type || '生命周期',
    title: row.type_label || lifecycleActionMap[row.type] || row.type || '生命周期记录',
    description: row.description || row.status_change_label || '-',
    operator: row.operator || '-',
    time: row.time,
    raw_time: row.time_value || row.time,
    tone: lifecycleTone(row),
    meta: [row.status_change_label, row.responsible_label && row.responsible_label !== '-' ? `责任人：${row.responsible_label}` : ''].filter(Boolean)
  }
}

function changeTimeline(row) {
  return {
    source: 'change',
    source_id: row.id,
    event: row.field,
    group: 'change',
    type: '字段变更',
    title: `${row.field_label || row.field || '字段'}变更`,
    description: `${emptyText(row.old_value)} -> ${emptyText(row.new_value)}`,
    operator: row.operator || '-',
    time: row.created_at || '',
    raw_time: row.created_at || '',
    tone: 'info',
    meta: [row.summary].filter(Boolean)
  }
}

function checkoutTimeline(row) {
  const out = {
    source: 'checkout',
    source_id: row.id,
    event: 'checkout',
    group: 'checkout',
    type: row.checkout_type_label || '借用',
    title: `${row.checkout_type_label || '资产'}登记`,
    description: [row.assignee_name ? `借用人：${row.assignee_name}` : '', row.location ? `位置：${row.location}` : '', row.due_date ? `计划归还：${row.due_date}` : '', row.remark].filter(Boolean).join('；') || '资产已登记借用',
    operator: row.checked_out_by || '-',
    time: row.checked_out_at || '',
    raw_time: row.checked_out_at || '',
    tone: row.checkout_type === 'borrowed' ? 'warning' : 'success',
    meta: [row.dept_id, row.status_label].filter(Boolean)
  }
  const rows = [out]
  if (row.checked_in_at) {
    rows.push({
      source: 'checkout',
      source_id: row.id,
      event: 'checkin',
      group: 'checkout',
      type: '归还',
      title: '资产归还',
      description: [row.assignee_name ? `归还人：${row.assignee_name}` : '', row.checkin_location ? `入库位置：${row.checkin_location}` : '', row.checkin_remark].filter(Boolean).join('；') || '资产已归还入库',
      operator: row.checked_in_by || '-',
      time: row.checked_in_at,
      raw_time: row.checked_in_at,
      tone: 'primary',
      meta: [row.checkout_type_label].filter(Boolean)
    })
  }
  return rows
}

function lifecycleTone(row) {
  if (row.to_status === 'in_stock') return 'primary'
  if (['in_use', 'out_stock'].includes(row.to_status)) return 'success'
  if (row.to_status === 'borrowed') return 'warning'
  if (['repair', 'pending_scrap', 'scrapped', 'disposed', 'lost'].includes(row.to_status)) return 'danger'
  return 'info'
}

function lifecycleGroup(row) {
  if (['STATUS_CHANGE', 'PURCHASE', 'PURCHASE_ACCEPTANCE'].includes(row.type)) return 'inventory'
  if (['REPAIR_CREATE', 'REPAIR_FINISH'].includes(row.type) || row.to_status === 'repair') return 'repair'
  if (['SCRAP_REQUEST', 'SCRAP_APPROVE', 'SCRAP_REJECT', 'SCRAP_DISPOSE'].includes(row.type) || ['ready_scrap', 'pending_scrap', 'scrapped', 'disposed', 'lost'].includes(row.to_status)) return 'scrap'
  return 'lifecycle'
}

function emptyText(value) {
  return value === undefined || value === null || value === '' ? '-' : String(value)
}

function buildAssetRisksV2(asset) {
  if (!asset) return []
  const risks = []
  const today = startOfToday()
  const activeStatuses = ['in_use', 'borrowed', 'out_stock']
  const isActive = activeStatuses.includes(asset.status)
  const warrantyDate = parseDate(asset.warranty_expire_date)
  const retirementDate = parseDate(asset.retirement_date)

  if (!asset.owner && asset.status === 'in_use') risks.push({ level: 'high', message: '在用资产未绑定责任人', detail: '资产处于在用状态，但没有明确责任人，后续盘点、归还和追责都会受影响。' })
  if (!asset.dept && asset.price >= 50000) risks.push({ level: 'high', message: '高价值资产未绑定部门', detail: `资产原值 ¥${Number(asset.price || 0).toLocaleString()}，建议绑定部门用于预算归属和审计。` })

  if (warrantyDate) {
    const days = daysUntil(warrantyDate, today)
    if (days < 0) risks.push({ level: isActive ? 'high' : 'medium', message: `已过保 ${Math.abs(days)} 天`, detail: `质保到期日：${asset.warranty_expire_date}。仍在使用的过保设备建议评估延保、替换或纳入重点巡检。` })
    else if (days <= 30) risks.push({ level: 'medium', message: `质保 ${days} 天后到期`, detail: `质保到期日：${asset.warranty_expire_date}，建议提前确认是否续保或安排替换。` })
    else if (days <= 90) risks.push({ level: 'low', message: `质保 ${days} 天后到期`, detail: `质保到期日：${asset.warranty_expire_date}，可加入到期提醒清单。` })
  }

  if (retirementDate) {
    const days = daysUntil(retirementDate, today)
    if (days < 0) risks.push({ level: isActive ? 'high' : 'medium', message: `已超过服役年限 ${Math.abs(days)} 天`, detail: `预计退役时间：${asset.retirement_date}。仍在使用的超服役设备建议评估性能、安全和替换计划。` })
    else if (days <= 30) risks.push({ level: 'medium', message: `距离预计退役 ${days} 天`, detail: `预计退役时间：${asset.retirement_date}，建议提前准备替换或处置方案。` })
    else if (days <= 90) risks.push({ level: 'low', message: `距离预计退役 ${days} 天`, detail: `预计退役时间：${asset.retirement_date}，可纳入季度资产复核。` })
  }

  if (asset.status === 'idle') risks.push({ level: 'medium', message: '资产处于闲置状态', detail: '建议优先调拨复用，长期无法复用时进入报废或处置评估。' })
  if (asset.status === 'repair') risks.push({ level: 'medium', message: '资产维修中', detail: '请关注维修周期、费用和供应商反馈，避免长期占用资产。' })
  if (asset.status === 'ready_scrap') risks.push({ level: 'medium', message: '资产待报废', detail: '资产已标记待报废，可提交报废处置登记并补充处置依据。' })
  if (asset.status === 'pending_scrap') risks.push({ level: 'medium', message: '待处置登记', detail: '资产已进入报废处置登记流程，请补充退役时间、审批单号和处理手段。' })
  if (asset.status === 'scrapped') risks.push({ level: 'low', message: '资产已报废', detail: '资产已报废，等待处置归档，后续盘点应作为非在用资产处理。' })
  if (asset.status === 'disposed') risks.push({ level: 'low', message: '资产已处置归档', detail: '资产已完成处置，保留审计记录和附件归档即可。' })
  if (asset.status === 'lost') risks.push({ level: 'high', message: '资产已丢失', detail: '资产已登记丢失，应保留盘点、审批或责任确认记录，禁止继续领用、维修或处置操作。' })
  return risks.length ? risks : [{ level: 'low', message: '暂无显著风险', detail: '责任人、状态、质保和预计退役时间未发现明显异常。' }]
}

function parseDate(value) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function startOfToday() {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

function daysUntil(date, base = startOfToday()) {
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  return Math.ceil((target.getTime() - base.getTime()) / 86400000)
}

function buildAssetRisks(asset) {
  if (!asset) return []
  const risks = []
  if (!asset.owner && asset.status === 'in_use') risks.push({ level: 'high', message: '在用资产未绑定责任人' })
  if (!asset.dept && asset.price >= 50000) risks.push({ level: 'high', message: '高价值资产未绑定部门' })
  if (asset.status === 'idle') risks.push({ level: 'medium', message: '资产处于闲置状态，建议调拨复用' })
  if (asset.status === 'repair') risks.push({ level: 'medium', message: '资产维修中，请关注维修周期' })
  if (asset.status === 'ready_scrap') risks.push({ level: 'medium', message: '资产已标记待报废，可提交报废处置登记' })
  if (asset.status === 'pending_scrap') risks.push({ level: 'medium', message: '资产待报废处置登记' })
  if (asset.status === 'scrapped') risks.push({ level: 'low', message: '资产已报废，等待处置归档' })
  if (asset.status === 'disposed') risks.push({ level: 'low', message: '资产已处置归档，仅保留审计记录' })
  if (asset.status === 'lost') risks.push({ level: 'high', message: '资产已丢失，仅保留审计记录' })
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

function dateValue(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 0 : date.getTime()
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
