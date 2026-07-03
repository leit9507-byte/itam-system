<template>
  <div class="dashboard-page">
    <section class="summary-grid">
      <article v-for="item in summaryCards" :key="item.label" class="summary-card">
        <div class="summary-icon" :class="item.tone">
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
        <div class="summary-body">
          <span>{{ item.label }}</span>
          <strong>{{ formatValue(item.value) }}</strong>
          <small :class="item.changeTone">{{ item.caption || `较上月 ${item.change}` }}</small>
        </div>
      </article>
    </section>

    <section class="dashboard-grid main-grid">
      <article class="panel chart-panel">
        <header class="panel-head">
          <h3>资产状态分布</h3>
          <el-button link type="primary" @click="$router.push('/asset/list')">查看详情</el-button>
        </header>
        <div class="donut-layout">
          <div ref="statusRef" class="donut-chart" />
          <div class="legend-list">
            <div v-for="item in statusDistribution" :key="item.name" class="legend-row">
              <span class="legend-dot" :style="{ background: item.color }" />
              <span>{{ item.name }}</span>
              <strong>{{ formatValue(item.value) }}</strong>
              <em>{{ percent(item.value, totalAssets) }}</em>
            </div>
          </div>
        </div>
      </article>

      <article class="panel chart-panel">
        <header class="panel-head">
          <h3>资产分类占比</h3>
          <el-button link type="primary" @click="$router.push('/asset/list')">查看详情</el-button>
        </header>
        <div class="donut-layout">
          <div ref="categoryRef" class="donut-chart" />
          <div class="legend-list">
            <div v-for="item in categoryLegend" :key="item.name" class="legend-row">
              <span class="legend-dot" :style="{ background: item.color }" />
              <span>{{ item.name }}</span>
              <strong>{{ percentValue(item.value) }}</strong>
            </div>
          </div>
        </div>
      </article>

      <article class="panel people-panel">
        <header class="panel-head">
          <h3>入离职人员趋势</h3>
          <el-button link type="primary" @click="$router.push('/personnel')">人员管理</el-button>
        </header>
        <div class="people-layout">
          <div ref="peopleRef" class="people-chart" />
          <div class="people-stats">
            <div><span>当前在职</span><strong>{{ formatValue(data.personnelTrend.activeTotal) }}</strong></div>
            <div><span>离职人员</span><strong>{{ formatValue(data.personnelTrend.inactiveTotal) }}</strong></div>
            <div><span>近六月入职</span><strong>{{ formatValue(data.personnelTrend.onboardingTotal) }}</strong></div>
            <div><span>近六月离职</span><strong>{{ formatValue(data.personnelTrend.offboardingTotal) }}</strong></div>
          </div>
        </div>
      </article>
    </section>

    <section class="dashboard-grid lower-grid">
      <article class="panel recent-panel">
        <header class="panel-head">
          <h3>最近领用 / 归还记录</h3>
          <el-button link type="primary" @click="$router.push('/lifecycle')">查看全部</el-button>
        </header>
        <el-table :data="data.recentRecords" border stripe size="small" empty-text="暂无记录">
          <el-table-column prop="user" label="用户" width="86" />
          <el-table-column prop="asset" label="资产名称" min-width="150" show-overflow-tooltip />
          <el-table-column prop="type" label="类型" width="82" />
          <el-table-column prop="time" label="时间" width="108" />
          <el-table-column prop="action" label="操作" width="82">
            <template #default="{ row }">
              <el-tag :type="row.action === '归还' ? 'success' : 'primary'" effect="light">{{ row.action }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </article>

      <article class="panel warranty-panel">
        <header class="panel-head">
          <h3>维保到期提醒</h3>
          <el-button link type="primary" @click="$router.push('/asset/list')">查看全部</el-button>
        </header>
        <el-table :data="data.warrantyRows" border stripe size="small" empty-text="暂无即将到期资产">
          <el-table-column prop="name" label="资产名称" min-width="170" show-overflow-tooltip />
          <el-table-column prop="type" label="维保类型" width="100" />
          <el-table-column prop="date" label="到期日期" width="110" />
          <el-table-column prop="days" label="剩余天数" width="90" />
          <el-table-column prop="status" label="状态" width="92">
            <template #default="{ row }">
              <el-tag :type="row.status === '已过保' ? 'danger' : row.status === '即将到期' ? 'warning' : 'success'" effect="light">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import {
  Box,
  CircleCheck,
  Delete,
  Files,
  Tools,
  Warning
} from '@element-plus/icons-vue'
import { getEnterpriseDashboard } from '../../api/dashboard'

const statusRef = ref(null)
const categoryRef = ref(null)
const peopleRef = ref(null)
const charts = []
const data = reactive({
  metrics: [],
  categoryDistribution: [],
  lifecycleDistribution: [],
  retirementSoonAssets: [],
  maintenance: { top10: [], mttr: '0小时', monthCost: 0, yearCost: 0 },
  personnelTrend: { months: [], onboarding: [], offboarding: [], activeTotal: 0, inactiveTotal: 0, onboardingTotal: 0, offboardingTotal: 0 },
  recentRecords: [],
  warrantyRows: []
})

const statusColors = ['#2478ff', '#38c5d8', '#ff9345', '#9b5de5', '#6389ff', '#9db5f4']
const categoryColors = ['#2478ff', '#38c5d8', '#44c486', '#ff9345', '#6683ff', '#8ba4f8']
const totalAssets = computed(() => metricValue('在管资产'))
const inUseAssets = computed(() => metricValue('在用资产'))
const idleAssets = computed(() => metricValue('闲置资产'))
const repairAssets = computed(() => metricValue('维修中资产'))
const pendingScrapAssets = computed(() => lifecycleValue('待报废') + lifecycleValue('已提交报废审批'))
const expiringAssets = computed(() => metricValue('即将过保资产'))

const summaryCards = computed(() => [
  card('在管资产', totalAssets.value, metricChange('在管资产'), trendTone('在管资产'), 'blue', Files, `本月新增 ${formatValue(metricValue('本月新增资产'))}`),
  card('在用资产', inUseAssets.value, '实时', 'up', 'green', CircleCheck, '实时状态'),
  card('闲置资产', idleAssets.value, '实时', 'up', 'cyan', Box, '实时状态'),
  card('维修中', repairAssets.value, '实时', 'up', 'purple', Tools, '实时状态'),
  card('待报废', pendingScrapAssets.value, '实时', 'up', 'orange', Delete, '含审批中'),
  card('即将过保', expiringAssets.value, '180天内', 'down', 'violet', Warning, '180天内')
])

const statusDistribution = computed(() => {
  const rows = [
    { name: '在用', value: inUseAssets.value },
    { name: '闲置', value: idleAssets.value },
    { name: '维修中', value: repairAssets.value },
    { name: '待报废', value: pendingScrapAssets.value },
    { name: '其他', value: Math.max(totalAssets.value - inUseAssets.value - idleAssets.value - repairAssets.value - pendingScrapAssets.value, 0) }
  ]
  return rows.map((item, index) => ({ ...item, color: statusColors[index] }))
})

const categoryLegend = computed(() => {
  const rows = data.categoryDistribution.filter(item => item.value > 0).slice(0, 6)
  const fallback = rows.length ? rows : [{ name: '暂无分类', value: 0 }]
  const total = fallback.reduce((sum, item) => sum + Number(item.value || 0), 0) || 1
  return fallback.map((item, index) => ({
    ...item,
    value: Number(item.value || 0),
    percent: Math.round((Number(item.value || 0) / total) * 1000) / 10,
    color: categoryColors[index % categoryColors.length]
  }))
})

onMounted(() => {
  window.addEventListener('resize', resizeCharts)
  load()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  charts.forEach(chart => chart.dispose())
})

async function load() {
  Object.assign(data, await getEnterpriseDashboard())
  await nextTick()
  renderCharts()
}

function renderCharts() {
  charts.forEach(chart => chart.dispose())
  charts.length = 0
  renderDonut(statusRef.value, statusDistribution.value, statusColors, `${formatValue(totalAssets.value)}\n在管资产`)
  renderDonut(categoryRef.value, categoryLegend.value, categoryColors, '')
  renderPersonnelTrend()
  resizeCharts()
}

function renderDonut(target, rows, colors, centerText) {
  if (!target) return
  const chart = echarts.init(target)
  chart.setOption({
    color: colors,
    tooltip: { trigger: 'item' },
    graphic: centerText ? {
      type: 'text',
      left: 'center',
      top: 'center',
      style: { text: centerText, fill: '#102044', fontSize: 18, fontWeight: 700, align: 'center', lineHeight: 28 }
    } : null,
    series: [{
      type: 'pie',
      radius: ['56%', '78%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: true,
      label: { show: false },
      labelLine: { show: false },
      data: rows.map(item => ({ name: item.name, value: item.value }))
    }]
  })
  charts.push(chart)
}

function renderPersonnelTrend() {
  if (!peopleRef.value) return
  const trend = data.personnelTrend || {}
  const chart = echarts.init(peopleRef.value)
  chart.setOption({
    color: ['#2478ff', '#ff9345'],
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0, data: ['入职', '离职'] },
    grid: { left: 34, right: 16, top: 42, bottom: 28 },
    xAxis: { type: 'category', data: trend.months || [], axisTick: { show: false } },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#edf2f8' } } },
    series: [
      { name: '入职', type: 'bar', barMaxWidth: 28, data: trend.onboarding || [] },
      { name: '离职', type: 'line', smooth: true, symbolSize: 7, data: trend.offboarding || [] }
    ]
  })
  charts.push(chart)
}

function resizeCharts() {
  charts.forEach(chart => chart.resize())
}

function card(label, value, change, changeTone, tone, icon, caption = '') {
  return { label, value, change, changeTone, tone, icon, caption }
}

function metricValue(label) {
  return Number(data.metrics.find(item => item.label === label)?.value || 0)
}

function metricChange(label) {
  return data.metrics.find(item => item.label === label)?.change || '无变化'
}

function trendTone(label, lowerIsGood = false) {
  const change = metricChange(label)
  const isDown = String(change).startsWith('-')
  return lowerIsGood ? (isDown ? 'up' : 'down') : (isDown ? 'down' : 'up')
}

function lifecycleValue(name) {
  return Number(data.lifecycleDistribution.find(item => item.name === name)?.value || 0)
}

function formatValue(value) {
  return Number(value || 0).toLocaleString()
}

function percent(value, total) {
  if (!total) return '0%'
  return `${Math.round((Number(value || 0) / total) * 1000) / 10}%`
}

function percentValue(value) {
  const total = categoryLegend.value.reduce((sum, item) => sum + Number(item.value || 0), 0)
  return percent(value, total)
}
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 18px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(150px, 1fr));
  gap: 16px;
}

.summary-card,
.panel {
  border: 1px solid #e6edf7;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(18, 46, 94, 0.08);
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 126px;
  padding: 20px;
}

.summary-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 54px;
  height: 54px;
  border-radius: 14px;
  font-size: 30px;
}

.summary-icon.blue { color: #2478ff; background: #eaf2ff; }
.summary-icon.green { color: #18b87a; background: #e9f9f2; }
.summary-icon.cyan { color: #2aa8e8; background: #e8f7ff; }
.summary-icon.purple { color: #6b63ff; background: #f0efff; }
.summary-icon.orange { color: #ff8a3d; background: #fff0e8; }
.summary-icon.violet { color: #7657e8; background: #f0ecff; }

.summary-body {
  display: grid;
  min-width: 0;
}

.summary-body span {
  color: #25345d;
  font-size: 15px;
  font-weight: 700;
}

.summary-body strong {
  margin-top: 10px;
  color: #102044;
  font-size: 28px;
  line-height: 1;
}

.summary-body small {
  margin-top: 12px;
  color: #8a96ad;
  font-size: 13px;
}

.summary-body small.up { color: #23a66a; }
.summary-body small.down { color: #f04438; }

.dashboard-grid {
  display: grid;
  gap: 16px;
}

.main-grid {
  grid-template-columns: minmax(420px, 1fr) minmax(420px, 1fr);
}

.lower-grid {
  grid-template-columns: minmax(430px, 1fr) minmax(430px, 1fr);
}

.people-panel {
  grid-column: span 2;
}

.panel {
  min-width: 0;
  padding: 22px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.panel-head h3 {
  margin: 0;
  color: #17254d;
  font-size: 18px;
}

.donut-layout {
  display: grid;
  grid-template-columns: minmax(180px, 0.86fr) minmax(170px, 1fr);
  gap: 10px;
  align-items: center;
}

.donut-chart {
  width: 100%;
  height: 240px;
}

.legend-list {
  display: grid;
  gap: 12px;
}

.legend-row {
  display: grid;
  grid-template-columns: 10px minmax(70px, 1fr) 56px 52px;
  gap: 10px;
  align-items: center;
  color: #53617d;
  font-size: 13px;
}

.legend-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}

.legend-row strong,
.legend-row em {
  color: #1a2a52;
  font-style: normal;
  font-weight: 700;
  text-align: right;
}

.people-layout {
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(180px, 0.34fr);
  gap: 18px;
  align-items: center;
}

.people-chart {
  width: 100%;
  height: 260px;
}

.people-stats {
  display: grid;
  gap: 12px;
}

.people-stats div {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 8px;
  background: #f6f9fe;
  color: #607096;
}

.people-stats strong {
  color: #102044;
  font-size: 20px;
}

@media (max-width: 1500px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(170px, 1fr));
  }

  .main-grid,
  .lower-grid {
    grid-template-columns: repeat(2, minmax(320px, 1fr));
  }

  .people-panel {
    grid-column: span 2;
  }
}

@media (max-width: 900px) {
  .summary-grid,
  .main-grid,
  .lower-grid,
  .donut-layout,
  .people-layout {
    grid-template-columns: 1fr;
  }

  .people-panel {
    grid-column: auto;
  }
}
</style>
