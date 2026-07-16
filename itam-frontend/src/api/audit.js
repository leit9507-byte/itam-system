import request from '../utils/request'
import { getAssets } from './asset'
import { getPurchases } from './purchase'
import { getUsers } from './user'

export const ruleLabels = {
  USER_ASSET_COUNT_LIMIT: '资产数量超配',
  OFFBOARDING_ASSET_NOT_RETURNED: '离职未回收',
  BORROWED_ASSET_NOT_RETURNED: '借用未回收',
  SINGLE_OWNER_VALUE_LIMIT: '资产价值超标',
  HIGH_VALUE_PURCHASE: '超价值采购',
  ASSET_IDLE_OVER_90_DAYS: '长期闲置',
  ASSET_RETIREMENT_OVERDUE: '超期服役审计',
  DEVICE_FAULT_AUDIT: '设备故障审计'
}

const severityLabels = {
  high: '高',
  medium: '中',
  low: '低'
}
const AUDIT_CONTEXT_LIMIT = 1000

export function getAuditRules() {
  return request.get('/audit/rules')
}

export function saveAuditRules(rules) {
  return request.post('/audit/rules', rules)
}

export function getAuditResponses() {
  return request.get('/audit/responses')
}

export function saveAuditResponse(payload) {
  return request.post('/audit/responses', payload)
}

export async function runAudit(options = {}) {
  const [{ list: assets }, purchaseResult, users, backend, rules, responses] = await Promise.all([
    getAssets({ page: 1, page_size: AUDIT_CONTEXT_LIMIT }),
    getPurchases({ page: 1, page_size: AUDIT_CONTEXT_LIMIT }).catch(() => ({ list: [] })),
    getUsers().catch(() => []),
    request.post('/audit/run', { users: [], notify: Boolean(options.notify) }).catch(() => null),
    getAuditRules().catch(() => []),
    getAuditResponses().catch(() => [])
  ])
  const purchases = purchaseResult.list || []

  const violations = normalizeViolations(backend?.violations || [], assets, users, rules, responses)
  const personRisks = buildPersonRisks(assets, users, violations, rules)
  const assetRisks = buildAssetRisks(assets, purchases, violations, rules)
  const allRisks = [...personRisks, ...assetRisks]
  const riskScore = Math.min(100, backend?.risk_score ?? scoreFromRisks(allRisks, violations))
  const involvedAmount = allRisks.reduce((sum, item) => sum + Number(item.amount || 0), 0)

  return {
    total_assets: backend?.total_assets ?? assets.length,
    risk_score: riskScore,
    health_score: Math.max(0, 100 - riskScore),
    involved_amount: involvedAmount,
    violations,
    responses: responses || [],
    person_risks: personRisks,
    asset_risks: assetRisks,
    ai_risks: allRisks,
    rules: buildRules(violations, allRisks, rules),
    suggestions: buildSuggestions(allRisks, violations, backend?.suggestions || []),
    riskTrend: [{ name: '本次审计', value: riskScore }],
    deptRank: buildDeptRank(assets, violations),
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

export async function getReports(params = {}) {
  const result = await request.get('/reports/audit-reports', { params })
  return result.list || result
}

export async function generateReport() {
  return request.post('/reports/audit-reports')
  const result = await request.post('/audit/run', { users: [], notify: false })
  const html = await request.get('/audit/report', { responseType: 'text' })
  return {
    id: `AR-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}`,
    name: '即时资产审计报告',
    type: '审计报告',
    status: '已生成',
    created_at: new Date().toISOString().slice(0, 10),
    total_assets: result.total_assets,
    risk_score: result.risk_score,
    html
  }
}

export function getReportHtml(reportId) {
  return request.get(`/reports/audit-reports/${encodeURIComponent(reportId)}/html`, { responseType: 'text' })
}

export async function downloadArchivedAuditReport(reportId, type = 'pdf') {
  const blob = await request.get(`/reports/audit-reports/${encodeURIComponent(reportId)}/${type}`, { responseType: 'blob' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${reportId}.${type === 'xlsx' ? 'xlsx' : 'pdf'}`
  link.click()
  URL.revokeObjectURL(url)
}

function normalizeViolations(rows, assets, users, rules, responses) {
  const ruleMap = Object.fromEntries((rules || []).map(rule => [rule.rule_code, rule]))
  const userMap = Object.fromEntries((users || []).map(user => [user.user_id, user]))
  const responseMap = Object.fromEntries((responses || []).map(item => [item.violation_key, item]))
  return rows.map(row => {
    const asset = assets.find(item => item.asset_id === row.asset_id)
    const user = userMap[row.owner_user_id || asset?.owner_user_id || '']
    const rule = row.rule || row.type || 'UNKNOWN_RULE'
    const savedRule = ruleMap[rule]
    const auditScope = row.audit_scope || savedRule?.audit_scope || inferScope(rule)
    const violationKey = buildViolationKey({ ...row, rule, audit_scope: auditScope, asset })
    const groupKey = buildPersonGroupKey({ ...row, rule, audit_scope: auditScope, asset })
    const response = responseMap[violationKey] || {}
    const groupResponse = responseMap[groupKey] || {}
    return {
      violation_key: violationKey,
      person_group_key: groupKey,
      asset_id: row.asset_id,
      asset_name: asset?.name || row.asset_name || '-',
      dept: user?.dept_name || asset?.dept_name || asset?.dept || row.dept || '未绑定',
      owner: user?.display_name || asset?.owner_name || asset?.owner || row.owner_name || '未分配',
      owner_user_id: row.owner_user_id || asset?.owner_user_id || '',
      user_status: user?.status || '',
      price: Number(asset?.price || row.price || 0),
      rule,
      type: ruleLabels[rule] || savedRule?.name || row.type || rule,
      audit_scope: auditScope,
      target_type: row.target_type || inferScope(rule),
      severity: row.severity || savedRule?.severity || 'medium',
      severity_label: severityLabels[row.severity] || row.severity || '中',
      message: row.message || '发现资产合规风险',
      decision: response.decision || groupResponse.decision || row.decision || 'pending',
      response_reason: response.reason || groupResponse.reason || row.response_reason || '',
      responder: response.responder || groupResponse.responder || row.responder || '',
      response_updated_at: response.updated_at || groupResponse.updated_at || row.response_updated_at || ''
    }
  })
}

export function buildViolationKey(row) {
  return [row.rule || '', row.asset_id || '', row.owner_user_id || row.asset?.owner_user_id || '', row.audit_scope || inferScope(row.rule)].join('|')
}

export function buildPersonGroupKey(row) {
  return [row.rule || '', row.owner_user_id || row.asset?.owner_user_id || '', 'person_group'].join('|')
}

function buildPersonRisks(assets, users, violations, rules) {
  const offboardedUsers = users.filter(user => isInactiveUser(user.status))
  const offboardedAssetIds = new Set(
    assets
      .filter(asset => offboardedUsers.some(user => user.user_id === asset.owner_user_id) && ['in_use', 'borrowed', 'out_stock'].includes(asset.status))
      .map(item => item.asset_id)
  )
  const customCountRisks = (rules || [])
    .filter(rule => isCustomPersonCountRule(rule.rule_code))
    .map(rule => riskCard(rule.rule_code, rule.name || '人员跨品类数量审计', 'person', violations, assets, rules, rule.scope_category ? `按 ${rule.scope_category.replaceAll(',', '、')} 数量阈值核对人员配置` : '按全部设备类型统计人员名下资产数量'))
  return [
    riskCard('USER_ASSET_COUNT_LIMIT', '人员资产超数量配置', 'person', violations, assets, rules, '按设备类型和数量阈值核对个人配置标准'),
    riskCard('OFFBOARDING_ASSET_NOT_RETURNED', '离职没有回收', 'person', violations, assets.filter(asset => offboardedAssetIds.has(asset.asset_id)), rules, '联动离职状态，发起资产回收入库'),
    riskCard('BORROWED_ASSET_NOT_RETURNED', '借用没有回收', 'person', violations, assets.filter(asset => asset.status === 'borrowed'), rules, '跟踪借用周期，超期提醒并回收'),
    ...customCountRisks
  ]
}

function buildAssetRisks(assets, purchases, violations, rules) {
  const highValueRule = rules.find(rule => rule.rule_code === 'HIGH_VALUE_PURCHASE')
  const highValue = Number(highValueRule?.threshold_value || 50000)
  const highValueAssets = assets.filter(item => Number(item.price || 0) >= highValue)
  const idleAssets = assets.filter(item => ['idle', 'in_stock'].includes(item.status))
  const retirementOverdueAssetIds = new Set(violations.filter(item => item.rule === 'ASSET_RETIREMENT_OVERDUE').map(item => item.asset_id))
  const retirementOverdueAssets = retirementOverdueAssetIds.size ? assets.filter(item => retirementOverdueAssetIds.has(item.asset_id)) : assets.filter(isActiveRetirementOverdue)
  const faultyAssetIds = new Set(violations.filter(item => item.rule === 'DEVICE_FAULT_AUDIT').map(item => item.asset_id))
  const faultyAssets = assets.filter(item => faultyAssetIds.has(item.asset_id) || item.status === 'repair')
  return [
    riskCard('HIGH_VALUE_PURCHASE', '超价值采购', 'asset', violations, highValueAssets, rules, '复核采购审批、供应商和预算依据'),
    riskCard('ASSET_IDLE_OVER_90_DAYS', '长期闲置', 'asset', violations, idleAssets, rules, '优先调拨复用，无法复用则进入处置流程'),
    riskCard('ASSET_RETIREMENT_OVERDUE', '超期服役审计', 'asset', violations, retirementOverdueAssets, rules, '评估性能、安全和维修成本，安排替换、延寿审批或报废处置'),
    riskCard('DEVICE_FAULT_AUDIT', '设备故障审计', 'asset', violations, faultyAssets, rules, '复核重复故障、未修好和在保送修设备，必要时进入报废或换新流程')
  ]
}

function riskCard(rule, title, scope, violations, assets, rules, action) {
  const hits = violations.filter(item => item.rule === rule)
  const count = hits.length || assets.length
  const hitAssetIds = new Set(hits.map(item => item.asset_id))
  const sourceAssets = hits.length ? assets.filter(asset => hitAssetIds.has(asset.asset_id)) : assets
  const savedRule = rules.find(item => item.rule_code === rule)
  const severity = savedRule?.severity || hits[0]?.severity || (scope === 'asset' ? 'medium' : 'high')
  return {
    rule,
    type: title,
    scope,
    count,
    level: severityLabels[severity] || severity,
    severity,
    amount: sumValue(sourceAssets),
    action
  }
}

function buildRules(violations, risks, savedRules) {
  return (savedRules || []).map(rule => {
    const key = rule.rule_code || rule.key
    const risk = risks.find(item => item.rule === key)
    return {
      ...rule,
      key,
      name: rule.name || ruleLabels[key] || key,
      audit_scope: rule.audit_scope || inferScope(key),
      severity_label: severityLabels[rule.severity] || rule.severity,
      hits: Math.max(countRule(violations, key), risk?.count || 0)
    }
  })
}

function buildSuggestions(risks, violations, backendSuggestions) {
  const suggestions = [...(backendSuggestions || [])]
  const addWhen = (rule, text) => {
    if (((risks.find(item => item.rule === rule)?.count || 0) > 0 || countRule(violations, rule) > 0) && !suggestions.includes(text)) suggestions.push(text)
  }

  addWhen('USER_ASSET_COUNT_LIMIT', '人员资产数量超配建议按设备类型设置阈值，并对超配设备发起回收或审批豁免。')
  addWhen('OFFBOARDING_ASSET_NOT_RETURNED', '离职未回收建议接入 HR/SSO 状态，离职时自动生成回收清单。')
  addWhen('BORROWED_ASSET_NOT_RETURNED', '借用未回收建议记录预计归还日期，并对超期借用自动提醒。')
  addWhen('HIGH_VALUE_PURCHASE', '超价值采购建议复核采购审批单、供应商和合同预算。')
  addWhen('ASSET_IDLE_OVER_90_DAYS', '长期闲置资产建议优先调拨复用，降低重复采购。')
  addWhen('ASSET_RETIREMENT_OVERDUE', '超期服役资产建议评估继续使用风险，形成延寿审批、换新计划或报废处置台账。')
  addWhen('DEVICE_FAULT_AUDIT', '设备故障审计建议重点跟进重复维修、未修好和在保送修设备，评估报废、换新或供应商质保。')

  if (!suggestions.length) suggestions.push('当前正式数据未发现高优先级风险，建议保持月度盘点和季度审计节奏。')
  return suggestions
}

function buildDeptRank(assets, violations) {
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
    const row = ensure(item.dept_name || item.dept)
    if (item.status === 'idle') row.score += 10
    if (item.status === 'borrowed') row.score += 8
  })

  return Object.values(map).filter(item => item.score > 0).sort((a, b) => b.score - a.score).slice(0, 6)
}

function buildIdleStats(assets) {
  return [
    { name: '库存中', value: countStatus(assets, 'in_stock') },
    { name: '闲置', value: countStatus(assets, 'idle') },
    { name: '借出', value: countStatus(assets, 'borrowed') }
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

function inferScope(rule) {
  if (isCustomPersonCountRule(rule)) return 'person'
  return ['USER_ASSET_COUNT_LIMIT', 'OFFBOARDING_ASSET_NOT_RETURNED', 'BORROWED_ASSET_NOT_RETURNED', 'SINGLE_OWNER_VALUE_LIMIT'].includes(rule) ? 'person' : 'asset'
}

function isCustomPersonCountRule(rule) {
  return String(rule || '').startsWith('CUSTOM_PERSON_COUNT_')
}

function isInactiveUser(status) {
  return ['inactive', 'disabled', 'locked', 'resigned', 'left', 'offboarded', '离职', '停用', '禁用'].includes(String(status || '').toLowerCase())
}

function countRule(violations, rule) {
  return violations.filter(item => item.rule === rule).length
}

function countStatus(assets, status) {
  return assets.filter(item => item.status === status).length
}

function isActiveRetirementOverdue(asset) {
  if (!['in_use', 'borrowed', 'out_stock', 'repair'].includes(asset.status)) return false
  if (!asset.retirement_date) return false
  return new Date(asset.retirement_date) < new Date()
}

function sumValue(list) {
  return list.reduce((sum, item) => sum + Number(item.price || 0), 0)
}
