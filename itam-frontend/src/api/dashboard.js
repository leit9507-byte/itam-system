import { getAssets, getAssetSummary, getLifecycleList } from './asset'
import { getPurchases } from './purchase'
import { getProducts } from './product'
import { getRepairDashboard } from './repair'
import { getStocktakeDashboard, getStocktakeTasks } from './stocktake'
import { getTodoItems } from './todo'

const DASHBOARD_SOURCE_LIMIT = 1000
const categoryNames = ['笔记本电脑', '台式机', 'Mac设备', '显示器', '服务器', '存储设备', '网络设备', '软件授权', '其他']
const lifecycleNames = {
  pending_purchase: '待采购',
  pending_acceptance: '待验收',
  in_stock: '库存中',
  in_use: '已领用',
  repair: '维修中',
  idle: '闲置',
  ready_scrap: '待报废',
  pending_scrap: '已提交报废审批',
  scrapped: '已报废'
}

export async function getEnterpriseDashboard(filters = {}) {
  const [
    { list: allAssets },
    assetSummary,
    purchaseResult,
    products,
    repairDashboard,
    stocktakeDashboard,
    stocktakeTasks,
    todoItems,
    lifecycleResult
  ] = await Promise.all([
    getAssets({ page: 1, page_size: DASHBOARD_SOURCE_LIMIT }),
    getAssetSummary().catch(() => null),
    getPurchases({ page: 1, page_size: DASHBOARD_SOURCE_LIMIT }).catch(() => ({ list: [] })),
    getProducts().catch(() => []),
    getRepairDashboard(filters).catch(() => ({ total: 0, inProgress: 0, totalCost: 0, topFaults: [] })),
    getStocktakeDashboard(filters).catch(() => ({ completionRate: 0, metrics: [], abnormalItems: [] })),
    getStocktakeTasks(filters).catch(() => []),
    getTodoItems().catch(() => []),
    getLifecycleList({ page: 1, page_size: 20 }).catch(() => ({ list: [] }))
  ])
  const purchases = purchaseResult.list || []

  const scopedAssets = filterByDateRange(allAssets, filters.dateRange, 'created_at')
  const assets = filters.dateRange?.length ? scopedAssets : allAssets
  const summary = normalizeAssetSummary(assetSummary, allAssets)
  const useGlobalSummary = !filters.dateRange?.length
  const total = useGlobalSummary ? summary.total : assets.length
  const originalValue = useGlobalSummary ? summary.totalValue : sumAssets(assets)
  const netValue = Math.round(originalValue * 0.68)
  const inUse = useGlobalSummary ? summary.statusCounts.in_use || 0 : countStatus(assets, 'in_use')
  const idle = useGlobalSummary ? summary.statusCounts.idle || 0 : countStatus(assets, 'idle')
  const repair = useGlobalSummary ? summary.statusCounts.repair || 0 : countStatus(assets, 'repair')
  const scrapped = useGlobalSummary ? summary.statusCounts.scrapped || 0 : countStatus(assets, 'scrapped')
  const pendingScrap = useGlobalSummary
    ? (summary.statusCounts.ready_scrap || 0) + (summary.statusCounts.pending_scrap || 0)
    : countStatus(assets, 'ready_scrap') + countStatus(assets, 'pending_scrap')
  const thisMonthAssets = useGlobalSummary ? summary.currentMonthCount : allAssets.filter(item => isMonth(item.created_at, 0)).length
  const previousMonthAssets = useGlobalSummary ? summary.previousMonthCount : allAssets.filter(item => isMonth(item.created_at, 1)).length
  const previousTotalAssets = Math.max(total - thisMonthAssets, 0)
  const retirementSoonAssets = buildRetirementSoonAssets(assets, products)
  const allRetirementSoonAssets = buildRetirementSoonAssets(allAssets, products)
  const retirementSoon = retirementSoonAssets.length

  return {
    metrics: [
      metric('资产总数', total, '项', '', compare(total, previousTotalAssets), monthTrendFromAssets(assets, 'count'), 'primary'),
      metric('资产原值', originalValue, '', '¥', compare(sumAssetsByMonth(allAssets, 0), sumAssetsByMonth(allAssets, 1)), monthTrendFromAssets(assets, 'value'), 'success'),
      metric('资产净值', netValue, '', '¥', '按原值估算', monthTrendFromAssets(assets, 'net'), 'warning'),
      metric('在用资产', inUse, '项', '', compare(inUse, countStatus(allAssets, 'in_use')), statusTrend(assets, 'in_use'), 'success'),
      metric('闲置资产', idle, '项', '', compare(idle, countStatus(allAssets, 'idle')), statusTrend(assets, 'idle'), 'warning'),
      metric('维修中资产', repair, '项', '', compare(repair, countStatus(allAssets, 'repair')), statusTrend(assets, 'repair'), 'danger'),
      metric('本月新增资产', thisMonthAssets, '项', '', compare(thisMonthAssets, previousMonthAssets), monthTrendFromAssets(allAssets, 'count'), 'primary'),
      metric('即将过保资产', retirementSoon, '项', '', compare(retirementSoon, allRetirementSoonAssets.length), retirementTrend(assets, products), 'danger')
    ],
    categoryDistribution: useGlobalSummary ? buildCategoryDistributionFromCounts(summary.categoryCounts) : buildCategoryDistribution(assets),
    departmentDistribution: buildDepartmentDistribution(assets),
    purchaseTrend: buildPurchaseTrend(purchases, filters.dateRange),
    lifecycleDistribution: buildLifecycleDistribution(assets, purchases, useGlobalSummary ? summary.statusCounts : null),
    retirementSoonAssets,
    maintenance: buildMaintenance(repairDashboard, assets),
    statusCounts: { in_use: inUse, idle, repair, scrapped, pending_scrap: pendingScrap },
    todoItems,
    recentRecords: buildRecentRecords(lifecycleResult.list || [], assets),
    stocktakeProgress: buildStocktakeProgress(stocktakeDashboard, stocktakeTasks),
    nextStocktakeDate: buildNextStocktakeDate(stocktakeTasks),
    operationLogs: buildOperationLogs(lifecycleResult.list || []),
    warrantyRows: buildWarrantyRows(retirementSoonAssets)
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

function normalizeAssetSummary(summary, fallbackAssets) {
  return {
    total: Number(summary?.total ?? fallbackAssets.length),
    totalValue: Number(summary?.total_value ?? sumAssets(fallbackAssets)),
    statusCounts: summary?.status_counts || {},
    categoryCounts: summary?.category_counts || {},
    currentMonthCount: Number(summary?.current_month_count ?? fallbackAssets.filter(item => isMonth(item.created_at, 0)).length),
    previousMonthCount: Number(summary?.previous_month_count ?? fallbackAssets.filter(item => isMonth(item.created_at, 1)).length)
  }
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

function retirementTrend(assets, products) {
  const now = new Date()
  return [4, 3, 2, 1, 0].map(offset => {
    const target = new Date(now.getFullYear(), now.getMonth() - offset, 1)
    return buildRetirementSoonAssets(assets, products).filter(item => {
      const date = new Date(item.retirement_date)
      return date.getFullYear() === target.getFullYear() && date.getMonth() === target.getMonth()
    }).length
  })
}

function buildRetirementSoonAssets(assets, products) {
  const now = new Date()
  const deadline = new Date(now)
  deadline.setDate(deadline.getDate() + 180)
  return assets
    .map(asset => {
      const expireDate = resolveWarrantyExpireDate(asset)
      const retirementDate = expireDate || resolveRetirementDate(asset, products)
      if (!retirementDate || ['scrapped'].includes(asset.status)) return null
      const days = Math.ceil((retirementDate.getTime() - now.getTime()) / 86400000)
      if (days > 180) return null
      return {
        asset_id: asset.asset_id,
        name: asset.name,
        brand: asset.brand,
        model: asset.model,
        retirement_date: retirementDate.toISOString().slice(0, 10),
        days_remaining: days,
        overdue: days < 0
      }
    })
    .filter(Boolean)
    .sort((a, b) => a.days_remaining - b.days_remaining)
}

function resolveWarrantyExpireDate(asset) {
  if (!asset.warranty_expire_date) return null
  const date = new Date(asset.warranty_expire_date)
  return Number.isNaN(date.getTime()) ? null : date
}

function resolveRetirementDate(asset, products) {
  const years = resolveRetirementYears(asset, products)
  if (!years || !asset.purchase_date) return null
  return addYears(asset.purchase_date, years)
}

function resolveRetirementYears(asset, products) {
  const configYears = Number(asset.retirement_years || asset.config?.retirement_years || 0)
  if (configYears > 0) return configYears
  const product = products.find(item => productMatchesAsset(item, asset))
  return Number(product?.retirement_years || 0)
}

function productMatchesAsset(product, asset) {
  const sameName = normalizeText(product.product_name) === normalizeText(asset.name)
  const sameModel = normalizeText(product.model) === normalizeText(asset.model)
  const sameBrand = !product.brand || !asset.brand || normalizeText(product.brand) === normalizeText(asset.brand)
  return sameName && sameModel && sameBrand
}

function normalizeText(value) {
  return String(value || '').trim().toLowerCase()
}

function addYears(value, years) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  date.setFullYear(date.getFullYear() + Number(years))
  return date
}

function buildCategoryDistribution(assets) {
  const map = Object.fromEntries(categoryNames.map(name => [name, 0]))
  assets.forEach(asset => {
    const name = normalizeCategory(asset.category)
    map[name] = (map[name] || 0) + 1
  })
  return Object.entries(map).map(([name, value]) => ({ name, value }))
}

function buildCategoryDistributionFromCounts(counts = {}) {
  const map = Object.fromEntries(categoryNames.map(name => [name, 0]))
  Object.entries(counts).forEach(([category, value]) => {
    const name = normalizeCategory(category)
    map[name] = (map[name] || 0) + Number(value || 0)
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
    const name = normalizeDepartment(asset.dept_name || asset.dept || asset.dept_id || asset.location)
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

function buildLifecycleDistribution(assets, purchases, statusCounts = null) {
  const count = status => statusCounts ? Number(statusCounts[status] || 0) : countStatus(assets, status)
  return [
    { name: lifecycleNames.pending_purchase, value: purchases.filter(item => item.status === 'created').length },
    { name: lifecycleNames.pending_acceptance, value: count('pending_acceptance') + purchases.filter(item => item.status === 'pending_acceptance').length },
    { name: lifecycleNames.in_stock, value: count('in_stock') },
    { name: lifecycleNames.in_use, value: count('in_use') },
    { name: lifecycleNames.repair, value: count('repair') },
    { name: lifecycleNames.idle, value: count('idle') },
    { name: lifecycleNames.ready_scrap, value: count('ready_scrap') },
    { name: lifecycleNames.pending_scrap, value: count('pending_scrap') },
    { name: lifecycleNames.scrapped, value: count('scrapped') }
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

function buildRecentRecords(lifecycles, assets) {
  const assetMap = Object.fromEntries(assets.map(asset => [asset.asset_id, asset]))
  return lifecycles
    .filter(item => item.category === 'daily_inventory' || ['in_stock', 'in_use', 'borrowed', 'out_stock'].includes(item.to_status))
    .slice(0, 6)
    .map(item => {
      const asset = assetMap[item.asset_id] || {}
      const action = item.to_status === 'in_stock' ? '归还' : '领用'
      return {
        user: item.responsible_label && item.responsible_label !== '-' ? item.responsible_label : item.operator || asset.owner_name || '-',
        asset: asset.name || item.asset_name || item.asset_id || '-',
        type: asset.category || '-',
        time: shortDate(item.time_value || item.time),
        action
      }
    })
}

function buildStocktakeProgress(stocktakeDashboard, tasks) {
  const total = Number(stocktakeDashboard.metrics?.find(item => item.label === '盘点任务')?.value || tasks.length || 0)
  const done = tasks.filter(item => ['已完成', 'finished', 'completed'].includes(item.status)).length
  const doing = tasks.filter(item => ['进行中', 'running', 'in_progress'].includes(item.status)).length
  const pending = Math.max(total - done - doing, 0)
  return {
    total,
    done,
    doing,
    pending,
    rate: Number(stocktakeDashboard.completionRate || (total ? Math.round((done / total) * 100) : 0))
  }
}

function buildNextStocktakeDate(tasks) {
  const candidates = tasks
    .map(item => item.plan_date || item.start_date || item.created_at)
    .map(value => new Date(value))
    .filter(date => !Number.isNaN(date.getTime()) && date >= new Date())
    .sort((a, b) => a - b)
  if (candidates.length) return candidates[0].toISOString().slice(0, 10)
  const date = new Date()
  date.setMonth(date.getMonth() + 1)
  date.setDate(1)
  return date.toISOString().slice(0, 10)
}

function buildOperationLogs(lifecycles) {
  return lifecycles.slice(0, 6).map(item => ({
    text: `${item.operator || '系统'} ${item.type_label || item.type || '更新'} ${item.asset_id || ''}`.trim(),
    time: formatLogTime(item.time_value || item.time)
  }))
}

function buildWarrantyRows(retirementSoonAssets) {
  return retirementSoonAssets.slice(0, 6).map(item => ({
    name: item.name,
    type: '硬件维保',
    date: item.retirement_date,
    days: Math.max(Number(item.days_remaining || 0), 0),
    status: item.overdue ? '已过保' : item.days_remaining <= 30 ? '即将到期' : '正常'
  }))
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

function shortDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10)
  return date.toISOString().slice(0, 10)
}

function formatLogTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  const now = new Date()
  const sameDay = date.toDateString() === now.toDateString()
  if (sameDay) return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
  return date.toISOString().slice(0, 10)
}
