<template>
  <div class="location-detail-page">
    <div class="page-header">
      <div>
        <el-button link class="back-link" @click="router.back()">返回位置列表</el-button>
        <h2 class="page-title">{{ locationName || '位置详情' }}</h2>
        <p class="page-subtitle">查看该位置下的资产清单和位置基础信息。</p>
      </div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </div>

    <section class="metric-grid">
      <el-card shadow="never"><el-statistic title="资产数量" :value="locationAssets.length" /></el-card>
      <el-card shadow="never"><el-statistic title="资产原值" :value="assetValue" prefix="￥" /></el-card>
      <el-card shadow="never"><el-statistic title="在用资产" :value="inUseCount" /></el-card>
      <el-card shadow="never"><el-statistic title="维修/待处置" :value="attentionCount" /></el-card>
    </section>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>位置资产</span>
          <el-tag type="info">{{ locationInfo.type || '未设置类型' }}</el-tag>
        </div>
      </template>
      <el-descriptions :column="3" border class="info-block">
        <el-descriptions-item label="位置编码">{{ locationInfo.code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="负责部门">{{ locationInfo.owner_dept || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ locationInfo.status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="说明" :span="3">{{ locationInfo.description || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-table v-loading="loading" :data="pagedAssets" border stripe empty-text="暂无资产数据">
        <el-table-column prop="asset_no" label="资产编号" width="140" />
        <el-table-column prop="name" label="资产名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="category" label="类型" width="120" />
        <el-table-column label="产品信息" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.brand || '-' }} / {{ row.model || '-' }}</template>
        </el-table-column>
        <el-table-column prop="sn" label="序列号" width="150" show-overflow-tooltip />
        <el-table-column prop="company" label="公司" width="160" show-overflow-tooltip />
        <el-table-column prop="dept_id" label="部门" width="160" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type || 'info'">{{ row.status_label || statusMap[row.status]?.label || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="purchase_price" label="原值" width="120">
          <template #default="{ row }">￥{{ Number(row.purchase_price || 0).toLocaleString() }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="locationAssets.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="pagination.page = 1"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAssets, statusMap } from '../../api/asset'
import { getLocations } from '../../api/location'

const route = useRoute()
const router = useRouter()
const locationName = computed(() => String(route.query.name || ''))
const loading = ref(false)
const assets = ref([])
const locations = ref([])
const pagination = reactive({ page: 1, pageSize: 10 })
const DETAIL_LIMIT = 2000

const locationInfo = computed(() => locations.value.find(item => item.name === locationName.value) || {})
const locationAssets = computed(() => assets.value.filter(asset => asset.location === locationName.value))
const assetValue = computed(() => locationAssets.value.reduce((sum, asset) => sum + Number(asset.price || asset.purchase_price || 0), 0))
const inUseCount = computed(() => locationAssets.value.filter(asset => asset.status === 'in_use').length)
const attentionCount = computed(() => locationAssets.value.filter(asset => ['repair', 'pending_scrap', 'ready_scrap'].includes(asset.status)).length)
const pagedAssets = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  return locationAssets.value.slice(start, start + pagination.pageSize)
})

onMounted(load)

async function load() {
  if (!locationName.value) return
  loading.value = true
  try {
    const [locationRows, assetResult] = await Promise.all([getLocations(locationName.value), getAssets({ page: 1, page_size: DETAIL_LIMIT })])
    locations.value = locationRows
    assets.value = assetResult.list || []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.location-detail-page {
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

.info-block {
  margin-bottom: 16px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
