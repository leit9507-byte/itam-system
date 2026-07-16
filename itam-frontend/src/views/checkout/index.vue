<template>
  <div class="page checkout-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">借用中心</h2>
        <p class="page-subtitle">登记设备借用、计划归还时间、实际归还和逾期未归还情况</p>
      </div>
      <div class="header-actions">
        <el-button @click="openBatchCheckout">批量借用</el-button>
        <el-button type="primary" :disabled="!selectedOpenRows.length" @click="openBatchCheckin">批量归还</el-button>
      </div>
    </div>

    <section class="summary-grid">
      <article v-for="item in summaryCards" :key="item.key" class="summary-card" :class="{ active: filters.status === item.filter }" @click="setStatusFilter(item.filter)">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </section>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="filters.keyword" clearable placeholder="搜索资产编号/名称/人员/部门/序列号" style="width: 280px" @keyup.enter="refresh" @clear="refresh" />
        <el-select v-model="filters.status" clearable placeholder="记录状态" style="width: 150px" @change="refresh">
          <el-option label="借用中" value="current" />
          <el-option label="已归还" value="closed" />
          <el-option label="即将到期" value="due_soon" />
          <el-option label="逾期未归还" value="overdue" />
        </el-select>
        <el-select v-model="filters.assignee_user_id" clearable filterable placeholder="借用人" style="width: 190px" @change="refresh">
          <el-option v-for="user in users" :key="user.user_id" :label="userLabel(user)" :value="user.user_id" />
        </el-select>
        <el-select v-model="filters.dept_id" clearable filterable placeholder="部门" style="width: 170px" @change="refresh">
          <el-option v-for="dept in deptOptions" :key="dept" :label="dept" :value="dept" />
        </el-select>
        <el-date-picker v-model="checkoutRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="借用开始" end-placeholder="借用结束" @change="refresh" />
        <el-date-picker v-model="dueRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="计划归还开始" end-placeholder="计划归还结束" @change="refresh" />
        <el-button @click="resetFilters">重置</el-button>
        <el-button type="primary" @click="refresh">查询</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ tableTitle }}</span>
          <el-tag effect="light">共 {{ pagination.total }} 条</el-tag>
        </div>
      </template>
      <el-table v-loading="loading" :data="records" border stripe @selection-change="selectedRows = $event">
        <el-table-column type="selection" width="48" />
        <el-table-column label="资产" min-width="220">
          <template #default="{ row }">
            <div class="asset-cell">
              <strong>{{ row.asset_name || row.asset_id }}</strong>
              <span>{{ row.asset_no || row.asset_id }} / {{ row.asset_category || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="checkout_type_label" label="类型" width="90" />
        <el-table-column label="借用人" min-width="180">
          <template #default="{ row }">
            <div class="asset-cell">
              <strong>{{ row.assignee_name || row.assignee_user_id || '-' }}</strong>
              <span>{{ row.dept_id || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="位置" min-width="130" show-overflow-tooltip />
        <el-table-column prop="checked_out_at" label="借用时间" width="160" />
        <el-table-column prop="due_date" label="计划归还" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.is_overdue" type="danger" effect="light">逾期 {{ row.days_overdue }} 天</el-tag>
            <span v-else>{{ row.due_date || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="checked_in_at" label="归还时间" width="160">
          <template #default="{ row }">{{ row.checked_in_at || '-' }}</template>
        </el-table-column>
        <el-table-column prop="status_label" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'open' ? (row.is_overdue ? 'danger' : 'success') : 'info'" effect="light">{{ row.status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goAsset(row)">详情</el-button>
            <el-button link type="primary" :disabled="row.status !== 'open'" @click="openSingleCheckin(row)">归还</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="refresh"
          @current-change="loadRecords"
        />
      </div>
    </el-card>

    <el-dialog v-model="checkoutDialog.visible" title="批量借用" width="720px">
      <el-form :model="checkoutDialog.form" label-width="96px">
        <el-form-item label="选择资产" required>
          <el-select v-model="checkoutDialog.assetIds" multiple filterable collapse-tags collapse-tags-tooltip style="width: 100%" placeholder="选择在库或闲置资产">
            <el-option v-for="asset in availableAssets" :key="asset.asset_id" :label="assetOptionLabel(asset)" :value="asset.asset_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="借用人" required>
          <el-select v-model="checkoutDialog.form.owner_user_id" filterable style="width: 100%" placeholder="选择借用人" @change="fillUser">
            <el-option v-for="user in users" :key="user.user_id" :label="userLabel(user)" :value="user.user_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门"><el-input v-model="checkoutDialog.form.dept_id" disabled /></el-form-item>
        <el-form-item label="计划归还" required>
          <el-date-picker v-model="checkoutDialog.form.due_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="借用位置">
          <el-select v-model="checkoutDialog.form.location" filterable clearable placeholder="选择位置" style="width: 100%">
            <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="checkoutDialog.form.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="checkoutDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitBatchCheckout">确认借用</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="checkinDialog.visible" title="批量归还" width="560px">
      <el-alert :title="`本次将归还 ${checkinDialog.assetIds.length} 台资产`" type="info" show-icon :closable="false" />
      <el-form :model="checkinDialog.form" label-width="88px" class="dialog-form">
        <el-form-item label="入库位置">
          <el-select v-model="checkinDialog.form.location" filterable clearable placeholder="选择归还入库位置" style="width: 100%">
            <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="checkinDialog.form.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="checkinDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitBatchCheckin">确认归还</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { batchCheckinAssets, batchCheckoutAssets, getAssets, getCheckoutRecords } from '../../api/asset'
import { getLocations } from '../../api/location'
import { getUsers } from '../../api/user'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const submitting = ref(false)
const records = ref([])
const users = ref([])
const locations = ref([])
const availableAssets = ref([])
const selectedRows = ref([])
const checkoutRange = ref([])
const dueRange = ref([])
const summary = reactive({ open: 0, closed: 0, overdue: 0, due_soon: 0 })
const filters = reactive({ keyword: '', status: 'current', checkout_type: 'borrowed', assignee_user_id: '', dept_id: '', due_days: 7 })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const checkoutDialog = reactive({
  visible: false,
  assetIds: [],
  form: { checkout_type: 'borrowed', outboundTarget: 'user', owner_user_id: '', dept_id: '', location: '', due_date: '', remark: '' }
})
const checkinDialog = reactive({
  visible: false,
  assetIds: [],
  form: { location: '', remark: '' }
})

const selectedOpenRows = computed(() => selectedRows.value.filter(row => row.status === 'open'))
const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))
const deptOptions = computed(() => [...new Set(users.value.map(user => user.dept_name || user.dept_id).filter(Boolean))])
const summaryCards = computed(() => [
  { key: 'current', label: '借用中', value: summary.open || 0, filter: 'current' },
  { key: 'due_soon', label: '即将到期', value: summary.due_soon || 0, filter: 'due_soon' },
  { key: 'overdue', label: '逾期未归还', value: summary.overdue || 0, filter: 'overdue' },
  { key: 'closed', label: '已归还', value: summary.closed || 0, filter: 'closed' }
])
const tableTitle = computed(() => summaryCards.value.find(item => item.filter === filters.status)?.label || '借用记录')

onMounted(async () => {
  applyRouteQuery()
  const [userRows, locationRows] = await Promise.all([
    getUsers().catch(() => []),
    getLocations().catch(() => [])
  ])
  users.value = userRows
  locations.value = locationRows
  await loadAvailableAssets()
  await loadRecords()
})

function applyRouteQuery() {
  filters.keyword = typeof route.query.keyword === 'string' ? route.query.keyword : ''
  filters.status = typeof route.query.status === 'string' ? route.query.status : 'current'
  filters.checkout_type = 'borrowed'
}

async function loadRecords() {
  loading.value = true
  try {
    const result = await getCheckoutRecords({
      ...filters,
      date_from: checkoutRange.value?.[0] || '',
      date_to: checkoutRange.value?.[1] || '',
      due_from: dueRange.value?.[0] || '',
      due_to: dueRange.value?.[1] || '',
      page: pagination.page,
      pageSize: pagination.pageSize
    })
    records.value = result.list
    pagination.total = result.total
    Object.assign(summary, result.summary || {})
  } finally {
    loading.value = false
  }
}

async function loadAvailableAssets() {
  const result = await getAssets({ page: 1, page_size: 500 })
  availableAssets.value = result.list.filter(asset => ['in_stock', 'idle'].includes(asset.status))
}

function refresh() {
  pagination.page = 1
  loadRecords()
}

function resetFilters() {
  Object.assign(filters, { keyword: '', status: 'current', checkout_type: 'borrowed', assignee_user_id: '', dept_id: '', due_days: 7 })
  checkoutRange.value = []
  dueRange.value = []
  refresh()
}

function setStatusFilter(status) {
  filters.status = status
  refresh()
}

function openBatchCheckout() {
  checkoutDialog.assetIds = []
  Object.assign(checkoutDialog.form, { checkout_type: 'borrowed', outboundTarget: 'user', owner_user_id: '', dept_id: '', location: '', due_date: '', remark: '设备借用登记' })
  checkoutDialog.visible = true
  loadAvailableAssets()
}

function openBatchCheckin() {
  checkinDialog.assetIds = selectedOpenRows.value.map(row => row.asset_id)
  Object.assign(checkinDialog.form, { location: '', remark: '资产批量归还入库' })
  checkinDialog.visible = true
}

function openSingleCheckin(row) {
  selectedRows.value = [row]
  checkinDialog.assetIds = [row.asset_id]
  Object.assign(checkinDialog.form, { location: row.location || '', remark: '资产归还入库' })
  checkinDialog.visible = true
}

async function submitBatchCheckout() {
  if (!checkoutDialog.assetIds.length) return ElMessage.warning('请选择资产')
  if (!checkoutDialog.form.owner_user_id) return ElMessage.warning('请选择借用人')
  if (!checkoutDialog.form.due_date) return ElMessage.warning('请选择计划归还时间')
  checkoutDialog.form.checkout_type = 'borrowed'
  checkoutDialog.form.outboundTarget = 'user'
  submitting.value = true
  try {
    const result = await batchCheckoutAssets(checkoutDialog.assetIds, checkoutDialog.form)
    showBatchResult(result, '批量借用完成')
    checkoutDialog.visible = false
    await loadAvailableAssets()
    await loadRecords()
  } finally {
    submitting.value = false
  }
}

async function submitBatchCheckin() {
  if (!checkinDialog.assetIds.length) return ElMessage.warning('请选择要归还的资产')
  submitting.value = true
  try {
    const result = await batchCheckinAssets(checkinDialog.assetIds, checkinDialog.form)
    showBatchResult(result, '批量归还完成')
    checkinDialog.visible = false
    selectedRows.value = []
    await loadAvailableAssets()
    await loadRecords()
  } finally {
    submitting.value = false
  }
}

function showBatchResult(result, message) {
  const failed = Number(result.failed || 0)
  if (failed) {
    const first = result.errors?.[0]
    ElMessage.warning(`${message}，成功 ${result.success || 0}，失败 ${failed}${first ? `：${first.asset_id} ${first.message}` : ''}`)
  } else {
    ElMessage.success(`${message}，成功 ${result.success || 0}`)
  }
}

function fillUser(userId) {
  const user = users.value.find(item => item.user_id === userId)
  checkoutDialog.form.dept_id = user?.dept_id || user?.dept_name || ''
}

function goAsset(row) {
  router.push(`/asset/detail/${row.asset_id}`)
}

function userLabel(user) {
  return `${user.display_name || user.username || user.user_id} / ${user.dept_name || user.dept_id || '未分部门'}`
}

function assetOptionLabel(asset) {
  return `${asset.name || asset.asset_id} / ${asset.asset_no || asset.asset_id} / ${asset.status_label || asset.status}`
}

function locationLabel(item) {
  const meta = [item.code, item.type].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}
</script>

<style scoped>
.checkout-page {
  min-width: 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(150px, 1fr));
  gap: 14px;
}

.summary-card {
  position: relative;
  display: grid;
  gap: 8px;
  min-height: 92px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: var(--shadow);
  cursor: pointer;
  overflow: hidden;
}

.summary-card::after {
  position: absolute;
  right: -28px;
  bottom: -34px;
  width: 84px;
  height: 84px;
  border-radius: 50%;
  background: rgba(25, 117, 252, 0.08);
  content: "";
}

.summary-card:hover {
  border-color: #9dc8ff;
}

.summary-card.active {
  border-color: #9dc8ff;
  background: var(--primary-soft);
}

.summary-card span {
  color: var(--muted);
  font-size: 13px;
  font-weight: 800;
}

.summary-card strong {
  color: var(--text);
  font-size: 28px;
  line-height: 1;
}

.asset-cell {
  display: grid;
  gap: 4px;
}

.asset-cell span {
  color: var(--muted);
  font-size: 12px;
}

.dialog-form {
  margin-top: 14px;
}

.header-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
