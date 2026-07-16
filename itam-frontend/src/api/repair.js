import request from '../utils/request'

const REPAIR_DASHBOARD_LIMIT = 500

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
  const rows = []
  for (const asset of assets) {
    rows.push(await createRepairRecord(asset, payload))
  }
  return rows
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
  const { list: rows } = await getRepairRecords({ ...filters, page: 1, page_size: REPAIR_DASHBOARD_LIMIT })
  const inProgress = rows.filter(item => item.status === '维修中')
  const completed = rows.filter(item => ['已完成', '未修好'].includes(item.status))
  const totalCost = rows.reduce((sum, item) => sum + Number(item.repair_cost || 0), 0)
  return {
    total: rows.length,
    inProgress: inProgress.length,
    completed: completed.length,
    totalCost,
    avgCost: rows.length ? Math.round(totalCost / rows.length) : 0,
    topFaults: groupCount(rows, 'fault_reason').slice(0, 10),
    topModels: groupCount(rows, 'asset_model').slice(0, 10),
    costTrend: buildCostTrend(rows)
  }
}

function mapRepair(row) {
  const statusLabelMap = { approval_submitted: '已提交飞书审批', rejected: '已驳回' }
  return {
    id: row.id,
    repair_no: row.repair_no,
    asset_id: row.asset_id,
    asset_name: row.asset_name || '',
    sn: row.sn || '',
    category: row.category || '',
    asset_model: row.asset_model || '',
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
