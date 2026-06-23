<template>
  <div class="dashboard-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产总览</h2>
        <p class="page-subtitle">基于正式资产、采购和库存状态数据生成首页指标</p>
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
        <el-button type="primary" @click="load">刷新数据</el-button>
      </div>
    </div>

    <section class="metric-grid dashboard-metrics">
      <el-card v-for="item in data.metrics" :key="item.label" shadow="never" class="metric-card">
        <div class="metric-head">
          <span>{{ item.label }}</span>
          <el-tag :type="tagType(item.tone)" effect="light">{{ item.change }}</el-tag>
        </div>
        <div class="metric-value">{{ item.prefix || '' }}{{ formatValue(item.value) }}<small>{{ item.suffix || '' }}</small></div>
        <div class="sparkline">
          <span v-for="(point, index) in item.trend" :key="`${item.label}-${index}`" :style="{ height: `${sparkHeight(point, item.trend)}%` }" />
        </div>
      </el-card>
    </section>

    <section class="dashboard-section two-column">
      <el-card shadow="never">
        <template #header>资产分类占比</template>
        <div ref="categoryRef" class="chart" />
      </el-card>
      <el-card shadow="never">
        <template #header>部门资产分布</template>
        <div ref="departmentRef" class="chart" />
      </el-card>
    </section>

    <section class="dashboard-section two-column">
      <el-card shadow="never">
        <template #header>近 12 个月采购趋势</template>
        <div ref="purchaseRef" class="chart" />
      </el-card>
      <el-card shadow="never">
        <template #header>资产生命周期分布</template>
        <div ref="lifecycleRef" class="chart" />
      </el-card>
    </section>

    <section class="dashboard-section">
      <el-card shadow="never">
        <template #header>维修统计</template>
        <div class="repair-layout">
          <div ref="repairRef" class="chart repair-chart" />
          <div class="repair-kpis">
            <div>
              <span>平均修复时间 MTTR</span>
              <strong>{{ data.maintenance.mttr }}</strong>
            </div>
            <div>
              <span>本月维修费用</span>
              <strong>¥{{ formatValue(data.maintenance.monthCost) }}</strong>
            </div>
            <div>
              <span>年累计维修费用</span>
              <strong>¥{{ formatValue(data.maintenance.yearCost) }}</strong>
            </div>
          </div>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { getEnterpriseDashboard } from '../../api/dashboard'

const categoryRef = ref(null)
const departmentRef = ref(null)
const purchaseRef = ref(null)
const lifecycleRef = ref(null)
const repairRef = ref(null)
const dateRange = ref(defaultDateRange())
const charts = []
const data = reactive({
  metrics: [],
  categoryDistribution: [],
  departmentDistribution: [],
  purchaseTrend: { months: [], amount: [], quantity: [] },
  lifecycleDistribution: [],
  maintenance: { top10: [], mttr: '0小时', monthCost: 0, yearCost: 0 }
})

onMounted(load)
onUnmounted(() => charts.forEach(chart => chart.dispose()))

async function load() {
  Object.assign(data, await getEnterpriseDashboard({ dateRange: dateRange.value }))
  await nextTick()
  renderCharts()
}

function renderCharts() {
  charts.forEach(chart => chart.dispose())
  charts.length = 0

  const category = echarts.init(categoryRef.value)
  category.setOption({
    color: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#6366f1', '#14b8a6', '#8b5cf6', '#64748b', '#94a3b8'],
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, type: 'scroll' },
    series: [{ name: '资产分类', type: 'pie', radius: ['42%', '68%'], center: ['50%', '44%'], data: data.categoryDistribution }]
  })

  const department = echarts.init(departmentRef.value)
  department.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 18, top: 28, bottom: 52 },
    xAxis: { type: 'category', data: data.departmentDistribution.map(item => item.name), axisLabel: { interval: 0, rotate: 24 } },
    yAxis: { type: 'value' },
    series: [{ name: '资产数量', type: 'bar', barWidth: 24, data: data.departmentDistribution.map(item => item.value), itemStyle: { color: '#1f7a6a', borderRadius: [4, 4, 0, 0] } }]
  })

  const purchase = echarts.init(purchaseRef.value)
  purchase.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 52, right: 52, top: 48, bottom: 34 },
    xAxis: { type: 'category', data: data.purchaseTrend.months },
    yAxis: [
      { type: 'value', name: '金额' },
      { type: 'value', name: '数量' }
    ],
    series: [
      { name: '采购金额', type: 'bar', data: data.purchaseTrend.amount, itemStyle: { color: '#2563eb', borderRadius: [4, 4, 0, 0] } },
      { name: '采购数量', type: 'line', yAxisIndex: 1, smooth: true, data: data.purchaseTrend.quantity, itemStyle: { color: '#f59e0b' } }
    ]
  })

  const lifecycle = echarts.init(lifecycleRef.value)
  lifecycle.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 70, right: 20, top: 28, bottom: 36 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: data.lifecycleDistribution.map(item => item.name) },
    series: [{ name: '资产数量', type: 'bar', data: data.lifecycleDistribution.map(item => item.value), itemStyle: { color: '#14b8a6', borderRadius: [0, 4, 4, 0] } }]
  })

  const repair = echarts.init(repairRef.value)
  repair.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 110, right: 20, top: 20, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: data.maintenance.top10.map(item => item.name), axisLabel: { width: 96, overflow: 'truncate' } },
    series: [{ name: '故障次数', type: 'bar', data: data.maintenance.top10.map(item => item.count), itemStyle: { color: '#c2410c', borderRadius: [0, 4, 4, 0] } }]
  })

  charts.push(category, department, purchase, lifecycle, repair)
}

function defaultDateRange() {
  const end = new Date()
  const start = new Date()
  start.setMonth(start.getMonth() - 11)
  return [formatDate(start), formatDate(end)]
}

function formatDate(date) {
  return date.toISOString().slice(0, 10)
}

function formatValue(value) {
  return Number(value || 0).toLocaleString()
}

function tagType(tone) {
  return ({ primary: 'primary', success: 'success', warning: 'warning', danger: 'danger' })[tone] || 'info'
}

function sparkHeight(point, trend) {
  const max = Math.max(...trend, 1)
  return Math.max(18, Math.round((Number(point || 0) / max) * 100))
}
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 16px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.dashboard-metrics {
  grid-template-columns: repeat(4, minmax(180px, 1fr));
}

.metric-card {
  min-height: 136px;
}

.metric-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--muted);
  font-size: 13px;
}

.metric-value {
  margin-top: 16px;
  color: var(--text);
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
}

.metric-value small {
  margin-left: 4px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 500;
}

.sparkline {
  display: flex;
  align-items: end;
  gap: 4px;
  height: 28px;
  margin-top: 14px;
}

.sparkline span {
  width: 14px;
  border-radius: 3px 3px 0 0;
  background: #1f7a6a;
  opacity: 0.72;
}

.dashboard-section {
  align-items: stretch;
}

.chart {
  width: 100%;
  height: 320px;
}

.repair-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 16px;
}

.repair-chart {
  height: 320px;
}

.repair-kpis {
  display: grid;
  align-content: center;
  gap: 12px;
}

.repair-kpis div {
  display: grid;
  gap: 8px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}

.repair-kpis span {
  color: var(--muted);
  font-size: 13px;
}

.repair-kpis strong {
  color: var(--text);
  font-size: 22px;
}

@media (max-width: 1320px) {
  .dashboard-metrics {
    grid-template-columns: repeat(2, minmax(180px, 1fr));
  }
}

@media (max-width: 900px) {
  .dashboard-metrics,
  .two-column,
  .repair-layout {
    grid-template-columns: 1fr;
  }
}
</style>
