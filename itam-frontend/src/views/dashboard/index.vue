<template>
  <div class="dashboard-page">
    <section class="dashboard-toolbar">
      <div>
        <h2>资产总览</h2>
        <p>实时汇总资产、待办、风险和近期运营动作</p>
      </div>
      <div class="toolbar-actions">
        <span class="range-chip">{{ dashboardRangeText }}</span>
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
        <el-button type="primary" :loading="dashboardLoading" @click="load">刷新</el-button>
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

    <section class="operations-grid">
      <article class="panel todo-panel">
        <header class="panel-head">
          <div>
            <h3>待办中心</h3>
            <p>只显示需要处理的事项</p>
          </div>
          <el-button link type="primary" @click="goPath('/todo')">查看全部</el-button>
        </header>
        <div class="todo-summary">
          <div v-for="item in todoStats" :key="item.label" class="todo-stat" :class="item.tone">
            <span>{{ item.label }}</span>
            <strong>{{ formatValue(item.value) }}</strong>
          </div>
        </div>
        <div class="todo-list">
          <button v-for="item in topTodos" :key="item.id" type="button" class="todo-row" @click="goTodo(item)">
            <el-tag :type="priorityType(item.priority)" effect="light">{{ priorityLabel(item.priority) }}</el-tag>
            <span>
              <strong>{{ item.title }}</strong>
              <small>{{ item.type_label || item.owner || item.created_at || '待处理' }}</small>
            </span>
          </button>
          <el-empty v-if="!topTodos.length" description="暂无待处理事项" :image-size="72" />
        </div>
      </article>

      <article class="panel action-panel">
        <header class="panel-head">
          <div>
            <h3>运营入口</h3>
            <p>高频动作直达</p>
          </div>
        </header>
        <div class="action-grid">
          <button v-for="item in actionCards" :key="item.label" type="button" class="action-card" @click="goPath(item.path, item.query)">
            <span class="action-icon" :class="item.tone">
              <el-icon><component :is="item.icon" /></el-icon>
            </span>
            <span>
              <strong>{{ item.label }}</strong>
              <small>{{ item.caption }}</small>
            </span>
            <em>{{ formatValue(item.value) }}</em>
          </button>
        </div>
      </article>
    </section>

    <section class="dashboard-grid main-grid">
      <article class="panel chart-panel">
        <header class="panel-head">
          <h3>资产状态分布</h3>
          <el-button link type="primary" @click="openDashboardDialog('status')">查看详情</el-button>
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
          <el-button link type="primary" @click="openDashboardDialog('category')">查看详情</el-button>
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
          <el-button link type="primary" @click="goPersonnel">人员管理</el-button>
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

    <section class="dashboard-grid insight-grid">
      <article class="panel lifecycle-panel">
        <header class="panel-head">
          <h3>生命周期分布</h3>
          <el-button link type="primary" @click="goPath('/lifecycle')">生命周期</el-button>
        </header>
        <div class="bar-list">
          <div v-for="item in lifecycleBars" :key="item.name" class="bar-row">
            <div class="bar-label">
              <span>{{ item.name }}</span>
              <strong>{{ formatValue(item.value) }}</strong>
            </div>
            <div class="bar-track">
              <span :style="{ width: item.percent + '%', background: item.color }" />
            </div>
          </div>
          <el-empty v-if="!lifecycleBars.length" description="暂无生命周期数据" :image-size="72" />
        </div>
      </article>

      <article class="panel department-panel">
        <header class="panel-head">
          <h3>部门资产排行</h3>
          <el-button link type="primary" @click="goPath('/department')">部门管理</el-button>
        </header>
        <div class="rank-list">
          <div v-for="(item, index) in departmentTop" :key="item.name" class="rank-row">
            <em>{{ index + 1 }}</em>
            <span>{{ item.name }}</span>
            <strong>{{ formatValue(item.value) }}</strong>
          </div>
          <el-empty v-if="!departmentTop.length" description="暂无部门数据" :image-size="72" />
        </div>
      </article>

      <article class="panel fault-panel">
        <header class="panel-head">
          <h3>维修故障排行</h3>
          <el-button link type="primary" @click="goPath('/repair')">维修管理</el-button>
        </header>
        <div class="rank-list">
          <div v-for="(item, index) in maintenanceTop" :key="`${item.name}-${index}`" class="rank-row">
            <em>{{ index + 1 }}</em>
            <span>{{ item.name }}</span>
            <strong>{{ formatValue(item.count) }}</strong>
          </div>
          <el-empty v-if="!maintenanceTop.length" description="暂无维修数据" :image-size="72" />
        </div>
      </article>
    </section>

    <section class="dashboard-grid trend-grid">
      <article class="panel trend-panel">
        <header class="panel-head">
          <h3>采购和报废趋势</h3>
          <el-button link type="primary" @click="openDashboardDialog('purchase')">采购管理</el-button>
        </header>
        <div ref="purchaseScrapRef" class="trend-chart" />
      </article>

      <article class="panel trend-panel">
        <header class="panel-head">
          <h3>待退役资产趋势</h3>
          <el-button link type="primary" @click="openDashboardDialog('retirement')">查看资产</el-button>
        </header>
        <div ref="retirementTrendRef" class="trend-chart" />
      </article>
    </section>

    <section class="dashboard-grid lower-grid">
      <article class="panel recent-panel">
        <header class="panel-head">
          <h3>最近借用 / 归还记录</h3>
          <el-button link type="primary" @click="goCheckout()">查看全部</el-button>
        </header>
        <el-table :data="data.recentRecords" border stripe size="small" empty-text="暂无记录" class="clickable-table" @row-click="goCheckout">
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
          <el-button link type="primary" @click="openDashboardDialog('warranty')">查看全部</el-button>
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

    <el-dialog v-model="detailDialog.visible" :title="detailDialogTitle" width="860px" class="dashboard-detail-dialog">
      <template v-if="detailDialog.type === 'status'">
        <el-table :data="statusDistribution" border stripe>
          <el-table-column prop="name" label="状态" min-width="160" />
          <el-table-column prop="value" label="数量" width="120">
            <template #default="{ row }">{{ formatValue(row.value) }}</template>
          </el-table-column>
          <el-table-column label="占比" width="120">
            <template #default="{ row }">{{ percent(row.value, totalAssets) }}</template>
          </el-table-column>
        </el-table>
        <p class="dialog-note">其他包含待采购、待验收、借出、已出库、已报废、已处置等未展开状态。</p>
      </template>

      <el-table v-else-if="detailDialog.type === 'category'" :data="categoryDetailRows" border stripe>
        <el-table-column prop="name" label="分类" min-width="180" />
        <el-table-column prop="value" label="数量" width="120">
          <template #default="{ row }">{{ formatValue(row.value) }}</template>
        </el-table-column>
        <el-table-column label="占比" width="120">
          <template #default="{ row }">{{ percent(row.value, categoryDetailTotal) }}</template>
        </el-table-column>
      </el-table>

      <el-table v-else-if="detailDialog.type === 'personnel'" :data="personnelDetailRows" border stripe>
        <el-table-column prop="month" label="月份" min-width="140" />
        <el-table-column prop="onboarding" label="入职" width="120" />
        <el-table-column prop="offboarding" label="离职" width="120" />
      </el-table>

      <el-table v-else-if="detailDialog.type === 'purchase'" :data="purchaseDetailRows" border stripe>
        <el-table-column prop="month" label="月份" min-width="140" />
        <el-table-column prop="amount" label="采购金额" width="160">
          <template #default="{ row }">¥{{ Number(row.amount || 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="采购数量" width="120" />
        <el-table-column prop="scrapApproved" label="报废通过" width="120" />
      </el-table>

      <template v-else-if="detailDialog.type === 'retirement'">
        <el-table :data="retirementDetailRows" border stripe>
          <el-table-column prop="asset_id" label="资产编号" width="150" />
          <el-table-column prop="name" label="资产名称" min-width="180" show-overflow-tooltip />
          <el-table-column prop="retirement_date" label="到期/退役日期" width="140" />
          <el-table-column prop="days_remaining" label="剩余天数" width="110">
            <template #default="{ row }">{{ row.overdue ? `逾期 ${Math.abs(row.days_remaining)} 天` : `${row.days_remaining} 天` }}</template>
          </el-table-column>
        </el-table>
      </template>

      <el-table v-else-if="detailDialog.type === 'recent'" :data="data.recentRecords" border stripe>
        <el-table-column prop="user" label="用户" width="130" />
        <el-table-column prop="asset" label="资产名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="action" label="操作" width="100" />
        <el-table-column prop="time" label="时间" width="130" />
      </el-table>

      <el-table v-else-if="detailDialog.type === 'warranty'" :data="data.warrantyRows" border stripe>
        <el-table-column prop="name" label="资产名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="date" label="到期日期" width="130" />
        <el-table-column prop="days" label="剩余天数" width="110" />
        <el-table-column prop="status" label="状态" width="110" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
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
import { getTodoItems } from '../../api/todo'

const router = useRouter()
const statusRef = ref(null)
const categoryRef = ref(null)
const peopleRef = ref(null)
const purchaseScrapRef = ref(null)
const retirementTrendRef = ref(null)
const charts = []
let resizeTimer = null
const dashboardDateRange = ref([])
const dashboardLoading = ref(false)
const todos = ref([])
const detailDialog = reactive({ visible: false, type: 'status' })
const data = reactive({
  metrics: [],
  categoryDistribution: [],
  purchaseTrend: { months: [], amount: [], quantity: [] },
  scrapTrend: { months: [], submitted: [], approved: [] },
  retirementTrend: { months: [], due: [], overdue: 0 },
  lifecycleDistribution: [],
  retirementSoonAssets: [],
  maintenance: { top10: [], mttr: '0小时', monthCost: 0, yearCost: 0 },
  departmentDistribution: [],
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
const pendingScrapAssets = computed(() => lifecycleValue('待报废') + lifecycleValue('待处置登记'))
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
  card('待报废', pendingScrapAssets.value, '实时', 'up', 'orange', Delete, '含待处置登记'),
  card('即将过保', expiringAssets.value, '180天内', 'down', 'violet', Warning, '180天内')
])

const todoStats = computed(() => [
  { label: '全部待办', value: todos.value.length, tone: 'blue' },
  { label: '高优先级', value: todos.value.filter(item => item.priority === 'high').length, tone: 'red' },
  { label: '入职配置', value: todos.value.filter(item => item.type === 'onboarding_assign').length, tone: 'green' },
  { label: '回收/处置', value: todos.value.filter(item => ['offboarding_reclaim', 'scrap_disposal', 'scrap_request'].includes(item.type)).length, tone: 'orange' }
])

const topTodos = computed(() => {
  const priorityWeight = { high: 0, medium: 1, low: 2 }
  return [...todos.value]
    .sort((a, b) => (priorityWeight[a.priority] ?? 9) - (priorityWeight[b.priority] ?? 9))
    .slice(0, 5)
})

const actionCards = computed(() => [
  { label: '采购验收', value: lifecycleValue('待采购') + lifecycleValue('待验收'), caption: '采购单和待验收入库', path: '/purchase', tone: 'blue', icon: Files },
  { label: '借用登记', value: inUseAssets.value, caption: '员工资产流转', path: '/checkout', tone: 'green', icon: CircleCheck },
  { label: '维修跟进', value: repairAssets.value, caption: `费用 ¥${formatCompact(data.maintenance?.monthCost || 0)}`, path: '/repair', tone: 'purple', icon: Tools },
  { label: '报废处置', value: pendingScrapAssets.value, caption: '待报废和退役登记', path: '/scrap', tone: 'orange', icon: Delete }
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
const categoryDetailRows = computed(() => data.categoryDistribution.filter(item => Number(item.value || 0) > 0))
const categoryDetailTotal = computed(() => categoryDetailRows.value.reduce((sum, item) => sum + Number(item.value || 0), 0))
const personnelDetailRows = computed(() => {
  const trend = data.personnelTrend || {}
  return (trend.months || []).map((month, index) => ({
    month,
    onboarding: trend.onboarding?.[index] || 0,
    offboarding: trend.offboarding?.[index] || 0
  }))
})
const purchaseDetailRows = computed(() => {
  const purchase = data.purchaseTrend || {}
  const scrap = data.scrapTrend || {}
  return (purchase.months || scrap.months || []).map((month, index) => ({
    month,
    amount: purchase.amount?.[index] || 0,
    quantity: purchase.quantity?.[index] || 0,
    scrapApproved: scrap.approved?.[index] || 0
  }))
})
const retirementDetailRows = computed(() => data.retirementSoonAssets || [])
const lifecycleBars = computed(() => {
  const rows = (data.lifecycleDistribution || []).filter(item => Number(item.value || 0) > 0)
  const total = rows.reduce((sum, item) => sum + Number(item.value || 0), 0) || 1
  return rows.slice(0, 9).map((item, index) => ({
    ...item,
    percent: Math.max(4, Math.round((Number(item.value || 0) / total) * 100)),
    color: statusColors[index % statusColors.length]
  }))
})
const departmentTop = computed(() => (data.departmentDistribution || []).filter(item => Number(item.value || 0) > 0).slice(0, 6))
const maintenanceTop = computed(() => (data.maintenance?.top10 || []).filter(item => Number(item.count || 0) > 0).slice(0, 6))
const detailDialogTitle = computed(() => ({
  status: '资产状态分布详情',
  category: '资产分类占比详情',
  personnel: '入离职人员趋势详情',
  purchase: '采购和报废趋势详情',
  retirement: '待退役资产详情',
  recent: '最近借用 / 归还记录',
  warranty: '维保到期提醒详情'
})[detailDialog.type] || '详情')

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
  dashboardLoading.value = true
  try {
    const [dashboardResult, todoResult] = await Promise.allSettled([
      getEnterpriseDashboard({ dateRange: dashboardDateRange.value }),
      getTodoItems()
    ])
    if (dashboardResult.status === 'fulfilled') Object.assign(data, dashboardResult.value)
    if (todoResult.status === 'fulfilled') todos.value = todoResult.value
    await nextTick()
    renderCharts()
  } finally {
    dashboardLoading.value = false
  }
}

function clearDateRange() {
  dashboardDateRange.value = []
  load()
}

function openDashboardDialog(type) {
  detailDialog.type = type
  detailDialog.visible = true
}

function goPersonnel() {
  router.push('/personnel')
}

function goCheckout(row = null) {
  const keyword = row?.asset_id || row?.asset || ''
  router.push({ path: '/checkout', query: keyword ? { keyword } : {} })
}

function goPath(path, query = {}) {
  router.push({ path, query })
}

function goTodo(row) {
  router.push({ path: row.target_path || '/todo', query: row.target_query || {} })
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

function priorityLabel(priority) {
  return { high: '高', medium: '中', low: '低' }[priority] || '低'
}

function priorityType(priority) {
  return { high: 'danger', medium: 'warning', low: 'info' }[priority] || 'info'
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

.range-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid #d9e5f5;
  border-radius: 8px;
  background: #f7fbff;
  color: var(--muted);
  font-size: 13px;
  white-space: nowrap;
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

.operations-grid {
  display: grid;
  grid-template-columns: minmax(420px, 0.82fr) minmax(520px, 1.18fr);
  gap: 16px;
}

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

.insight-grid {
  grid-template-columns: minmax(420px, 1.1fr) minmax(280px, 0.7fr) minmax(280px, 0.7fr);
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

.panel-head p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.todo-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.todo-stat {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid #edf4ff;
  border-radius: 10px;
  background: #fff;
}

.todo-stat span {
  color: var(--muted);
  font-size: 12px;
}

.todo-stat strong {
  color: var(--text);
  font-size: 22px;
  line-height: 1;
}

.todo-stat.red strong { color: #dc2626; }
.todo-stat.orange strong { color: #d97706; }
.todo-stat.green strong { color: #16a34a; }

.todo-list {
  display: grid;
  gap: 8px;
}

.todo-row,
.action-card {
  width: 100%;
  border: 1px solid #edf2f8;
  border-radius: 10px;
  background: #fff;
  color: inherit;
  cursor: pointer;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.todo-row:hover,
.action-card:hover {
  border-color: #b7d4ff;
  box-shadow: 0 8px 20px rgba(36, 120, 255, 0.09);
  transform: translateY(-1px);
}

.todo-row {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  text-align: left;
}

.todo-row span:last-child,
.action-card span:last-of-type {
  display: grid;
  min-width: 0;
  gap: 4px;
}

.todo-row strong,
.action-card strong {
  overflow: hidden;
  color: var(--text);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-row small,
.action-card small {
  overflow: hidden;
  color: var(--muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.action-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  min-height: 84px;
  padding: 14px;
  text-align: left;
}

.action-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  font-size: 22px;
}

.action-icon.blue { color: #1975fc; background: #e5f2ff; }
.action-icon.green { color: #16a34a; background: #eaf8f0; }
.action-icon.purple { color: #7c3aed; background: #f1edff; }
.action-icon.orange { color: #d97706; background: #fff7e8; }

.action-card em {
  color: var(--text);
  font-style: normal;
  font-size: 22px;
  font-weight: 800;
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

.dialog-note {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.dashboard-detail-dialog :deep(.el-dialog__body) {
  max-height: 70vh;
  overflow: auto;
}

.clickable-table :deep(.el-table__row) {
  cursor: pointer;
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

.bar-list,
.rank-list {
  display: grid;
  gap: 12px;
}

.bar-row {
  display: grid;
  gap: 7px;
}

.bar-label,
.rank-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.bar-label span,
.rank-row span {
  min-width: 0;
  overflow: hidden;
  color: var(--muted);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-label strong,
.rank-row strong {
  color: var(--text);
  font-size: 14px;
}

.bar-track {
  height: 8px;
  overflow: hidden;
  border-radius: 99px;
  background: #edf3fb;
}

.bar-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.rank-row {
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid #edf2f8;
  border-radius: 10px;
  background: #fff;
}

.rank-row em {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  background: #eef4ff;
  color: #2478ff;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

@media (max-width: 1500px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(170px, 1fr));
  }

  .main-grid,
  .trend-grid,
  .lower-grid,
  .insight-grid {
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
  .operations-grid,
  .main-grid,
  .insight-grid,
  .trend-grid,
  .lower-grid,
  .donut-layout,
  .people-layout {
    grid-template-columns: 1fr;
  }

  .todo-summary,
  .action-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .people-panel {
    grid-column: auto;
  }
}

@media (max-width: 520px) {
  .dashboard-page {
    gap: 12px;
  }

  .panel,
  .dashboard-toolbar,
  .summary-card {
    padding: 14px;
    border-radius: 12px;
  }

  .summary-grid,
  .todo-summary,
  .action-grid {
    grid-template-columns: 1fr;
  }

  .toolbar-actions :deep(.el-date-editor) {
    width: 100%;
  }

  .donut-chart,
  .people-chart,
  .trend-chart {
    height: 220px;
  }
}
</style>
