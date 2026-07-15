<template>
  <div class="page log-center-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">日志中心</h2>
        <p class="page-subtitle">集中查看操作日志和错误日志</p>
      </div>
      <div class="toolbar">
        <el-button :loading="activeTab === 'operation' ? loading : errorLoading" @click="activeTab === 'operation' ? load() : loadErrors()">刷新</el-button>
        <el-button v-if="activeTab === 'operation'" type="primary" :loading="exporting" @click="handleExport">导出 CSV</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="log-tabs" @tab-change="handleTabChange">
      <el-tab-pane label="操作日志" name="operation">
        <el-card shadow="never" class="filter-card">
          <el-form :model="filters" label-width="72px" class="filter-form">
            <el-form-item label="模块">
              <el-select v-model="filters.module" clearable filterable placeholder="全部模块" @change="refresh">
                <el-option v-for="item in moduleOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="动作">
              <el-input v-model="filters.action" clearable placeholder="例如 create / approve" @keyup.enter="refresh" />
            </el-form-item>
            <el-form-item label="操作人">
              <el-input v-model="filters.operator" clearable placeholder="姓名/账号/角色" @keyup.enter="refresh" />
            </el-form-item>
            <el-form-item label="关键字">
              <el-input v-model="filters.keyword" clearable placeholder="对象、摘要、详情" @keyup.enter="refresh" />
            </el-form-item>
            <el-form-item label="时间">
              <el-date-picker
                v-model="filters.dateRange"
                type="daterange"
                value-format="YYYY-MM-DD"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                @change="refresh"
              />
            </el-form-item>
            <el-form-item label=" ">
              <div class="filter-actions">
                <el-button type="primary" @click="refresh">查询</el-button>
                <el-button @click="resetFilters">重置</el-button>
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never">
          <el-table :data="rows" border stripe v-loading="loading" empty-text="暂无操作日志">
            <el-table-column prop="created_at" label="时间" width="170" />
            <el-table-column prop="module" label="模块" width="110">
              <template #default="{ row }">
                <el-tag type="info">{{ moduleLabel(row.module) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="action" label="动作" width="150" show-overflow-tooltip />
            <el-table-column prop="target_type" label="对象类型" width="130" show-overflow-tooltip />
            <el-table-column prop="target_id" label="对象ID" width="150" show-overflow-tooltip />
            <el-table-column prop="operator" label="操作人" width="170" show-overflow-tooltip />
            <el-table-column prop="summary" label="摘要" min-width="260" show-overflow-tooltip />
            <el-table-column label="详情" width="90" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row, '操作日志详情')">查看</el-button>
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
              @size-change="handleSizeChange"
              @current-change="load"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="错误日志" name="error">
        <el-card shadow="never" class="filter-card">
          <el-form :model="errorFilters" label-width="72px" class="filter-form error-filter-form">
            <el-form-item label="关键字">
              <el-input v-model="errorFilters.keyword" clearable placeholder="错误信息、对象、详情" @keyup.enter="refreshErrors" />
            </el-form-item>
            <el-form-item label="时间">
              <el-date-picker
                v-model="errorFilters.dateRange"
                type="daterange"
                value-format="YYYY-MM-DD"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                @change="refreshErrors"
              />
            </el-form-item>
            <el-form-item label=" ">
              <div class="filter-actions">
                <el-button type="primary" @click="refreshErrors">查询</el-button>
                <el-button @click="resetErrorFilters">重置</el-button>
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never">
          <el-table :data="errorRows" border stripe v-loading="errorLoading" empty-text="暂无错误日志">
            <el-table-column prop="created_at" label="时间" width="170" />
            <el-table-column prop="module" label="模块" width="110">
              <template #default="{ row }">
                <el-tag type="danger">{{ moduleLabel(row.module) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="action" label="动作" width="150" show-overflow-tooltip />
            <el-table-column prop="target_id" label="对象ID" width="150" show-overflow-tooltip />
            <el-table-column prop="operator" label="操作人" width="170" show-overflow-tooltip />
            <el-table-column prop="summary" label="错误摘要" min-width="300" show-overflow-tooltip />
            <el-table-column label="详情" width="90" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row, '错误日志详情')">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="errorPagination.page"
              v-model:page-size="errorPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="errorPagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleErrorSizeChange"
              @current-change="loadErrors"
            />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="detailDrawer.visible" :title="detailDrawer.title" size="560px">
      <el-descriptions v-if="detailDrawer.row" :column="1" border>
        <el-descriptions-item label="时间">{{ detailDrawer.row.created_at }}</el-descriptions-item>
        <el-descriptions-item label="模块">{{ moduleLabel(detailDrawer.row.module) }} / {{ detailDrawer.row.module }}</el-descriptions-item>
        <el-descriptions-item label="动作">{{ detailDrawer.row.action }}</el-descriptions-item>
        <el-descriptions-item label="对象">{{ detailDrawer.row.target_type || '-' }} / {{ detailDrawer.row.target_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ detailDrawer.row.operator || '-' }}</el-descriptions-item>
        <el-descriptions-item label="摘要">{{ detailDrawer.row.summary || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div class="detail-block">
        <span>原始详情</span>
        <pre>{{ formattedDetail }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { exportOperationLogs, getErrorLogs, getOperationLogs } from '../../api/ops'

const activeTab = ref('operation')
const rows = ref([])
const loading = ref(false)
const exporting = ref(false)
const filters = reactive({ module: '', action: '', operator: '', keyword: '', dateRange: [] })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const errorRows = ref([])
const errorLoading = ref(false)
const errorLoaded = ref(false)
const errorFilters = reactive({ keyword: '', dateRange: [] })
const errorPagination = reactive({ page: 1, pageSize: 10, total: 0 })

const detailDrawer = reactive({ visible: false, row: null, title: '日志详情' })
const moduleOptions = [
  { label: '资产', value: 'asset' },
  { label: '采购', value: 'purchase' },
  { label: '维修', value: 'repair' },
  { label: '报废', value: 'scrap' },
  { label: '盘点', value: 'stocktake' },
  { label: '文件', value: 'file' },
  { label: '审批', value: 'approval' },
  { label: '权限', value: 'rbac' },
  { label: '人员/身份源', value: 'identity' },
  { label: '运维', value: 'ops' },
  { label: '飞书', value: 'feishu' }
]

const formattedDetail = computed(() => {
  const value = detailDrawer.row?.detail
  if (!value) return '-'
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    const result = await getOperationLogs(queryParams())
    rows.value = result.list || []
    pagination.total = result.total || 0
  } finally {
    loading.value = false
  }
}

async function loadErrors() {
  errorLoading.value = true
  try {
    const result = await getErrorLogs(errorQueryParams())
    errorRows.value = result.list || []
    errorPagination.total = result.total || 0
    errorLoaded.value = true
  } finally {
    errorLoading.value = false
  }
}

function queryParams(extra = {}) {
  const [start, end] = filters.dateRange || []
  return {
    page: pagination.page,
    page_size: pagination.pageSize,
    module: filters.module || undefined,
    action: filters.action || undefined,
    operator: filters.operator || undefined,
    keyword: filters.keyword || undefined,
    start: start || undefined,
    end: end || undefined,
    ...extra
  }
}

function errorQueryParams() {
  const [start, end] = errorFilters.dateRange || []
  return {
    page: errorPagination.page,
    page_size: errorPagination.pageSize,
    keyword: errorFilters.keyword || undefined,
    start: start || undefined,
    end: end || undefined
  }
}

function refresh() {
  pagination.page = 1
  load()
}

function refreshErrors() {
  errorPagination.page = 1
  loadErrors()
}

function resetFilters() {
  Object.assign(filters, { module: '', action: '', operator: '', keyword: '', dateRange: [] })
  refresh()
}

function resetErrorFilters() {
  Object.assign(errorFilters, { keyword: '', dateRange: [] })
  refreshErrors()
}

function handleSizeChange() {
  pagination.page = 1
  load()
}

function handleErrorSizeChange() {
  errorPagination.page = 1
  loadErrors()
}

function handleTabChange(name) {
  if (name === 'error' && !errorLoaded.value) {
    loadErrors()
  }
}

async function handleExport() {
  exporting.value = true
  try {
    await exportOperationLogs(queryParams({ limit: 20000 }))
    ElMessage.success('操作日志已导出')
  } finally {
    exporting.value = false
  }
}

function openDetail(row, title) {
  detailDrawer.row = row
  detailDrawer.title = title
  detailDrawer.visible = true
}

function moduleLabel(value) {
  return moduleOptions.find(item => item.value === value)?.label || value || '-'
}
</script>

<style scoped>
.log-center-page {
  min-width: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.log-tabs {
  margin-top: 4px;
}

.filter-card {
  margin-bottom: 14px;
}

.filter-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(220px, 1fr));
  gap: 0 12px;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.filter-form :deep(.el-select),
.filter-form :deep(.el-date-editor) {
  width: 100%;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
  overflow-x: auto;
}

.detail-block {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}

.detail-block > span {
  color: var(--muted);
  font-size: 13px;
}

.detail-block pre {
  max-height: 46vh;
  overflow: auto;
  margin: 0;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #0f172a;
  color: #e5e7eb;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 980px) {
  .filter-form,
  .error-filter-form {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .toolbar,
  .filter-actions {
    width: 100%;
    justify-content: stretch;
  }

  .toolbar .el-button,
  .filter-actions .el-button {
    flex: 1;
  }
}
</style>
