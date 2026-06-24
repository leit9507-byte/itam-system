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
          @change="load"
        />
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
    </section>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>维修记录</span>
          <div class="table-tools">
            <el-input v-model="filters.keyword" clearable placeholder="搜索资产/序列号/故障原因/维修商" style="width: 280px" @input="load" />
            <el-select v-model="filters.status" clearable placeholder="维修状态" style="width: 140px" @change="load">
              <el-option label="维修中" value="维修中" />
              <el-option label="已完成" value="已完成" />
            </el-select>
          </div>
        </div>
      </template>
      <el-table :data="records" border stripe empty-text="暂无维修记录">
        <el-table-column prop="id" label="维修单号" width="140" />
        <el-table-column prop="asset_id" label="资产ID" width="120" />
        <el-table-column prop="asset_name" label="资产名称" min-width="180" />
        <el-table-column prop="sn" label="序列号" width="150" />
        <el-table-column prop="repair_time" label="维修时间" width="120" />
        <el-table-column prop="fault_reason" label="故障原因" min-width="220" />
        <el-table-column prop="repair_cost" label="维修费用" width="120">
          <template #default="{ row }">¥{{ Number(row.repair_cost || 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="vendor" label="维修商" width="140" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '维修中' ? 'warning' : 'success'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button type="success" link :disabled="row.status === '已完成'" @click="finish(row)">完成维修</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { finishRepairRecord, getRepairDashboard, getRepairRecords } from '../../api/repair'

const records = ref([])
const trendRef = ref(null)
const faultRef = ref(null)
const charts = []
const filters = reactive({ keyword: '', status: '', dateRange: defaultDateRange() })
const dashboard = reactive({ total: 0, inProgress: 0, completed: 0, totalCost: 0, avgCost: 0, topFaults: [], costTrend: [] })

onMounted(load)
onUnmounted(() => charts.forEach(chart => chart.dispose()))

async function load() {
  records.value = await getRepairRecords(filters)
  Object.assign(dashboard, await getRepairDashboard(filters))
  await nextTick()
  renderCharts()
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

  charts.push(trend, fault)
}

async function finish(row) {
  await finishRepairRecord(row.id, { next_status: 'in_stock', remark: '维修完成，入库待分配' })
  ElMessage.success('维修已完成，资产状态已恢复为在库')
  await load()
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

@media (max-width: 1200px) {
  .repair-metrics,
  .chart-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .repair-metrics,
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
