<template>
  <div class="audit-workbench">
    <div class="page-header">
      <div>
        <h2 class="page-title">AI资产审计中心</h2>
        <p class="page-subtitle">集中处理超配、闲置、离职未归还、即将报废和异常采购风险</p>
      </div>
      <el-space>
        <el-button @click="router.push('/report')">生成报告</el-button>
        <el-button type="primary" :loading="loading" @click="handleRun">立即审计</el-button>
      </el-space>
    </div>

    <section class="audit-summary">
      <el-card shadow="never" class="score-card">
        <div class="score-ring">
          <el-progress type="dashboard" :percentage="result?.risk_score || 0" :width="164" status="exception" />
          <span>风险评分</span>
        </div>
        <div class="score-copy">
          <strong>{{ result?.health_score || 0 }}</strong>
          <span>资产健康分</span>
          <p>共审计 {{ result?.total_assets || 0 }} 项资产，发现 {{ result?.violations?.length || 0 }} 条规则命中。</p>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>风险趋势</template>
        <div ref="trendRef" class="chart small-chart" />
      </el-card>

      <el-card shadow="never">
        <template #header>部门风险排行</template>
        <div ref="deptRef" class="chart small-chart" />
      </el-card>
    </section>

    <section class="risk-grid">
      <el-card v-for="risk in result?.ai_risks || []" :key="risk.type" shadow="never" class="risk-card">
        <div class="risk-head">
          <strong>{{ risk.type }}</strong>
          <el-tag :type="risk.level === '高' ? 'danger' : 'warning'">{{ risk.level }}风险</el-tag>
        </div>
        <div class="risk-numbers">
          <div>
            <span>数量</span>
            <b>{{ risk.count }}</b>
          </div>
          <div>
            <span>涉及金额</span>
            <b>￥{{ formatValue(Math.round(risk.amount || 0)) }}</b>
          </div>
        </div>
        <p>{{ risk.action }}</p>
        <el-button type="primary" link @click="focusRule(risk.rule)">查看详情</el-button>
      </el-card>
    </section>

    <section class="audit-main">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>审计规则矩阵</span>
            <el-tag type="info">AI + 规则引擎</el-tag>
          </div>
        </template>
        <el-table :data="result?.rules || []" border>
          <el-table-column prop="name" label="规则名称" min-width="180" />
          <el-table-column prop="severity" label="等级" width="90">
            <template #default="{ row }">
              <el-tag :type="row.severity === '高' ? 'danger' : 'warning'">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="hits" label="命中数" width="90" />
          <el-table-column prop="enabled" label="启用" width="90">
            <template #default="{ row }"><el-switch v-model="row.enabled" disabled /></template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>违规资产明细</span>
            <el-segmented v-model="severityFilter" :options="severityOptions" />
          </div>
        </template>
        <el-table :data="filteredViolations" border stripe>
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
          <el-table-column prop="price" label="金额" width="120">
            <template #default="{ row }">￥{{ formatValue(row.price) }}</template>
          </el-table-column>
          <el-table-column prop="message" label="说明" min-width="220" />
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="router.push(`/asset/detail/${row.asset_id}`)">资产详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>

    <section class="bottom-grid">
      <el-card shadow="never">
        <template #header>闲置资产账龄</template>
        <div ref="idleRef" class="chart small-chart" />
      </el-card>

      <el-card shadow="never">
        <template #header>处置建议</template>
        <el-space direction="vertical" alignment="stretch" style="width: 100%">
          <el-alert v-for="item in result?.suggestions || []" :key="item" :title="item" type="info" show-icon :closable="false" />
        </el-space>
      </el-card>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { runAudit } from '../../api/audit'

const router = useRouter()
const loading = ref(false)
const result = ref(null)
const severityFilter = ref('全部')
const severityOptions = ['全部', '高', '中', '低']
const trendRef = ref(null)
const deptRef = ref(null)
const idleRef = ref(null)
const charts = []

const filteredViolations = computed(() => {
  const rows = result.value?.violations || []
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
    ElMessage.success('AI资产审计已完成')
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  charts.forEach(chart => chart.dispose())
  charts.length = 0
  if (!result.value) return

  const trend = echarts.init(trendRef.value)
  trend.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 34, right: 16, top: 20, bottom: 28 },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '本月', '预测'] },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{ name: '风险评分', type: 'line', smooth: true, areaStyle: {}, data: result.value.trend, itemStyle: { color: '#c2410c' } }]
  })

  const dept = echarts.init(deptRef.value)
  dept.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 70, right: 18, top: 20, bottom: 24 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: result.value.deptRank.map(item => item.dept) },
    series: [{ name: '风险分', type: 'bar', data: result.value.deptRank.map(item => item.score), itemStyle: { color: '#b7791f', borderRadius: [0, 4, 4, 0] } }]
  })

  const idle = echarts.init(idleRef.value)
  idle.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{ type: 'pie', radius: ['45%', '70%'], center: ['50%', '44%'], data: result.value.idleStats }]
  })

  charts.push(trend, dept, idle)
}

function focusRule(rule) {
  const matched = result.value?.violations?.find(item => item.rule === rule)
  severityFilter.value = matched ? severityLabel(matched.severity) : '全部'
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
.audit-workbench {
  display: grid;
  gap: 16px;
}

.audit-summary {
  display: grid;
  grid-template-columns: 1.1fr 1fr 1fr;
  gap: 16px;
}

.score-card {
  display: grid;
  align-items: center;
}

.score-card :deep(.el-card__body) {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  align-items: center;
  gap: 18px;
}

.score-ring {
  display: grid;
  justify-items: center;
  gap: 6px;
  color: var(--muted);
}

.score-copy strong {
  display: block;
  font-size: 42px;
  line-height: 1;
}

.score-copy span,
.risk-numbers span {
  color: var(--muted);
  font-size: 13px;
}

.score-copy p,
.risk-card p {
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.chart {
  width: 100%;
  height: 320px;
}

.small-chart {
  height: 240px;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(160px, 1fr));
  gap: 12px;
}

.risk-card {
  border-color: #f1c2aa;
}

.risk-head,
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.risk-numbers {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.risk-numbers div {
  display: grid;
  gap: 4px;
}

.risk-numbers b {
  font-size: 22px;
}

.audit-main {
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  gap: 16px;
}

.bottom-grid {
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  gap: 16px;
}

@media (max-width: 1320px) {
  .audit-summary,
  .audit-main,
  .bottom-grid {
    grid-template-columns: 1fr;
  }

  .risk-grid {
    grid-template-columns: repeat(2, minmax(180px, 1fr));
  }
}

@media (max-width: 760px) {
  .risk-grid,
  .score-card :deep(.el-card__body) {
    grid-template-columns: 1fr;
  }
}
</style>
