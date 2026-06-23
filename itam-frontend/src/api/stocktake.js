import { getAssets, statusMap } from './asset'

const tasks = [
  {
    id: 'ST-2026-001',
    name: '2026年6月上海IT库盘点',
    scope: '仓库',
    target: '上海 IT 库',
    owner: '资产管理员',
    status: '进行中',
    created_at: '2026-06-22',
    total: 2,
    checked: 1,
    abnormal: 1,
    items: [
      {
        asset_id: 'A001',
        name: 'MacBook Pro 14',
        sn: 'SN-A001',
        book_location: '上海总部 12F',
        book_status: '在用',
        actual_location: '上海总部 12F',
        result: '正常',
        checker: '资产管理员',
        checked_at: '2026-06-22 10:20',
        remark: ''
      },
      {
        asset_id: 'A003',
        name: 'Dell U2723QE',
        sn: 'SN-A003',
        book_location: '上海总部 8F',
        book_status: '借出',
        actual_location: '',
        result: '未盘',
        checker: '',
        checked_at: '',
        remark: ''
      }
    ]
  }
]

export function getStocktakeTasks() {
  refreshTaskStats()
  return Promise.resolve([...tasks])
}

export async function createStocktakeTask(payload) {
  const { list } = await getAssets({})
  const scopedAssets = list.filter(asset => {
    if (payload.scope === '部门') return !payload.target || asset.dept === payload.target
    if (payload.scope === '仓库') return !payload.target || asset.warehouse === payload.target
    if (payload.scope === '状态') return !payload.target || asset.status === payload.target
    return true
  })

  const task = {
    id: `ST-${new Date().getFullYear()}-${String(tasks.length + 1).padStart(3, '0')}`,
    name: payload.name,
    scope: payload.scope,
    target: payload.target,
    owner: payload.owner || '资产管理员',
    status: '待开始',
    created_at: new Date().toISOString().slice(0, 10),
    total: scopedAssets.length,
    checked: 0,
    abnormal: 0,
    items: scopedAssets.map(asset => ({
      asset_id: asset.asset_id,
      name: asset.name,
      sn: asset.sn,
      book_location: asset.location,
      book_status: statusMap[asset.status]?.label || asset.status,
      actual_location: '',
      result: '未盘',
      checker: '',
      checked_at: '',
      remark: ''
    }))
  }
  tasks.unshift(task)
  return Promise.resolve(task)
}

export function startStocktakeTask(taskId) {
  const task = findTask(taskId)
  if (!task) return Promise.reject(new Error('盘点任务不存在'))
  task.status = '进行中'
  return Promise.resolve(task)
}

export function submitStocktakeItem(taskId, assetId, payload) {
  const task = findTask(taskId)
  if (!task) return Promise.reject(new Error('盘点任务不存在'))
  const item = task.items.find(row => row.asset_id === assetId)
  if (!item) return Promise.reject(new Error('盘点明细不存在'))
  item.actual_location = payload.actual_location
  item.result = payload.result
  item.checker = payload.checker || task.owner
  item.checked_at = new Date().toLocaleString('zh-CN', { hour12: false })
  item.remark = payload.remark || ''
  refreshTaskStats()
  return Promise.resolve(item)
}

export function finishStocktakeTask(taskId) {
  const task = findTask(taskId)
  if (!task) return Promise.reject(new Error('盘点任务不存在'))
  task.status = '已完成'
  refreshTaskStats()
  return Promise.resolve(task)
}

function findTask(taskId) {
  return tasks.find(task => task.id === taskId)
}

function refreshTaskStats() {
  tasks.forEach(task => {
    task.total = task.items.length
    task.checked = task.items.filter(item => item.result !== '未盘').length
    task.abnormal = task.items.filter(item => ['盘亏', '盘盈', '位置不符', '状态不符'].includes(item.result)).length
    if (task.status !== '已完成' && task.total > 0 && task.checked === task.total) {
      task.status = '待确认'
    }
  })
}
