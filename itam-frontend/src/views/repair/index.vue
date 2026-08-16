<template>
  <div class="repair-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">维修管理</h2>
        <p class="page-subtitle">查看资产维修记录、维修费用、故障原因和维修状态</p>
      </div>
      <div class="toolbar">
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          clearable
          @change="refreshDashboardAndList"
        />
        <el-button @click="downloadRepairsCsv">导出维修台账</el-button>
        <el-button @click="openFaultTypeDialog">故障类型设置</el-button>
        <el-button type="primary" @click="load">刷新</el-button>
      </div>
    </div>

    <section class="metric-grid repair-metrics">
      <el-card shadow="never"><el-statistic title="维修单数" :value="dashboard.total" /></el-card>
      <el-card shadow="never"><el-statistic title="维修中" :value="dashboard.inProgress" /></el-card>
      <el-card shadow="never"><el-statistic title="已完成" :value="dashboard.completed" /></el-card>
      <el-card shadow="never"><el-statistic title="维修总费用" :value="dashboard.totalCost" prefix="¥" /></el-card>
      <el-card shadow="never"><el-statistic title="平均维修费用" :value="dashboard.avgCost" prefix="¥" /></el-card>
    </section>

    <section class="chart-grid">
      <el-card shadow="never">
        <template #header>维修费用趋势</template>
        <div ref="trendRef" class="chart" />
      </el-card>
      <el-card shadow="never">
        <template #header>故障原因 TOP10</template>
        <div ref="faultRef" class="chart" />
      </el-card>
      <el-card shadow="never">
        <template #header>维修型号 TOP10</template>
        <div ref="modelRef" class="chart" />
      </el-card>
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>品牌故障率</span>
            <el-tag v-if="dashboard.brandFaultPeak" type="danger" effect="light">{{ dashboard.brandFaultPeak }}</el-tag>
          </div>
        </template>
        <div ref="brandRateRef" class="chart" />
      </el-card>
      <el-card shadow="never" class="wide-chart">
        <template #header>
          <div class="card-header">
            <span>故障年限趋势</span>
            <el-tag v-if="dashboard.ageTrendPeak" type="warning" effect="light">{{ dashboard.ageTrendPeak }}</el-tag>
          </div>
        </template>
        <div ref="ageTrendRef" class="chart" />
      </el-card>
    </section>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>维修记录</span>
          <div class="table-tools">
            <el-input v-model="filters.keyword" clearable placeholder="搜索资产/序列号/故障原因/维修商" style="width: 280px" @input="debouncedRefresh" />
            <el-select v-model="filters.status" clearable placeholder="维修状态" style="width: 140px" @change="refresh">
              <el-option label="维修中" value="维修中" />
              <el-option label="已完成" value="已完成" />
              <el-option label="未修好" value="未修好" />
              <el-option label="在保送修" value="在保送修" />
            </el-select>
            <el-select v-model="filters.sortMode" placeholder="排序" style="width: 170px" @change="refresh">
              <el-option label="最新维修单" value="latest" />
              <el-option label="故障设备数量降序" value="fault_count_desc" />
              <el-option label="故障设备数量升序" value="fault_count_asc" />
            </el-select>
          </div>
        </div>
      </template>
      <el-table :data="records" border stripe empty-text="暂无维修记录">
        <el-table-column prop="id" label="维修单号" width="140" />
        <el-table-column prop="asset_no" label="资产编号" width="140">
          <template #default="{ row }">{{ row.asset_no || '-' }}</template>
        </el-table-column>
        <el-table-column prop="asset_name" label="资产名称" min-width="180" />
        <el-table-column prop="asset_model" label="型号" width="130" show-overflow-tooltip />
        <el-table-column prop="sn" label="序列号" width="150" />
        <el-table-column prop="repair_time" label="维修时间" width="120" />
        <el-table-column prop="repair_type" label="维修类型" width="110" />
        <el-table-column prop="fault_reason" label="故障原因" min-width="220" />
        <el-table-column prop="fault_device_count" label="故障次数" width="100">
          <template #default="{ row }">
            <el-tag :type="row.fault_device_count > 1 ? 'warning' : 'info'" effect="light">{{ row.fault_device_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="repair_cost" label="维修费用" width="120">
          <template #default="{ row }">¥{{ Number(row.repair_cost || 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="vendor" label="维修商" width="140" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '维修中' ? 'warning' : 'success'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="repair_result" label="维修结果" width="110">
          <template #default="{ row }">{{ row.repair_result || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button type="success" link :disabled="isRepairClosed(row)" @click="openFinishDialog(row)">处理结果</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="load"
        />
      </div>
    </el-card>

    <el-dialog v-model="faultTypeDialog.visible" title="故障类型设置" width="760px">
      <div class="fault-type-form">
        <el-input v-model="faultTypeDialog.form.name" placeholder="故障类型，例如：无法开机" />
        <el-input v-model="faultTypeDialog.form.description" placeholder="说明，可选" />
        <el-select v-model="faultTypeDialog.form.enabled" style="width: 120px">
          <el-option label="启用" value="启用" />
          <el-option label="停用" value="停用" />
        </el-select>
        <el-button type="primary" @click="saveFaultType">保存</el-button>
      </div>
      <el-table :data="faultTypes" border stripe>
        <el-table-column prop="name" label="故障类型" min-width="160" />
        <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
        <el-table-column prop="enabled" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled === '启用' ? 'success' : 'info'">{{ row.enabled }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="editFaultType(row)">编辑</el-button>
            <el-button link type="danger" @click="removeFaultType(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="finishDialog.visible" title="维修处理结果" width="520px">
      <el-form :model="finishDialog.form" label-width="96px">
        <el-form-item label="维修结果" required>
          <el-select v-model="finishDialog.form.repair_result" style="width: 100%" @change="applyRepairResult">
            <el-option label="已修好" value="已修好" />
            <el-option label="未修好" value="未修好" />
            <el-option label="在保送修" value="在保送修" />
          </el-select>
        </el-form-item>
        <el-form-item label="资产后续状态" required>
          <el-select v-model="finishDialog.form.next_status" style="width: 100%">
            <el-option label="入库待分配" value="in_stock" />
            <el-option label="继续维修中" value="repair" />
            <el-option label="待报废" value="ready_scrap" />
          </el-select>
        </el-form-item>
        <el-form-item label="完成时间">
          <el-date-picker v-model="finishDialog.form.finish_time" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="finishDialog.form.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="finishDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitFinish">确认处理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import echarts from '../../utils/echarts'
import { deleteRepairFaultType, finishRepairRecord, getRepairDashboard, getRepairFaultTypes, getRepairRecords, saveRepairFaultType } from '../../api/repair'
import { downloadRepairsCsv } from '../../api/reporting'

const records = ref([])
const trendRef = ref(null)
const faultRef = ref(null)
const modelRef = ref(null)
const brandRateRef = ref(null)
const ageTrendRef = ref(null)
const charts = []
const faultTypes = ref([])
const filters = reactive({ keyword: '', status: '', dateRange: defaultDateRange(), sortMode: 'latest' })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const dashboard = reactive({ total: 0, inProgress: 0, completed: 0, totalCost: 0, avgCost: 0, topFaults: [], topModels: [], brandFaultRates: [], brandFaultPeak: '', ageTrend: [], ageTrendPeak: '', costTrend: [] })
const faultTypeDialog = reactive({ visible: false, form: defaultFaultTypeForm() })
const finishDialog = reactive({ visible: false, row: null, form: defaultFinishForm() })

onMounted(() => {
  isActive = true
  load()
  loadDashboard()
})
onUnmounted(() => {
  isActive = false
  if (searchTimer) window.clearTimeout(searchTimer)
  charts.forEach(chart => chart.dispose())
  charts.length = 0
})

let isActive = true
let searchTimer = null
function debouncedSearch(fn) {
  return function(...args) {
    if (searchTimer) window.clearTimeout(searchTimer)
    searchTimer = window.setTimeout(() => fn.apply(this, args), 350)
  }
}
const debouncedRefresh = debouncedSearch(refresh)

async function load() {
  const result = await getRepairRecords({ ...filters, ...repairSortParams(), page: pagination.page, page_size: pagination.pageSize })
  if (!isActive) return
  records.value = result.list
  pagination.total = result.total
  faultTypes.value = await getRepairFaultTypes()
  if (!isActive) return
  await nextTick()
  if (!isActive) return
  renderCharts()
}

// 仪表盘（含 500 条维修 + 2000 台资产统计）仅挂载时加载一次，避免列表刷新/翻页反复重算
let dashboardLoaded = false
async function loadDashboard() {
  if (dashboardLoaded) return
  dashboardLoaded = true
  Object.assign(dashboard, await getRepairDashboard(filters))
  if (!isActive) return
  await nextTick()
  if (!isActive) return
  renderCharts()
}

function repairSortParams() {
  if (filters.sortMode === 'fault_count_desc') return { sort_by: 'fault_device_count', sort_order: 'desc' }
  if (filters.sortMode === 'fault_count_asc') return { sort_by: 'fault_device_count', sort_order: 'asc' }
  return {}
}

function handlePageSizeChange() {
  pagination.page = 1
  load()
}

function refresh() {
  pagination.page = 1
  load()
}

// 日期范围影响仪表盘统计，需要列表与仪表盘一起刷新；其他筛选只刷新列表
function refreshDashboardAndList() {
  dashboardLoaded = false
  pagination.page = 1
  load()
  loadDashboard()
}

function renderCharts() {
  charts.forEach(chart => chart.dispose())
  charts.length = 0

  const trend = echarts.init(trendRef.value)
  trend.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 56, right: 44, top: 48, bottom: 34 },
    xAxis: { type: 'category', data: dashboard.costTrend.map(item => item.month) },
    yAxis: [
      { type: 'value', name: '费用' },
      { type: 'value', name: '数量' }
    ],
    series: [
      { name: '维修费用', type: 'bar', data: dashboard.costTrend.map(item => item.cost), itemStyle: { color: '#dc2626', borderRadius: [4, 4, 0, 0] } },
      { name: '维修单数', type: 'line', yAxisIndex: 1, smooth: true, data: dashboard.costTrend.map(item => item.count), itemStyle: { color: '#2563eb' } }
    ]
  })

  const fault = echarts.init(faultRef.value)
  fault.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 120, right: 20, top: 20, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: dashboard.topFaults.map(item => item.name), axisLabel: { width: 108, overflow: 'truncate' } },
    series: [{ name: '次数', type: 'bar', data: dashboard.topFaults.map(item => item.value), itemStyle: { color: '#f59e0b', borderRadius: [0, 4, 4, 0] } }]
  })

  const model = echarts.init(modelRef.value)
  model.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 120, right: 20, top: 20, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: dashboard.topModels.map(item => item.name), axisLabel: { width: 108, overflow: 'truncate' } },
    series: [{ name: '维修次数', type: 'bar', data: dashboard.topModels.map(item => item.value), itemStyle: { color: '#2563eb', borderRadius: [0, 4, 4, 0] } }]
  })

  const brandRate = echarts.init(brandRateRef.value)
  brandRate.setOption({
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const brand = params[0]?.axisValue || ''
        const row = dashboard.brandFaultRates.find(item => item.brand === brand)
        if (!row) return brand
        return `${brand}<br/>故障率：${row.rate}%<br/>故障设备：${row.fault_asset_count}/${row.asset_count}<br/>维修次数：${row.repair_count}`
      }
    },
    grid: { left: 118, right: 48, top: 26, bottom: 28 },
    xAxis: { type: 'value', name: '%' },
    yAxis: { type: 'category', data: dashboard.brandFaultRates.map(item => item.brand), axisLabel: { width: 104, overflow: 'truncate' } },
    series: [
      {
        name: '故障率',
        type: 'bar',
        data: dashboard.brandFaultRates.map(item => item.rate),
        label: { show: true, position: 'right', formatter: '{c}%' },
        itemStyle: { color: '#dc2626', borderRadius: [0, 4, 4, 0] }
      }
    ]
  })

  const ageTrend = echarts.init(ageTrendRef.value)
  ageTrend.setOption({
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const count = params.find(item => item.seriesName === '故障次数')?.value || 0
        const cost = params.find(item => item.seriesName === '平均维修费用')?.value || 0
        return `${params[0]?.axisValue || ''}<br/>故障次数：${count}<br/>平均维修费用：¥${Number(cost).toLocaleString()}`
      }
    },
    legend: { top: 0 },
    grid: { left: 56, right: 54, top: 48, bottom: 34 },
    xAxis: { type: 'category', data: dashboard.ageTrend.map(item => item.name) },
    yAxis: [
      { type: 'value', name: '次数' },
      { type: 'value', name: '费用' }
    ],
    series: [
      { name: '故障次数', type: 'bar', data: dashboard.ageTrend.map(item => item.value), itemStyle: { color: '#f97316', borderRadius: [4, 4, 0, 0] } },
      { name: '平均维修费用', type: 'line', yAxisIndex: 1, smooth: true, data: dashboard.ageTrend.map(item => item.avg_cost), itemStyle: { color: '#0f766e' } }
    ]
  })

  charts.push(trend, fault, model, brandRate, ageTrend)
}

function isRepairClosed(row) {
  return ['已完成', '未修好'].includes(row.status)
}

function openFinishDialog(row) {
  finishDialog.row = row
  finishDialog.form = defaultFinishForm()
  finishDialog.visible = true
}

function applyRepairResult(value) {
  if (value === '已修好') {
    finishDialog.form.next_status = 'in_stock'
    finishDialog.form.remark = '维修完成，入库待分配'
  } else if (value === '未修好') {
    finishDialog.form.next_status = 'ready_scrap'
    finishDialog.form.remark = '维修后仍无法正常使用，建议进入报废评估'
  } else if (value === '在保送修') {
    finishDialog.form.next_status = 'repair'
    finishDialog.form.remark = '在保维修，继续跟进供应商处理'
  }
}

async function submitFinish() {
  if (!finishDialog.row) return
  await finishRepairRecord(finishDialog.row.id, finishDialog.form)
  ElMessage.success(`维修结果已记录：${finishDialog.form.repair_result}`)
  finishDialog.visible = false
  await load()
}

function openFaultTypeDialog() {
  faultTypeDialog.form = defaultFaultTypeForm()
  faultTypeDialog.visible = true
}

function editFaultType(row) {
  faultTypeDialog.form = { ...row }
}

async function saveFaultType() {
  if (!faultTypeDialog.form.name.trim()) {
    ElMessage.warning('请填写故障类型名称')
    return
  }
  await saveRepairFaultType(faultTypeDialog.form)
  ElMessage.success('故障类型已保存')
  faultTypeDialog.form = defaultFaultTypeForm()
  faultTypes.value = await getRepairFaultTypes()
}

async function removeFaultType(row) {
  const confirmed = await ElMessageBox.confirm(`确认删除故障类型“${row.name}”？已有维修记录不会受影响。`, '删除故障类型', { type: 'warning' }).then(() => true).catch(() => false)
  if (!confirmed) return
  await deleteRepairFaultType(row.id)
  ElMessage.success('故障类型已删除')
  if (faultTypeDialog.form.id === row.id) faultTypeDialog.form = defaultFaultTypeForm()
  faultTypes.value = await getRepairFaultTypes()
}

function defaultFaultTypeForm() {
  return { id: null, name: '', description: '', enabled: '启用' }
}

function defaultFinishForm() {
  return { repair_result: '已修好', next_status: 'in_stock', finish_time: '', remark: '维修完成，入库待分配' }
}

function defaultDateRange() {
  const end = new Date()
  const start = new Date()
  start.setMonth(start.getMonth() - 11)
  return [start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)]
}
</script>

<style scoped>
.repair-page {
  display: grid;
  gap: 16px;
}

.toolbar,
.card-header,
.table-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.repair-metrics {
  grid-template-columns: repeat(5, minmax(150px, 1fr));
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

.wide-chart {
  grid-column: 1 / -1;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.fault-type-form {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(180px, 1.2fr) 120px auto;
  gap: 10px;
  margin-bottom: 14px;
}

@media (max-width: 1200px) {
  .repair-metrics,
  .chart-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .repair-metrics,
  .chart-grid,
  .fault-type-form {
    grid-template-columns: 1fr;
  }
}
</style>
