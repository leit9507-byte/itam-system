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

    <section class="stocktake-dashboard">
      <el-card shadow="never" class="completion-card">
        <div class="completion-body">
          <el-progress type="dashboard" :percentage="dashboard.completionRate" :width="154" />
          <div>
            <span class="muted">盘点完成率</span>
            <strong>{{ dashboard.completionRate }}%</strong>
            <p>基于当前时间范围内的盘点任务明细统计。</p>
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
          <span>盘点任务</span>
          <el-tag type="info">{{ tasks.length }} 个任务</el-tag>
        </div>
      </template>
      <el-table :data="tasks" border stripe empty-text="当前时间范围暂无盘点任务">
        <el-table-column prop="id" label="任务编号" width="140" />
        <el-table-column prop="name" label="任务名称" min-width="220" />
        <el-table-column prop="scope" label="范围类型" width="100" />
        <el-table-column prop="target" label="盘点范围" width="150" />
        <el-table-column prop="owner" label="负责人" width="110" />
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
    </el-card>

    <el-card shadow="never">
      <template #header>差异明细</template>
      <el-table :data="dashboard.abnormalItems" border stripe empty-text="当前时间范围暂无盘点差异">
        <el-table-column prop="asset_id" label="资产ID" width="120" />
        <el-table-column prop="name" label="资产名称" min-width="180" />
        <el-table-column prop="sn" label="序列号" width="150" />
        <el-table-column prop="book_location" label="账面位置" width="160" />
        <el-table-column prop="actual_location" label="实盘位置" width="160" />
        <el-table-column prop="result" label="结果" width="110" />
        <el-table-column prop="remark" label="备注" min-width="180" />
      </el-table>
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
          <el-input v-model="form.target" placeholder="如：研发部、上海 IT 库、in_stock；全部资产可留空" />
        </el-form-item>
        <el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" @click="createTask">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialog" :title="currentTask ? `盘点明细：${currentTask.name}` : '盘点明细'" width="1100px">
      <el-table :data="currentTask?.items || []" border stripe>
        <el-table-column prop="asset_id" label="资产ID" width="100" />
        <el-table-column prop="name" label="资产名称" min-width="160" />
        <el-table-column prop="sn" label="序列号" width="140" />
        <el-table-column prop="book_location" label="账面位置" width="160" />
        <el-table-column prop="book_status" label="账面状态" width="100" />
        <el-table-column prop="actual_location" label="实盘位置" width="160">
          <template #default="{ row }">
            <el-input v-model="row.actual_location" placeholder="实盘位置" />
          </template>
        </el-table-column>
        <el-table-column prop="result" label="结果" width="130">
          <template #default="{ row }">
            <el-select v-model="row.result">
              <el-option label="未盘" value="未盘" />
              <el-option label="正常" value="正常" />
              <el-option label="盘盈" value="盘盈" />
              <el-option label="盘亏" value="盘亏" />
              <el-option label="位置不符" value="位置不符" />
              <el-option label="状态不符" value="状态不符" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="170">
          <template #default="{ row }">
            <el-input v-model="row.remark" placeholder="备注" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="submitItem(row)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import {
  createStocktakeTask,
  finishStocktakeTask,
  getStocktakeDashboard,
  getStocktakeTasks,
  startStocktakeTask,
  submitStocktakeItem
} from '../../api/stocktake'

const tasks = ref([])
const createDialog = ref(false)
const detailDialog = ref(false)
const currentTask = ref(null)
const dateRange = ref(defaultDateRange())
const resultRef = ref(null)
const trendRef = ref(null)
const charts = []
const form = reactive(defaultForm())
const dashboard = reactive({
  metrics: [],
  completionRate: 0,
  resultDistribution: [],
  taskTrend: [],
  scopeDistribution: [],
  abnormalItems: []
})

onMounted(load)
onUnmounted(() => charts.forEach(chart => chart.dispose()))

async function load() {
  tasks.value = await getStocktakeTasks({ dateRange: dateRange.value })
  Object.assign(dashboard, await getStocktakeDashboard({ dateRange: dateRange.value }))
  await nextTick()
  renderCharts()
}

function renderCharts() {
  charts.forEach(chart => chart.dispose())
  charts.length = 0

  const result = echarts.init(resultRef.value)
  result.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{ name: '盘点结果', type: 'pie', radius: ['42%', '68%'], center: ['50%', '44%'], data: dashboard.resultDistribution }]
  })

  const trend = echarts.init(trendRef.value)
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

  charts.push(result, trend)
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
  ElMessage.success('盘点任务已开始')
  await load()
}

function openDetail(row) {
  currentTask.value = row
  detailDialog.value = true
}

async function submitItem(row) {
  if (!row.actual_location && row.result !== '盘亏') {
    ElMessage.warning('请填写实盘位置，盘亏可留空')
    return
  }
  await submitStocktakeItem(currentTask.value.id, row.asset_id, row)
  ElMessage.success('盘点结果已保存')
  await load()
}

async function finish(row) {
  await ElMessageBox.confirm(`确认完成盘点任务 ${row.id}？完成后将汇总差异结果。`, '完成盘点', { type: 'warning' })
  await finishStocktakeTask(row.id)
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

function tagType(tone) {
  return ({ primary: 'primary', success: 'success', warning: 'warning', danger: 'danger' })[tone] || 'info'
}

function formatValue(value) {
  return Number(value || 0).toLocaleString()
}

function formatDate(date) {
  return date.toISOString().slice(0, 10)
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

@media (max-width: 1280px) {
  .stocktake-dashboard {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .stocktake-dashboard,
  .chart-grid,
  .completion-body {
    grid-template-columns: 1fr;
  }
}
</style>
