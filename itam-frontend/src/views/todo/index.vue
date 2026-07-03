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
            <el-button type="primary" link @click="goTodo(row)">去处理</el-button>
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTodoItems } from '../../api/todo'

const router = useRouter()
const loading = ref(false)
const todos = ref([])
const filters = reactive({ keyword: '', type: '', priority: '' })
const pagination = reactive({ page: 1, pageSize: 20 })

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

function goTodo(row) {
  router.push({ path: row.target_path, query: row.target_query || {} })
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
</style>
