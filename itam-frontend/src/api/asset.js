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
  { label: '待报废', value: 'pending_scrap', type: 'warning' },
  { label: '已报废', value: 'scrapped', type: 'info' }
]

export const statusMap = Object.fromEntries(assetStatuses.map(item => [item.value, item]))

const localLifecycles = {}
const localInventoryRecords = []
const scrapRequests = []

export async function getAssets(params = {}) {
  const rows = await request.get('/asset/list')
  const mapped = rows.map(mapBackendAsset)
  const keyword = (params.keyword || '').toLowerCase()
  const status = params.status || ''
  const category = params.category || ''
  const supplier = params.supplier || ''
  const list = mapped.filter(item => {
    const searchText = [
      item.asset_id,
      item.name,
      item.dept,
      item.dept_name,
      item.sn,
      item.brand,
      item.model,
      item.owner,
      item.owner_name,
      item.owner_username,
      item.purchase_approval_no,
      item.purchase_supplier_name
    ].join(' ').toLowerCase()
    const hitSupplier = !supplier || item.purchase_supplier_name === supplier
    return (!keyword || searchText.includes(keyword)) && (!status || item.status === status) && (!category || item.category === category) && hitSupplier
  })
  return { list, total: list.length }
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

export async function importAssets(items, operator = 'asset-import') {
  const result = await request.post('/asset/import', { items, operator })
  return normalizeImportResult(result)
}

export async function updateAsset(assetId, payload) {
  const row = await request.put(`/asset/${assetId}`, {
    name: payload.name,
    category: payload.category,
    brand: payload.brand,
    model: payload.model,
    sn: payload.sn,
    config: { spec: payload.spec || '', warehouse: payload.warehouse || '' },
    purchase_price: Number(payload.price || payload.purchase_price || 0),
    purchase_date: dateToApi(payload.purchase_date),
    purchase_approval_no: payload.purchase_approval_no || '',
    purchase_supplier_name: payload.purchase_supplier_name || '',
    warranty_expire_date: dateToApi(payload.warranty_expire_date),
    warranty_months: payload.warranty_months === '' || payload.warranty_months == null ? null : Number(payload.warranty_months),
    status: payload.status,
    owner_user_id: payload.owner_user_id || '',
    dept_id: payload.dept_id || '',
    location: payload.location || payload.warehouse || ''
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
  return {
    asset,
    lifecycles: localLifecycles[assetId] || [
      { type: '建档', status: asset?.status || 'in_stock', operator: '后端系统', time: asset?.created_at || '', description: '资产从后端接口加载' }
    ],
    usageRecords: [
      { user: asset?.owner_name || asset?.owner || '未分配', dept: asset?.dept_name || asset?.dept || '未绑定', from: asset?.created_at || '-', to: '至今' }
    ],
    inventoryRecords: localInventoryRecords.filter(item => item.asset_id === assetId),
    risks: buildAssetRisks(asset)
  }
}

export async function getLifecycleList() {
  const { list } = await getAssets({})
  return list.flatMap(asset => localLifecycles[asset.asset_id] || [
    { asset_id: asset.asset_id, type: '建档', status: asset.status, operator: '后端系统', time: asset.created_at || '', description: '资产建档' }
  ])
}

export function getInventoryRecords() {
  return Promise.resolve([...localInventoryRecords])
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
  pushLifecycle(assetId, payload.action || '状态变更', status, payload.operator || '资产管理员', payload.remark || `状态更新为${statusMap[status]?.label || status}`)
  return mapBackendAsset(asset)
}

export async function inboundAsset(assetId, payload = {}) {
  const asset = await changeAssetStatus(assetId, 'in_stock', {
    ...payload,
    owner_user_id: '',
    dept_id: '',
    location: payload.warehouse || payload.location || '',
    action: '入库',
    remark: payload.remark || '资产入库'
  })
  localInventoryRecords.unshift(buildInventory(assetId, '入库', payload.warehouse || asset.warehouse || '默认仓库', payload.remark || '资产入库'))
  return asset
}

export async function outboundAsset(assetId, payload = {}) {
  const status = payload.toStatus || 'in_use'
  const asset = await changeAssetStatus(assetId, status, {
    ...payload,
    owner_user_id: payload.owner_user_id,
    dept_id: payload.dept_id,
    location: payload.location,
    action: '出库',
    remark: payload.remark || '资产出库'
  })
  localInventoryRecords.unshift(buildInventory(assetId, '出库', `${payload.owner_name || asset.owner_name || asset.owner || '未指定'} / ${payload.dept_name || asset.dept_name || asset.dept || '未指定'}`, payload.remark || '资产出库'))
  return asset
}

export async function createScrapRequest(assetId, payload = {}) {
  const { list } = await getAssets({})
  const asset = list.find(item => item.asset_id === assetId)
  if (!asset) throw new Error('资产不存在')
  const existed = scrapRequests.find(item => item.asset_id === assetId && item.status === '审批中')
  if (existed) return existed

  await changeAssetStatus(assetId, 'pending_scrap', { action: '报废申请', remark: payload.reason || '创建报废审批流程' })
  const requestItem = {
    id: `SC-${new Date().getFullYear()}-${String(scrapRequests.length + 1).padStart(3, '0')}`,
    asset_id: asset.asset_id,
    asset_name: asset.name,
    sn: asset.sn,
    applicant: payload.applicant || asset.dept || '资产管理员',
    reason: payload.reason,
    disposal_method: payload.disposal_method || '环保回收',
    estimated_residual_value: Number(payload.estimated_residual_value || 0),
    status: '审批中',
    created_at: new Date().toISOString().slice(0, 10),
    approver: ''
  }
  scrapRequests.unshift(requestItem)
  return requestItem
}

export function getScrapRequests() {
  return Promise.resolve([...scrapRequests])
}

export async function approveScrapRequest(requestId, approver = '资产负责人') {
  const item = scrapRequests.find(row => row.id === requestId)
  if (!item) throw new Error('报废申请不存在')
  await changeAssetStatus(item.asset_id, 'scrapped', { action: '报废审批通过', operator: approver, remark: `处置方式：${item.disposal_method}` })
  item.status = '已通过'
  item.approver = approver
  return item
}

export async function rejectScrapRequest(requestId, approver = '资产负责人') {
  const item = scrapRequests.find(row => row.id === requestId)
  if (!item) throw new Error('报废申请不存在')
  await changeAssetStatus(item.asset_id, 'idle', { action: '报废审批驳回', operator: approver, remark: '资产恢复为闲置' })
  item.status = '已驳回'
  item.approver = approver
  return item
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
      config: { spec: product.spec, warehouse: product.warehouse },
      purchase_price: Number(product.unit_price || 0),
      purchase_date: dateToApi(product.purchase_date),
      purchase_approval_no: product.purchase_no || product.approval_no || '',
      purchase_supplier_name: product.supplier_name || '',
      warranty_expire_date: dateToApi(product.warranty_expire_date),
      warranty_months: product.warranty_months || null,
      status: 'in_stock',
      dept_id: product.dept || '',
      location: product.warehouse || '待分配仓库'
    })
    created.push(mapBackendAsset(asset))
    localInventoryRecords.unshift(buildInventory(asset.asset_id, '入库', product.warehouse || '待分配仓库', '采购验收入库'))
  }
  return created
}

export async function getDashboardStats() {
  const { list } = await getAssets({})
  const inUse = list.filter(item => item.status === 'in_use').length
  const idle = list.filter(item => item.status === 'idle').length
  const risk = list.filter(item => !item.owner || !item.dept || ['idle', 'repair', 'pending_scrap', 'scrapped'].includes(item.status)).length
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
  return {
    asset_id: row.asset_id,
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
    purchase_date: formatDate(row.purchase_date),
    purchase_approval_no: row.purchase_approval_no || '',
    purchase_supplier_name: row.purchase_supplier_name || '',
    warranty_expire_date: formatDate(row.warranty_expire_date),
    warranty_months: row.warranty_months ?? '',
    brand: row.brand || '',
    model: row.model || '',
    spec: config.spec || '',
    location: row.location || '',
    sn: row.sn || '',
    warehouse: config.warehouse || row.location || '',
    created_at: formatDate(row.created_at)
  }
}

function groupBy(list, key, emptyLabel) {
  const map = {}
  list.forEach(item => {
    const name = item[key] || emptyLabel
    map[name] = (map[name] || 0) + 1
  })
  return Object.entries(map).map(([name, value]) => ({ name, value }))
}

function pushLifecycle(assetId, type, status, operator, description) {
  localLifecycles[assetId] ||= []
  localLifecycles[assetId].unshift({
    type,
    status,
    operator,
    time: new Date().toLocaleString('zh-CN', { hour12: false }),
    description
  })
}

function buildInventory(assetId, type, target, remark) {
  return {
    id: `IO-${Date.now()}`,
    asset_id: assetId,
    type,
    operator: '资产管理员',
    target,
    time: new Date().toLocaleString('zh-CN', { hour12: false }),
    remark
  }
}

function buildAssetRisks(asset) {
  if (!asset) return []
  const risks = []
  if (!asset.owner && asset.status === 'in_use') risks.push({ level: 'high', message: '在用资产未绑定责任人' })
  if (!asset.dept && asset.price >= 50000) risks.push({ level: 'high', message: '高价值资产未绑定部门' })
  if (asset.status === 'idle') risks.push({ level: 'medium', message: '资产处于闲置状态，建议调拨复用' })
  if (asset.status === 'repair') risks.push({ level: 'medium', message: '资产维修中，请关注维修周期' })
  if (asset.status === 'pending_scrap') risks.push({ level: 'medium', message: '资产处于待报废审批流程' })
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

function dateToApi(value) {
  if (!value) return null
  return `${value}T00:00:00`
}
