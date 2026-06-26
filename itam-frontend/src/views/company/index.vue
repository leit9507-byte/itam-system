<template>
  <div class="company-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">公司管理</h2>
        <p class="page-subtitle">维护公司主数据，并按公司查看资产数量、资产原值和状态分布</p>
      </div>
      <div class="toolbar">
        <el-input v-model="keyword" clearable placeholder="搜索公司/资产/部门" style="width: 260px" />
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
      <el-table :data="filteredCompanies" border stripe highlight-current-row @row-click="selectCompany">
        <el-table-column prop="name" label="公司" min-width="180" />
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
        <el-table-column prop="pending_scrap_count" label="待报废" width="90" />
        <el-table-column prop="scrapped_count" label="已报废" width="90" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :disabled="row.virtual" @click.stop="openEdit(row)">编辑</el-button>
            <el-button type="danger" link :disabled="row.virtual" @click.stop="removeCompany(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ currentCompany?.name || '公司资产明细' }}</span>
          <el-tag v-if="currentCompany" type="success">{{ currentCompany.asset_count }} 台资产</el-tag>
        </div>
      </template>
      <el-table :data="currentAssets" border stripe empty-text="请选择一个公司查看资产明细">
        <el-table-column prop="asset_id" label="资产ID" width="130" />
        <el-table-column prop="name" label="资产名称" min-width="170" />
        <el-table-column prop="category" label="类型" width="110" />
        <el-table-column label="产品信息" min-width="180">
          <template #default="{ row }">{{ row.brand || '-' }} / {{ row.model || '-' }}</template>
        </el-table-column>
        <el-table-column prop="sn" label="序列号" width="140" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type || 'info'">{{ row.status_label || statusMap[row.status]?.label || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="dept_id" label="部门" width="150" show-overflow-tooltip />
        <el-table-column prop="purchase_supplier_name" label="供应商" width="140" show-overflow-tooltip />
        <el-table-column prop="purchase_price" label="原值" width="120">
          <template #default="{ row }">¥{{ formatValue(row.purchase_price) }}</template>
        </el-table-column>
      </el-table>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { statusMap } from '../../api/asset'
import { createCompany, deleteCompany, getCompanies, updateCompany } from '../../api/company'

const companies = ref([])
const currentCompany = ref(null)
const keyword = ref('')
const dialog = reactive({ visible: false, form: defaultForm() })

const filteredCompanies = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return companies.value
  return companies.value.filter(company => {
    const assetText = company.assets.map(asset => [asset.asset_id, asset.name, asset.dept_id, asset.purchase_supplier_name].join(' ')).join(' ')
    return [company.name, company.code, company.contact, assetText].join(' ').toLowerCase().includes(text)
  })
})

const summary = computed(() => ({
  assetCount: filteredCompanies.value.reduce((sum, item) => sum + item.asset_count, 0),
  totalValue: filteredCompanies.value.reduce((sum, item) => sum + item.total_original_value, 0),
  inUse: filteredCompanies.value.reduce((sum, item) => sum + item.in_use_count, 0)
}))

const currentAssets = computed(() => currentCompany.value?.assets || [])

onMounted(load)

async function load() {
  companies.value = await getCompanies()
  if (!currentCompany.value) currentCompany.value = companies.value[0] || null
  else currentCompany.value = companies.value.find(item => item.id === currentCompany.value.id || item.name === currentCompany.value.name) || companies.value[0] || null
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

async function removeCompany(row) {
  if (row.virtual) return
  try {
    await ElMessageBox.confirm(`确定删除公司“${row.name}”吗？该公司下的资产会调整为“未设置公司”。`, '删除公司', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  await deleteCompany(row.id)
  if (currentCompany.value?.id === row.id) currentCompany.value = null
  ElMessage.success('公司已删除，相关资产已调整为未设置公司')
  await load()
}

function selectCompany(row) {
  currentCompany.value = row
}

function formatValue(value) {
  return Number(value || 0).toLocaleString()
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
</style>
