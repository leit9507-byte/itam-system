<template>
  <div class="audit-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">审计中心</h2>
        <p class="page-subtitle">合并 AI 资产审计与风险分析，基于正式资产台账、采购数据和规则引擎生成风险结果</p>
      </div>
      <el-space>
        <el-button :icon="Document" @click="router.push('/report')">生成报告</el-button>
        <el-button type="primary" :icon="Refresh" :loading="loading" @click="handleRun">立即审计</el-button>
      </el-space>
    </div>

    <section class="summary-grid">
      <el-card shadow="never" class="score-card">
        <div class="score-body">
          <el-progress type="dashboard" :percentage="result?.risk_score || 0" :width="150" status="exception" />
          <div>
            <span class="meta-label">风险评分</span>
            <strong>{{ result?.risk_score || 0 }}</strong>
            <p>评分来自正式规则命中结果，满分 100 分封顶。</p>
          </div>
        </div>
      </el-card>

      <el-card v-for="item in summaryCards" :key="item.label" shadow="never" class="summary-card">
        <span class="meta-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <p>{{ item.hint }}</p>
      </el-card>
    </section>

    <section class="risk-section">
      <el-card shadow="never" class="risk-panel">
        <template #header>
          <div class="card-header">
            <span>风险分类</span>
            <el-tag type="info">正式数据</el-tag>
          </div>
        </template>
        <div class="risk-list">
          <button
            v-for="risk in result?.ai_risks || []"
            :key="risk.rule"
            class="risk-item"
            :class="{ active: activeRule === risk.rule }"
            type="button"
            @click="focusRule(risk.rule)"
          >
            <span class="risk-title">{{ risk.type }}</span>
            <el-tag :type="severityType(risk.severity)" size="small">{{ risk.level }}风险</el-tag>
            <strong>{{ risk.count }}</strong>
            <span class="risk-amount">涉及金额 ¥{{ formatValue(Math.round(risk.amount || 0)) }}</span>
            <small>{{ risk.action }}</small>
          </button>
        </div>
      </el-card>

      <div class="chart-stack">
        <el-card shadow="never">
          <template #header>本次风险评分</template>
          <div ref="scoreRef" class="chart compact-chart" />
        </el-card>
        <el-card shadow="never">
          <template #header>库存与闲置结构</template>
          <div ref="idleRef" class="chart compact-chart" />
        </el-card>
      </div>
    </section>

    <section class="analysis-section">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>风险分析</span>
            <el-tag type="warning">已合并到审计中心</el-tag>
          </div>
        </template>
        <div class="analysis-grid">
          <div ref="trendRef" class="chart" />
          <div ref="deptRef" class="chart" />
        </div>
      </el-card>
    </section>

    <section class="detail-grid">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>规则命中矩阵</span>
            <el-tag type="success">已启用</el-tag>
          </div>
        </template>
        <el-table :data="result?.rules || []" border>
          <el-table-column prop="name" label="规则名称" min-width="180" />
          <el-table-column prop="severity" label="等级" width="90">
            <template #default="{ row }">
              <el-tag :type="row.severity === '高' ? 'danger' : row.severity === '中' ? 'warning' : 'info'">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="hits" label="命中数" width="90" />
          <el-table-column prop="enabled" label="启用" width="90">
            <template #default="{ row }"><el-switch v-model="row.enabled" disabled /></template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never">
        <template #header>处置建议</template>
        <el-space direction="vertical" alignment="stretch" class="suggestions">
          <el-alert v-for="item in result?.suggestions || []" :key="item" :title="item" type="info" show-icon :closable="false" />
        </el-space>
      </el-card>
    </section>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>违规资产明细</span>
          <div class="table-tools">
            <el-segmented v-model="severityFilter" :options="severityOptions" />
            <el-button text @click="clearRule">全部规则</el-button>
          </div>
        </div>
      </template>
      <el-table :data="filteredViolations" border stripe empty-text="当前正式数据暂无规则违规记录">
        <el-table-column prop="asset_id" label="资产ID" width="130" />
        <el-table-column prop="asset_name" label="资产名称" min-width="160" />
        <el-table-column prop="type" label="风险类型" min-width="160" />
        <el-table-column prop="severity" label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)">{{ severityLabel(row.severity) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="dept" label="部门" width="120" />
        <el-table-column prop="owner" label="责任人" width="120" />
        <el-table-column prop="price" label="金额" width="130">
          <template #default="{ row }">¥{{ formatValue(row.price) }}</template>
        </el-table-column>
        <el-table-column prop="message" label="说明" min-width="240" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="router.push(`/asset/detail/${row.asset_id}`)">资产详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { runAudit } from '../../api/audit'

const router = useRouter()
const loading = ref(false)
const result = ref(null)
const severityFilter = ref('全部')
const activeRule = ref('')
const severityOptions = ['全部', '高', '中', '低']
const scoreRef = ref(null)
const trendRef = ref(null)
const deptRef = ref(null)
const idleRef = ref(null)
const charts = []

const summaryCards = computed(() => [
  { label: '资产健康分', value: result.value?.health_score || 0, hint: '100 - 风险评分' },
  { label: '规则命中数', value: result.value?.violations?.length || 0, hint: `共审计 ${result.value?.total_assets || 0} 项资产` },
  { label: '涉及金额', value: `¥${formatValue(Math.round(result.value?.involved_amount || 0))}`, hint: '按当前风险资产原值汇总' }
])

const filteredViolations = computed(() => {
  let rows = result.value?.violations || []
  if (activeRule.value) rows = rows.filter(item => item.rule === activeRule.value)
  if (severityFilter.value === '全部') return rows
  const target = { 高: 'high', 中: 'medium', 低: 'low' }[severityFilter.value]
  return rows.filter(item => item.severity === target)
})

onMounted(handleRun)
onUnmounted(() => charts.forEach(chart => chart.dispose()))

async function handleRun() {
  loading.value = true
  try {
    result.value = await runAudit()
    await nextTick()
    renderCharts()
    ElMessage.success('资产审计已完成')
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  charts.forEach(chart => chart.dispose())
  charts.length = 0
  if (!result.value) return

  const riskTrend = result.value.riskTrend?.length ? result.value.riskTrend : [{ name: '本次审计', value: result.value.risk_score || 0 }]
  const deptRows = result.value.deptRank?.length ? result.value.deptRank : [{ dept: '暂无风险', score: 0 }]

  const score = echarts.init(scoreRef.value)
  score.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 34, right: 16, top: 20, bottom: 28 },
    xAxis: { type: 'category', data: riskTrend.map(item => item.name) },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{ name: '风险评分', type: 'bar', barWidth: 42, data: riskTrend.map(item => item.value), itemStyle: { color: '#dc2626', borderRadius: [4, 4, 0, 0] } }]
  })

  const idle = echarts.init(idleRef.value)
  idle.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{ type: 'pie', radius: ['45%', '70%'], center: ['50%', '44%'], data: result.value.idleStats }]
  })

  const trend = echarts.init(trendRef.value)
  trend.setOption({
    title: { text: '风险趋势', left: 8, top: 0, textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 18, top: 48, bottom: 30 },
    xAxis: { type: 'category', data: riskTrend.map(item => item.name) },
    yAxis: { type: 'value', max: 100 },
    series: [{ name: '风险评分', type: 'line', smooth: true, areaStyle: {}, data: riskTrend.map(item => item.value), itemStyle: { color: '#b45309' } }]
  })

  const dept = echarts.init(deptRef.value)
  dept.setOption({
    title: { text: '部门风险排行', left: 8, top: 0, textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 78, right: 18, top: 48, bottom: 24 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: deptRows.map(item => item.dept) },
    series: [{ name: '风险分', type: 'bar', data: deptRows.map(item => item.score), itemStyle: { color: '#b45309', borderRadius: [0, 4, 4, 0] } }]
  })

  charts.push(score, idle, trend, dept)
}

function focusRule(rule) {
  activeRule.value = activeRule.value === rule ? '' : rule
}

function clearRule() {
  activeRule.value = ''
}

function formatValue(value) {
  return Number(value || 0).toLocaleString()
}

function severityType(severity) {
  return severity === 'high' ? 'danger' : severity === 'medium' ? 'warning' : 'success'
}

function severityLabel(severity) {
  return ({ high: '高', medium: '中', low: '低' })[severity] || severity
}
</script>

<style scoped>
.audit-page {
  display: grid;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1.35fr repeat(3, minmax(180px, 1fr));
  gap: 12px;
}

.score-body {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  align-items: center;
  gap: 16px;
}

.summary-card :deep(.el-card__body) {
  display: grid;
  align-content: center;
  min-height: 128px;
  gap: 8px;
}

.score-body strong,
.summary-card strong {
  display: block;
  font-size: 34px;
  line-height: 1.1;
}

.score-body p,
.summary-card p,
.risk-item small,
.risk-amount,
.meta-label {
  color: var(--muted);
}

.score-body p,
.summary-card p {
  margin: 0;
  line-height: 1.6;
}

.risk-section {
  display: grid;
  grid-template-columns: minmax(460px, 1.2fr) minmax(360px, 0.8fr);
  gap: 16px;
}

.risk-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 12px;
}

.risk-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 12px;
  align-items: center;
  width: 100%;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.risk-item:hover,
.risk-item.active {
  border-color: var(--primary);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.risk-title {
  font-weight: 700;
}

.risk-item strong {
  grid-column: 1 / 2;
  font-size: 30px;
  line-height: 1;
}

.risk-amount,
.risk-item small {
  grid-column: 1 / -1;
}

.chart-stack,
.detail-grid,
.analysis-grid {
  display: grid;
  gap: 16px;
}

.detail-grid,
.analysis-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart {
  width: 100%;
  height: 280px;
}

.compact-chart {
  height: 218px;
}

.card-header,
.table-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.table-tools {
  justify-content: flex-end;
}

.suggestions {
  width: 100%;
}

@media (max-width: 1280px) {
  .summary-grid,
  .risk-section,
  .detail-grid,
  .analysis-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .risk-list,
  .score-body,
  .card-header,
  .table-tools {
    grid-template-columns: 1fr;
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
