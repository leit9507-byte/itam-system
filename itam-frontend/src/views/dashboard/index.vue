<template>
  <div class="dashboard-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产总览</h2>
        <p class="page-subtitle">集中展示资产规模、库存流转、审批待办、盘点差异和风险预警</p>
      </div>
      <el-button type="primary" @click="load">刷新数据</el-button>
    </div>

    <div class="metric-grid dashboard-metrics">
      <el-card v-for="item in data.metrics" :key="item.label" shadow="never" class="metric-card">
        <div class="metric-title">
          <span>{{ item.label }}</span>
          <el-tag :type="item.type" effect="light">{{ item.trend }}</el-tag>
        </div>
        <strong>{{ item.prefix || '' }}{{ formatValue(item.value) }}</strong>
      </el-card>
    </div>

    <div class="dashboard-main">
      <div class="left-column">
        <div class="chart-grid">
          <el-card shadow="never">
            <template #header>利用率趋势</template>
            <div ref="lineRef" class="chart" />
          </el-card>
          <el-card shadow="never">
            <template #header>资产状态分布</template>
            <div ref="statusRef" class="chart" />
          </el-card>
        </div>

        <el-card shadow="never">
          <template #header>月度出入库与报废</template>
          <div ref="flowRef" class="chart chart-short" />
        </el-card>

        <div class="two-column">
          <el-card shadow="never">
            <template #header>风险资产排行</template>
            <el-table :data="data.riskAssets" border>
              <el-table-column prop="asset_id" label="资产ID" width="100" />
              <el-table-column prop="name" label="资产名称" min-width="170" />
              <el-table-column prop="risk" label="风险说明" min-width="180" />
              <el-table-column prop="owner" label="责任人" width="100" />
              <el-table-column prop="level" label="等级" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.level === 'high' ? 'danger' : 'warning'">{{ row.level === 'high' ? '高' : '中' }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never">
            <template #header>盘点差异概览</template>
            <div class="stocktake-list">
              <div v-for="item in data.stocktakeSummary" :key="item.label" class="stocktake-item">
                <span>{{ item.label }}</span>
                <el-progress :percentage="stocktakePercent(item.value)" :show-text="false" />
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </el-card>
        </div>
      </div>

      <div class="right-column">
        <el-card shadow="never">
          <template #header>待办中心</template>
          <div class="todo-list">
            <button v-for="item in data.todos" :key="item.title" class="todo-item" type="button" @click="router.push(item.route)">
              <span>{{ item.title }}</span>
              <el-tag :type="item.level">{{ item.count }}</el-tag>
            </button>
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>部门资产分布</template>
          <div ref="deptRef" class="chart chart-compact" />
        </el-card>

        <el-card shadow="never">
          <template #header>最近动态</template>
          <el-timeline>
            <el-timeline-item v-for="item in data.recentActivities" :key="`${item.time}-${item.text}`" :timestamp="item.time">
              <strong>{{ item.type }}</strong>
              <p>{{ item.text }}</p>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { getDashboardOverview } from '../../api/dashboard'

const router = useRouter()
const lineRef = ref(null)
const statusRef = ref(null)
const deptRef = ref(null)
const flowRef = ref(null)
const charts = []
const data = reactive({
  metrics: [],
  utilization: [],
  deptDistribution: [],
  statusDistribution: [],
  monthlyFlow: { months: [], inbound: [], outbound: [], scrap: [] },
  todos: [],
  riskAssets: [],
  recentActivities: [],
  stocktakeSummary: []
})

onMounted(load)

async function load() {
  Object.assign(data, await getDashboardOverview())
  await nextTick()
  renderCharts()
}

function renderCharts() {
  charts.forEach(chart => chart.dispose())
  charts.length = 0

  const line = echarts.init(lineRef.value)
  line.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 36, right: 20, top: 24, bottom: 28 },
    xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{ name: '利用率', type: 'line', smooth: true, data: data.utilization, areaStyle: {} }]
  })

  const status = echarts.init(statusRef.value)
  status.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{ type: 'pie', radius: ['42%', '68%'], data: data.statusDistribution }]
  })

  const dept = echarts.init(deptRef.value)
  dept.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{ type: 'pie', radius: ['45%', '70%'], data: data.deptDistribution }]
  })

  const flow = echarts.init(flowRef.value)
  flow.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 36, right: 20, top: 42, bottom: 28 },
    xAxis: { type: 'category', data: data.monthlyFlow.months },
    yAxis: { type: 'value' },
    series: [
      { name: '入库', type: 'bar', data: data.monthlyFlow.inbound },
      { name: '出库', type: 'bar', data: data.monthlyFlow.outbound },
      { name: '报废', type: 'line', data: data.monthlyFlow.scrap }
    ]
  })

  charts.push(line, status, dept, flow)
}

function formatValue(value) {
  return Number(value || 0).toLocaleString()
}

function stocktakePercent(value) {
  const total = data.stocktakeSummary.reduce((sum, item) => sum + item.value, 0) || 1
  return Math.round((value / total) * 100)
}
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 16px;
}

.dashboard-metrics {
  grid-template-columns: repeat(4, minmax(180px, 1fr));
}

.metric-card {
  min-height: 112px;
}

.metric-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--muted);
  font-size: 13px;
}

.metric-card strong {
  display: block;
  margin-top: 18px;
  color: var(--text);
  font-size: 28px;
  line-height: 1;
}

.dashboard-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}

.left-column,
.right-column {
  display: grid;
  align-content: start;
  gap: 16px;
  min-width: 0;
}

.chart-short {
  height: 280px;
}

.chart-compact {
  height: 260px;
}

.todo-list,
.stocktake-list {
  display: grid;
  gap: 10px;
}

.todo-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0 12px;
  background: #fff;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}

.todo-item:hover {
  border-color: var(--primary);
}

.stocktake-item {
  display: grid;
  grid-template-columns: 80px minmax(80px, 1fr) 40px;
  align-items: center;
  gap: 10px;
}

:deep(.el-timeline) {
  padding-left: 4px;
}

:deep(.el-timeline-item__content p) {
  margin: 4px 0 0;
  color: var(--muted);
  line-height: 1.5;
}

@media (max-width: 1280px) {
  .dashboard-main {
    grid-template-columns: 1fr;
  }

  .right-column {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .dashboard-metrics,
  .right-column {
    grid-template-columns: 1fr;
  }
}
</style>
