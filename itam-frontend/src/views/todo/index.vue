<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">待办中心</h2>
        <p class="page-subtitle">集中处理入职配置、采购、验收、报废、离职回收和维修跟进事项</p>
      </div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </div>

    <div class="metric-grid">
      <el-card shadow="never"><el-statistic title="全部待办" :value="todos.length" /></el-card>
      <el-card shadow="never"><el-statistic title="高优先级" :value="countByPriority('high')" /></el-card>
      <el-card shadow="never"><el-statistic title="入职配置" :value="countByTypes(['onboarding_assign'])" /></el-card>
      <el-card shadow="never"><el-statistic title="资产回收/报废" :value="countByTypes(['scrap_approval', 'scrap_request', 'offboarding_reclaim'])" /></el-card>
    </div>

    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索单号/资产/说明/责任人" style="width: 280px" @input="resetPage" />
        <el-select v-model="filters.type" clearable placeholder="待办类型" style="width: 160px" @change="resetPage">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.priority" clearable placeholder="优先级" style="width: 130px" @change="resetPage">
          <el-option label="高" value="high" />
          <el-option label="中" value="medium" />
          <el-option label="低" value="low" />
        </el-select>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="pagedTodos" border stripe>
        <el-table-column label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)">{{ priorityLabel(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type_label" label="类型" width="120" />
        <el-table-column label="待办事项" min-width="280">
          <template #default="{ row }">
            <div class="todo-title">
              <strong>{{ row.title }}</strong>
              <span>{{ row.description }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="owner" label="责任人/处理人" width="150" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="110" />
        <el-table-column prop="created_at" label="产生时间" width="170" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :loading="processingId === row.id" @click="handleTodo(row)">处理</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !filteredTodos.length" description="暂无待办事项" />
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredTodos.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="resetPage"
        />
      </div>
    </el-card>

    <el-dialog v-model="assignDialog.visible" title="入职资产分配" width="620px">
      <el-alert :title="`为 ${assignDialog.todo?.name || assignDialog.todo?.owner || '员工'} 分配在库或闲置资产`" type="info" show-icon :closable="false" />
      <el-form :model="assignDialog.form" label-width="100px" class="todo-form">
        <el-form-item label="选择资产" required>
          <el-select v-model="assignDialog.form.asset_id" filterable remote reserve-keyword placeholder="搜索资产编号、名称、序列号" :remote-method="searchAssignableAssets" style="width: 100%">
            <el-option v-for="item in assignDialog.assets" :key="item.asset_id" :label="assetLabel(item)" :value="item.asset_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="使用位置">
          <el-input v-model="assignDialog.form.location" placeholder="可填写办公位置" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="assignDialog.form.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="processingId === assignDialog.todo?.id" @click="submitAssign">确认分配</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="scrapDialog.visible" title="提交报废审批" width="620px">
      <el-alert :title="scrapDialog.todo?.title || '提交报废审批'" type="warning" show-icon :closable="false" />
      <el-form :model="scrapDialog.form" label-width="110px" class="todo-form">
        <el-form-item label="申请人/部门">
          <el-input v-model="scrapDialog.form.applicant" />
        </el-form-item>
        <el-form-item label="处置方式">
          <el-select v-model="scrapDialog.form.disposal_method" style="width: 100%">
            <el-option label="环保回收" value="环保回收" />
            <el-option label="供应商回收" value="供应商回收" />
            <el-option label="内部拆件" value="内部拆件" />
            <el-option label="销毁处理" value="销毁处理" />
          </el-select>
        </el-form-item>
        <el-form-item label="预计残值">
          <el-input-number v-model="scrapDialog.form.estimated_residual_value" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="报废原因" required>
          <el-input v-model="scrapDialog.form.reason" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scrapDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="processingId === scrapDialog.todo?.id" @click="submitScrapRequest">提交审批</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approveScrapRequest, createScrapRequest, getAssets, getScrapRequests, inboundAsset, outboundAsset } from '../../api/asset'
import { approvePurchase, getPurchases, receivePurchase } from '../../api/purchase'
import { finishRepairRecord, getRepairRecords } from '../../api/repair'
import { getTodoItems } from '../../api/todo'
import { getUsers } from '../../api/user'

const loading = ref(false)
const processingId = ref('')
const todos = ref([])
const filters = reactive({ keyword: '', type: '', priority: '' })
const pagination = reactive({ page: 1, pageSize: 20 })
const users = ref([])
const assignDialog = reactive({
  visible: false,
  todo: null,
  assets: [],
  form: { asset_id: '', location: '', remark: '入职资产分配' }
})
const scrapDialog = reactive({
  visible: false,
  todo: null,
  form: { applicant: '资产管理员', disposal_method: '环保回收', estimated_residual_value: 0, reason: '' }
})

const typeOptions = [
  { label: '入职配置', value: 'onboarding_assign' },
  { label: '采购审批', value: 'purchase_approval' },
  { label: '采购验收', value: 'purchase_acceptance' },
  { label: '报废审批', value: 'scrap_approval' },
  { label: '报废申请', value: 'scrap_request' },
  { label: '离职回收', value: 'offboarding_reclaim' },
  { label: '维修跟进', value: 'repair_followup' }
]

const filteredTodos = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return todos.value.filter(item => {
    const hitKeyword = !keyword || [item.title, item.description, item.owner, item.status, item.type_label].join(' ').toLowerCase().includes(keyword)
    const hitType = !filters.type || item.type === filters.type
    const hitPriority = !filters.priority || item.priority === filters.priority
    return hitKeyword && hitType && hitPriority
  })
})

const pagedTodos = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  return filteredTodos.value.slice(start, start + pagination.pageSize)
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    const [todoRows, userRows] = await Promise.all([getTodoItems(), users.value.length ? Promise.resolve(users.value) : getUsers().catch(() => [])])
    todos.value = todoRows
    users.value = userRows
    resetPage()
  } catch (error) {
    ElMessage.error(`待办加载失败：${error?.message || '请稍后重试'}`)
  } finally {
    loading.value = false
  }
}

function countByPriority(priority) {
  return todos.value.filter(item => item.priority === priority).length
}

function countByTypes(types) {
  return todos.value.filter(item => types.includes(item.type)).length
}

function resetPage() {
  pagination.page = 1
}

function resetFilters() {
  filters.keyword = ''
  filters.type = ''
  filters.priority = ''
  resetPage()
}

function priorityLabel(priority) {
  return { high: '高', medium: '中', low: '低' }[priority] || '-'
}

function priorityType(priority) {
  return { high: 'danger', medium: 'warning', low: 'info' }[priority] || 'info'
}

async function handleTodo(row) {
  if (row.type === 'onboarding_assign') return openAssignDialog(row)
  if (row.type === 'scrap_request') return openScrapDialog(row)
  if (row.type === 'purchase_approval') return approvePurchaseTodo(row)
  if (row.type === 'purchase_acceptance') return receivePurchaseTodo(row)
  if (row.type === 'scrap_approval') return approveScrapTodo(row)
  if (row.type === 'offboarding_reclaim') return reclaimAssetTodo(row)
  if (row.type === 'repair_followup') return finishRepairTodo(row)
  ElMessage.warning('暂不支持该类型待办的直接处理')
}

async function openAssignDialog(row) {
  assignDialog.todo = row
  Object.assign(assignDialog.form, {
    asset_id: '',
    location: '',
    remark: '入职资产分配'
  })
  assignDialog.assets = await loadAssignableAssets('')
  assignDialog.visible = true
}

async function searchAssignableAssets(keyword = '') {
  assignDialog.assets = await loadAssignableAssets(keyword)
}

async function loadAssignableAssets(keyword = '') {
  const { list } = await getAssets({ keyword, page: 1, page_size: 50 })
  return list.filter(item => ['in_stock', 'idle'].includes(item.status))
}

async function submitAssign() {
  if (!assignDialog.form.asset_id) return ElMessage.warning('请选择要分配的资产')
  const todo = assignDialog.todo
  processingId.value = todo.id
  try {
    const user = users.value.find(item => item.user_id === todo.user_id || item.username === todo.username)
    await outboundAsset(assignDialog.form.asset_id, {
      outboundTarget: 'user',
      toStatus: 'in_use',
      owner_user_id: user?.user_id || todo.user_id || todo.username,
      owner_name: user?.display_name || todo.name || todo.owner,
      dept_id: user?.dept_id || user?.dept_name || '',
      dept_name: user?.dept_name || user?.dept_id || '',
      location: assignDialog.form.location,
      remark: assignDialog.form.remark || '入职资产分配'
    })
    ElMessage.success('入职资产已分配')
    assignDialog.visible = false
    await load()
  } catch (error) {
    ElMessage.error(`分配失败：${error?.message || '请稍后重试'}`)
  } finally {
    processingId.value = ''
  }
}

function openScrapDialog(row) {
  scrapDialog.todo = row
  Object.assign(scrapDialog.form, {
    applicant: row.owner || '资产管理员',
    disposal_method: '环保回收',
    estimated_residual_value: 0,
    reason: ''
  })
  scrapDialog.visible = true
}

async function submitScrapRequest() {
  if (!scrapDialog.form.reason.trim()) return ElMessage.warning('请填写报废原因')
  const todo = scrapDialog.todo
  processingId.value = todo.id
  try {
    await createScrapRequest(todo.asset_id, scrapDialog.form)
    ElMessage.success('报废审批已提交')
    scrapDialog.visible = false
    await load()
  } catch (error) {
    ElMessage.error(`提交失败：${error?.message || '请稍后重试'}`)
  } finally {
    processingId.value = ''
  }
}

async function approvePurchaseTodo(row) {
  const confirmed = await confirmAction(`确认通过采购单 ${row.purchase_no} 的审批？`, '采购审批')
  if (!confirmed) return
  await runTodoAction(row, async () => {
    const purchase = await findPurchase(row.purchase_no)
    await approvePurchase(purchase)
    ElMessage.success('采购审批已通过')
  })
}

async function receivePurchaseTodo(row) {
  const confirmed = await confirmAction(`确认验收采购单 ${row.purchase_no} 并自动入库？`, '采购验收')
  if (!confirmed) return
  await runTodoAction(row, async () => {
    const result = await receivePurchase(row.purchase_no)
    ElMessage.success(`采购验收完成，生成 ${result.generated_assets} 个资产`)
  })
}

async function approveScrapTodo(row) {
  const confirmed = await confirmAction(`确认通过 ${row.asset_id} 的报废审批？通过后资产将正式报废。`, '报废审批')
  if (!confirmed) return
  await runTodoAction(row, async () => {
    const request = await findScrapRequest(row)
    await approveScrapRequest(request.id, '资产负责人')
    ElMessage.success('报废审批已通过')
  })
}

async function reclaimAssetTodo(row) {
  const confirmed = await confirmAction(`确认回收 ${row.asset_id} 到在库状态？`, '离职资产回收')
  if (!confirmed) return
  await runTodoAction(row, async () => {
    await inboundAsset(row.asset_id, { location: '', remark: '离职资产收回' })
    ElMessage.success('离职资产已回收')
  })
}

async function finishRepairTodo(row) {
  const confirmed = await confirmAction(`确认完成维修单 ${row.repair_no || row.repair_id}？资产将恢复为在库。`, '维修跟进')
  if (!confirmed) return
  await runTodoAction(row, async () => {
    const repair = await findRepair(row)
    await finishRepairRecord(repair.id, { next_status: 'in_stock', remark: '维修完成，入库待分配' })
    ElMessage.success('维修已完成')
  })
}

async function runTodoAction(row, action) {
  processingId.value = row.id
  try {
    await action()
    await load()
  } catch (error) {
    ElMessage.error(`处理失败：${error?.message || '请稍后重试'}`)
  } finally {
    processingId.value = ''
  }
}

async function findPurchase(purchaseNo) {
  const { list } = await getPurchases({ page: 1, page_size: 500 })
  const purchase = list.find(item => item.purchase_no === purchaseNo)
  if (!purchase) throw new Error('未找到采购单')
  return purchase
}

async function findScrapRequest(row) {
  if (row.request_id) return { id: row.request_id }
  const { list } = await getScrapRequests({ status: '审批中', page: 1, page_size: 500 })
  const request = list.find(item => item.request_no === row.request_no || item.asset_id === row.asset_id)
  if (!request) throw new Error('未找到报废申请')
  return request
}

async function findRepair(row) {
  if (row.repair_id) return { id: row.repair_id }
  const { list } = await getRepairRecords({ status: '维修中', page: 1, page_size: 500 })
  const repair = list.find(item => item.repair_no === row.repair_no || item.asset_id === row.asset_id)
  if (!repair) throw new Error('未找到维修单')
  return repair
}

async function confirmAction(message, title) {
  return ElMessageBox.confirm(message, title, { type: 'warning' }).then(() => true).catch(() => false)
}

function assetLabel(item) {
  return `${item.asset_id} / ${item.name || '-'} / ${item.sn || '-'} / ${item.location || '未填写位置'}`
}
</script>

<style scoped>
.filter-card {
  margin-top: -4px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.todo-title {
  display: grid;
  gap: 4px;
}

.todo-title span {
  color: var(--muted);
  font-size: 12px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.todo-form {
  margin-top: 14px;
}
</style>
