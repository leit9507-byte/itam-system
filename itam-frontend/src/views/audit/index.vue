<template>
  <div class="audit-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">审计中心</h2>
        <p class="page-subtitle">按人员和资产两个维度审计正式资产数据，输出风险评分、规则命中和处置建议</p>
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
            <p>评分由启用规则的命中结果生成，最高 100 分。</p>
          </div>
        </div>
      </el-card>

      <el-card v-for="item in summaryCards" :key="item.label" shadow="never" class="summary-card">
        <span class="meta-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <p>{{ item.hint }}</p>
      </el-card>
    </section>

    <el-tabs v-model="activeScope" class="audit-tabs">
      <el-tab-pane label="人员审计" name="person">
        <section class="risk-grid">
          <button
            v-for="risk in result?.person_risks || []"
            :key="risk.rule"
            type="button"
            class="risk-card"
            :class="{ active: activeRule === risk.rule }"
            @click="focusRule(risk.rule)"
          >
            <div class="risk-card-head">
              <span>{{ risk.type }}</span>
              <el-tag :type="severityType(risk.severity)" size="small">{{ risk.level }}风险</el-tag>
            </div>
            <strong>{{ risk.count }}</strong>
            <span>涉及金额 ￥{{ formatValue(Math.round(risk.amount || 0)) }}</span>
            <small>{{ risk.action }}</small>
          </button>
        </section>
      </el-tab-pane>

      <el-tab-pane label="资产审计" name="asset">
        <section class="risk-grid asset-risk-grid">
          <button
            v-for="risk in result?.asset_risks || []"
            :key="risk.rule"
            type="button"
            class="risk-card"
            :class="{ active: activeRule === risk.rule }"
            @click="focusRule(risk.rule)"
          >
            <div class="risk-card-head">
              <span>{{ risk.type }}</span>
              <el-tag :type="severityType(risk.severity)" size="small">{{ risk.level }}风险</el-tag>
            </div>
            <strong>{{ risk.count }}</strong>
            <span>涉及金额 ￥{{ formatValue(Math.round(risk.amount || 0)) }}</span>
            <small>{{ risk.action }}</small>
          </button>
        </section>
      </el-tab-pane>
    </el-tabs>

    <section class="detail-grid">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>规则命中矩阵</span>
            <el-button text type="primary" @click="openRules">调整规则</el-button>
          </div>
        </template>
        <el-table :data="scopedRules" border>
          <el-table-column prop="name" label="规则名称" min-width="170" />
          <el-table-column prop="audit_scope" label="审计对象" width="100">
            <template #default="{ row }">{{ scopeLabel(row.audit_scope) }}</template>
          </el-table-column>
          <el-table-column prop="scope_category" label="设备类型" width="130">
            <template #default="{ row }">{{ row.scope_category || '全部' }}</template>
          </el-table-column>
          <el-table-column label="阈值" width="140">
            <template #default="{ row }">{{ ruleThreshold(row) }}</template>
          </el-table-column>
          <el-table-column prop="severity_label" label="等级" width="90">
            <template #default="{ row }">
              <el-tag :type="severityType(row.severity)">{{ row.severity_label || severityLabel(row.severity) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="hits" label="命中数" width="90" />
        </el-table>
      </el-card>

      <div class="chart-stack">
        <el-card shadow="never">
          <template #header>风险评分</template>
          <div ref="scoreRef" class="chart compact-chart" />
        </el-card>
        <el-card shadow="never">
          <template #header>库存、闲置与借出结构</template>
          <div ref="idleRef" class="chart compact-chart" />
        </el-card>
      </div>
    </section>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ scopeLabel(activeScope) }}明细</span>
          <div class="table-tools">
            <el-segmented v-model="severityFilter" :options="severityOptions" />
            <el-button text @click="clearRule">全部规则</el-button>
          </div>
        </div>
      </template>
      <el-table :data="filteredViolations" border stripe empty-text="当前正式数据暂无规则命中记录">
        <el-table-column prop="asset_id" label="资产ID" width="130" />
        <el-table-column prop="asset_name" label="资产名称" min-width="160" />
        <el-table-column prop="type" label="风险类型" min-width="150" />
        <el-table-column prop="severity" label="等级" width="90">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)">{{ severityLabel(row.severity) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner" label="责任人" width="140" />
        <el-table-column prop="dept" label="部门" width="140" />
        <el-table-column prop="price" label="金额" width="130">
          <template #default="{ row }">￥{{ formatValue(row.price) }}</template>
        </el-table-column>
        <el-table-column prop="message" label="说明" min-width="280" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="router.push(`/asset/detail/${row.asset_id}`)">资产详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>处置建议</template>
      <el-space direction="vertical" alignment="stretch" class="suggestions">
        <el-alert v-for="item in result?.suggestions || []" :key="item" :title="item" type="info" show-icon :closable="false" />
      </el-space>
    </el-card>

    <el-drawer v-model="rulesDrawer.visible" title="审计规则设置" size="900px">
      <div class="rule-help">
        <strong>规则说明：</strong>
        人员审计用于检查人员配置标准、离职回收和借用回收；资产审计用于检查采购价值和闲置复用。
      </div>
      <el-table :data="rulesDrawer.rules" border>
        <el-table-column prop="name" label="规则" min-width="170" />
        <el-table-column prop="audit_scope" label="对象" width="90">
          <template #default="{ row }">{{ scopeLabel(row.audit_scope) }}</template>
        </el-table-column>
        <el-table-column label="启用" width="76">
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
        <el-table-column label="天数阈值" width="130">
          <template #default="{ row }">
            <el-input-number
              v-if="usesDayThreshold(row.rule_code)"
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
const activeScope = ref('person')
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
  { label: '人员审计命中', value: result.value?.violations?.filter(item => item.audit_scope === 'person').length || 0, hint: '超配、离职、借用回收' },
  { label: '资产审计命中', value: result.value?.violations?.filter(item => item.audit_scope === 'asset').length || 0, hint: '超价值采购、长期闲置' },
  { label: '涉及金额', value: `￥${formatValue(Math.round(result.value?.involved_amount || 0))}`, hint: '按命中资产原值汇总' }
])

const scopedRules = computed(() => (result.value?.rules || []).filter(item => (item.audit_scope || 'asset') === activeScope.value))

const filteredViolations = computed(() => {
  let rows = (result.value?.violations || []).filter(item => (item.audit_scope || 'asset') === activeScope.value)
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
  return ['USER_ASSET_COUNT_LIMIT', 'HIGH_VALUE_PURCHASE', 'SINGLE_OWNER_VALUE_LIMIT'].includes(ruleCode)
}

function usesDayThreshold(ruleCode) {
  return ['ASSET_IDLE_OVER_90_DAYS', 'BORROWED_ASSET_NOT_RETURNED'].includes(ruleCode)
}

function ruleThreshold(row) {
  if (usesDayThreshold(row.rule_code)) return `${row.threshold_days || 0} 天`
  if (row.rule_code === 'USER_ASSET_COUNT_LIMIT') return `${row.threshold_value || 0} 台`
  if (row.threshold_value) return `￥${formatValue(row.threshold_value)}`
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

function scopeLabel(scope) {
  return scope === 'person' ? '人员审计' : '资产审计'
}
</script>

<style scoped>
.audit-page {
  display: grid;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1.35fr repeat(4, minmax(150px, 1fr));
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
  font-size: 32px;
  line-height: 1.1;
}

.score-body p,
.summary-card p,
.risk-card small,
.risk-card span,
.meta-label,
.muted {
  color: var(--muted);
}

.score-body p,
.summary-card p {
  margin: 0;
  line-height: 1.6;
}

.audit-tabs :deep(.el-tabs__content) {
  overflow: visible;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(220px, 1fr));
  gap: 12px;
}

.asset-risk-grid {
  grid-template-columns: repeat(2, minmax(260px, 1fr));
}

.risk-card {
  display: grid;
  gap: 10px;
  width: 100%;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.risk-card:hover,
.risk-card.active {
  border-color: var(--primary);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.risk-card-head,
.card-header,
.table-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.risk-card-head span {
  color: var(--text);
  font-weight: 700;
}

.risk-card strong {
  font-size: 34px;
  line-height: 1;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(360px, 0.8fr);
  gap: 16px;
}

.chart-stack {
  display: grid;
  gap: 16px;
}

.chart {
  width: 100%;
  height: 260px;
}

.compact-chart {
  height: 210px;
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
  .risk-grid,
  .asset-risk-grid,
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .score-body,
  .card-header,
  .table-tools {
    grid-template-columns: 1fr;
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
