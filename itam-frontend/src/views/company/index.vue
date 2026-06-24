<template>
  <div class="company-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">公司管理</h2>
        <p class="page-subtitle">按公司维度查看资产数量、资产原值和状态分布</p>
      </div>
      <div class="toolbar">
        <el-input v-model="keyword" clearable placeholder="搜索公司/资产/部门" style="width: 260px" />
        <el-button @click="load">刷新</el-button>
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
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="dept_id" label="部门" width="150" show-overflow-tooltip />
        <el-table-column prop="purchase_supplier_name" label="供应商" width="140" show-overflow-tooltip />
        <el-table-column prop="purchase_price" label="原值" width="120">
          <template #default="{ row }">¥{{ formatValue(row.purchase_price) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getCompanies } from '../../api/company'

const companies = ref([])
const currentCompany = ref(null)
const keyword = ref('')

const filteredCompanies = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return companies.value
  return companies.value.filter(company => {
    const assetText = company.assets.map(asset => [asset.asset_id, asset.name, asset.dept_id, asset.purchase_supplier_name].join(' ')).join(' ')
    return [company.name, assetText].join(' ').toLowerCase().includes(text)
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
  currentCompany.value = companies.value[0] || null
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
