import request from '../utils/request'
import { getAssets } from './asset'

const REPAIR_DASHBOARD_LIMIT = 500
const REPAIR_ASSET_RATE_LIMIT = 2000

export async function createRepairRecord(asset, payload) {
  return mapRepair(
    await request.post('/repair/create', {
      asset_id: asset.asset_id,
      repair_time: `${payload.repair_time}T00:00:00`,
      repair_type: payload.repair_type || '普通维修',
      fault_reason: payload.fault_reason,
      repair_cost: Number(payload.repair_cost || 0),
      vendor: payload.vendor || '',
      operator: payload.operator || '资产管理员',
      remark: payload.remark || ''
    })
  )
}

export async function createRepairRecords(assets, payload) {
  return request.post('/asset/batch-repair', {
    asset_ids: assets.map(asset => asset.asset_id),
    repair_time: `${payload.repair_time}T00:00:00`,
    repair_type: payload.repair_type || '普通维修',
    fault_reason: payload.fault_reason,
    repair_cost: Number(payload.repair_cost || 0),
    vendor: payload.vendor || '',
    operator: payload.operator || '资产管理员',
    remark: payload.remark || ''
  })
}

export function getRepairFaultTypes() {
  return request.get('/repair/fault-types')
}

export function saveRepairFaultType(payload) {
  if (payload.id) return request.put(`/repair/fault-types/${payload.id}`, payload)
  return request.post('/repair/fault-types', payload)
}

export function deleteRepairFaultType(id) {
  return request.delete(`/repair/fault-types/${id}`)
}

export async function getRepairRecords(filters = {}) {
  const result = await request.get('/repair/list', {
    params: {
      keyword: filters.keyword || undefined,
      status: filters.status || undefined,
      start_date: filters.dateRange?.[0] || undefined,
      end_date: filters.dateRange?.[1] || undefined,
      sort_by: filters.sort_by || undefined,
      sort_order: filters.sort_order || undefined,
      page: filters.page || undefined,
      page_size: filters.page_size ?? filters.pageSize ?? undefined
    }
  })
  const { rows, total } = normalizePagedResult(result)
  return { list: rows.map(mapRepair), total }
}

export async function finishRepairRecord(recordId, payload = {}) {
  return mapRepair(
    await request.post(`/repair/${recordId}/finish`, {
      finish_time: payload.finish_time ? `${payload.finish_time}T00:00:00` : null,
      next_status: payload.next_status || 'in_stock',
      repair_result: payload.repair_result || '已修好',
      operator: payload.operator || '资产管理员',
      remark: payload.remark || ''
    })
  )
}

export async function getRepairDashboard(filters = {}) {
  const [{ list: rows }, { list: assets }] = await Promise.all([
    getRepairRecords({ ...filters, page: 1, page_size: REPAIR_DASHBOARD_LIMIT }),
    getAssets({ page: 1, page_size: REPAIR_ASSET_RATE_LIMIT }).catch(() => ({ list: [] }))
  ])
  const inProgress = rows.filter(item => item.status === '维修中')
  const completed = rows.filter(item => ['已完成', '未修好'].includes(item.status))
  const totalCost = rows.reduce((sum, item) => sum + Number(item.repair_cost || 0), 0)
  const brandFaultRates = buildBrandFaultRates(rows, assets)
  return {
    total: rows.length,
    inProgress: inProgress.length,
    completed: completed.length,
    totalCost,
    avgCost: rows.length ? Math.round(totalCost / rows.length) : 0,
    topFaults: groupCount(rows, 'fault_reason').slice(0, 10),
    topModels: groupCount(rows, 'asset_model').slice(0, 10),
    brandFaultRates,
    brandFaultPeak: buildBrandFaultPeak(brandFaultRates),
    ageTrend: buildAgeTrend(rows),
    ageTrendPeak: buildAgeTrendPeak(rows),
    costTrend: buildCostTrend(rows)
  }
}

function mapRepair(row) {
  const statusLabelMap = { approval_submitted: '维修中', rejected: '已驳回' }
  return {
    id: row.id,
    repair_no: row.repair_no,
    asset_id: row.asset_id,
    asset_name: row.asset_name || '',
    sn: row.sn || '',
    category: row.category || '',
    brand: row.brand || '',
    asset_model: row.asset_model || '',
    purchase_date: formatDate(row.purchase_date),
    owner: row.owner || '',
    dept: row.dept || '',
    repair_time: formatDate(row.repair_time),
    repair_type: row.repair_type || '普通维修',
    fault_reason: row.fault_reason,
    repair_cost: Number(row.repair_cost || 0),
    vendor: row.vendor || '',
    operator: row.operator || '',
    status: row.status,
    status_label: statusLabelMap[row.status] || row.status,
    repair_result: row.repair_result || '',
    fault_device_count: Number(row.fault_device_count || 1),
    finish_time: row.finish_time ? formatDate(row.finish_time) : '',
    created_at: formatDate(row.created_at),
    remark: row.remark || '',
    current_status: row.current_status || ''
  }
}

function filterRecord(item, filters) {
  const keyword = (filters.keyword || '').toLowerCase()
  const status = filters.status || ''
  const hitKeyword = !keyword || [item.repair_no, item.asset_id, item.asset_name, item.asset_model, item.sn, item.fault_reason, item.vendor].join(' ').toLowerCase().includes(keyword)
  const hitStatus = !status || item.status === status
  const hitDate = !filters.dateRange?.length || inDateRange(item.repair_time || item.created_at, filters.dateRange)
  return hitKeyword && hitStatus && hitDate
}

function groupCount(rows, key) {
  const map = {}
  rows.forEach(item => {
    const name = item[key] || '未填写'
    map[name] = (map[name] || 0) + 1
  })
  return Object.entries(map).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value)
}

function buildCostTrend(rows) {
  const now = new Date()
  return [5, 4, 3, 2, 1, 0].map(offset => {
    const target = new Date(now.getFullYear(), now.getMonth() - offset, 1)
    const monthRows = rows.filter(item => {
      const date = new Date(item.repair_time || item.created_at)
      return date.getFullYear() === target.getFullYear() && date.getMonth() === target.getMonth()
    })
    return {
      month: `${target.getMonth() + 1}月`,
      count: monthRows.length,
      cost: monthRows.reduce((sum, item) => sum + Number(item.repair_cost || 0), 0)
    }
  })
}

function buildAgeTrend(rows) {
  const buckets = [
    { key: '0-1', name: '0-1年', min: 0, max: 1 },
    { key: '1-2', name: '1-2年', min: 1, max: 2 },
    { key: '2-3', name: '2-3年', min: 2, max: 3 },
    { key: '3-4', name: '3-4年', min: 3, max: 4 },
    { key: '4-5', name: '4-5年', min: 4, max: 5 },
    { key: '5+', name: '5年以上', min: 5, max: Infinity },
    { key: 'unknown', name: '未知', min: null, max: null }
  ].map(item => ({ ...item, value: 0, cost: 0 }))
  rows.forEach(row => {
    const age = repairAssetAge(row)
    const bucket = age == null ? buckets[buckets.length - 1] : buckets.find(item => item.min != null && age >= item.min && age < item.max)
    if (!bucket) return
    bucket.value += 1
    bucket.cost += Number(row.repair_cost || 0)
  })
  return buckets.filter(item => item.value > 0 || item.key !== 'unknown').map(item => ({
    name: item.name,
    value: item.value,
    cost: item.cost,
    avg_cost: item.value ? Math.round(item.cost / item.value) : 0
  }))
}

function buildBrandFaultRates(rows, assets) {
  const managedAssets = assets.filter(item => !['scrapped', 'disposed'].includes(item.status))
  const byBrand = new Map()
  managedAssets.forEach(asset => {
    const brand = normalizeBrand(asset.brand)
    if (!byBrand.has(brand)) byBrand.set(brand, { brand, asset_count: 0, fault_asset_ids: new Set(), repair_count: 0, rate: 0 })
    byBrand.get(brand).asset_count += 1
  })
  const assetBrandMap = new Map(managedAssets.map(asset => [asset.asset_id, normalizeBrand(asset.brand)]))
  rows.forEach(row => {
    const brand = assetBrandMap.get(row.asset_id) || normalizeBrand(row.brand)
    if (!byBrand.has(brand)) byBrand.set(brand, { brand, asset_count: 0, fault_asset_ids: new Set(), repair_count: 0, rate: 0 })
    const item = byBrand.get(brand)
    if (row.asset_id) item.fault_asset_ids.add(row.asset_id)
    item.repair_count += 1
  })
  return [...byBrand.values()]
    .map(item => {
      const fault_asset_count = item.fault_asset_ids.size
      const rate = item.asset_count ? Math.round((fault_asset_count / item.asset_count) * 1000) / 10 : 0
      return { brand: item.brand, asset_count: item.asset_count, fault_asset_count, repair_count: item.repair_count, rate }
    })
    .filter(item => item.asset_count > 0 || item.repair_count > 0)
    .sort((a, b) => b.rate - a.rate || b.repair_count - a.repair_count)
    .slice(0, 10)
}

function buildBrandFaultPeak(rows) {
  if (!rows.length) return ''
  const peak = rows[0]
  return peak.rate ? `${peak.brand}故障率最高：${peak.rate}%` : ''
}

function normalizeBrand(value) {
  return String(value || '').trim() || '未填写'
}

function buildAgeTrendPeak(rows) {
  const trend = buildAgeTrend(rows).filter(item => item.name !== '未知')
  if (!trend.length) return ''
  const peak = trend.reduce((best, item) => (item.value > best.value ? item : best), trend[0])
  return peak.value ? `${peak.name}故障最多：${peak.value} 次` : ''
}

function repairAssetAge(row) {
  if (!row.purchase_date) return null
  const purchase = new Date(row.purchase_date)
  const repair = new Date(row.repair_time || row.created_at)
  if (Number.isNaN(purchase.getTime()) || Number.isNaN(repair.getTime()) || repair < purchase) return null
  return (repair.getTime() - purchase.getTime()) / (365.25 * 24 * 60 * 60 * 1000)
}

function inDateRange(value, dateRange) {
  if (!value) return false
  const date = new Date(value)
  const start = new Date(dateRange[0])
  const end = new Date(dateRange[1])
  end.setHours(23, 59, 59, 999)
  return date >= start && date <= end
}

function normalizePagedResult(result) {
  if (Array.isArray(result)) return { rows: result, total: result.length }
  const rows = result?.list || result?.items || []
  return { rows, total: Number(result?.total ?? rows.length) }
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toISOString().slice(0, 10)
}
