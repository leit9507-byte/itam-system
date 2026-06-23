export function runAudit() {
  return Promise.resolve({
    risk_score: 78,
    violations: [
      { asset_id: 'A001', type: 'over_allocated', severity: 'high', message: '用户资产超配' },
      { asset_id: 'A002', type: 'idle_over_90_days', severity: 'medium', message: '资产闲置超过90天' },
      { asset_id: 'A004', type: 'missing_owner', severity: 'high', message: '无责任人资产' },
      { asset_id: 'A005', type: 'missing_dept', severity: 'high', message: '高价值资产未绑定部门' }
    ],
    suggestions: [
      '复核用户名下资产数量，建立超配审批机制。',
      '对闲置资产发起调拨或回收流程。',
      '高价值资产必须绑定部门和责任人。'
    ]
  })
}

export function getRiskAnalytics() {
  return Promise.resolve({
    trend: [42, 48, 51, 60, 72, 78, 64],
    deptRank: [
      { dept: '行政部', score: 86 },
      { dept: '研发部', score: 72 },
      { dept: '销售部', score: 58 },
      { dept: '财务部', score: 36 }
    ],
    idleStats: [
      { name: '0-30天', value: 8 },
      { name: '31-90天', value: 5 },
      { name: '90天以上', value: 3 }
    ]
  })
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
      <h2>ITAM 审计报告</h2>
      <p>本报告由前端模拟生成，用于展示审计中心到报告中心的闭环。</p>
      <ul>
        <li>总资产：6</li>
        <li>风险评分：78</li>
        <li>高风险事项：3</li>
      </ul>
    `
  })
}
