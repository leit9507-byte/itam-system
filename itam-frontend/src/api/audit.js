import request from '../utils/request'
import { getAssets } from './asset'
import { getPurchases } from './purchase'

const ruleLabels = {
  USER_ASSET_COUNT_LIMIT: '用户资产数量超限',
  ASSET_IDLE_OVER_90_DAYS: '资产闲置超期',
  HIGH_VALUE_WITHOUT_DEPT: '高价值资产未绑定部门',
  SINGLE_OWNER_VALUE_LIMIT: '单人资产价值超标',
  MISSING_RETURN_ON_OFFBOARDING: '离职未归还资产',
  PENDING_SCRAP: '即将报废资产',
  ABNORMAL_PURCHASE: '异常采购资产'
}

const severityLabels = {
  high: '高',
  medium: '中',
  low: '低'
}

export function getAuditRules() {
  return request.get('/audit/rules')
}

export function saveAuditRules(rules) {
  return request.post('/audit/rules', rules)
}

export async function runAudit() {
  const [{ list: assets }, purchases, backend, rules] = await Promise.all([
    getAssets({}),
    getPurchases().catch(() => []),
    request.post('/audit/run', { users: [] }).catch(() => null),
    getAuditRules().catch(() => [])
  ])

  const violations = normalizeViolations(backend?.violations || [], assets)
  const aiRisks = buildAiRisks(assets, purchases, violations)
  const riskScore = Math.min(100, backend?.risk_score ?? scoreFromRisks(aiRisks, violations))
  const involvedAmount = aiRisks.reduce((sum, item) => sum + Number(item.amount || 0), 0)

  return {
    total_assets: backend?.total_assets ?? assets.length,
    risk_score: riskScore,
    health_score: Math.max(0, 100 - riskScore),
    involved_amount: involvedAmount,
    violations,
    ai_risks: aiRisks,
    rules: buildRules(violations, aiRisks, rules),
    suggestions: buildSuggestions(aiRisks, violations, backend?.suggestions || []),
    riskTrend: [{ name: '本次审计', value: riskScore }],
    deptRank: buildDeptRank(assets, violations, aiRisks),
    idleStats: buildIdleStats(assets)
  }
}

export async function getRiskAnalytics() {
  const result = await runAudit()
  return {
    trend: result.riskTrend,
    deptRank: result.deptRank,
    idleStats: result.idleStats
  }
}

export function getReports() {
  return Promise.resolve([
    { id: 'R20260601', name: '6月资产审计报告', type: '审计报告', status: '已生成', created_at: '2026-06-01' },
    { id: 'R20260501', name: '5月风险分析报告', type: '风险报告', status: '已归档', created_at: '2026-05-01' }
  ])
}

export function generateReport() {
  return runAudit().then(result => ({
    id: `R${Date.now()}`,
    name: '即时审计报告',
    html: `
      <h2>ITAM 资产审计报告</h2>
      <p>本报告基于当前正式资产台账、采购单和后端规则引擎生成。</p>
      <p>总资产：${result.total_assets}，风险评分：${result.risk_score}，规则命中：${result.violations.length}</p>
      <ul>
        ${result.suggestions.map(item => `<li>${item}</li>`).join('')}
      </ul>
    `
  }))
}

function normalizeViolations(rows, assets) {
  return rows.map(row => {
    const asset = assets.find(item => item.asset_id === row.asset_id)
    const rule = row.rule || row.type || 'UNKNOWN_RULE'
    return {
      asset_id: row.asset_id,
      asset_name: asset?.name || '-',
      dept: asset?.dept || '未绑定',
      owner: asset?.owner || '未分配',
      price: Number(asset?.price || 0),
      rule,
      type: ruleLabels[rule] || row.type || rule,
      severity: row.severity || 'medium',
      severity_label: severityLabels[row.severity] || row.severity || '中',
      message: row.message || '发现资产合规风险'
    }
  })
}

function buildAiRisks(assets, purchases, violations) {
  const highValueAssets = assets.filter(item => Number(item.price || 0) >= 50000)
  const idleAssets = assets.filter(item => item.status === 'idle')
  const missingOwnerAssets = assets.filter(item => item.status === 'in_use' && !item.owner)
  const pendingScrapAssets = assets.filter(item => item.status === 'pending_scrap')
  const abnormalPurchases = purchases.filter(item => {
    const hasAmount = Number(item.total_amount || 0) > 0
    const hasItems = Array.isArray(item.items) && item.items.length > 0
    const hasHighUnitPrice = (item.items || []).some(product => Number(product.unit_price || 0) >= 50000)
    return (hasAmount && !hasItems) || hasHighUnitPrice
  })

  return [
    {
      type: '超标准配置资产',
      count: Math.max(highValueAssets.length, countRule(violations, 'HIGH_VALUE_WITHOUT_DEPT')),
      level: '高',
      severity: 'high',
      amount: sumValue(highValueAssets),
      rule: 'HIGH_VALUE_WITHOUT_DEPT',
      action: '复核配置标准、采购审批和部门归属'
    },
    {
      type: '长期闲置资产',
      count: Math.max(idleAssets.length, countRule(violations, 'ASSET_IDLE_OVER_90_DAYS')),
      level: '中',
      severity: 'medium',
      amount: sumValue(idleAssets),
      rule: 'ASSET_IDLE_OVER_90_DAYS',
      action: '发起调拨、回收或报废流程'
    },
    {
      type: '离职未归还资产',
      count: missingOwnerAssets.length,
      level: '高',
      severity: 'high',
      amount: sumValue(missingOwnerAssets),
      rule: 'MISSING_RETURN_ON_OFFBOARDING',
      action: '接入用户离职状态后自动核对归还记录'
    },
    {
      type: '即将报废资产',
      count: pendingScrapAssets.length,
      level: '中',
      severity: 'medium',
      amount: sumValue(pendingScrapAssets),
      rule: 'PENDING_SCRAP',
      action: '推进报废审批和处置归档'
    },
    {
      type: '异常采购资产',
      count: abnormalPurchases.length,
      level: '高',
      severity: 'high',
      amount: abnormalPurchases.reduce((sum, item) => sum + Number(item.total_amount || 0), 0),
      rule: 'ABNORMAL_PURCHASE',
      action: '复核采购单价、明细完整性和审批单号'
    }
  ]
}

function buildRules(violations, aiRisks, savedRules) {
  const baseRules = savedRules?.length
    ? savedRules
    : [
        { rule_code: 'USER_ASSET_COUNT_LIMIT', name: '用户资产数量超限', severity: 'medium', enabled: true },
        { rule_code: 'ASSET_IDLE_OVER_90_DAYS', name: '资产闲置超期', severity: 'low', enabled: true },
        { rule_code: 'HIGH_VALUE_WITHOUT_DEPT', name: '高价值资产未绑定部门', severity: 'high', enabled: true },
        { rule_code: 'SINGLE_OWNER_VALUE_LIMIT', name: '单人资产价值超标', severity: 'high', enabled: true }
      ]

  return baseRules.map(rule => {
    const key = rule.rule_code || rule.key
    const risk = aiRisks.find(item => item.rule === key)
    return {
      ...rule,
      key,
      name: rule.name || ruleLabels[key] || key,
      severity_label: severityLabels[rule.severity] || rule.severity,
      hits: Math.max(countRule(violations, key), risk?.count || 0)
    }
  })
}

function buildSuggestions(aiRisks, violations, backendSuggestions) {
  const suggestions = []
  const addWhen = (rule, text) => {
    if ((aiRisks.find(item => item.rule === rule)?.count || 0) > 0 || countRule(violations, rule) > 0) suggestions.push(text)
  }

  addWhen('HIGH_VALUE_WITHOUT_DEPT', '高价值或超标准资产建议补齐部门、责任人和审批依据。')
  addWhen('ASSET_IDLE_OVER_90_DAYS', '长期闲置资产建议生成调拨、回收或报废待办。')
  addWhen('MISSING_RETURN_ON_OFFBOARDING', '离职未归还风险需要接入用户离职状态后联动归还流程。')
  addWhen('PENDING_SCRAP', '待报废资产建议补齐审批记录、残值和处置方式。')
  addWhen('ABNORMAL_PURCHASE', '异常采购资产建议复核供应商、采购单价和审批单号。')
  addWhen('USER_ASSET_COUNT_LIMIT', '用户资产数量超限建议按设备类型复核是否存在重复领用或未归还。')

  backendSuggestions.forEach(item => {
    if (item && !suggestions.includes(item)) suggestions.push(item)
  })

  if (!suggestions.length) suggestions.push('当前正式数据未发现高优先级风险，建议保持月度盘点和季度审计节奏。')
  return suggestions
}

function buildDeptRank(assets, violations, aiRisks) {
  const map = {}
  const ensure = dept => {
    const name = dept || '未绑定'
    map[name] ||= { dept: name, score: 0, count: 0 }
    return map[name]
  }

  violations.forEach(item => {
    const row = ensure(item.dept)
    row.count += 1
    row.score += item.severity === 'high' ? 30 : item.severity === 'medium' ? 15 : 5
  })

  assets.forEach(item => {
    const row = ensure(item.dept)
    if (!item.dept && Number(item.price || 0) >= 50000) row.score += 30
    if (item.status === 'idle') row.score += 10
    if (item.status === 'pending_scrap') row.score += 10
  })

  const ranked = Object.values(map).filter(item => item.score > 0)
  if (!ranked.length && aiRisks.some(item => item.count > 0)) return [{ dept: '未绑定', score: scoreFromRisks(aiRisks, violations), count: 0 }]
  return ranked.sort((a, b) => b.score - a.score).slice(0, 6)
}

function buildIdleStats(assets) {
  return [
    { name: '库存中', value: countStatus(assets, 'in_stock') },
    { name: '闲置', value: countStatus(assets, 'idle') },
    { name: '待报废', value: countStatus(assets, 'pending_scrap') }
  ]
}

function scoreFromRisks(risks, violations) {
  const riskScore = risks.reduce((sum, item) => {
    const weight = item.severity === 'high' ? 12 : item.severity === 'medium' ? 7 : 4
    return sum + item.count * weight
  }, 0)
  const violationScore = violations.reduce((sum, item) => {
    const weight = item.severity === 'high' ? 30 : item.severity === 'medium' ? 15 : 5
    return sum + weight
  }, 0)
  return Math.min(100, Math.max(riskScore, violationScore))
}

function countRule(violations, rule) {
  return violations.filter(item => item.rule === rule).length
}

function countStatus(assets, status) {
  return assets.filter(item => item.status === status).length
}

function sumValue(list) {
  return list.reduce((sum, item) => sum + Number(item.price || 0), 0)
}
