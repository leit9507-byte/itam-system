import { getAssets, getScrapRequests, statusMap } from './asset'
import { getPurchases } from './purchase'
import { getStocktakeTasks } from './stocktake'

export async function getDashboardOverview() {
  const [{ list: assets }, purchases, stocktakeTasks, scrapRequests] = await Promise.all([
    getAssets({}),
    getPurchases().catch(() => []),
    getStocktakeTasks().catch(() => []),
    getScrapRequests().catch(() => [])
  ])

  const totalValue = assets.reduce((sum, item) => sum + Number(item.price || 0), 0)
  const inUse = countBy(assets, 'status', 'in_use')
  const idle = countBy(assets, 'status', 'idle')
  const inStock = countBy(assets, 'status', 'in_stock')
  const riskAssets = assets.filter(item => !item.owner || !item.dept || ['idle', 'repair', 'pending_scrap', 'scrapped'].includes(item.status))
  const pendingAcceptance = purchases.filter(item => ['待验收', '已到货'].includes(item.status)).length
  const pendingScrap = scrapRequests.filter(item => item.status === '审批中').length + countBy(assets, 'status', 'pending_scrap')
  const stocktakeAbnormal = stocktakeTasks.reduce((sum, item) => sum + Number(item.abnormal || 0), 0)

  return {
    metrics: [
      { label: '资产总数', value: assets.length, trend: `${assets.length ? '后端同步' : '暂无数据'}`, type: 'primary' },
      { label: '资产总值', value: totalValue, prefix: '¥', trend: '按后端资产计算', type: 'success' },
      { label: '在用资产', value: inUse, trend: `利用率 ${percent(inUse, assets.length)}%`, type: 'success' },
      { label: '风险资产', value: riskAssets.length, trend: `闲置 ${idle}`, type: 'danger' },
      { label: '待验收', value: pendingAcceptance, trend: '采购到货待验', type: 'warning' },
      { label: '待报废审批', value: pendingScrap, trend: '流程待处理', type: 'warning' },
      { label: '盘点差异', value: stocktakeAbnormal, trend: '来自盘点任务', type: 'danger' },
      { label: '库存资产', value: inStock, trend: '可调拨资产', type: 'primary' }
    ],
    utilization: [62, 66, 71, 69, 74, 78, percent(inUse, assets.length)],
    deptDistribution: groupBy(assets, 'dept', '未绑定'),
    statusDistribution: groupByStatus(assets),
    monthlyFlow: {
      months: ['1月', '2月', '3月', '4月', '5月', '6月'],
      inbound: [12, 9, 16, 8, 18, inStock],
      outbound: [8, 11, 12, 10, 13, inUse],
      scrap: [1, 0, 2, 1, 1, countBy(assets, 'status', 'scrapped')]
    },
    todos: [
      { title: '采购设备待验收', count: pendingAcceptance, route: '/purchase', level: 'warning' },
      { title: '报废流程待审批', count: pendingScrap, route: '/scrap', level: 'danger' },
      { title: '盘点任务待确认', count: stocktakeTasks.filter(item => item.status === '待确认').length, route: '/stocktake', level: 'warning' },
      { title: '风险资产待处理', count: riskAssets.length, route: '/audit', level: 'danger' }
    ],
    riskAssets: riskAssets.slice(0, 5).map(item => ({
      asset_id: item.asset_id,
      name: item.name,
      risk: riskReason(item),
      level: item.price >= 50000 || !item.dept ? 'high' : 'medium',
      owner: item.owner || '未分配'
    })),
    recentActivities: [
      { time: '实时', type: '后端', text: `已从 FastAPI 同步 ${assets.length} 条资产数据` },
      { time: '实时', type: '采购', text: `当前采购单 ${purchases.length} 条` },
      { time: '实时', type: '盘点', text: `盘点任务 ${stocktakeTasks.length} 个，差异 ${stocktakeAbnormal} 项` },
      { time: '实时', type: '报废', text: `待报废/待审批 ${pendingScrap} 项` }
    ],
    stocktakeSummary: [
      { label: '正常', value: sumStocktake(stocktakeTasks, '正常') },
      { label: '盘亏', value: sumStocktake(stocktakeTasks, '盘亏') },
      { label: '盘盈', value: sumStocktake(stocktakeTasks, '盘盈') },
      { label: '位置不符', value: sumStocktake(stocktakeTasks, '位置不符') }
    ]
  }
}

function countBy(list, key, value) {
  return list.filter(item => item[key] === value).length
}

function percent(value, total) {
  return total ? Math.round((value / total) * 100) : 0
}

function groupBy(list, key, emptyLabel) {
  const map = {}
  list.forEach(item => {
    const name = item[key] || emptyLabel
    map[name] = (map[name] || 0) + 1
  })
  return Object.entries(map).map(([name, value]) => ({ name, value }))
}

function groupByStatus(list) {
  const map = {}
  list.forEach(item => {
    const name = statusMap[item.status]?.label || item.status
    map[name] = (map[name] || 0) + 1
  })
  return Object.entries(map).map(([name, value]) => ({ name, value }))
}

function sumStocktake(tasks, result) {
  return tasks.reduce((sum, task) => sum + task.items.filter(item => item.result === result).length, 0)
}

function riskReason(asset) {
  if (!asset.dept && asset.price >= 50000) return '高价值资产未绑定部门'
  if (!asset.owner && asset.status === 'in_use') return '在用资产未绑定责任人'
  if (asset.status === 'idle') return '闲置资产待调拨'
  if (asset.status === 'repair') return '维修资产待跟进'
  if (asset.status === 'pending_scrap') return '待报废审批'
  return '基础信息待完善'
}
