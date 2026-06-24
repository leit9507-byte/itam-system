import { getAssets } from './asset'
import { getPurchases } from './purchase'
import { getRepairDashboard } from './repair'

const categoryNames = ['笔记本电脑', '台式机', 'Mac设备', '显示器', '服务器', '存储设备', '网络设备', '软件授权', '其他']
const lifecycleNames = {
  pending_purchase: '待采购',
  pending_acceptance: '待验收',
  in_stock: '库存中',
  in_use: '已领用',
  repair: '维修中',
  idle: '闲置',
  scrapped: '已报废'
}

export async function getEnterpriseDashboard(filters = {}) {
  const [{ list: allAssets }, purchases, repairDashboard] = await Promise.all([
    getAssets({}),
    getPurchases().catch(() => []),
    getRepairDashboard(filters).catch(() => ({ total: 0, inProgress: 0, totalCost: 0, topFaults: [] }))
  ])

  const scopedAssets = filterByDateRange(allAssets, filters.dateRange, 'created_at')
  const assets = filters.dateRange?.length ? scopedAssets : allAssets
  const total = assets.length
  const originalValue = sumAssets(assets)
  const netValue = Math.round(originalValue * 0.68)
  const inUse = countStatus(assets, 'in_use')
  const idle = countStatus(assets, 'idle')
  const repair = countStatus(assets, 'repair')
  const thisMonthAssets = allAssets.filter(item => isMonth(item.created_at, 0)).length
  const previousMonthAssets = allAssets.filter(item => isMonth(item.created_at, 1)).length
  const scrappingSoon = countStatus(assets, 'pending_scrap')

  return {
    metrics: [
      metric('资产总数', total, '项', '', compare(total, Math.max(0, total - thisMonthAssets)), monthTrendFromAssets(assets, 'count'), 'primary'),
      metric('资产原值', originalValue, '', '¥', compare(sumAssetsByMonth(allAssets, 0), sumAssetsByMonth(allAssets, 1)), monthTrendFromAssets(assets, 'value'), 'success'),
      metric('资产净值', netValue, '', '¥', '按原值估算', monthTrendFromAssets(assets, 'net'), 'warning'),
      metric('在用资产', inUse, '项', '', compare(inUse, countStatus(allAssets, 'in_use')), statusTrend(assets, 'in_use'), 'success'),
      metric('闲置资产', idle, '项', '', compare(idle, countStatus(allAssets, 'idle')), statusTrend(assets, 'idle'), 'warning'),
      metric('维修中资产', repair, '项', '', compare(repair, countStatus(allAssets, 'repair')), statusTrend(assets, 'repair'), 'danger'),
      metric('本月新增资产', thisMonthAssets, '项', '', compare(thisMonthAssets, previousMonthAssets), monthTrendFromAssets(allAssets, 'count'), 'primary'),
      metric('即将报废资产', scrappingSoon, '项', '', compare(scrappingSoon, countStatus(allAssets, 'pending_scrap')), statusTrend(assets, 'pending_scrap'), 'danger')
    ],
    categoryDistribution: buildCategoryDistribution(assets),
    departmentDistribution: buildDepartmentDistribution(assets),
    purchaseTrend: buildPurchaseTrend(purchases, filters.dateRange),
    lifecycleDistribution: buildLifecycleDistribution(assets, purchases),
    maintenance: buildMaintenance(repairDashboard, assets)
  }
}

function metric(label, value, suffix, prefix, change, trend, tone) {
  return { label, value, suffix, prefix, change, trend, tone }
}

function countStatus(assets, status) {
  return assets.filter(item => item.status === status).length
}

function sumAssets(assets) {
  return assets.reduce((sum, item) => sum + Number(item.price || 0), 0)
}

function sumAssetsByMonth(assets, offset) {
  return sumAssets(assets.filter(item => isMonth(item.created_at, offset)))
}

function isMonth(value, offset) {
  if (!value) return false
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  const now = new Date()
  const target = new Date(now.getFullYear(), now.getMonth() - offset, 1)
  return date.getFullYear() === target.getFullYear() && date.getMonth() === target.getMonth()
}

function compare(current, previous) {
  if (!previous && !current) return '无变化'
  if (!previous) return current ? '新增' : '无变化'
  const rate = Math.round(((current - previous) / previous) * 100)
  return `${rate >= 0 ? '+' : ''}${rate}%`
}

function monthTrendFromAssets(assets, mode) {
  const now = new Date()
  return [4, 3, 2, 1, 0].map(offset => {
    const target = new Date(now.getFullYear(), now.getMonth() - offset, 1)
    const rows = assets.filter(item => {
      if (!item.created_at) return false
      const date = new Date(item.created_at)
      return date.getFullYear() === target.getFullYear() && date.getMonth() === target.getMonth()
    })
    if (mode === 'value') return sumAssets(rows)
    if (mode === 'net') return Math.round(sumAssets(rows) * 0.68)
    return rows.length
  })
}

function statusTrend(assets, status) {
  const current = countStatus(assets, status)
  return [0, 0, 0, 0, current]
}

function buildCategoryDistribution(assets) {
  const map = Object.fromEntries(categoryNames.map(name => [name, 0]))
  assets.forEach(asset => {
    const name = normalizeCategory(asset.category)
    map[name] = (map[name] || 0) + 1
  })
  return Object.entries(map).map(([name, value]) => ({ name, value }))
}

function normalizeCategory(category = '') {
  const raw = String(category).toLowerCase()
  if (raw.includes('laptop') || raw.includes('notebook') || raw.includes('笔记本')) return '笔记本电脑'
  if (raw.includes('desktop') || raw.includes('台式')) return '台式机'
  if (raw.includes('mac')) return 'Mac设备'
  if (raw.includes('monitor') || raw.includes('display') || raw.includes('显示')) return '显示器'
  if (raw.includes('server') || raw.includes('服务器')) return '服务器'
  if (raw.includes('storage') || raw.includes('存储')) return '存储设备'
  if (raw.includes('network') || raw.includes('交换') || raw.includes('网络')) return '网络设备'
  if (raw.includes('software') || raw.includes('license') || raw.includes('授权')) return '软件授权'
  return categoryNames.includes(category) ? category : '其他'
}

function buildDepartmentDistribution(assets) {
  const map = {}
  assets.forEach(asset => {
    const name = normalizeDepartment(asset.dept || asset.dept_id || asset.location)
    map[name] = (map[name] || 0) + 1
  })
  return Object.entries(map)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value || a.name.localeCompare(b.name, 'zh-CN'))
}

function normalizeDepartment(value = '') {
  const raw = String(value || '').trim()
  if (!raw) return '未绑定'
  const lower = raw.toLowerCase()
  if (['it', 'it部', 'it department'].includes(lower)) return 'IT部'
  if (lower.includes('研发') || lower.includes('rd') || lower.includes('r&d')) return '研发中心'
  if (lower.includes('美术') || lower.includes('art')) return '美术中心'
  if (lower.includes('运营') || lower.includes('operation')) return '运营中心'
  if (lower.includes('发行') || lower.includes('publish')) return '发行中心'
  if (lower.includes('财务') || lower.includes('finance')) return '财务部'
  if (lower.includes('行政') || lower.includes('admin')) return '行政部'
  return raw
}

function buildPurchaseTrend(purchases, dateRange) {
  const now = new Date()
  const months = []
  const amount = []
  const quantity = []
  for (let offset = 11; offset >= 0; offset -= 1) {
    const target = new Date(now.getFullYear(), now.getMonth() - offset, 1)
    months.push(`${target.getMonth() + 1}月`)
    const rows = purchases.filter(item => {
      if (!item.created_at) return offset === 0 && (!dateRange?.length || true)
      const date = new Date(item.created_at)
      return date.getFullYear() === target.getFullYear() && date.getMonth() === target.getMonth() && (!dateRange?.length || inDateRange(item.created_at, dateRange))
    })
    amount.push(rows.reduce((sum, item) => sum + Number(item.total_amount || 0), 0))
    quantity.push(rows.reduce((sum, item) => sum + Number(item.quantity || item.items?.length || 0), 0))
  }
  return { months, amount, quantity }
}

function buildLifecycleDistribution(assets, purchases) {
  return [
    { name: lifecycleNames.pending_purchase, value: purchases.filter(item => item.status === 'created').length },
    { name: lifecycleNames.pending_acceptance, value: countStatus(assets, 'pending_acceptance') + purchases.filter(item => item.status === 'pending_acceptance').length },
    { name: lifecycleNames.in_stock, value: countStatus(assets, 'in_stock') },
    { name: lifecycleNames.in_use, value: countStatus(assets, 'in_use') },
    { name: lifecycleNames.repair, value: countStatus(assets, 'repair') },
    { name: lifecycleNames.idle, value: countStatus(assets, 'idle') },
    { name: lifecycleNames.scrapped, value: countStatus(assets, 'scrapped') }
  ]
}

function buildMaintenance(repairDashboard, assets) {
  const repairAssets = assets.filter(item => item.status === 'repair')
  return {
    top10: repairDashboard.topFaults?.length
      ? repairDashboard.topFaults.map(item => ({ name: item.name, count: item.value || item.count || 0 }))
      : repairAssets.slice(0, 10).map(item => ({ name: item.name, count: 1 })),
    mttr: repairDashboard.total ? '待完工统计' : '0小时',
    monthCost: repairDashboard.totalCost || 0,
    yearCost: repairDashboard.totalCost || 0
  }
}

function filterByDateRange(rows, dateRange, key) {
  if (!dateRange?.length) return rows
  return rows.filter(item => inDateRange(item[key], dateRange))
}

function inDateRange(value, dateRange) {
  if (!value || !dateRange?.length) return false
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  const start = new Date(dateRange[0])
  const end = new Date(dateRange[1])
  end.setHours(23, 59, 59, 999)
  return date >= start && date <= end
}
