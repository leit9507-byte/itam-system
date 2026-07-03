<template>
  <div class="stocktake-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产盘点</h2>
        <p class="page-subtitle">按时间范围查看盘点仪表盘，创建任务并登记实盘结果</p>
      </div>
      <div class="toolbar">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          clearable
          @change="load"
        />
        <el-button type="primary" @click="openCreate">创建盘点任务</el-button>
      </div>
    </div>

    <el-card shadow="never" class="task-picker-card">
      <div class="task-picker">
        <div>
          <span class="muted">当前盘点任务</span>
          <strong>{{ selectedTask?.name || '请选择盘点任务' }}</strong>
          <p>{{ selectedTask ? `${selectedTask.id} / ${selectedTask.status} / ${selectedTask.checked || 0}/${selectedTask.total || 0}` : '选择任务后，下方仪表盘、图表和差异明细会刷新为该任务数据。' }}</p>
        </div>
        <div class="task-picker-actions">
          <el-select v-model="selectedTaskId" filterable placeholder="选择盘点任务" style="width: 340px" @change="selectTask">
            <el-option v-for="task in tasks" :key="task.id" :label="taskOptionLabel(task)" :value="task.id" />
          </el-select>
          <el-button :disabled="!selectedTask" @click="openDetail(selectedTask)">进入盘点</el-button>
          <el-button type="success" :disabled="!selectedTask || !['待确认', '进行中'].includes(selectedTask.status)" @click="finish(selectedTask)">完成</el-button>
        </div>
      </div>
    </el-card>

    <section class="stocktake-dashboard">
      <el-card shadow="never" class="completion-card">
        <div class="completion-body">
          <el-progress type="dashboard" :percentage="dashboard.completionRate" :width="154" />
          <div>
            <span class="muted">盘点完成率</span>
            <strong>{{ dashboard.completionRate }}%</strong>
            <p>{{ selectedTask ? '基于当前选中盘点任务的明细统计。' : '请先选择一次盘点任务。' }}</p>
          </div>
        </div>
      </el-card>
      <el-card v-for="item in dashboard.metrics" :key="item.label" shadow="never" class="metric-card">
        <span>{{ item.label }}</span>
        <strong>{{ formatValue(item.value) }}</strong>
        <el-tag :type="tagType(item.tone)" effect="light">当前范围</el-tag>
      </el-card>
    </section>

    <section class="chart-grid">
      <el-card shadow="never">
        <template #header>盘点结果分布</template>
        <div ref="resultRef" class="chart" />
      </el-card>
      <el-card shadow="never">
        <template #header>近 6 个月盘点趋势</template>
        <div ref="trendRef" class="chart" />
      </el-card>
    </section>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
        <span>盘点任务列表</span>
          <el-tag type="info">{{ tasks.length }} 个任务</el-tag>
        </div>
      </template>
      <el-table v-loading="loading" :data="pagedTasks" border stripe empty-text="当前时间范围暂无盘点任务" highlight-current-row :current-row-key="selectedTaskId" row-key="id" @current-change="handleCurrentTaskChange">
        <el-table-column prop="id" label="任务编号" width="140" />
        <el-table-column prop="name" label="任务名称" min-width="220" />
        <el-table-column prop="scope" label="范围类型" width="100" />
        <el-table-column prop="target" label="盘点范围" width="150" />
        <el-table-column prop="owner" label="负责人" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="taskStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="180">
          <template #default="{ row }">
            <el-progress :percentage="progress(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="abnormal" label="差异" width="80" />
        <el-table-column prop="created_at" label="创建日期" width="120" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :disabled="row.status !== '待开始'" @click="start(row)">开始</el-button>
            <el-button type="primary" link @click="openDetail(row)">盘点</el-button>
            <el-button type="success" link :disabled="!['待确认', '进行中'].includes(row.status)" @click="finish(row)">完成</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="taskPagination.page"
          v-model:page-size="taskPagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="tasks.length"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>差异明细</template>
      <el-table :data="pagedAbnormalItems" border stripe empty-text="当前任务暂无盘点差异">
        <el-table-column prop="asset_id" label="资产ID" width="120" />
        <el-table-column prop="name" label="资产名称" min-width="180" />
        <el-table-column prop="sn" label="序列号" width="150" />
        <el-table-column prop="book_location" label="账面位置" width="160" />
        <el-table-column prop="actual_location" label="实盘位置" width="160" />
        <el-table-column prop="result" label="结果" width="110" />
        <el-table-column prop="remark" label="备注" min-width="180" />
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="abnormalPagination.page"
          v-model:page-size="abnormalPagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="dashboard.abnormalItems.length"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </el-card>

    <el-dialog v-model="createDialog" title="创建盘点任务" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="范围类型">
          <el-select v-model="form.scope" style="width: 100%">
            <el-option label="全部资产" value="全部" />
            <el-option label="按部门" value="部门" />
            <el-option label="按仓库" value="仓库" />
            <el-option label="按状态" value="状态" />
          </el-select>
        </el-form-item>
        <el-form-item label="盘点范围">
          <el-input v-model="form.target" placeholder="如：研发部、上海 IT 仓、in_stock；全部资产可留空" />
        </el-form-item>
        <el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" @click="createTask">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialog" :title="currentTask ? `盘点明细：${currentTask.name}` : '盘点明细'" width="1180px">
      <div class="detail-toolbar">
        <el-input v-model="itemFilters.keyword" clearable placeholder="搜索资产编号/名称/序列号/位置" style="width: 280px" />
        <el-select v-model="itemFilters.result" clearable placeholder="盘点结果" style="width: 140px">
          <el-option label="未盘" value="未盘" />
          <el-option label="正常" value="正常" />
          <el-option label="盘盈" value="盘盈" />
          <el-option label="盘亏" value="盘亏" />
          <el-option label="位置不符" value="位置不符" />
          <el-option label="状态不符" value="状态不符" />
        </el-select>
        <el-button @click="resetItemFilters">重置</el-button>
      </div>
      <div class="quick-register">
        <el-input v-model="quickForm.code" clearable autofocus placeholder="扫码或输入资产编号 / 序列号后回车确认" @keyup.enter="registerQuickItem" />
        <el-button type="primary" :loading="savingItem" @click="registerQuickItem">扫码确认</el-button>
        <span class="scan-tip">扫描确认后，系统按账面位置登记实盘位置；未扫描项目在完成盘点时自动记为盘亏。</span>
      </div>
      <el-table :data="pagedTaskItems" border stripe row-key="asset_id">
        <el-table-column prop="asset_id" label="资产ID" width="120" />
        <el-table-column prop="name" label="资产名称" min-width="160" />
        <el-table-column prop="sn" label="序列号" width="140" />
        <el-table-column prop="book_location" label="账面位置" width="160" />
        <el-table-column prop="book_status" label="账面状态" width="100" />
        <el-table-column prop="actual_location" label="实盘位置" width="160">
          <template #default="{ row }">
            {{ row.actual_location || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="result" label="结果" width="130">
          <template #default="{ row }">
            <el-tag :type="itemResultType(row.result)">{{ row.result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="review_status" label="复核状态" width="120">
          <template #default="{ row }">
            <el-tag :type="reviewStatusType(row.review_status)">{{ row.review_status || '无需复核' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="170">
          <template #default="{ row }">
            {{ row.remark || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="异常处理" width="210" fixed="right">
          <template #default="{ row }">
            <el-button link type="warning" :disabled="row.result === '正常'" @click="reportLocationException(row)">上报</el-button>
            <el-button link type="success" :disabled="row.review_status !== '待复核'" @click="reviewItem(row, '已确认')">确认</el-button>
            <el-button link type="danger" :disabled="row.review_status !== '待复核'" @click="reviewItem(row, '已驳回')">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="itemPagination.page"
          v-model:page-size="itemPagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredTaskItems.length"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import {
  createStocktakeTask,
  buildStocktakeDashboard,
  finishStocktakeTask,
  getStocktakeTasks,
  reportStocktakeException,
  reviewStocktakeItem,
  startStocktakeTask,
  submitStocktakeItem
} from '../../api/stocktake'
import { assetCodeMatches, parseAssetCode } from '../../utils/assetCode'

const tasks = ref([])
const loading = ref(false)
const savingAssetId = ref('')
const createDialog = ref(false)
const detailDialog = ref(false)
const currentTask = ref(null)
const selectedTaskId = ref('')
const dateRange = ref(defaultDateRange())
const resultRef = ref(null)
const trendRef = ref(null)
const charts = []
const form = reactive(defaultForm())
const taskPagination = reactive({ page: 1, pageSize: 20 })
const abnormalPagination = reactive({ page: 1, pageSize: 20 })
const itemPagination = reactive({ page: 1, pageSize: 20 })
const itemFilters = reactive({ keyword: '', result: '' })
const quickForm = reactive({ code: '' })
const dashboard = reactive({
  metrics: [],
  completionRate: 0,
  resultDistribution: [],
  taskTrend: [],
  scopeDistribution: [],
  abnormalItems: []
})
const currentTaskItems = computed(() => currentTask.value?.items || [])
const selectedTask = computed(() => tasks.value.find(task => task.id === selectedTaskId.value) || null)
const dashboardTasks = computed(() => selectedTask.value ? [selectedTask.value] : [])
const savingItem = computed(() => Boolean(savingAssetId.value))
const pagedTasks = computed(() => paginate(tasks.value, taskPagination))
const pagedAbnormalItems = computed(() => paginate(dashboard.abnormalItems, abnormalPagination))
const filteredTaskItems = computed(() => {
  const keyword = itemFilters.keyword.trim().toLowerCase()
  return currentTaskItems.value.filter(item => {
    const hitKeyword = !keyword || [item.asset_id, item.name, item.sn, item.book_location, item.actual_location, item.remark].join(' ').toLowerCase().includes(keyword)
    const hitResult = !itemFilters.result || item.result === itemFilters.result
    return hitKeyword && hitResult
  })
})
const pagedTaskItems = computed(() => paginate(filteredTaskItems.value, itemPagination))

onMounted(load)
onUnmounted(() => charts.forEach(chart => chart.dispose()))

async function load() {
  loading.value = true
  try {
    tasks.value = await getStocktakeTasks({ dateRange: dateRange.value })
    ensureSelectedTask()
    refreshDashboard()
    taskPagination.page = Math.min(taskPagination.page, Math.max(1, Math.ceil(tasks.value.length / taskPagination.pageSize) || 1))
    abnormalPagination.page = Math.min(abnormalPagination.page, Math.max(1, Math.ceil(dashboard.abnormalItems.length / abnormalPagination.pageSize) || 1))
    syncCurrentTask()
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  if (!resultRef.value || !trendRef.value) return

  const result = charts[0] || echarts.init(resultRef.value)
  result.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{ name: '盘点结果', type: 'pie', radius: ['42%', '68%'], center: ['50%', '44%'], data: dashboard.resultDistribution }]
  })

  const trend = charts[1] || echarts.init(trendRef.value)
  trend.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 42, right: 24, top: 48, bottom: 32 },
    xAxis: { type: 'category', data: dashboard.taskTrend.map(item => item.month) },
    yAxis: { type: 'value' },
    series: [
      { name: '任务数', type: 'bar', data: dashboard.taskTrend.map(item => item.tasks), itemStyle: { color: '#2563eb', borderRadius: [4, 4, 0, 0] } },
      { name: '已盘资产', type: 'line', smooth: true, data: dashboard.taskTrend.map(item => item.checked), itemStyle: { color: '#16a34a' } },
      { name: '差异项', type: 'line', smooth: true, data: dashboard.taskTrend.map(item => item.abnormal), itemStyle: { color: '#dc2626' } }
    ]
  })

  if (!charts.length) charts.push(result, trend)
}

function defaultDateRange() {
  const end = new Date()
  const start = new Date()
  start.setMonth(start.getMonth() - 11)
  return [formatDate(start), formatDate(end)]
}

function defaultForm() {
  return {
    name: '月度资产盘点',
    scope: '全部',
    target: '',
    owner: '资产管理员'
  }
}

function openCreate() {
  Object.assign(form, defaultForm())
  createDialog.value = true
}

async function createTask() {
  await createStocktakeTask(form)
  createDialog.value = false
  ElMessage.success('盘点任务已创建')
  await load()
}

async function start(row) {
  await startStocktakeTask(row.id)
  selectedTaskId.value = row.id
  ElMessage.success('盘点任务已开始')
  await load()
}

function openDetail(row) {
  if (!row) return
  selectedTaskId.value = row.id
  currentTask.value = row
  itemPagination.page = 1
  resetItemFilters()
  quickForm.code = ''
  detailDialog.value = true
}

async function confirmScannedItem(row) {
  savingAssetId.value = row.asset_id
  try {
    const saved = await submitStocktakeItem(currentTask.value.id, row.asset_id, {
      actual_location: row.book_location || '',
      result: '正常',
      checker: '扫码确认',
      remark: row.checked_at ? '重新扫码确认' : '扫码确认',
      scan_raw: quickForm.code,
      parsed_code: parseAssetCode(quickForm.code),
      client_source: 'desktop'
    })
    applySavedItem(currentTask.value.id, saved)
    ElMessage.success(`${row.asset_id} 已扫码确认`)
  } finally {
    savingAssetId.value = ''
  }
}

async function registerQuickItem() {
  const code = parseAssetCode(quickForm.code)
  if (!code) return ElMessage.warning('请扫码或输入资产编号 / 序列号')
  if (!currentTask.value) return
  const row = currentTaskItems.value.find(item => assetCodeMatches(item, quickForm.code))
  if (!row) return ElMessage.error('该资产不在当前盘点任务范围内')
  await confirmScannedItem(row)
  quickForm.code = ''
}

async function reportLocationException(row) {
  const value = await ElMessageBox.prompt('请输入发现的位置或异常说明', '异常上报', {
    inputValue: row.actual_location || row.book_location || '',
    confirmButtonText: '上报',
    cancelButtonText: '取消',
    inputPlaceholder: '例如：上海办公区 A-08'
  }).then(result => result.value).catch(() => '')
  if (!value) return
  const saved = await reportStocktakeException(currentTask.value.id, row.asset_id, {
    actual_location: value,
    result: '位置不符',
    reporter: '资产管理员',
    remark: `异常上报：${value}`,
    client_source: 'desktop'
  })
  applySavedItem(currentTask.value.id, saved)
  ElMessage.success('异常已上报，等待复核')
}

async function reviewItem(row, status) {
  const note = await ElMessageBox.prompt('填写复核意见', '盘点异常复核', {
    inputValue: status === '已确认' ? '异常确认' : '异常驳回，需重新核对',
    confirmButtonText: status,
    cancelButtonText: '取消'
  }).then(result => result.value).catch(() => '')
  if (!note) return
  const saved = await reviewStocktakeItem(currentTask.value.id, row.asset_id, {
    review_status: status,
    reviewer: '资产管理员',
    review_note: note
  })
  applySavedItem(currentTask.value.id, saved)
  ElMessage.success(`复核已${status === '已确认' ? '确认' : '驳回'}`)
}

function applySavedItem(taskId, saved) {
  const task = tasks.value.find(item => item.id === taskId)
  if (!task) return
  const item = task.items.find(row => row.asset_id === saved.asset_id)
  if (item) Object.assign(item, saved)
  task.checked = task.items.filter(row => row.result !== '未盘').length
  task.abnormal = task.items.filter(row => ['盘盈', '盘亏', '位置不符', '状态不符'].includes(row.result)).length
  if (task.status !== '已完成' && task.total && task.checked === task.total) task.status = '待确认'
  currentTask.value = task
  refreshDashboard()
  renderCharts()
}

function refreshDashboard() {
  Object.assign(dashboard, buildStocktakeDashboard(dashboardTasks.value))
}

function syncCurrentTask() {
  if (!currentTask.value) return
  currentTask.value = tasks.value.find(task => task.id === currentTask.value.id) || currentTask.value
}

function ensureSelectedTask() {
  if (selectedTask.value) return
  const active = tasks.value.find(task => ['进行中', '待开始', '待确认'].includes(task.status))
  selectedTaskId.value = active?.id || tasks.value[0]?.id || ''
}

function selectTask() {
  abnormalPagination.page = 1
  if (detailDialog.value && selectedTask.value) currentTask.value = selectedTask.value
  refreshDashboard()
  nextTick(renderCharts)
}

function handleCurrentTaskChange(row) {
  if (row?.id) {
    selectedTaskId.value = row.id
    selectTask()
  }
}

function taskOptionLabel(task) {
  return `${task.name} / ${task.status} / ${task.checked || 0}/${task.total || 0}`
}

function resetItemFilters() {
  itemFilters.keyword = ''
  itemFilters.result = ''
  itemPagination.page = 1
}

async function finish(row) {
  if (!row) return
  await ElMessageBox.confirm(`确认完成盘点任务 ${row.id}？完成后将汇总差异结果。`, '完成盘点', { type: 'warning' })
  await finishStocktakeTask(row.id)
  selectedTaskId.value = row.id
  ElMessage.success('盘点任务已完成')
  await load()
}

function progress(row) {
  return row.total ? Math.round((row.checked / row.total) * 100) : 0
}

function taskStatusType(status) {
  if (status === '已完成') return 'success'
  if (status === '待确认') return 'warning'
  if (status === '进行中') return 'primary'
  return 'info'
}

function itemResultType(result) {
  if (result === '正常') return 'success'
  if (result === '未盘') return 'info'
  if (result === '盘亏') return 'danger'
  return 'warning'
}

function reviewStatusType(status) {
  if (status === '已确认') return 'success'
  if (status === '已驳回') return 'danger'
  if (status === '待复核') return 'warning'
  return 'info'
}

function tagType(tone) {
  return ({ primary: 'primary', success: 'success', warning: 'warning', danger: 'danger' })[tone] || 'info'
}

function formatValue(value) {
  return Number(value || 0).toLocaleString()
}

function formatDate(date) {
  return date.toISOString().slice(0, 10)
}

function paginate(rows, pagination) {
  const start = (pagination.page - 1) * pagination.pageSize
  return rows.slice(start, start + pagination.pageSize)
}
</script>

<style scoped>
.stocktake-page {
  display: grid;
  gap: 16px;
}

.toolbar,
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.stocktake-dashboard {
  display: grid;
  grid-template-columns: 1.45fr repeat(3, minmax(150px, 1fr));
  gap: 12px;
}

.task-picker {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: center;
}

.task-picker strong {
  display: block;
  margin-top: 6px;
  font-size: 20px;
  line-height: 1.25;
}

.task-picker p {
  margin: 6px 0 0;
  color: var(--muted);
}

.task-picker-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.completion-body {
  display: grid;
  grid-template-columns: 170px minmax(0, 1fr);
  align-items: center;
  gap: 18px;
}

.completion-body strong {
  display: block;
  margin-top: 8px;
  font-size: 34px;
  line-height: 1;
}

.completion-body p {
  margin: 10px 0 0;
  color: var(--muted);
}

.metric-card :deep(.el-card__body) {
  display: grid;
  align-content: center;
  min-height: 128px;
  gap: 8px;
}

.metric-card span,
.muted {
  color: var(--muted);
}

.metric-card strong {
  color: var(--text);
  font-size: 28px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.chart {
  width: 100%;
  height: 320px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.detail-toolbar,
.quick-register {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.quick-register {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto minmax(280px, 1.2fr);
  align-items: center;
}

.scan-tip {
  color: #64748b;
  font-size: 12px;
}

@media (max-width: 1280px) {
  .stocktake-dashboard {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .stocktake-dashboard,
  .chart-grid,
  .completion-body,
  .quick-register,
  .task-picker {
    grid-template-columns: 1fr;
  }

  .task-picker-actions {
    justify-content: stretch;
  }

  .task-picker-actions :deep(.el-select),
  .task-picker-actions .el-button {
    width: 100%;
  }
}
</style>
