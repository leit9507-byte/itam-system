<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">报废处置登记</h2>
        <p class="page-subtitle">资产实际完成处置后，登记退役时间、处置方式、审批单号和处理结果</p>
      </div>
      <div class="header-actions">
        <el-button :disabled="!batchDisposableRows.length" type="warning" @click="openBatchDispose('变卖')">批量变卖</el-button>
        <el-button :disabled="!batchDisposableRows.length" type="primary" @click="openBatchDispose()">批量退役登记</el-button>
        <el-button @click="load">刷新</el-button>
      </div>
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
        <el-form-item label="处理手段">
          <el-select v-model="filters.disposalMethod" clearable placeholder="全部处理手段" @change="refresh">
            <el-option label="员工领用" value="员工领用" />
            <el-option label="变卖" value="变卖" />
            <el-option label="报废" value="报废" />
          </el-select>
        </el-form-item>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-alert v-if="selected.length" :title="`已选择 ${selected.length} 张退役单，可退役登记 ${batchDisposableRows.length} 台资产`" type="info" show-icon :closable="false" class="selection-alert" />
      <el-table :data="requests" border stripe @selection-change="selected = $event">
        <el-table-column type="selection" width="48" />
        <el-table-column type="expand">
          <template #default="{ row }">
            <el-table :data="row.items || []" border size="small" class="inner-table">
              <el-table-column prop="registration_no" label="登记单号" width="140" />
              <el-table-column prop="asset_no" label="资产编号" width="140">
                <template #default="{ row: item }">{{ item.asset_no || '-' }}</template>
              </el-table-column>
              <el-table-column label="资产信息" min-width="260">
                <template #default="{ row: item }">
                  <div class="asset-info">
                    <strong>{{ item.asset_name || '-' }}</strong>
                    <span>{{ item.category || '-' }} / {{ item.brand || '-' }} / {{ item.model || '-' }}</span>
                    <span>SN：{{ item.sn || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="owner_user_id" label="责任人" width="130">
                <template #default="{ row: item }">{{ item.owner_user_id || '-' }}</template>
              </el-table-column>
              <el-table-column prop="dept_id" label="部门" width="140" show-overflow-tooltip />
              <el-table-column prop="estimated_residual_value" label="预计残值" width="120">
                <template #default="{ row: item }">￥{{ item.estimated_residual_value.toLocaleString() }}</template>
              </el-table-column>
              <el-table-column prop="purchase_date" label="采购时间" width="120">
                <template #default="{ row: item }">{{ item.purchase_date || '-' }}</template>
              </el-table-column>
              <el-table-column prop="purchase_price" label="采购价格" width="120">
                <template #default="{ row: item }">￥{{ Number(item.purchase_price || 0).toLocaleString() }}</template>
              </el-table-column>
              <el-table-column prop="final_residual_value" label="实际残值" width="120">
                <template #default="{ row: item }">￥{{ item.final_residual_value.toLocaleString() }}</template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row: item }"><el-tag :type="statusType(item.status)">{{ item.status }}</el-tag></template>
              </el-table-column>
            </el-table>
          </template>
        </el-table-column>
        <el-table-column prop="flow_no" label="流程单号" width="140" />
        <el-table-column prop="company" label="公司" width="120" show-overflow-tooltip />
        <el-table-column prop="asset_no" label="资产数量" width="140">
          <template #default="{ row }">{{ row.asset_no || '-' }}</template>
        </el-table-column>
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
              <span>采购时间：{{ row.purchase_date || '-' }}</span>
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
        <el-table-column label="接收方/供应商" width="140" show-overflow-tooltip>
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
            <el-button type="primary" link :disabled="!flowDisposableRows(row).length" @click="openDispose(row)">登记处置</el-button>
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

    <el-dialog v-model="disposeDialog.visible" :title="disposeDialogTitle" width="92vw" class="dispose-dialog">
      <el-alert
        :title="disposeDialogRows.length > 1 ? `本次将登记 ${disposeDialogRows.length} 台资产的退役处置` : '本次登记当前这一台资产'"
        :description="disposeDialogRows.length > 1 ? '每台资产可单独填写退役时间、审批单号、处置方式、接收方、实际残值和说明；确认后资产状态保持已报废，报废单标记为已处置。' : singleDisposeDescription"
        type="warning"
        show-icon
        :closable="false"
      />
      <el-table v-if="disposeDialogRows.length > 1" :data="disposeDialogRows" border stripe max-height="420" class="dispose-asset-summary">
        <el-table-column prop="registration_no" label="登记单号" width="140" />
        <el-table-column prop="asset_no" label="资产编号" width="140">
          <template #default="{ row }">{{ row.asset_no || '-' }}</template>
        </el-table-column>
        <el-table-column prop="asset_name" label="资产名称" min-width="190" show-overflow-tooltip />
        <el-table-column prop="sn" label="序列号" width="150">
          <template #default="{ row }">{{ row.sn || '-' }}</template>
        </el-table-column>
        <el-table-column prop="purchase_date" label="采购时间" width="120">
          <template #default="{ row }">{{ row.purchase_date || '-' }}</template>
        </el-table-column>
        <el-table-column prop="purchase_price" label="采购价格" width="120">
          <template #default="{ row }">￥{{ Number(row.purchase_price || 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="estimated_residual_value" label="预计残值" width="120">
          <template #default="{ row }">¥{{ row.estimated_residual_value.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="退役时间" width="160">
          <template #default="{ row }">
            <el-date-picker v-model="itemForm(row).retirement_date" type="date" value-format="YYYY-MM-DD" style="width: 132px" />
          </template>
        </el-table-column>
        <el-table-column label="审批单号" width="180">
          <template #default="{ row }">
            <el-input v-model="itemForm(row).retirement_approval_no" placeholder="审批单号" />
          </template>
        </el-table-column>
        <el-table-column label="处置方式" width="130">
          <template #default="{ row }">
            <el-select v-model="itemForm(row).disposal_method" placeholder="选择" @change="handleItemMethodChange(row)">
              <el-option label="报废" value="报废" />
              <el-option label="变卖" value="变卖" />
              <el-option label="员工领用" value="员工领用" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="接收方/供应商" width="220">
          <template #default="{ row }">
            <el-select
              v-if="itemForm(row).disposal_method === '员工领用'"
              v-model="itemForm(row).dispose_recipient_user_id"
              filterable
              clearable
              placeholder="选择员工"
              @change="value => handleItemRecipientChange(row, value)"
            >
              <el-option v-for="user in users" :key="user.user_id || user.username" :label="userLabel(user)" :value="user.user_id || user.username" />
            </el-select>
            <el-select
              v-else-if="itemForm(row).disposal_method === '变卖'"
              v-model="itemForm(row).dispose_recipient_name"
              filterable
              clearable
              allow-create
              default-first-option
              placeholder="选择或填写供应商"
            >
              <el-option v-for="supplier in activeSuppliers" :key="supplier.id || supplier.name" :label="supplierLabel(supplier)" :value="supplier.name" />
            </el-select>
            <span v-else class="muted-text">无需填写</span>
          </template>
        </el-table-column>
        <el-table-column label="实际残值" width="140">
          <template #default="{ row }">
            <el-input-number v-model="itemForm(row).final_residual_value" :min="0" :precision="2" :controls="false" style="width: 110px" />
          </template>
        </el-table-column>
        <el-table-column label="处置说明" min-width="220">
          <template #default="{ row }">
            <el-input v-model="itemForm(row).disposal_remark" placeholder="可选" />
          </template>
        </el-table-column>
      </el-table>
      <el-descriptions v-else-if="disposeDialog.row" :column="2" border class="dispose-asset-summary">
        <el-descriptions-item label="资产编号">{{ disposeDialog.row.asset_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="序列号">{{ disposeDialog.row.sn || '-' }}</el-descriptions-item>
        <el-descriptions-item label="资产名称">{{ disposeDialog.row.asset_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="登记单号">{{ disposeDialog.row.request_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采购时间">{{ disposeDialog.row.purchase_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采购价格">￥{{ Number(disposeDialog.row.purchase_price || 0).toLocaleString() }}</el-descriptions-item>
      </el-descriptions>
      <el-form v-if="disposeDialogRows.length <= 1" :model="disposeDialog.form" label-width="110px" class="dispose-form">
        <el-form-item label="退役时间" required>
          <el-date-picker v-model="disposeDialog.form.retirement_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="退役审批单号" required>
          <el-input v-model="disposeDialog.form.retirement_approval_no" placeholder="填写退役/报废审批单号" />
        </el-form-item>
        <el-form-item label="实际处置方式" required>
          <el-segmented v-model="disposeDialog.form.disposal_method" :options="disposalMethodOptions" class="disposal-method-segment" />
          <div class="form-tip">当前选择仅作用于上方这一台资产。</div>
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
        <el-form-item v-if="disposeDialog.form.disposal_method === '变卖'" label="处理供应商">
          <el-select
            v-model="disposeDialog.form.dispose_recipient_name"
            filterable
            clearable
            allow-create
            default-first-option
            placeholder="选择或填写回收/购买供应商"
            style="width: 100%"
          >
            <el-option
              v-for="supplier in activeSuppliers"
              :key="supplier.id || supplier.name"
              :label="supplierLabel(supplier)"
              :value="supplier.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="finalResidualLabel">
          <el-input-number v-model="disposeDialog.form.final_residual_value" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="处置说明">
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
import { disposeScrapRequest, getScrapFlows, getScrapRequests } from '../../api/asset'
import { getSuppliers } from '../../api/supplier'
import { getUsers } from '../../api/user'

const requests = ref([])
const allRequests = ref([])
const selected = ref([])
const users = ref([])
const suppliers = ref([])
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const filters = reactive({ createdRange: [], disposalMethod: '' })
const disposeDialog = reactive({
  visible: false,
  row: null,
  rows: [],
  form: {
    final_residual_value: 0,
    disposal_method: '',
    retirement_date: '',
    retirement_approval_no: '',
    dispose_recipient_user_id: '',
    dispose_recipient_name: '',
    disposal_remark: ''
  },
  itemForms: {}
})
const SCRAP_SUMMARY_LIMIT = 500
const disposalMethodOptions = [
  { label: '报废', value: '报废' },
  { label: '变卖', value: '变卖' },
  { label: '员工领用', value: '员工领用' }
]

const totalResidual = computed(() => allRequests.value.reduce((sum, item) => sum + Number(item.estimated_residual_value || 0), 0))
const pendingDisposalCount = computed(() => allRequests.value.filter(item => ['待处置', '审批中', '已通过'].includes(item.status)).length)
const activeSuppliers = computed(() => suppliers.value.filter(item => item.status !== '停用'))
const batchDisposableRows = computed(() => selected.value.flatMap(flowDisposableRows))
const disposeDialogRows = computed(() => disposeDialog.rows?.length ? disposeDialog.rows : (disposeDialog.row ? [disposeDialog.row] : []))
const disposeDialogTitle = computed(() => disposeDialogRows.value.length > 1 ? `批量退役登记 / ${disposeDialogRows.value.length} 台资产` : (disposeDialog.row ? `报废处置登记 / ${disposeDialog.row.asset_no || disposeDialog.row.asset_id}` : '报废处置登记'))
const singleDisposeDescription = computed(() => disposeDialog.row ? `${disposeDialog.row.asset_no || disposeDialog.row.asset_id} / ${disposeDialog.row.asset_name || '-'}；确认后资产状态保持已报废，报废单标记为已处置。` : '')
const finalResidualLabel = computed(() => '实际残值')
const disposeRemarkPlaceholder = computed(() => {
  if (disposeDialog.form.disposal_method === '员工领用') return '例如：报废资产由员工领走，已签收确认'
  if (disposeDialog.form.disposal_method === '变卖') return '例如：变卖给回收商，交易单号 XXX'
  return '例如：报废销毁、环保回收，回收单号 XXX'
})

onMounted(async () => {
  await Promise.all([load(), loadUsers(), loadSuppliers()])
})

async function loadUsers() {
  users.value = await getUsers().catch(() => [])
}

async function loadSuppliers() {
  suppliers.value = await getSuppliers().catch(() => [])
}

async function load() {
  const params = {
    disposal_method: filters.disposalMethod || '',
    created_from: filters.createdRange?.[0] || '',
    created_to: filters.createdRange?.[1] || ''
  }
  const [paged, all] = await Promise.all([
    getScrapFlows({ ...params, page: pagination.page, page_size: pagination.pageSize }),
    getScrapRequests({ ...params, page: 1, page_size: SCRAP_SUMMARY_LIMIT })
  ])
  requests.value = paged.list
  pagination.total = paged.total
  allRequests.value = all.list
  selected.value = []
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
  filters.disposalMethod = ''
  pagination.page = 1
  await load()
}

function openDispose(row) {
  const rows = flowDisposableRows(row)
  if (!rows.length) return ElMessage.warning('当前退役单没有可登记处置的资产')
  const first = rows[0]
  disposeDialog.row = rows.length === 1 ? first : null
  disposeDialog.rows = rows
  resetItemForms(rows, rows.length === 1 ? '' : normalizeDisposeMethod(first.disposal_method))
  disposeDialog.form.final_residual_value = rows.reduce((sum, item) => sum + Number(item.estimated_residual_value || 0), 0)
  disposeDialog.form.disposal_method = rows.length === 1 && first.status === '已处置' ? normalizeDisposeMethod(first.disposal_method) : ''
  disposeDialog.form.retirement_date = first.retirement_date || todayText()
  disposeDialog.form.retirement_approval_no = first.retirement_approval_no || ''
  disposeDialog.form.dispose_recipient_user_id = first.dispose_recipient_user_id || ''
  disposeDialog.form.dispose_recipient_name = first.dispose_recipient_name || ''
  disposeDialog.form.disposal_remark = first.disposal_remark || ''
  disposeDialog.visible = true
}

function openBatchDispose(method = '') {
  const rows = batchDisposableRows.value
  if (!rows.length) return ElMessage.warning('请选择待处置、审批中或已通过的报废记录')
  disposeDialog.row = null
  disposeDialog.rows = rows
  resetItemForms(rows, method)
  disposeDialog.form.final_residual_value = rows.reduce((sum, item) => sum + Number(item.estimated_residual_value || 0), 0)
  disposeDialog.form.disposal_method = method
  disposeDialog.form.retirement_date = todayText()
  disposeDialog.form.retirement_approval_no = ''
  disposeDialog.form.dispose_recipient_user_id = ''
  disposeDialog.form.dispose_recipient_name = ''
  disposeDialog.form.disposal_remark = method === '变卖' ? '批量变卖处置，按资产预计残值比例分摊变卖金额' : ''
  disposeDialog.visible = true
}

async function dispose() {
  const rows = disposeDialogRows.value
  if (!rows.length) return
  if (rows.length > 1) {
    await disposeItems(rows)
    return
  }
  if (!disposeDialog.form.retirement_date) return ElMessage.warning('请选择退役时间')
  if (!disposeDialog.form.retirement_approval_no.trim()) return ElMessage.warning('请填写退役审批单号')
  if (!disposeDialog.form.disposal_method) return ElMessage.warning('请选择实际处置方式')
  if (disposeDialog.form.disposal_method === '员工领用' && !disposeDialog.form.dispose_recipient_user_id) {
    ElMessage.warning('请选择报废领走员工')
    return
  }
  const recipientText = disposalRecipientConfirmText()
  const targetText = rows.length > 1 ? `${rows.length} 台资产` : `${rows[0].asset_no || rows[0].asset_id}`
  await ElMessageBox.confirm(`确认登记 ${targetText} 的报废处置？退役时间：${disposeDialog.form.retirement_date}，实际处置方式：${disposeDialog.form.disposal_method}${recipientText}。登记后资产状态保持已报废，报废单标记为已处置。`, '确认登记', { type: 'warning' })
  await disposeScrapRequest(rows[0].id, { ...disposeDialog.form, retirement_flow_no: rows[0].retirement_flow_no || rows[0].flow_no || '' })
  ElMessage.success('报废资产已处置归档')
  disposeDialog.visible = false
  await load()
}

async function disposeItems(rows) {
  const invalid = rows.find(row => {
    const form = itemForm(row)
    return !form.retirement_date || !form.retirement_approval_no.trim() || !form.disposal_method || (form.disposal_method === '员工领用' && !form.dispose_recipient_user_id)
  })
  if (invalid) {
    ElMessage.warning(`请补全 ${invalid.asset_no || invalid.asset_id} 的退役时间、审批单号、处置方式和必要接收方`)
    return
  }
  await ElMessageBox.confirm(`确认逐条登记 ${rows.length} 台资产的报废处置？每台资产会按表格中填写的处置方式、接收方和实际残值保存。`, '确认登记', { type: 'warning' })
  let success = 0
  const errors = []
  for (const row of rows) {
    try {
      await disposeScrapRequest(row.id, { ...itemForm(row), retirement_flow_no: row.retirement_flow_no || row.flow_no || '' })
      success += 1
    } catch (error) {
      errors.push(`${row.asset_no || row.asset_id}：${error?.message || '登记失败'}`)
    }
  }
  disposeDialog.visible = false
  if (errors.length) ElMessage.warning(`退役登记完成 ${success} 条，失败 ${errors.length} 条：${errors[0]}`)
  else ElMessage.success(`已完成 ${success} 台资产退役登记`)
  await load()
}

function resetItemForms(rows, method = '') {
  disposeDialog.itemForms = {}
  rows.forEach(row => {
    const normalizedMethod = method || normalizeDisposeMethod(row.disposal_method)
    disposeDialog.itemForms[row.id] = {
      final_residual_value: Number(row.final_residual_value || row.estimated_residual_value || 0),
      disposal_method: normalizedMethod,
      retirement_date: row.retirement_date || todayText(),
      retirement_approval_no: row.retirement_approval_no || '',
      dispose_recipient_user_id: row.dispose_recipient_user_id || '',
      dispose_recipient_name: row.dispose_recipient_name || '',
      disposal_remark: row.disposal_remark || ''
    }
  })
}

function itemForm(row) {
  if (!disposeDialog.itemForms[row.id]) {
    disposeDialog.itemForms[row.id] = {
      final_residual_value: Number(row.final_residual_value || row.estimated_residual_value || 0),
      disposal_method: normalizeDisposeMethod(row.disposal_method),
      retirement_date: row.retirement_date || todayText(),
      retirement_approval_no: row.retirement_approval_no || '',
      dispose_recipient_user_id: row.dispose_recipient_user_id || '',
      dispose_recipient_name: row.dispose_recipient_name || '',
      disposal_remark: row.disposal_remark || ''
    }
  }
  return disposeDialog.itemForms[row.id]
}

function handleItemMethodChange(row) {
  const form = itemForm(row)
  form.dispose_recipient_user_id = ''
  form.dispose_recipient_name = ''
}

function handleItemRecipientChange(row, userId) {
  const user = users.value.find(item => (item.user_id || item.username) === userId)
  itemForm(row).dispose_recipient_name = user ? (user.display_name || user.username || user.user_id || '') : ''
}

function handleDisposeRecipientChange(userId) {
  const user = users.value.find(item => (item.user_id || item.username) === userId)
  disposeDialog.form.dispose_recipient_name = user ? (user.display_name || user.username || user.user_id || '') : ''
}

function disposalRecipientConfirmText() {
  if (disposeDialog.form.disposal_method === '员工领用') {
    return `，报废领走人：${disposeDialog.form.dispose_recipient_name || disposeDialog.form.dispose_recipient_user_id}`
  }
  if (disposeDialog.form.disposal_method === '变卖' && disposeDialog.form.dispose_recipient_name) {
    return `，处理供应商：${disposeDialog.form.dispose_recipient_name}`
  }
  return ''
}

function normalizeDisposeMethod(method) {
  if (['报废', '变卖', '员工领用'].includes(method)) return method
  if (['出售', '转卖'].includes(method)) return '变卖'
  return '报废'
}

function isDisposable(row) {
  return row && !['已处置', '已驳回'].includes(row.status)
}

function flowDisposableRows(row) {
  const rows = row?.items?.length ? row.items : (row ? [row] : [])
  return rows.filter(isDisposable)
}

function userLabel(user) {
  return [user.display_name || user.username || user.user_id, user.dept_name || user.dept_id].filter(Boolean).join(' / ')
}

function supplierLabel(supplier) {
  const meta = [supplier.contact, supplier.phone].filter(Boolean).join(' / ')
  return meta ? `${supplier.name} (${meta})` : supplier.name
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

.dispose-dialog :deep(.el-dialog__body) {
  overflow-x: auto;
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

.muted-text {
  color: var(--muted);
  font-size: 12px;
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
