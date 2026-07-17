<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">报废处置登记</h2>
        <p class="page-subtitle">资产实际完成处置后，登记退役时间、处置方式、审批单号和处理结果</p>
      </div>
      <el-button @click="load">刷新</el-button>
    </div>

    <div class="metric-grid">
      <el-card shadow="never"><el-statistic title="待处置" :value="pendingDisposalCount" /></el-card>
      <el-card shadow="never"><el-statistic title="已处置" :value="countByStatus('已处置')" /></el-card>
      <el-card shadow="never"><el-statistic title="员工领走" :value="countByMethod('员工领用')" /></el-card>
      <el-card shadow="never"><el-statistic title="变卖" :value="countByMethod('变卖')" /></el-card>
      <el-card shadow="never"><el-statistic title="残值合计" :value="totalResidual" prefix="¥" /></el-card>
    </div>

    <el-card shadow="never" class="filter-card">
      <div class="filter-grid">
        <el-form-item label="申请时间">
          <el-date-picker
            v-model="filters.createdRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            @change="refresh"
          />
        </el-form-item>
        <el-form-item label="处置状态">
          <el-select v-model="filters.status" clearable placeholder="全部状态" @change="refresh">
            <el-option label="待处置" value="待处置" />
            <el-option label="历史审批中" value="审批中" />
            <el-option label="已通过" value="已通过" />
            <el-option label="已驳回" value="已驳回" />
            <el-option label="已处置" value="已处置" />
          </el-select>
        </el-form-item>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table :data="requests" border stripe>
        <el-table-column prop="request_no" label="流程单号" width="140" />
        <el-table-column prop="company" label="公司" width="120" show-overflow-tooltip />
        <el-table-column prop="asset_id" label="资产ID" width="120" />
        <el-table-column label="资产历史信息" min-width="260">
          <template #default="{ row }">
            <div class="asset-info">
              <strong>{{ row.asset_name }}</strong>
              <span>{{ row.category || '-' }} / {{ row.brand || '-' }} / {{ row.model || '-' }}</span>
              <span>SN：{{ row.sn || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="采购历史" min-width="220">
          <template #default="{ row }">
            <div class="asset-info">
              <span>供应商：{{ row.purchase_supplier_name || '-' }}</span>
              <span>审批单：{{ row.purchase_approval_no || '-' }}</span>
              <span>采购价：¥{{ row.purchase_price.toLocaleString() }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="责任历史" min-width="190">
          <template #default="{ row }">
            <div class="asset-info">
              <span>责任人：{{ row.owner_user_id || '-' }}</span>
              <span>部门：{{ row.dept_id || '-' }}</span>
              <span>位置：{{ row.location || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="报废原因" min-width="220" show-overflow-tooltip />
        <el-table-column prop="retirement_date" label="退役时间" width="120" />
        <el-table-column prop="retirement_approval_no" label="退役审批单号" width="150" show-overflow-tooltip />
        <el-table-column label="实际处置方式" width="130">
          <template #default="{ row }">{{ row.disposal_method || '未登记' }}</template>
        </el-table-column>
        <el-table-column label="报废领走人" width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.dispose_recipient_name || row.dispose_recipient_user_id || '-' }}</template>
        </el-table-column>
        <el-table-column prop="estimated_residual_value" label="预计残值" width="120">
          <template #default="{ row }">¥{{ row.estimated_residual_value.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建日期" width="120" />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :disabled="row.status === '已处置' || row.status === '已驳回'" @click="openDispose(row)">登记处置</el-button>
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
          @size-change="handlePageSizeChange"
          @current-change="load"
        />
      </div>
    </el-card>

    <el-dialog v-model="disposeDialog.visible" :title="disposeDialog.row ? `报废处置登记 / ${disposeDialog.row.asset_id}` : '报废处置登记'" width="660px">
      <el-alert
        title="本次只登记当前这一台资产"
        :description="disposeDialog.row ? `${disposeDialog.row.asset_id} / ${disposeDialog.row.asset_name || '-'}；确认后该资产将进入已处置终态。` : ''"
        type="warning"
        show-icon
        :closable="false"
      />
      <el-descriptions v-if="disposeDialog.row" :column="2" border class="dispose-asset-summary">
        <el-descriptions-item label="资产编号">{{ disposeDialog.row.asset_id }}</el-descriptions-item>
        <el-descriptions-item label="序列号">{{ disposeDialog.row.sn || '-' }}</el-descriptions-item>
        <el-descriptions-item label="资产名称">{{ disposeDialog.row.asset_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="登记单号">{{ disposeDialog.row.request_no || '-' }}</el-descriptions-item>
      </el-descriptions>
      <el-form :model="disposeDialog.form" label-width="110px" class="dispose-form">
        <el-form-item label="退役时间" required>
          <el-date-picker v-model="disposeDialog.form.retirement_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="退役审批单号" required>
          <el-input v-model="disposeDialog.form.retirement_approval_no" placeholder="填写退役/报废审批单号" />
        </el-form-item>
        <el-form-item label="实际处置方式" required>
          <el-segmented v-model="disposeDialog.form.disposal_method" :options="disposalMethodOptions" class="disposal-method-segment" />
          <div class="form-tip">当前选择仅作用于上方这一台资产；其他资产需要分别登记。</div>
        </el-form-item>
        <el-form-item v-if="disposeDialog.form.disposal_method === '员工领用'" label="领用员工" required>
          <el-select
            v-model="disposeDialog.form.dispose_recipient_user_id"
            filterable
            clearable
            placeholder="选择报废领走员工"
            style="width: 100%"
            @change="handleDisposeRecipientChange"
          >
            <el-option
              v-for="user in users"
              :key="user.user_id || user.username"
              :label="userLabel(user)"
              :value="user.user_id || user.username"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="实际残值">
          <el-input-number v-model="disposeDialog.form.final_residual_value" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="处置说明" required>
          <el-input v-model="disposeDialog.form.disposal_remark" type="textarea" :rows="4" :placeholder="disposeRemarkPlaceholder" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="disposeDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="dispose">确认登记</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { disposeScrapRequest, getScrapRequests } from '../../api/asset'
import { getUsers } from '../../api/user'

const requests = ref([])
const allRequests = ref([])
const users = ref([])
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const filters = reactive({ createdRange: [], status: '' })
const disposeDialog = reactive({
  visible: false,
  row: null,
  form: {
    final_residual_value: 0,
    disposal_method: '',
    retirement_date: '',
    retirement_approval_no: '',
    dispose_recipient_user_id: '',
    dispose_recipient_name: '',
    disposal_remark: ''
  }
})
const SCRAP_SUMMARY_LIMIT = 500
const disposalMethodOptions = [
  { label: '报废', value: '报废' },
  { label: '变卖', value: '变卖' },
  { label: '员工领用', value: '员工领用' }
]

const totalResidual = computed(() => allRequests.value.reduce((sum, item) => sum + Number(item.estimated_residual_value || 0), 0))
const pendingDisposalCount = computed(() => allRequests.value.filter(item => ['待处置', '审批中', '已通过'].includes(item.status)).length)
const disposeRemarkPlaceholder = computed(() => {
  if (disposeDialog.form.disposal_method === '员工领用') return '例如：报废资产由员工领走，已签收确认'
  if (disposeDialog.form.disposal_method === '变卖') return '例如：变卖给回收商，交易单号 XXX'
  return '例如：报废销毁、环保回收，回收单号 XXX'
})

onMounted(async () => {
  await Promise.all([load(), loadUsers()])
})

async function loadUsers() {
  users.value = await getUsers().catch(() => [])
}

async function load() {
  const params = {
    status: filters.status || '',
    created_from: filters.createdRange?.[0] || '',
    created_to: filters.createdRange?.[1] || ''
  }
  const [paged, all] = await Promise.all([
    getScrapRequests({ ...params, page: pagination.page, page_size: pagination.pageSize }),
    getScrapRequests({ ...params, page: 1, page_size: SCRAP_SUMMARY_LIMIT })
  ])
  requests.value = paged.list
  pagination.total = paged.total
  allRequests.value = all.list
}

function countByStatus(status) {
  return allRequests.value.filter(item => item.status === status).length
}

function countByMethod(method) {
  return allRequests.value.filter(item => item.disposal_method === method && item.status === '已处置').length
}

function handlePageSizeChange() {
  pagination.page = 1
  load()
}

function refresh() {
  pagination.page = 1
  load()
}

async function resetFilters() {
  filters.createdRange = []
  filters.status = ''
  pagination.page = 1
  await load()
}

function openDispose(row) {
  disposeDialog.row = row
  disposeDialog.form.final_residual_value = row.estimated_residual_value || 0
  disposeDialog.form.disposal_method = row.status === '已处置' ? normalizeDisposeMethod(row.disposal_method) : ''
  disposeDialog.form.retirement_date = row.retirement_date || todayText()
  disposeDialog.form.retirement_approval_no = row.retirement_approval_no || ''
  disposeDialog.form.dispose_recipient_user_id = row.dispose_recipient_user_id || ''
  disposeDialog.form.dispose_recipient_name = row.dispose_recipient_name || ''
  disposeDialog.form.disposal_remark = row.disposal_remark || ''
  disposeDialog.visible = true
}

async function dispose() {
  if (!disposeDialog.row) return
  if (!disposeDialog.form.retirement_date) return ElMessage.warning('请选择退役时间')
  if (!disposeDialog.form.retirement_approval_no.trim()) return ElMessage.warning('请填写退役审批单号')
  if (!disposeDialog.form.disposal_method) return ElMessage.warning('请选择实际处置方式')
  if (disposeDialog.form.disposal_method === '员工领用' && !disposeDialog.form.dispose_recipient_user_id) {
    ElMessage.warning('请选择报废领走员工')
    return
  }
  if (!disposeDialog.form.disposal_remark.trim()) return ElMessage.warning('请填写实际处置说明')
  const recipientText = disposeDialog.form.disposal_method === '员工领用' ? `，报废领走人：${disposeDialog.form.dispose_recipient_name || disposeDialog.form.dispose_recipient_user_id}` : ''
  await ElMessageBox.confirm(`确认登记 ${disposeDialog.row.asset_id} 的报废处置？退役时间：${disposeDialog.form.retirement_date}，实际处置方式：${disposeDialog.form.disposal_method}${recipientText}。登记后资产进入已处置终态。`, '确认登记', { type: 'warning' })
  await disposeScrapRequest(disposeDialog.row.id, disposeDialog.form)
  disposeDialog.visible = false
  ElMessage.success('报废资产已处置归档')
  await load()
}

function handleDisposeRecipientChange(userId) {
  const user = users.value.find(item => (item.user_id || item.username) === userId)
  disposeDialog.form.dispose_recipient_name = user ? (user.display_name || user.username || user.user_id || '') : ''
}

function normalizeDisposeMethod(method) {
  if (['报废', '变卖', '员工领用'].includes(method)) return method
  if (['出售', '转卖'].includes(method)) return '变卖'
  return '报废'
}

function userLabel(user) {
  return [user.display_name || user.username || user.user_id, user.dept_name || user.dept_id].filter(Boolean).join(' / ')
}

function todayText() {
  return new Date().toISOString().slice(0, 10)
}

function statusType(status) {
  if (status === '已处置') return 'info'
  if (status === '待处置') return 'warning'
  if (status === '已通过') return 'success'
  if (status === '已驳回') return 'danger'
  return 'warning'
}
</script>

<style scoped>
.asset-info {
  display: grid;
  gap: 4px;
}

.asset-info span {
  color: var(--muted);
  font-size: 12px;
}

.filter-card {
  margin-bottom: 12px;
}

.filter-grid {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(160px, 200px) auto;
  align-items: end;
  justify-content: start;
  gap: 12px;
}

.filter-grid :deep(.el-form-item) {
  margin-bottom: 0;
}

.filter-grid :deep(.el-date-editor),
.filter-grid :deep(.el-select) {
  width: 100%;
}

.dispose-form {
  margin-top: 16px;
}

.dispose-asset-summary {
  margin-top: 16px;
}

.disposal-method-segment {
  width: 100%;
}

.disposal-method-segment :deep(.el-segmented__group) {
  width: 100%;
}

.disposal-method-segment :deep(.el-segmented__item) {
  flex: 1;
  min-height: 40px;
}

.form-tip {
  width: 100%;
  margin-top: 6px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 980px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
