import request from '../utils/request'

const RESULT_UNCHECKED = '未盘'
const ABNORMAL_RESULTS = ['盘盈', '盘亏', '位置不符', '状态不符']

export async function getStocktakeTasks(filters = {}) {
  const tasks = await request.get('/stocktake/tasks')
  return filterTasks(tasks, filters.dateRange).map(task => cloneTask(task))
}

export async function getStocktakeDashboard(filters = {}) {
  const visibleTasks = await getStocktakeTasks(filters)
  const allItems = visibleTasks.flatMap(task => task.items)
  const total = allItems.length
  const checked = allItems.filter(item => item.result !== RESULT_UNCHECKED).length
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
      { name: '未盘', value: allItems.filter(item => item.result === RESULT_UNCHECKED).length },
      { name: '盘盈', value: surplus },
      { name: '盘亏', value: loss },
      { name: '位置不符', value: allItems.filter(item => item.result === '位置不符').length },
      { name: '状态不符', value: allItems.filter(item => item.result === '状态不符').length }
    ],
    taskTrend: buildTaskTrend(visibleTasks),
    scopeDistribution: groupTasks(visibleTasks, 'scope'),
    abnormalItems: allItems.filter(item => ABNORMAL_RESULTS.includes(item.result))
  }
}

export function createStocktakeTask(payload) {
  return request.post('/stocktake/tasks', payload)
}

export function startStocktakeTask(taskId) {
  return request.post(`/stocktake/tasks/${taskId}/start`)
}

export function submitStocktakeItem(taskId, assetId, payload) {
  return request.post(`/stocktake/tasks/${taskId}/items/${assetId}`, payload)
}

export function finishStocktakeTask(taskId) {
  return request.post(`/stocktake/tasks/${taskId}/finish`)
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
  return { ...task, items: (task.items || []).map(item => ({ ...item })) }
}
