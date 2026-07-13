<template>
  <div class="dashboard-page">
    <section class="dashboard-toolbar">
      <div>
        <h2>资产总览</h2>
        <p>{{ dashboardRangeText }}</p>
      </div>
      <div class="toolbar-actions">
        <el-date-picker
          v-model="dashboardDateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :shortcuts="dateShortcuts"
          clearable
          @change="load"
        />
        <el-button @click="clearDateRange">全部时间</el-button>
      </div>
    </section>

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
            <p class="status-note">其他包含待采购、待验收、借出、已出库、已报废、已处置等未展开状态。</p>
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

    <section class="dashboard-grid trend-grid">
      <article class="panel trend-panel">
        <header class="panel-head">
          <h3>采购和报废趋势</h3>
          <el-button link type="primary" @click="$router.push('/purchase')">采购管理</el-button>
        </header>
        <div ref="purchaseScrapRef" class="trend-chart" />
      </article>

      <article class="panel trend-panel">
        <header class="panel-head">
          <h3>待退役资产趋势</h3>
          <el-button link type="primary" @click="$router.push('/asset/list')">查看资产</el-button>
        </header>
        <div ref="retirementTrendRef" class="trend-chart" />
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
import echarts from '../../utils/echarts'
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
const purchaseScrapRef = ref(null)
const retirementTrendRef = ref(null)
const charts = []
let resizeTimer = null
const dashboardDateRange = ref([])
const data = reactive({
  metrics: [],
  categoryDistribution: [],
  purchaseTrend: { months: [], amount: [], quantity: [] },
  scrapTrend: { months: [], submitted: [], approved: [] },
  retirementTrend: { months: [], due: [], overdue: 0 },
  lifecycleDistribution: [],
  retirementSoonAssets: [],
  maintenance: { top10: [], mttr: '0小时', monthCost: 0, yearCost: 0 },
  personnelTrend: { months: [], onboarding: [], offboarding: [], activeTotal: 0, inactiveTotal: 0, onboardingTotal: 0, offboardingTotal: 0 },
  recentRecords: [],
  warrantyRows: []
})

const statusColors = ['#2478ff', '#38c5d8', '#ff9345', '#9b5de5', '#6389ff', '#9db5f4']
const categoryColors = ['#2478ff', '#38c5d8', '#44c486', '#ff9345', '#6683ff', '#8ba4f8']
const dateShortcuts = [
  { text: '近30天', value: () => recentRange(30) },
  { text: '近90天', value: () => recentRange(90) },
  { text: '今年', value: () => [new Date(new Date().getFullYear(), 0, 1), new Date()] }
]
const totalAssets = computed(() => metricValue('在管资产'))
const inUseAssets = computed(() => metricValue('在用资产'))
const stockAssets = computed(() => lifecycleValue('库存中') + lifecycleValue('在库'))
const idleAssets = computed(() => metricValue('闲置资产'))
const repairAssets = computed(() => metricValue('维修中资产'))
const pendingScrapAssets = computed(() => lifecycleValue('待报废') + lifecycleValue('已提交报废审批'))
const expiringAssets = computed(() => metricValue('即将过保资产'))
const dashboardRangeText = computed(() => {
  if (!dashboardDateRange.value?.length) return '全部时间范围'
  return `${dashboardDateRange.value[0]} 至 ${dashboardDateRange.value[1]}`
})

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
    { name: '库存', value: stockAssets.value },
    { name: '闲置', value: idleAssets.value },
    { name: '维修中', value: repairAssets.value },
    { name: '待报废', value: pendingScrapAssets.value },
    { name: '其他', value: Math.max(totalAssets.value - inUseAssets.value - stockAssets.value - idleAssets.value - repairAssets.value - pendingScrapAssets.value, 0) }
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
  if (resizeTimer) window.clearTimeout(resizeTimer)
  charts.forEach(chart => chart.dispose())
})

async function load() {
  Object.assign(data, await getEnterpriseDashboard({ dateRange: dashboardDateRange.value }))
  await nextTick()
  renderCharts()
}

function clearDateRange() {
  dashboardDateRange.value = []
  load()
}

function recentRange(days) {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - days + 1)
  return [start, end]
}

function renderCharts() {
  charts.forEach(chart => chart.dispose())
  charts.length = 0
  renderDonut(statusRef.value, statusDistribution.value, statusColors, `${formatValue(totalAssets.value)}\n在管资产`)
  renderDonut(categoryRef.value, categoryLegend.value, categoryColors, '')
  renderPersonnelTrend()
  renderPurchaseScrapTrend()
  renderRetirementTrend()
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

function renderPurchaseScrapTrend() {
  if (!purchaseScrapRef.value) return
  const purchase = data.purchaseTrend || {}
  const scrap = data.scrapTrend || {}
  const months = purchase.months?.length ? purchase.months : scrap.months || []
  const chart = echarts.init(purchaseScrapRef.value)
  chart.setOption({
    color: ['#2478ff', '#ff9345', '#dc2626'],
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0, data: ['采购金额', '采购数量', '报废通过'] },
    grid: { left: 58, right: 42, top: 44, bottom: 30 },
    xAxis: { type: 'category', data: months, axisTick: { show: false } },
    yAxis: [
      { type: 'value', name: '金额', splitLine: { lineStyle: { color: '#edf2f8' } }, axisLabel: { formatter: value => `¥${formatCompact(value)}` } },
      { type: 'value', name: '数量', minInterval: 1, splitLine: { show: false } }
    ],
    series: [
      { name: '采购金额', type: 'bar', barMaxWidth: 26, data: purchase.amount || [], itemStyle: { borderRadius: [4, 4, 0, 0] } },
      { name: '采购数量', type: 'line', yAxisIndex: 1, smooth: true, symbolSize: 6, data: purchase.quantity || [] },
      { name: '报废通过', type: 'line', yAxisIndex: 1, smooth: true, symbolSize: 6, data: scrap.approved || [] }
    ]
  })
  charts.push(chart)
}

function renderRetirementTrend() {
  if (!retirementTrendRef.value) return
  const trend = data.retirementTrend || {}
  const chart = echarts.init(retirementTrendRef.value)
  chart.setOption({
    color: ['#7657e8', '#f04438'],
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0, data: ['预计退役', '已超期'] },
    grid: { left: 38, right: 18, top: 44, bottom: 30 },
    xAxis: { type: 'category', data: trend.months || [], axisTick: { show: false } },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#edf2f8' } } },
    series: [
      { name: '预计退役', type: 'bar', barMaxWidth: 30, data: trend.due || [], itemStyle: { borderRadius: [4, 4, 0, 0] } },
      { name: '已超期', type: 'line', smooth: true, symbolSize: 7, data: (trend.months || []).map((_, index) => index === 0 ? Number(trend.overdue || 0) : 0) }
    ]
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
  if (resizeTimer) window.clearTimeout(resizeTimer)
  resizeTimer = window.setTimeout(() => {
    charts.forEach(chart => chart.resize())
  }, 120)
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

function formatCompact(value) {
  const number = Number(value || 0)
  if (Math.abs(number) >= 10000) return `${Math.round(number / 1000) / 10}万`
  return number.toLocaleString()
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
  gap: 16px;
}

.dashboard-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #fff;
  box-shadow: var(--shadow);
}

.dashboard-toolbar h2 {
  margin: 0;
  color: var(--text);
  font-size: 20px;
}

.dashboard-toolbar p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(150px, 1fr));
  gap: 14px;
}

.summary-card,
.panel {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: var(--shadow);
}

.summary-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 112px;
  padding: 18px;
  overflow: hidden;
}

.summary-card::after {
  position: absolute;
  right: -30px;
  bottom: -36px;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: rgba(25, 117, 252, 0.08);
  content: "";
}

.summary-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  font-size: 25px;
}

.summary-icon.blue { color: #1975fc; background: #e5f2ff; }
.summary-icon.green { color: #16a34a; background: #eaf8f0; }
.summary-icon.cyan { color: #0ea5e9; background: #e8f7ff; }
.summary-icon.purple { color: #7c3aed; background: #f1edff; }
.summary-icon.orange { color: #d97706; background: #fff7e8; }
.summary-icon.violet { color: #2563eb; background: #eef4ff; }

.summary-body {
  display: grid;
  min-width: 0;
}

.summary-body span {
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.summary-body strong {
  margin-top: 8px;
  color: var(--text);
  font-size: 26px;
  line-height: 1;
}

.summary-body small {
  margin-top: 10px;
  color: var(--muted);
  font-size: 13px;
}

.summary-body small.up { color: var(--success); }
.summary-body small.down { color: var(--danger); }

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

.trend-grid {
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
  color: var(--text);
  font-size: 17px;
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
  color: var(--muted);
  font-size: 13px;
}

.legend-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}

.legend-row strong,
.legend-row em {
  color: var(--text);
  font-style: normal;
  font-weight: 700;
  text-align: right;
}

.status-note {
  margin: 2px 0 0;
  padding: 9px 10px;
  border-radius: 8px;
  background: #f5f7fb;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.55;
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

.trend-chart {
  width: 100%;
  height: 280px;
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
  border-radius: 14px;
  border: 1px solid #edf4ff;
  background: linear-gradient(135deg, #ffffff, var(--panel-soft));
  color: var(--muted);
}

.people-stats strong {
  color: var(--text);
  font-size: 20px;
}

@media (max-width: 1500px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(170px, 1fr));
  }

  .main-grid,
  .trend-grid,
  .lower-grid {
    grid-template-columns: repeat(2, minmax(320px, 1fr));
  }

  .people-panel {
    grid-column: span 2;
  }
}

@media (max-width: 900px) {
  .dashboard-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .toolbar-actions {
    justify-content: flex-start;
  }

  .summary-grid,
  .main-grid,
  .trend-grid,
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
