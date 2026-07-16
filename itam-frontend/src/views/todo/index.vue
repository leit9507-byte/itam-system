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
    <TodoAssetActions ref="todoAssetActionsRef" @completed="load" />
    <PurchaseAcceptanceDialog ref="purchaseAcceptanceRef" @completed="load" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approveScrapRequest, createScrapRequest, getScrapRequests } from '../../api/asset'
import { getPurchases } from '../../api/purchase'
import { finishRepairRecord, getRepairRecords } from '../../api/repair'
import { getTodoItems } from '../../api/todo'
import TodoAssetActions from '../../components/TodoAssetActions.vue'
import PurchaseAcceptanceDialog from '../../components/PurchaseAcceptanceDialog.vue'

const loading = ref(false)
const processingId = ref('')
const todos = ref([])
const filters = reactive({ keyword: '', type: '', priority: '' })
const pagination = reactive({ page: 1, pageSize: 10 })
const todoAssetActionsRef = ref(null)
const purchaseAcceptanceRef = ref(null)
const scrapDialog = reactive({
  visible: false,
  todo: null,
  form: { applicant: '资产管理员', disposal_method: '环保回收', estimated_residual_value: 0, reason: '' }
})

const typeOptions = [
  { label: '入职配置', value: 'onboarding_assign' },
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
    todos.value = await getTodoItems()
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
  if (await todoAssetActionsRef.value?.handle(row)) return
  if (row.type === 'scrap_request') return openScrapDialog(row)
  if (row.type === 'purchase_acceptance') return receivePurchaseTodo(row)
  if (row.type === 'scrap_approval') return approveScrapTodo(row)
  if (row.type === 'repair_followup') return finishRepairTodo(row)
  ElMessage.warning('暂不支持该类型待办的直接处理')
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

async function receivePurchaseTodo(row) {
  const purchase = await findPurchase(row.purchase_no)
  purchaseAcceptanceRef.value?.open(purchase)
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
