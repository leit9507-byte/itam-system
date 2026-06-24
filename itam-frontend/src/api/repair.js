import { changeAssetStatus, getAssets } from './asset'

const repairRecords = []

export async function createRepairRecord(asset, payload) {
  const record = {
    id: `RP-${new Date().getFullYear()}-${String(repairRecords.length + 1).padStart(4, '0')}`,
    asset_id: asset.asset_id,
    asset_name: asset.name,
    sn: asset.sn,
    category: asset.category,
    owner: asset.owner || '',
    dept: asset.dept || '',
    repair_time: payload.repair_time,
    fault_reason: payload.fault_reason,
    repair_cost: Number(payload.repair_cost || 0),
    vendor: payload.vendor || '',
    operator: payload.operator || '资产管理员',
    status: '维修中',
    created_at: new Date().toISOString().slice(0, 10),
    remark: payload.remark || ''
  }
  repairRecords.unshift(record)
  await changeAssetStatus(asset.asset_id, 'repair', {
    action: '新增维修',
    operator: record.operator,
    remark: `故障原因：${record.fault_reason}；维修费用：${record.repair_cost}`
  })
  return record
}

export async function getRepairRecords(filters = {}) {
  const { list: assets } = await getAssets({})
  const hydrated = repairRecords.map(record => {
    const asset = assets.find(item => item.asset_id === record.asset_id)
    return {
      ...record,
      asset_name: asset?.name || record.asset_name,
      current_status: asset?.status || '',
      owner: asset?.owner || record.owner,
      dept: asset?.dept || record.dept
    }
  })
  return filterRecords(hydrated, filters)
}

export async function finishRepairRecord(recordId, payload = {}) {
  const record = repairRecords.find(item => item.id === recordId)
  if (!record) throw new Error('维修记录不存在')
  record.status = '已完成'
  record.finish_time = payload.finish_time || new Date().toISOString().slice(0, 10)
  record.remark = payload.remark || record.remark
  await changeAssetStatus(record.asset_id, payload.next_status || 'in_stock', {
    action: '维修完成',
    operator: payload.operator || '资产管理员',
    remark: payload.remark || '维修完成，资产恢复可用'
  })
  return record
}

export async function getRepairDashboard(filters = {}) {
  const rows = await getRepairRecords(filters)
  const inProgress = rows.filter(item => item.status === '维修中')
  const completed = rows.filter(item => item.status === '已完成')
  const totalCost = rows.reduce((sum, item) => sum + Number(item.repair_cost || 0), 0)
  return {
    total: rows.length,
    inProgress: inProgress.length,
    completed: completed.length,
    totalCost,
    avgCost: rows.length ? Math.round(totalCost / rows.length) : 0,
    topFaults: groupCount(rows, 'fault_reason').slice(0, 10),
    costTrend: buildCostTrend(rows)
  }
}

function filterRecords(rows, filters) {
  const keyword = (filters.keyword || '').toLowerCase()
  const status = filters.status || ''
  return rows.filter(item => {
    const hitKeyword = !keyword || [item.id, item.asset_id, item.asset_name, item.sn, item.fault_reason, item.vendor].join(' ').toLowerCase().includes(keyword)
    const hitStatus = !status || item.status === status
    const hitDate = !filters.dateRange?.length || inDateRange(item.repair_time || item.created_at, filters.dateRange)
    return hitKeyword && hitStatus && hitDate
  })
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
