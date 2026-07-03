import { getAssets, getScrapRequests, statusMap } from './asset'
import { getPurchases } from './purchase'
import { getRepairRecords } from './repair'
import { getUsers } from './user'

const inactiveStatuses = ['inactive', 'disabled', 'locked', 'resigned', 'left', 'offboarded', '离职', '停用', '禁用']
const TODO_SOURCE_LIMIT = 500

export async function getTodoItems() {
  const [purchaseResult, scrapResult, assetResult, repairResult, users] = await Promise.all([
    getPurchases({ page: 1, page_size: TODO_SOURCE_LIMIT }),
    getScrapRequests({ status: '审批中', page: 1, page_size: TODO_SOURCE_LIMIT }),
    getAssets({ page: 1, page_size: TODO_SOURCE_LIMIT }),
    getRepairRecords({ status: '维修中', page: 1, page_size: TODO_SOURCE_LIMIT }),
    getUsers()
  ])
  const purchases = purchaseResult.list || []
  const scraps = scrapResult.list || []
  const assets = assetResult.list || []
  const repairs = repairResult.list || []
  const inactiveUserMap = buildInactiveUserMap(users || [])
  const assignedUserIds = buildAssignedUserIds(assets)

  return [
    ...buildOnboardingTodos(users || [], assignedUserIds),
    ...buildPurchaseTodos(purchases),
    ...buildScrapTodos(scraps),
    ...buildReadyScrapTodos(assets),
    ...buildOffboardingTodos(assets, inactiveUserMap),
    ...buildRepairTodos(repairs)
  ].sort((a, b) => priorityWeight(b.priority) - priorityWeight(a.priority) || dateValue(b.created_at) - dateValue(a.created_at))
}

function buildOnboardingTodos(users, assignedUserIds) {
  return users
    .filter(user => isActiveUser(user.status) && !['admin', 'auditor'].includes(user.role) && !assignedUserIds.has(user.user_id) && !assignedUserIds.has(user.username))
    .map(user => ({
      id: `onboarding-${user.user_id || user.username}`,
      type: 'onboarding_assign',
      type_label: '入职配置',
      title: `${user.display_name || user.username} 待配置入职资产`,
      description: `${user.dept_name || user.dept_id || '未设置部门'} / ${user.email || '未填写邮箱'} / 当前未绑定资产`,
      owner: user.display_name || user.username,
      priority: 'medium',
      status: '待分配',
      created_at: user.created_at || user.last_synced_at || '',
      user_id: user.user_id,
      username: user.username || '',
      name: user.display_name || user.username || user.user_id,
      target_path: '/asset/list',
      target_query: {
        action: 'assign',
        user_id: user.user_id,
        username: user.username || '',
        name: user.display_name || user.username || user.user_id
      }
    }))
}

function buildPurchaseTodos(purchases) {
  return purchases
    .filter(item => ['created', 'pending_acceptance'].includes(item.status))
    .map(item => {
      if (item.status === 'created') {
        return {
          id: `purchase-approve-${item.purchase_no}`,
          type: 'purchase_approval',
          type_label: '采购审批',
          title: `采购单 ${item.purchase_no} 待审批`,
          description: `${item.company || '未指定公司'} / ${item.supplier_name || '未指定供应商'} / ${item.quantity || 0} 台 / ¥${Number(item.total_amount || 0).toLocaleString()}`,
          owner: item.dept || '采购负责人',
          priority: Number(item.total_amount || 0) >= 50000 ? 'high' : 'medium',
          status: '待审批',
          created_at: item.created_at || '',
          purchase_no: item.purchase_no,
          target_path: '/purchase',
          target_query: { todo: 'purchase_approval', purchase_no: item.purchase_no }
        }
      }
      return {
        id: `purchase-accept-${item.purchase_no}`,
        type: 'purchase_acceptance',
        type_label: '采购验收',
        title: `采购单 ${item.purchase_no} 待验收`,
        description: `${item.company || '未指定公司'} / ${item.supplier_name || '未指定供应商'} / ${item.quantity || 0} 台需要验收入库`,
        owner: '采购验收员',
        priority: 'medium',
        status: '待验收',
        created_at: item.created_at || '',
        purchase_no: item.purchase_no,
        target_path: '/purchase',
        target_query: { todo: 'purchase_acceptance', purchase_no: item.purchase_no }
      }
    })
}

function buildScrapTodos(scraps) {
  return scraps.map(item => ({
    id: `scrap-approve-${item.id || item.request_no}`,
    type: 'scrap_approval',
    type_label: '报废审批',
    title: `${item.asset_id} 报废申请待审批`,
    description: `${item.asset_name || '资产'} / ${item.reason || '未填写原因'} / 预计残值 ¥${Number(item.estimated_residual_value || 0).toLocaleString()}`,
    owner: '资产负责人',
    priority: 'high',
    status: item.status || '审批中',
    created_at: item.created_at || '',
    request_id: item.id,
    request_no: item.request_no,
    asset_id: item.asset_id,
    target_path: '/scrap',
    target_query: { todo: 'scrap_approval', request_no: item.request_no }
  }))
}

function buildReadyScrapTodos(assets) {
  return assets
    .filter(item => item.status === 'ready_scrap')
    .map(item => ({
      id: `ready-scrap-${item.asset_id}`,
      type: 'scrap_request',
      type_label: '报废申请',
      title: `${item.asset_id} 待提交报废审批`,
      description: `${item.name || '资产'} / ${item.category || '-'} / 当前状态：${statusMap[item.status]?.label || item.status}`,
      owner: item.owner_name || item.owner_user_id || '资产管理员',
      priority: 'medium',
      status: '待提交',
      created_at: item.updated_at || item.created_at || '',
      asset_id: item.asset_id,
      target_path: '/asset/list',
      target_query: { status: 'ready_scrap', keyword: item.asset_id }
    }))
}

function buildOffboardingTodos(assets, inactiveUserMap) {
  return assets
    .filter(item => inactiveUserMap.has(item.owner_user_id || item.owner))
    .map(item => {
      const user = inactiveUserMap.get(item.owner_user_id || item.owner)
      return {
        id: `offboarding-${item.asset_id}`,
        type: 'offboarding_reclaim',
        type_label: '离职回收',
        title: `${user.display_name || user.username || item.owner_user_id} 的资产待回收`,
        description: `${item.asset_id} / ${item.name || '资产'} / ${statusMap[item.status]?.label || item.status} / ${item.location || '未填写位置'}`,
        owner: user.display_name || user.username || item.owner_user_id,
        priority: 'high',
        status: '待回收',
        created_at: item.updated_at || item.created_at || '',
        asset_id: item.asset_id,
        user_id: user.user_id || item.owner_user_id,
        username: user.username || '',
        name: user.display_name || user.username || item.owner_user_id,
        target_path: '/asset/list',
        target_query: {
          action: 'reclaim',
          user_id: user.user_id || item.owner_user_id,
          username: user.username || '',
          name: user.display_name || user.username || item.owner_user_id
        }
      }
    })
}

function buildRepairTodos(repairs) {
  return repairs
    .filter(item => item.status === '维修中')
    .map(item => ({
      id: `repair-${item.id || item.repair_no}`,
      type: 'repair_followup',
      type_label: '维修跟进',
      title: `${item.asset_id} 维修中待跟进`,
      description: `${item.asset_name || '资产'} / ${item.fault_reason || '未填写故障原因'} / ${item.vendor || '未填写维修商'}`,
      owner: item.operator || '资产管理员',
      priority: 'low',
      status: '维修中',
      created_at: item.repair_time || item.created_at || '',
      repair_id: item.id,
      repair_no: item.repair_no,
      asset_id: item.asset_id,
      target_path: '/repair',
      target_query: { todo: 'repair_followup', repair_no: item.repair_no }
    }))
}

function buildInactiveUserMap(users) {
  const map = new Map()
  users.forEach(user => {
    if (!inactiveStatuses.includes(String(user.status || '').toLowerCase())) return
    if (user.user_id) map.set(user.user_id, user)
    if (user.username) map.set(user.username, user)
  })
  return map
}

function buildAssignedUserIds(assets) {
  const ids = new Set()
  assets.forEach(asset => {
    if (!['in_use', 'borrowed', 'out_stock'].includes(asset.status)) return
    if (asset.owner_user_id) ids.add(asset.owner_user_id)
    if (asset.owner) ids.add(asset.owner)
    if (asset.owner_username) ids.add(asset.owner_username)
  })
  return ids
}

function isActiveUser(status) {
  return String(status || '').toLowerCase() === 'active'
}

function priorityWeight(priority) {
  return { high: 3, medium: 2, low: 1 }[priority] || 0
}

function dateValue(value) {
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? 0 : time
}
