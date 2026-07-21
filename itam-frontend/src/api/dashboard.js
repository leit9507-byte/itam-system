import { getAssets, getAssetSummary, getLifecycleList, getScrapRequests } from './asset'
import { getPurchases } from './purchase'
import { getProducts } from './product'
import { getRepairDashboard } from './repair'
import { getUsers } from './user'
import request from '../utils/request'

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
  pending_scrap: '待处置登记',
  scrapped: '已报废',
  disposed: '已处置',
  lost: '已丢失'
}

export async function getEnterpriseDashboard(filters = {}) {
  const dateRange = filters.dateRange || []
  return request.get('/dashboard/enterprise', {
    params: {
      date_from: dateRange[0] || undefined,
      date_to: dateRange[1] || undefined
    }
  })
}

export async function legacyGetEnterpriseDashboard(filters = {}) {
  const [
    { list: allAssets },
    assetSummary,
    purchaseResult,
    products,
    repairDashboard,
    users,
    lifecycleResult,
    scrapResult
  ] = await Promise.all([
    getAssets({ page: 1, page_size: DASHBOARD_SOURCE_LIMIT }),
    getAssetSummary().catch(() => null),
    getPurchases({ page: 1, page_size: DASHBOARD_SOURCE_LIMIT }).catch(() => ({ list: [] })),
    getProducts().catch(() => []),
    getRepairDashboard(filters).catch(() => ({ total: 0, inProgress: 0, totalCost: 0, topFaults: [] })),
    getUsers().catch(() => []),
    getLifecycleList({ page: 1, page_size: 20 }).catch(() => ({ list: [] })),
    getScrapRequests({ page: 1, page_size: DASHBOARD_SOURCE_LIMIT }).catch(() => ({ list: [] }))
  ])
  const purchases = purchaseResult.list || []
  const scrapRequests = scrapResult.list || []

  const allManagedAssets = allAssets.filter(isManagedAsset)
  const scopedAssets = filterByDateRange(allManagedAssets, filters.dateRange, 'created_at')
  const assets = filters.dateRange?.length ? scopedAssets : allManagedAssets
  const summary = normalizeAssetSummary(assetSummary, allAssets)
  const useGlobalSummary = !filters.dateRange?.length
  const total = useGlobalSummary ? summary.managedTotal : assets.length
  const originalValue = useGlobalSummary ? summary.managedTotalValue : sumAssets(assets)
  const netValue = Math.round(originalValue * 0.68)
  const activeStatusCounts = useGlobalSummary ? summary.managedStatusCounts : {}
  const inUse = useGlobalSummary ? activeStatusCounts.in_use || 0 : countStatus(assets, 'in_use')
  const idle = useGlobalSummary ? activeStatusCounts.idle || 0 : countStatus(assets, 'idle')
  const repair = useGlobalSummary ? activeStatusCounts.repair || 0 : countStatus(assets, 'repair')
  const scrapped = useGlobalSummary ? summary.statusCounts.scrapped || 0 : countStatus(assets, 'scrapped')
  const lost = useGlobalSummary ? summary.statusCounts.lost || 0 : countStatus(assets, 'lost')
  const pendingScrap = useGlobalSummary
    ? (activeStatusCounts.ready_scrap || 0) + (activeStatusCounts.pending_scrap || 0)
    : countStatus(assets, 'ready_scrap') + countStatus(assets, 'pending_scrap')
  const thisMonthAssets = useGlobalSummary ? summary.currentMonthManagedCount : allManagedAssets.filter(item => isMonth(item.created_at, 0)).length
  const previousMonthAssets = useGlobalSummary ? summary.previousMonthManagedCount : allManagedAssets.filter(item => isMonth(item.created_at, 1)).length
  const previousTotalAssets = Math.max(total - thisMonthAssets, 0)
  const retirementSoonAssets = buildRetirementSoonAssets(assets, products)
  const allRetirementSoonAssets = buildRetirementSoonAssets(allManagedAssets, products)
  const retirementSoon = retirementSoonAssets.length

  return {
    metrics: [
      metric('在管资产', total, '项', '', compare(total, previousTotalAssets), monthTrendFromAssets(assets, 'count'), 'primary'),
      metric('资产原值', originalValue, '', '¥', compare(sumAssetsByMonth(allManagedAssets, 0), sumAssetsByMonth(allManagedAssets, 1)), monthTrendFromAssets(assets, 'value'), 'success'),
      metric('资产净值', netValue, '', '¥', '按原值估算', monthTrendFromAssets(assets, 'net'), 'warning'),
      metric('在用资产', inUse, '项', '', '实时', statusTrend(assets, 'in_use'), 'success'),
      metric('闲置资产', idle, '项', '', '实时', statusTrend(assets, 'idle'), 'warning'),
      metric('维修中资产', repair, '项', '', '实时', statusTrend(assets, 'repair'), 'danger'),
      metric('本月新增资产', thisMonthAssets, '项', '', compare(thisMonthAssets, previousMonthAssets), monthTrendFromAssets(allManagedAssets, 'count'), 'primary'),
      metric('即将过保资产', retirementSoon, '项', '', compare(retirementSoon, allRetirementSoonAssets.length), retirementTrend(assets, products), 'danger')
    ],
    categoryDistribution: useGlobalSummary ? buildCategoryDistributionFromCounts(summary.managedCategoryCounts) : buildCategoryDistribution(assets),
    departmentDistribution: buildDepartmentDistribution(assets),
    purchaseTrend: buildPurchaseTrend(purchases, filters.dateRange),
    scrapTrend: buildScrapTrend(scrapRequests, filters.dateRange),
    retirementTrend: buildRetirementDueTrend(allManagedAssets, products),
    lifecycleDistribution: buildLifecycleDistribution(assets, purchases, useGlobalSummary ? summary.statusCounts : null),
    retirementSoonAssets,
    maintenance: buildMaintenance(repairDashboard, assets),
    statusCounts: { in_use: inUse, idle, repair, scrapped, lost, pending_scrap: pendingScrap },
    personnelTrend: buildPersonnelTrend(users || []),
    recentRecords: buildRecentRecords(lifecycleResult.list || [], assets),
    warrantyRows: buildWarrantyRows(retirementSoonAssets)
  }
}

function metric(label, value, suffix, prefix, change, trend, tone) {
  return { label, value, suffix, prefix, change, trend, tone }
}

function countStatus(assets, status) {
  return assets.filter(item => item.status === status).length
}

function isManagedAsset(asset) {
  return !['scrapped', 'disposed', 'lost'].includes(asset.status)
}

function sumAssets(assets) {
  return assets.reduce((sum, item) => sum + Number(item.price || 0), 0)
}

function sumAssetsByMonth(assets, offset) {
  return sumAssets(assets.filter(item => isMonth(item.created_at, offset)))
}

function normalizeAssetSummary(summary, fallbackAssets) {
  const fallbackManagedAssets = fallbackAssets.filter(isManagedAsset)
  const fallbackManagedStatusCounts = fallbackManagedAssets.reduce((map, asset) => {
    const status = asset.status || 'unknown'
    map[status] = (map[status] || 0) + 1
    return map
  }, {})
  return {
    total: Number(summary?.total ?? fallbackAssets.length),
    totalValue: Number(summary?.total_value ?? sumAssets(fallbackAssets)),
    managedTotal: Number(summary?.managed_total ?? fallbackManagedAssets.length),
    managedTotalValue: Number(summary?.managed_total_value ?? sumAssets(fallbackManagedAssets)),
    statusCounts: summary?.status_counts || {},
    managedStatusCounts: summary?.managed_status_counts || fallbackManagedStatusCounts,
    categoryCounts: summary?.category_counts || {},
    managedCategoryCounts: summary?.managed_category_counts || buildRawCategoryCounts(fallbackManagedAssets),
    currentMonthCount: Number(summary?.current_month_count ?? fallbackAssets.filter(item => isMonth(item.created_at, 0)).length),
    previousMonthCount: Number(summary?.previous_month_count ?? fallbackAssets.filter(item => isMonth(item.created_at, 1)).length),
    currentMonthManagedCount: Number(summary?.current_month_managed_count ?? fallbackManagedAssets.filter(item => isMonth(item.created_at, 0)).length),
    previousMonthManagedCount: Number(summary?.previous_month_managed_count ?? fallbackManagedAssets.filter(item => isMonth(item.created_at, 1)).length)
  }
}

function buildRawCategoryCounts(assets) {
  return assets.reduce((map, asset) => {
    const category = asset.category || '其他'
    map[category] = (map[category] || 0) + 1
    return map
  }, {})
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
      if (!retirementDate || ['scrapped', 'disposed', 'lost'].includes(asset.status)) return null
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
  const months = lastMonths(12)
  return {
    months: months.map(item => item.label),
    amount: months.map(month => {
      const rows = purchases.filter(item => inMonth(item.created_at, month) && (!dateRange?.length || inDateRange(item.created_at, dateRange)))
      return rows.reduce((sum, item) => sum + Number(item.total_amount || 0), 0)
    }),
    quantity: months.map(month => {
      const rows = purchases.filter(item => inMonth(item.created_at, month) && (!dateRange?.length || inDateRange(item.created_at, dateRange)))
      return rows.reduce((sum, item) => sum + Number(item.quantity || item.items?.length || 0), 0)
    })
  }
}

function buildScrapTrend(scraps, dateRange) {
  const months = lastMonths(12)
  return {
    months: months.map(item => item.label),
    submitted: months.map(month => scraps.filter(item => inMonth(item.created_at, month) && (!dateRange?.length || inDateRange(item.created_at, dateRange))).length),
    approved: months.map(month => scraps.filter(item => item.status === '已通过' && inMonth(item.approved_at || item.updated_at || item.created_at, month) && (!dateRange?.length || inDateRange(item.approved_at || item.updated_at || item.created_at, dateRange))).length)
  }
}

function buildRetirementDueTrend(assets, products) {
  const months = nextMonths(6)
  const retirementAssets = assets
    .map(asset => {
      const retirementDate = resolveRetirementDate(asset, products) || resolveWarrantyExpireDate(asset)
      return retirementDate && !['scrapped', 'disposed', 'lost'].includes(asset.status) ? { asset, retirementDate } : null
    })
    .filter(Boolean)
  return {
    months: months.map(item => item.label),
    due: months.map(month => retirementAssets.filter(item => inMonth(item.retirementDate, month)).length),
    overdue: retirementAssets.filter(item => item.retirementDate < startOfToday()).length
  }
}

function legacyBuildPurchaseTrend(purchases, dateRange) {
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
    { name: lifecycleNames.scrapped, value: count('scrapped') },
    { name: lifecycleNames.disposed, value: count('disposed') },
    { name: lifecycleNames.lost, value: count('lost') }
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
      const action = item.to_status === 'in_stock' ? '归还' : '借用'
      return {
        asset_id: item.asset_id || '',
        user: item.responsible_label && item.responsible_label !== '-' ? item.responsible_label : item.operator || asset.owner_name || '-',
        asset: asset.name || item.asset_name || item.asset_id || '-',
        type: asset.category || '-',
        time: shortDate(item.time_value || item.time),
        action
      }
    })
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

function buildPersonnelTrend(users) {
  const months = lastMonths(6)
  const businessUsers = users.filter(isBusinessUser)
  const onboarding = months.map(month => countByMonth(businessUsers, 'created_at', month))
  const offboarding = months.map(month => businessUsers.filter(isInactiveUser).filter(user => inMonth(user.last_synced_at || user.created_at, month)).length)
  return {
    months: months.map(item => item.label),
    onboarding,
    offboarding,
    activeTotal: businessUsers.filter(user => !isInactiveUser(user)).length,
    inactiveTotal: businessUsers.filter(isInactiveUser).length,
    onboardingTotal: onboarding.reduce((sum, value) => sum + value, 0),
    offboardingTotal: offboarding.reduce((sum, value) => sum + value, 0)
  }
}

function lastMonths(size) {
  const now = new Date()
  return Array.from({ length: size }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth() - (size - 1 - index), 1)
    return {
      year: date.getFullYear(),
      month: date.getMonth(),
      label: `${date.getMonth() + 1}月`
    }
  })
}

function nextMonths(size) {
  const now = new Date()
  return Array.from({ length: size }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth() + index, 1)
    return {
      year: date.getFullYear(),
      month: date.getMonth(),
      label: `${date.getMonth() + 1}月`
    }
  })
}

function startOfToday() {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

function countByMonth(rows, key, month) {
  return rows.filter(item => inMonth(item[key], month)).length
}

function inMonth(value, month) {
  if (!value) return false
  const date = new Date(value)
  return !Number.isNaN(date.getTime()) && date.getFullYear() === month.year && date.getMonth() === month.month
}

function isBusinessUser(user) {
  return !['admin', 'auditor'].includes(user.role) && !['admin', 'auditor'].includes(String(user.username || '').toLowerCase())
}

function isInactiveUser(user) {
  return ['inactive', 'disabled', 'locked', 'resigned', 'left', 'offboarded', '离职', '停用', '禁用'].includes(String(user.status || '').toLowerCase())
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
