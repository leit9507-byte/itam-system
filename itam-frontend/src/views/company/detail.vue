<template>
  <div class="company-detail-page">
    <div class="page-header">
      <div>
        <el-button link class="back-link" @click="router.back()">返回公司列表</el-button>
        <h2 class="page-title">{{ companyName || '公司详情' }}</h2>
        <p class="page-subtitle">查看该公司下的资产清单和资产状态分布。</p>
      </div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </div>

    <section class="metric-grid">
      <el-card shadow="never"><el-statistic title="资产总数" :value="companyInfo.asset_count || assetTotal" /></el-card>
      <el-card shadow="never"><el-statistic title="资产原值" :value="companyInfo.total_original_value || 0" prefix="￥" /></el-card>
      <el-card shadow="never"><el-statistic title="在用资产" :value="companyInfo.in_use_count || 0" /></el-card>
      <el-card shadow="never"><el-statistic title="待处置资产" :value="companyInfo.pending_scrap_count || 0" /></el-card>
    </section>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>资产清单</span>
          <el-tag type="info">{{ assetTotal }} 台资产</el-tag>
        </div>
      </template>
      <el-table v-loading="loading" :data="assets" border stripe empty-text="暂无资产数据">
        <el-table-column prop="asset_no" label="资产编号" width="140">
          <template #default="{ row }">{{ row.asset_no || '-' }}</template>
        </el-table-column>
        <el-table-column prop="name" label="资产名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="category" label="类型" width="120" />
        <el-table-column label="产品信息" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.brand || '-' }} / {{ row.model || '-' }}</template>
        </el-table-column>
        <el-table-column prop="sn" label="序列号" width="150" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type || 'info'">{{ row.status_label || statusMap[row.status]?.label || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="dept_id" label="部门" width="160" show-overflow-tooltip />
        <el-table-column prop="location" label="位置" width="160" show-overflow-tooltip />
        <el-table-column prop="purchase_supplier_name" label="供应商" width="160" show-overflow-tooltip />
        <el-table-column prop="purchase_price" label="原值" width="120">
          <template #default="{ row }">￥{{ Number(row.purchase_price || 0).toLocaleString() }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="assetTotal"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="loadAssets"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { statusMap } from '../../api/asset'
import { getCompanies, getCompanyAssets } from '../../api/company'

const route = useRoute()
const router = useRouter()
const companyName = computed(() => String(route.query.name || ''))
const loading = ref(false)
const assets = ref([])
const assetTotal = ref(0)
const companyInfo = ref({})
const pagination = reactive({ page: 1, pageSize: 10 })

onMounted(load)

async function load() {
  if (!companyName.value) return
  loading.value = true
  try {
    await Promise.all([loadCompanyInfo(), loadAssets()])
  } finally {
    loading.value = false
  }
}

async function loadCompanyInfo() {
  const rows = await getCompanies()
  companyInfo.value = rows.find(item => item.name === companyName.value) || {}
}

async function loadAssets() {
  const result = await getCompanyAssets({ company: companyName.value, page: pagination.page, pageSize: pagination.pageSize })
  assets.value = result.list
  assetTotal.value = result.total
}

function handlePageSizeChange() {
  pagination.page = 1
  loadAssets()
}
</script>

<style scoped>
.company-detail-page {
  display: grid;
  gap: 16px;
}

.back-link {
  padding: 0;
  margin-bottom: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
