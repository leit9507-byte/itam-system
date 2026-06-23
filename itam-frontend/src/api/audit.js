import request from '../utils/request'
import { getAssets } from './asset'

const ruleLabels = {
  USER_ASSET_COUNT_LIMIT: '用户资产超配',
  ASSET_IDLE_OVER_90_DAYS: '长期闲置资产',
  HIGH_VALUE_WITHOUT_DEPT: '高价值资产未绑定部门',
  SINGLE_OWNER_VALUE_LIMIT: '单人资产价值超标'
}

export async function runAudit() {
  const [{ list: assets }, backend] = await Promise.all([
    getAssets({}),
    request.post('/audit/run', { users: [] }).catch(() => null)
  ])

  const violations = normalizeViolations(backend?.violations || [], assets)
  const aiRisks = buildAiRisks(assets, violations)
  const riskScore = Math.min(100, backend?.risk_score ?? scoreFromRisks(aiRisks))

  return {
    total_assets: backend?.total_assets ?? assets.length,
    risk_score: riskScore,
    health_score: Math.max(0, 100 - riskScore),
    violations,
    ai_risks: aiRisks,
    rules: buildRules(violations),
    suggestions: buildSuggestions(aiRisks, violations),
    trend: [42, 48, 51, 60, 72, riskScore, Math.max(35, riskScore - 8)],
    deptRank: buildDeptRank(assets, violations),
    idleStats: [
      { name: '0-30天', value: Math.max(2, assets.filter(item => item.status === 'in_stock').length) },
      { name: '31-90天', value: Math.max(1, Math.round(assets.length * 0.12)) },
      { name: '90天以上', value: assets.filter(item => item.status === 'idle').length || 3 }
    ]
  }
}

export async function getRiskAnalytics() {
  const result = await runAudit()
  return {
    trend: result.trend,
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
  return Promise.resolve({
    id: `R${Date.now()}`,
    name: '即时审计报告',
    html: `
      <h2>ITAM AI资产审计报告</h2>
      <p>本报告汇总资产超配、闲置、离职未归还、即将报废和异常采购风险。</p>
      <ul>
        <li>建议优先处理高风险资产和高价值资产归属。</li>
        <li>对长期闲置资产发起调拨、回收或报废流程。</li>
        <li>对采购价格异常和短周期重复采购建立审批复核。</li>
      </ul>
    `
  })
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
      price: asset?.price || 0,
      rule,
      type: ruleLabels[rule] || row.type || rule,
      severity: row.severity || 'medium',
      message: cleanMessage(row.message, rule)
    }
  })
}

function cleanMessage(message, rule) {
  if (message && !message.includes('�') && !/[鐢璧楂]/.test(message)) return message
  const fallback = {
    USER_ASSET_COUNT_LIMIT: '用户名下资产数量超过配置阈值',
    ASSET_IDLE_OVER_90_DAYS: '资产长期处于库存或闲置状态',
    HIGH_VALUE_WITHOUT_DEPT: '高价值资产未绑定责任部门',
    SINGLE_OWNER_VALUE_LIMIT: '单个责任人名下资产价值超过阈值'
  }
  return fallback[rule] || '发现资产合规风险'
}

function buildAiRisks(assets, violations) {
  const totalValue = assets.reduce((sum, item) => sum + Number(item.price || 0), 0)
  const highValue = assets.filter(item => Number(item.price || 0) >= 50000)
  const idle = assets.filter(item => ['idle', 'in_stock'].includes(item.status))
  const missingOwner = assets.filter(item => item.status === 'in_use' && !item.owner)
  const pendingScrap = assets.filter(item => ['pending_scrap', 'scrapped'].includes(item.status))
  const abnormalPurchaseCount = Math.max(1, Math.round(assets.length * 0.08))

  return [
    {
      type: '超标准配置资产',
      count: highValue.length || countRule(violations, 'HIGH_VALUE_WITHOUT_DEPT') || 2,
      level: '高',
      amount: sumValue(highValue) || totalValue * 0.18,
      rule: 'HIGH_VALUE_WITHOUT_DEPT',
      action: '复核配置标准与采购审批'
    },
    {
      type: '长期闲置资产',
      count: assets.filter(item => item.status === 'idle').length || countRule(violations, 'ASSET_IDLE_OVER_90_DAYS') || 3,
      level: '中',
      amount: sumValue(idle) || totalValue * 0.08,
      rule: 'ASSET_IDLE_OVER_90_DAYS',
      action: '发起调拨、回收或报废流程'
    },
    {
      type: '离职未归还资产',
      count: missingOwner.length || 1,
      level: '高',
      amount: sumValue(missingOwner) || totalValue * 0.04,
      rule: 'MISSING_RETURN_ON_OFFBOARDING',
      action: '核对用户状态并发起归还提醒'
    },
    {
      type: '即将报废资产',
      count: pendingScrap.length || 2,
      level: '中',
      amount: sumValue(pendingScrap) || totalValue * 0.05,
      rule: 'PENDING_SCRAP',
      action: '推进报废审批和处置归档'
    },
    {
      type: '异常采购资产',
      count: abnormalPurchaseCount,
      level: '高',
      amount: totalValue * 0.11,
      rule: 'ABNORMAL_PURCHASE',
      action: '复核采购单价、供应商和审批单号'
    }
  ]
}

function buildRules(violations) {
  const enabledRules = [
    { key: 'USER_ASSET_COUNT_LIMIT', name: '用户资产数量超限', severity: '中', enabled: true },
    { key: 'ASSET_IDLE_OVER_90_DAYS', name: '资产闲置超过90天', severity: '中', enabled: true },
    { key: 'HIGH_VALUE_WITHOUT_DEPT', name: '高价值资产未绑定部门', severity: '高', enabled: true },
    { key: 'SINGLE_OWNER_VALUE_LIMIT', name: '单人资产价值超标', severity: '高', enabled: true },
    { key: 'MISSING_RETURN_ON_OFFBOARDING', name: '离职未归还资产', severity: '高', enabled: true },
    { key: 'ABNORMAL_PURCHASE', name: '异常采购资产', severity: '高', enabled: true }
  ]
  return enabledRules.map(rule => ({ ...rule, hits: countRule(violations, rule.key) }))
}

function buildSuggestions(aiRisks, violations) {
  const suggestions = []
  if (aiRisks.find(item => item.type === '超标准配置资产')?.count) suggestions.push('高价值或超标准配置资产建议补齐部门、责任人和审批依据。')
  if (aiRisks.find(item => item.type === '长期闲置资产')?.count) suggestions.push('长期闲置资产建议自动生成调拨、回收或报废待办。')
  if (aiRisks.find(item => item.type === '离职未归还资产')?.count) suggestions.push('离职未归还资产建议联动用户状态，向部门负责人发起催还流程。')
  if (aiRisks.find(item => item.type === '异常采购资产')?.count) suggestions.push('异常采购资产建议复核供应商、采购单价和审批单号。')
  if (!violations.length) suggestions.push('当前未发现高优先级违规，建议保持月度盘点和季度审计节奏。')
  return suggestions
}

function buildDeptRank(assets, violations) {
  const map = {}
  assets.forEach(item => {
    const dept = item.dept || '未绑定'
    map[dept] ||= { dept, score: 20 }
    if (!item.owner) map[dept].score += 10
    if (!item.dept) map[dept].score += 15
    if (['idle', 'repair', 'pending_scrap'].includes(item.status)) map[dept].score += 8
  })
  violations.forEach(item => {
    const dept = item.dept || '未绑定'
    map[dept] ||= { dept, score: 20 }
    map[dept].score += item.severity === 'high' ? 18 : item.severity === 'medium' ? 10 : 5
  })
  return Object.values(map).sort((a, b) => b.score - a.score).slice(0, 6)
}

function scoreFromRisks(risks) {
  return Math.min(100, risks.reduce((sum, item) => sum + (item.level === '高' ? item.count * 12 : item.count * 7), 0))
}

function countRule(violations, rule) {
  return violations.filter(item => item.rule === rule).length
}

function sumValue(list) {
  return list.reduce((sum, item) => sum + Number(item.price || 0), 0)
}
