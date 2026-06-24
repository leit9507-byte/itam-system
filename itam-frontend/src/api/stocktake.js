import { getAssets, statusMap } from './asset'

const tasks = []

export function getStocktakeTasks(filters = {}) {
  refreshTaskStats()
  return Promise.resolve(filterTasks(tasks, filters.dateRange).map(task => cloneTask(task)))
}

export async function getStocktakeDashboard(filters = {}) {
  const visibleTasks = await getStocktakeTasks(filters)
  const allItems = visibleTasks.flatMap(task => task.items)
  const total = allItems.length
  const checked = allItems.filter(item => item.result !== '未盘').length
  const surplus = allItems.filter(item => item.result === '盘盈').length
  const loss = allItems.filter(item => item.result === '盘亏').length
  const mismatch = allItems.filter(item => ['位置不符', '状态不符'].includes(item.result)).length
  const abnormal = surplus + loss + mismatch

  return {
    metrics: [
      { label: '盘点任务', value: visibleTasks.length, tone: 'primary' },
      { label: '应盘资产', value: total, tone: 'primary' },
      { label: '已盘资产', value: checked, tone: 'success' },
      { label: '差异项', value: abnormal, tone: abnormal ? 'danger' : 'success' },
      { label: '盘盈数量', value: surplus, tone: 'warning' },
      { label: '盘亏数量', value: loss, tone: 'danger' }
    ],
    completionRate: total ? Math.round((checked / total) * 100) : 0,
    resultDistribution: [
      { name: '正常', value: allItems.filter(item => item.result === '正常').length },
      { name: '未盘', value: allItems.filter(item => item.result === '未盘').length },
      { name: '盘盈', value: surplus },
      { name: '盘亏', value: loss },
      { name: '位置不符', value: allItems.filter(item => item.result === '位置不符').length },
      { name: '状态不符', value: allItems.filter(item => item.result === '状态不符').length }
    ],
    taskTrend: buildTaskTrend(visibleTasks),
    scopeDistribution: groupTasks(visibleTasks, 'scope'),
    abnormalItems: allItems.filter(item => ['盘盈', '盘亏', '位置不符', '状态不符'].includes(item.result))
  }
}

export async function createStocktakeTask(payload) {
  const { list } = await getAssets({})
  const scopedAssets = list.filter(asset => {
    if (payload.scope === '部门') return !payload.target || asset.dept === payload.target || asset.dept_name === payload.target
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
      book_location: asset.location || asset.warehouse || '',
      book_status: statusMap[asset.status]?.label || asset.status,
      actual_location: '',
      result: '未盘',
      checker: '',
      checked_at: '',
      remark: ''
    }))
  }
  tasks.unshift(task)
  return Promise.resolve(cloneTask(task))
}

export function startStocktakeTask(taskId) {
  const task = findTask(taskId)
  if (!task) return Promise.reject(new Error('盘点任务不存在'))
  task.status = '进行中'
  return Promise.resolve(cloneTask(task))
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
  return Promise.resolve({ ...item })
}

export function finishStocktakeTask(taskId) {
  const task = findTask(taskId)
  if (!task) return Promise.reject(new Error('盘点任务不存在'))
  task.status = '已完成'
  refreshTaskStats()
  return Promise.resolve(cloneTask(task))
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

function filterTasks(rows, dateRange) {
  if (!dateRange?.length) return rows
  return rows.filter(task => inDateRange(task.created_at, dateRange))
}

function inDateRange(value, dateRange) {
  if (!value) return false
  const date = new Date(value)
  const start = new Date(dateRange[0])
  const end = new Date(dateRange[1])
  end.setHours(23, 59, 59, 999)
  return date >= start && date <= end
}

function buildTaskTrend(rows) {
  const now = new Date()
  return [5, 4, 3, 2, 1, 0].map(offset => {
    const target = new Date(now.getFullYear(), now.getMonth() - offset, 1)
    const monthRows = rows.filter(task => {
      const date = new Date(task.created_at)
      return date.getFullYear() === target.getFullYear() && date.getMonth() === target.getMonth()
    })
    return {
      month: `${target.getMonth() + 1}月`,
      tasks: monthRows.length,
      checked: monthRows.reduce((sum, item) => sum + Number(item.checked || 0), 0),
      abnormal: monthRows.reduce((sum, item) => sum + Number(item.abnormal || 0), 0)
    }
  })
}

function groupTasks(rows, key) {
  const map = {}
  rows.forEach(task => {
    const name = task[key] || '未设置'
    map[name] = (map[name] || 0) + 1
  })
  return Object.entries(map).map(([name, value]) => ({ name, value }))
}

function cloneTask(task) {
  return { ...task, items: task.items.map(item => ({ ...item })) }
}
