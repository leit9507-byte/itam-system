<template>
  <div class="company-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">公司管理</h2>
        <p class="page-subtitle">维护公司主数据，点击详情查看公司资产清单和状态分布</p>
      </div>
      <div class="toolbar">
        <el-input v-model="keyword" clearable placeholder="搜索公司/资产/部门" style="width: 260px" @input="resetCompanyPage" />
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openCreate">新增公司</el-button>
      </div>
    </div>

    <section class="metric-grid">
      <el-card shadow="never"><el-statistic title="公司数量" :value="filteredCompanies.length" /></el-card>
      <el-card shadow="never"><el-statistic title="资产总数" :value="summary.assetCount" /></el-card>
      <el-card shadow="never"><el-statistic title="资产原值" :value="summary.totalValue" prefix="¥" /></el-card>
      <el-card shadow="never"><el-statistic title="在用资产" :value="summary.inUse" /></el-card>
    </section>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>公司资产概览</span>
          <el-tag type="info">{{ filteredCompanies.length }} 家公司</el-tag>
        </div>
      </template>
      <el-table :data="pagedCompanies" border stripe>
        <el-table-column label="公司" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" class="entity-link" @click="goDetail(row)">{{ row.name }}</el-button>
            <div class="entity-meta">{{ [row.code, row.contact].filter(Boolean).join(' / ') || '未维护编码和联系人' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="编码" width="120" />
        <el-table-column prop="contact" label="联系人" width="120" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.virtual ? 'info' : row.status === '启用' ? 'success' : 'warning'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="asset_count" label="资产数" width="100" />
        <el-table-column prop="total_original_value" label="资产原值" width="150">
          <template #default="{ row }">¥{{ formatValue(row.total_original_value) }}</template>
        </el-table-column>
        <el-table-column prop="in_use_count" label="在用" width="80" />
        <el-table-column prop="in_stock_count" label="在库" width="80" />
        <el-table-column prop="idle_count" label="闲置" width="80" />
        <el-table-column prop="repair_count" label="维修中" width="90" />
        <el-table-column prop="ready_scrap_count" label="待报废" width="90" />
        <el-table-column prop="pending_scrap_count" label="待处置" width="90" />
        <el-table-column prop="scrapped_count" label="已报废" width="90" />
        <el-table-column prop="lost_count" label="已丢失" width="90" />
        <el-table-column label="详情" width="110" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="companyPagination.page"
          v-model:page-size="companyPagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredCompanies.length"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.form.id ? '编辑公司' : '新增公司'" width="520px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="公司名称" required>
          <el-input v-model="dialog.form.name" placeholder="请输入公司名称" />
        </el-form-item>
        <el-form-item label="公司编码">
          <el-input v-model="dialog.form.code" placeholder="例如：HQ、SUB-A" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="dialog.form.contact" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="dialog.form.status" style="width: 100%">
            <el-option label="启用" value="启用" />
            <el-option label="停用" value="停用" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitCompany">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createCompany, getCompanies, updateCompany } from '../../api/company'

const router = useRouter()
const companies = ref([])
const keyword = ref('')
const dialog = reactive({ visible: false, form: defaultForm() })
const companyPagination = reactive({ page: 1, pageSize: 10 })

const filteredCompanies = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return companies.value
  return companies.value.filter(company => {
    return [company.name, company.code, company.contact].join(' ').toLowerCase().includes(text)
  })
})

const summary = computed(() => ({
  assetCount: filteredCompanies.value.reduce((sum, item) => sum + item.asset_count, 0),
  totalValue: filteredCompanies.value.reduce((sum, item) => sum + item.total_original_value, 0),
  inUse: filteredCompanies.value.reduce((sum, item) => sum + item.in_use_count, 0)
}))

const pagedCompanies = computed(() => paginate(filteredCompanies.value, companyPagination))

onMounted(load)

async function load() {
  companies.value = await getCompanies()
}

function defaultForm() {
  return { id: null, name: '', code: '', contact: '', status: '启用' }
}

function openCreate() {
  dialog.form = defaultForm()
  dialog.visible = true
}

function openEdit(row) {
  if (row.virtual) return
  dialog.form = { id: row.id, name: row.name, code: row.code || '', contact: row.contact || '', status: row.status || '启用' }
  dialog.visible = true
}

async function submitCompany() {
  if (!dialog.form.name.trim()) {
    ElMessage.warning('请填写公司名称')
    return
  }
  if (dialog.form.id) await updateCompany(dialog.form.id, dialog.form)
  else await createCompany(dialog.form)
  dialog.visible = false
  ElMessage.success('公司信息已保存')
  await load()
}

function formatValue(value) {
  return Number(value || 0).toLocaleString()
}

function resetCompanyPage() {
  companyPagination.page = 1
}

function goDetail(row) {
  router.push({ name: 'CompanyDetail', query: { name: row.name } })
}

function paginate(rows, pagination) {
  const start = (pagination.page - 1) * pagination.pageSize
  return rows.slice(start, start + pagination.pageSize)
}
</script>

<style scoped>
.company-page {
  display: grid;
  gap: 16px;
}

.toolbar,
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.entity-link {
  padding: 0;
  white-space: normal;
  text-align: left;
}

.entity-meta {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
  margin-top: 4px;
}
</style>
