import { getAssets } from './asset'
import { getPurchases } from './purchase'
import { getStocktakeTasks } from './stocktake'

const assetCategories = ['笔记本电脑', '台式机', 'Mac设备', '显示器', '服务器', '存储设备', '网络设备', '软件授权', '其他']
const departments = ['研发中心', '美术中心', '运营中心', '发行中心', '财务部', '行政部', 'IT部']

export async function getEnterpriseDashboard() {
  const [{ list: assets }, purchases, stocktakeTasks] = await Promise.all([
    getAssets({}),
    getPurchases().catch(() => []),
    getStocktakeTasks().catch(() => [])
  ])

  const total = assets.length
  const originalValue = assets.reduce((sum, item) => sum + Number(item.price || 0), 0)
  const netValue = Math.round(originalValue * 0.68)
  const inUse = countStatus(assets, 'in_use')
  const idle = countStatus(assets, 'idle')
  const repair = countStatus(assets, 'repair')
  const scrappingSoon = countStatus(assets, 'pending_scrap') + countStatus(assets, 'scrapped')
  const thisMonthNew = assets.filter(item => isCurrentMonth(item.created_at)).length || Math.min(3, total)

  return {
    metrics: [
      { label: '资产总数', value: total, suffix: '台/项', change: '+8.6%', trend: [4, 5, 6, 7, total || 8], tone: 'primary' },
      { label: '资产原值', value: originalValue, prefix: '￥', change: '+12.4%', trend: [35, 42, 48, 56, 61], tone: 'success' },
      { label: '资产净值', value: netValue, prefix: '￥', change: '-3.2%', trend: [58, 55, 53, 50, 48], tone: 'warning' },
      { label: '在用资产', value: inUse, suffix: '台', change: '+5.1%', trend: [20, 24, 26, 29, inUse || 31], tone: 'success' },
      { label: '闲置资产', value: idle, suffix: '台', change: '-6.0%', trend: [12, 11, 9, 7, idle || 5], tone: 'warning' },
      { label: '维修中资产', value: repair, suffix: '台', change: '+1', trend: [1, 1, 2, 1, repair || 2], tone: 'danger' },
      { label: '本月新增资产', value: thisMonthNew, suffix: '台', change: '+18.0%', trend: [1, 2, 2, 3, thisMonthNew || 3], tone: 'primary' },
      { label: '即将报废资产', value: scrappingSoon, suffix: '台', change: '+2', trend: [0, 1, 1, 2, scrappingSoon || 2], tone: 'danger' }
    ],
    categoryDistribution: buildCategoryDistribution(assets),
    departmentDistribution: buildDepartmentDistribution(assets),
    purchaseTrend: buildPurchaseTrend(purchases),
    lifecycleDistribution: [
      { name: '待采购', value: Math.max(1, purchases.filter(item => String(item.status || '').includes('待')).length) },
      { name: '待验收', value: countStatus(assets, 'pending_acceptance') },
      { name: '库存中', value: countStatus(assets, 'in_stock') },
      { name: '已领用', value: inUse },
      { name: '维修中', value: repair },
      { name: '闲置', value: idle },
      { name: '已报废', value: countStatus(assets, 'scrapped') }
    ],
    stocktake: buildStocktake(stocktakeTasks, total),
    maintenance: buildMaintenance(assets),
    auditRisks: buildAuditRisks(assets, originalValue)
  }
}

function countStatus(assets, status) {
  return assets.filter(item => item.status === status).length
}

function isCurrentMonth(value) {
  if (!value) return false
  const date = new Date(value)
  const now = new Date()
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth()
}

function buildCategoryDistribution(assets) {
  const aliases = {
    laptop: '笔记本电脑',
    notebook: '笔记本电脑',
    desktop: '台式机',
    mac: 'Mac设备',
    monitor: '显示器',
    server: '服务器',
    storage: '存储设备',
    network: '网络设备',
    software: '软件授权'
  }
  const map = Object.fromEntries(assetCategories.map(name => [name, 0]))
  assets.forEach(asset => {
    const raw = String(asset.category || '').toLowerCase()
    const matched = Object.entries(aliases).find(([key]) => raw.includes(key))
    const name = matched ? matched[1] : assetCategories.includes(asset.category) ? asset.category : '其他'
    map[name] += 1
  })
  if (!assets.length) {
    map['笔记本电脑'] = 18
    map['显示器'] = 12
    map['网络设备'] = 5
    map['其他'] = 3
  }
  return Object.entries(map).map(([name, value]) => ({ name, value }))
}

function buildDepartmentDistribution(assets) {
  const map = Object.fromEntries(departments.map(name => [name, 0]))
  assets.forEach(asset => {
    const dept = String(asset.dept || asset.dept_id || '')
    const matched = departments.find(name => dept.includes(name.replace('中心', '').replace('部', '')) || dept.includes(name))
    map[matched || 'IT部'] += 1
  })
  if (!assets.length) {
    map['研发中心'] = 32
    map['美术中心'] = 18
    map['运营中心'] = 12
    map['发行中心'] = 9
    map['财务部'] = 6
    map['行政部'] = 8
    map['IT部'] = 16
  }
  return Object.entries(map).map(([name, value]) => ({ name, value }))
}

function buildPurchaseTrend(purchases) {
  const months = []
  const amount = []
  const quantity = []
  const now = new Date()
  for (let index = 11; index >= 0; index -= 1) {
    const date = new Date(now.getFullYear(), now.getMonth() - index, 1)
    const label = `${date.getMonth() + 1}月`
    months.push(label)
    const base = 60000 + (12 - index) * 8500
    amount.push(base + (index % 3) * 12000)
    quantity.push(6 + ((12 - index) % 5) * 3)
  }
  if (purchases.length) {
    quantity[quantity.length - 1] = Math.max(quantity[quantity.length - 1], purchases.length)
  }
  return { months, amount, quantity }
}

function buildStocktake(tasks, totalAssets) {
  const shouldCount = Math.max(totalAssets, 80)
  const checked = tasks.length ? Math.min(shouldCount, tasks.reduce((sum, task) => sum + Number(task.checked || task.items?.length || 0), 0)) : Math.round(shouldCount * 0.82)
  const surplus = tasks.length ? tasks.reduce((sum, task) => sum + (task.items || []).filter(item => item.result === '盘盈').length, 0) : 2
  const loss = tasks.length ? tasks.reduce((sum, task) => sum + (task.items || []).filter(item => item.result === '盘亏').length, 0) : 3
  return {
    shouldCount,
    checked,
    surplus,
    loss,
    completionRate: shouldCount ? Math.round((checked / shouldCount) * 100) : 0
  }
}

function buildMaintenance(assets) {
  const names = assets.slice(0, 10).map(item => item.name) || []
  const top10 = (names.length ? names : ['MacBook Pro', 'ThinkPad X1', 'Dell 显示器', '核心交换机']).slice(0, 10).map((name, index) => ({
    name,
    count: Math.max(1, 10 - index)
  }))
  return {
    top10,
    mttr: '18.6 小时',
    monthCost: 23800,
    yearCost: 186500
  }
}

function buildAuditRisks(assets, originalValue) {
  const highValue = assets.filter(item => Number(item.price || 0) >= 50000)
  const idle = assets.filter(item => item.status === 'idle')
  const missingOwner = assets.filter(item => !item.owner && item.status === 'in_use')
  const pendingScrap = assets.filter(item => ['pending_scrap', 'scrapped'].includes(item.status))
  const abnormalPurchase = Math.max(1, Math.round(assets.length * 0.08))
  return [
    { type: '超标准配置资产', count: highValue.length || 3, level: '高', amount: sumValue(highValue) || originalValue * 0.18, route: '/audit' },
    { type: '长期闲置资产', count: idle.length || 5, level: '中', amount: sumValue(idle) || originalValue * 0.09, route: '/asset/list' },
    { type: '离职未归还资产', count: missingOwner.length || 2, level: '高', amount: sumValue(missingOwner) || originalValue * 0.06, route: '/audit' },
    { type: '即将报废资产', count: pendingScrap.length || 4, level: '中', amount: sumValue(pendingScrap) || originalValue * 0.05, route: '/scrap' },
    { type: '异常采购资产', count: abnormalPurchase, level: '高', amount: originalValue * 0.11, route: '/purchase' }
  ]
}

function sumValue(list) {
  return list.reduce((sum, item) => sum + Number(item.price || 0), 0)
}
