import { getAssets } from './asset'
import { getPurchases } from './purchase'

const categoryNames = ['笔记本电脑', '台式机', 'Mac设备', '显示器', '服务器', '存储设备', '网络设备', '软件授权', '其他']
const departmentNames = ['研发中心', '美术中心', '运营中心', '发行中心', '财务部', '行政部', 'IT部']

export async function getEnterpriseDashboard() {
  const [{ list: assets }, purchases] = await Promise.all([
    getAssets({}),
    getPurchases().catch(() => [])
  ])

  const total = assets.length
  const originalValue = sumAssets(assets)
  const netValue = Math.round(originalValue * 0.68)
  const inUse = countStatus(assets, 'in_use')
  const idle = countStatus(assets, 'idle')
  const repair = countStatus(assets, 'repair')
  const thisMonthAssets = assets.filter(item => isMonth(item.created_at, 0)).length
  const previousMonthAssets = assets.filter(item => isMonth(item.created_at, 1)).length
  const scrappingSoon = countStatus(assets, 'pending_scrap')

  return {
    metrics: [
      metric('资产总数', total, '台/项', '', compare(total, Math.max(0, total - thisMonthAssets)), monthTrendFromAssets(assets, 'count'), 'primary'),
      metric('资产原值', originalValue, '', '￥', compare(sumAssetsByMonth(assets, 0), sumAssetsByMonth(assets, 1)), monthTrendFromAssets(assets, 'value'), 'success'),
      metric('资产净值', netValue, '', '￥', '按原值折算', monthTrendFromAssets(assets, 'net'), 'warning'),
      metric('在用资产', inUse, '台', '', compare(inUse, countStatus(assets, 'in_use', 1)), statusTrend(assets, 'in_use'), 'success'),
      metric('闲置资产', idle, '台', '', compare(idle, countStatus(assets, 'idle', 1)), statusTrend(assets, 'idle'), 'warning'),
      metric('维修中资产', repair, '台', '', compare(repair, countStatus(assets, 'repair', 1)), statusTrend(assets, 'repair'), 'danger'),
      metric('本月新增资产', thisMonthAssets, '台', '', compare(thisMonthAssets, previousMonthAssets), monthTrendFromAssets(assets, 'count'), 'primary'),
      metric('即将报废资产', scrappingSoon, '台', '', compare(scrappingSoon, countStatus(assets, 'pending_scrap', 1)), statusTrend(assets, 'pending_scrap'), 'danger')
    ],
    categoryDistribution: buildCategoryDistribution(assets),
    departmentDistribution: buildDepartmentDistribution(assets),
    purchaseTrend: buildPurchaseTrend(purchases),
    lifecycleDistribution: [
      { name: '待采购', value: purchases.filter(item => item.status === 'created').length },
      { name: '待验收', value: countStatus(assets, 'pending_acceptance') + purchases.filter(item => item.status === 'pending_acceptance').length },
      { name: '库存中', value: countStatus(assets, 'in_stock') },
      { name: '已领用', value: inUse },
      { name: '维修中', value: repair },
      { name: '闲置', value: idle },
      { name: '已报废', value: countStatus(assets, 'scrapped') }
    ],
    stocktake: {
      shouldCount: total,
      checked: 0,
      surplus: 0,
      loss: 0,
      completionRate: 0
    },
    maintenance: buildMaintenance(assets)
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
    map[name] += 1
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
  const map = Object.fromEntries(departmentNames.map(name => [name, 0]))
  assets.forEach(asset => {
    const dept = String(asset.dept || asset.dept_id || 'IT部')
    const matched = departmentNames.find(name => dept.includes(name) || dept.includes(name.replace('中心', '').replace('部', '')))
    map[matched || 'IT部'] += 1
  })
  return Object.entries(map).map(([name, value]) => ({ name, value }))
}

function buildPurchaseTrend(purchases) {
  const now = new Date()
  const months = []
  const amount = []
  const quantity = []
  for (let offset = 11; offset >= 0; offset -= 1) {
    const target = new Date(now.getFullYear(), now.getMonth() - offset, 1)
    months.push(`${target.getMonth() + 1}月`)
    const rows = offset === 0 ? purchases : []
    amount.push(rows.reduce((sum, item) => sum + Number(item.total_amount || 0), 0))
    quantity.push(rows.reduce((sum, item) => sum + Number(item.quantity || 0), 0))
  }
  return { months, amount, quantity }
}

function buildMaintenance(assets) {
  const repairAssets = assets.filter(item => item.status === 'repair')
  return {
    top10: repairAssets.slice(0, 10).map(item => ({ name: item.name, count: 1 })),
    mttr: repairAssets.length ? '待维修记录计算' : '0小时',
    monthCost: 0,
    yearCost: 0
  }
}
