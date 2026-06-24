<template>
  <div class="audit-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">审计中心</h2>
        <p class="page-subtitle">基于正式资产、采购和规则配置生成风险评分、命中明细与处置建议</p>
      </div>
      <el-space>
        <el-button :icon="Setting" @click="openRules">规则设置</el-button>
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
            <p>评分来自当前启用规则的命中结果，最高 100 分。</p>
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

    <section class="detail-grid">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>规则命中矩阵</span>
            <el-button text type="primary" @click="openRules">调整规则</el-button>
          </div>
        </template>
        <el-table :data="result?.rules || []" border>
          <el-table-column prop="name" label="规则名称" min-width="170" />
          <el-table-column prop="scope_category" label="设备类型" width="130">
            <template #default="{ row }">{{ row.scope_category || '全部' }}</template>
          </el-table-column>
          <el-table-column label="阈值" width="130">
            <template #default="{ row }">{{ ruleThreshold(row) }}</template>
          </el-table-column>
          <el-table-column prop="severity_label" label="等级" width="90">
            <template #default="{ row }">
              <el-tag :type="severityType(row.severity)">{{ row.severity_label || severityLabel(row.severity) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="hits" label="命中数" width="90" />
          <el-table-column prop="enabled" label="启用" width="80">
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
        <el-table-column prop="message" label="说明" min-width="260" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="router.push(`/asset/detail/${row.asset_id}`)">资产详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer v-model="rulesDrawer.visible" title="审计规则设置" size="780px">
      <div class="rule-help">
        <strong>用户资产超限示例：</strong>
        选择“笔记本电脑”，数量阈值填 2，表示同一用户名下笔记本电脑超过 2 台即命中规则。
      </div>
      <el-table :data="rulesDrawer.rules" border>
        <el-table-column prop="name" label="规则" min-width="160" />
        <el-table-column label="启用" width="72">
          <template #default="{ row }"><el-switch v-model="row.enabled" /></template>
        </el-table-column>
        <el-table-column label="等级" width="110">
          <template #default="{ row }">
            <el-select v-model="row.severity" size="small">
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="设备类型" min-width="150">
          <template #default="{ row }">
            <el-select v-model="row.scope_category" clearable filterable size="small" placeholder="全部">
              <el-option label="全部" value="" />
              <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="数量/金额阈值" width="150">
          <template #default="{ row }">
            <el-input-number
              v-if="usesValueThreshold(row.rule_code)"
              v-model="row.threshold_value"
              :min="1"
              :precision="0"
              size="small"
              controls-position="right"
              class="rule-number"
            />
            <span v-else class="muted">不适用</span>
          </template>
        </el-table-column>
        <el-table-column label="闲置天数" width="130">
          <template #default="{ row }">
            <el-input-number
              v-if="row.rule_code === 'ASSET_IDLE_OVER_90_DAYS'"
              v-model="row.threshold_days"
              :min="1"
              :precision="0"
              size="small"
              controls-position="right"
              class="rule-number"
            />
            <span v-else class="muted">不适用</span>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-space>
          <el-button @click="rulesDrawer.visible = false">取消</el-button>
          <el-button type="primary" :loading="rulesDrawer.saving" @click="saveRules">保存并重新审计</el-button>
        </el-space>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, Refresh, Setting } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getAuditRules, runAudit, saveAuditRules } from '../../api/audit'
import { getDeviceTypes } from '../../api/product'

const router = useRouter()
const loading = ref(false)
const result = ref(null)
const severityFilter = ref('全部')
const activeRule = ref('')
const severityOptions = ['全部', '高', '中', '低']
const categories = ref([])
const scoreRef = ref(null)
const idleRef = ref(null)
const charts = []
const rulesDrawer = reactive({ visible: false, saving: false, rules: [] })

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

onMounted(async () => {
  await Promise.all([loadCategories(), handleRun()])
})
onUnmounted(() => charts.forEach(chart => chart.dispose()))

async function loadCategories() {
  const rows = await getDeviceTypes().catch(() => [])
  categories.value = rows.map(item => item.name)
}

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

async function openRules() {
  rulesDrawer.rules = (await getAuditRules()).map(item => ({ ...item }))
  rulesDrawer.visible = true
}

async function saveRules() {
  rulesDrawer.saving = true
  try {
    await saveAuditRules(rulesDrawer.rules)
    rulesDrawer.visible = false
    ElMessage.success('规则已保存')
    await handleRun()
  } finally {
    rulesDrawer.saving = false
  }
}

function renderCharts() {
  charts.forEach(chart => chart.dispose())
  charts.length = 0
  if (!result.value || !scoreRef.value || !idleRef.value) return

  const riskTrend = result.value.riskTrend?.length ? result.value.riskTrend : [{ name: '本次审计', value: result.value.risk_score || 0 }]

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

  charts.push(score, idle)
}

function usesValueThreshold(ruleCode) {
  return ['USER_ASSET_COUNT_LIMIT', 'HIGH_VALUE_WITHOUT_DEPT', 'SINGLE_OWNER_VALUE_LIMIT'].includes(ruleCode)
}

function ruleThreshold(row) {
  if (row.rule_code === 'ASSET_IDLE_OVER_90_DAYS') return `${row.threshold_days || 0} 天`
  if (row.rule_code === 'USER_ASSET_COUNT_LIMIT') return `${row.threshold_value || 0} 台`
  if (row.threshold_value) return `¥${formatValue(row.threshold_value)}`
  return '-'
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
.meta-label,
.muted {
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
.detail-grid {
  display: grid;
  gap: 16px;
}

.detail-grid {
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

.rule-help {
  padding: 12px 14px;
  margin-bottom: 14px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #eff6ff;
  color: #1e3a8a;
  line-height: 1.7;
}

.rule-number {
  width: 112px;
}

@media (max-width: 1280px) {
  .summary-grid,
  .risk-section,
  .detail-grid {
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
