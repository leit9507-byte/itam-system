<template>
  <div class="supplier-detail-page">
    <div class="page-header">
      <div>
        <el-button link class="back-link" @click="router.back()">返回供应商列表</el-button>
        <h2 class="page-title">{{ supplierName || '供应商详情' }}</h2>
        <p class="page-subtitle">查看该供应商关联的采购设备和报废回收资产。</p>
      </div>
      <el-button @click="reload">刷新</el-button>
    </div>

    <section class="summary-grid">
      <el-card shadow="never" class="summary-card">
        <span>采购单数</span>
        <strong>{{ supplierInfo.purchase_count }}</strong>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <span>采购设备数</span>
        <strong>{{ supplierInfo.device_count }}</strong>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <span>采购金额</span>
        <strong>￥{{ Number(supplierInfo.total_amount || 0).toLocaleString() }}</strong>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <span>回收资产数</span>
        <strong>{{ supplierInfo.recycle_count }}</strong>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <span>回收金额</span>
        <strong>￥{{ Number(supplierInfo.recycle_amount || 0).toLocaleString() }}</strong>
      </el-card>
    </section>

    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="采购设备" name="purchase">
          <el-table :data="purchaseRows" border stripe empty-text="暂无采购设备">
            <el-table-column prop="purchase_no" label="采购单号" width="160" />
            <el-table-column prop="product_name" label="设备名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="category" label="类型" width="120" />
            <el-table-column prop="brand" label="品牌" width="120" />
            <el-table-column prop="model" label="型号" width="140" show-overflow-tooltip />
            <el-table-column prop="quantity" label="数量" width="90" />
            <el-table-column prop="unit_price" label="单价" width="120">
              <template #default="{ row }">￥{{ Number(row.unit_price || 0).toLocaleString() }}</template>
            </el-table-column>
            <el-table-column prop="total_amount" label="金额" width="130">
              <template #default="{ row }">￥{{ Number(row.total_amount || 0).toLocaleString() }}</template>
            </el-table-column>
            <el-table-column prop="warehouse" label="入库地址" width="160" show-overflow-tooltip />
            <el-table-column prop="dept" label="申请部门" width="140" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="110" />
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="purchasePagination.page"
              v-model:page-size="purchasePagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="purchasePagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handlePurchasePageSizeChange"
              @current-change="loadPurchaseRows"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="回收资产" name="recycle">
          <el-table :data="recycleRows" border stripe empty-text="暂无回收资产">
            <el-table-column prop="request_no" label="退役流程号" width="150" />
            <el-table-column prop="asset_no" label="资产编号" width="140" />
            <el-table-column prop="asset_name" label="资产名称" min-width="190" show-overflow-tooltip />
            <el-table-column prop="category" label="类型" width="120" />
            <el-table-column prop="brand" label="品牌" width="120" />
            <el-table-column prop="model" label="型号" width="140" show-overflow-tooltip />
            <el-table-column prop="sn" label="序列号" width="150" show-overflow-tooltip />
            <el-table-column prop="purchase_price" label="采购原值" width="120">
              <template #default="{ row }">￥{{ Number(row.purchase_price || 0).toLocaleString() }}</template>
            </el-table-column>
            <el-table-column prop="final_residual_value" label="处置金额" width="120">
              <template #default="{ row }">￥{{ Number(row.final_residual_value || 0).toLocaleString() }}</template>
            </el-table-column>
            <el-table-column prop="retirement_date" label="退役时间" width="120" />
            <el-table-column prop="disposed_at" label="处置时间" width="120" />
            <el-table-column prop="status" label="状态" width="110" />
            <el-table-column prop="disposal_remark" label="处置说明" min-width="180" show-overflow-tooltip />
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="recyclePagination.page"
              v-model:page-size="recyclePagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="recyclePagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleRecyclePageSizeChange"
              @current-change="loadRecycleRows"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSupplierPurchaseDevices, getSupplierRecycledAssets, getSuppliersPaged } from '../../api/supplier'

const route = useRoute()
const router = useRouter()
const supplierName = computed(() => String(route.query.name || ''))
const activeTab = ref('purchase')
const purchaseRows = ref([])
const recycleRows = ref([])
const supplierInfo = reactive({ purchase_count: 0, device_count: 0, total_amount: 0, recycle_count: 0, recycle_amount: 0 })
const purchasePagination = reactive({ page: 1, pageSize: 10, total: 0 })
const recyclePagination = reactive({ page: 1, pageSize: 10, total: 0 })

onMounted(reload)

async function reload() {
  if (!supplierName.value) return
  await Promise.all([loadSupplierInfo(), loadActiveRows()])
}

async function loadSupplierInfo() {
  const result = await getSuppliersPaged({ keyword: supplierName.value, page: 1, page_size: 20 })
  const exact = result.list.find(item => item.name === supplierName.value) || result.list[0] || {}
  Object.assign(supplierInfo, {
    purchase_count: Number(exact.purchase_count || 0),
    device_count: Number(exact.device_count || 0),
    total_amount: Number(exact.total_amount || 0),
    recycle_count: Number(exact.recycle_count || 0),
    recycle_amount: Number(exact.recycle_amount || 0)
  })
}

function loadActiveRows() {
  return activeTab.value === 'recycle' ? loadRecycleRows() : loadPurchaseRows()
}

async function loadPurchaseRows() {
  if (!supplierName.value) return
  const result = await getSupplierPurchaseDevices(supplierName.value, { page: purchasePagination.page, page_size: purchasePagination.pageSize })
  purchaseRows.value = result.list
  purchasePagination.total = result.total
}

async function loadRecycleRows() {
  if (!supplierName.value) return
  const result = await getSupplierRecycledAssets(supplierName.value, { page: recyclePagination.page, page_size: recyclePagination.pageSize })
  recycleRows.value = result.list
  recyclePagination.total = result.total
}

function handleTabChange() {
  loadActiveRows()
}

function handlePurchasePageSizeChange() {
  purchasePagination.page = 1
  loadPurchaseRows()
}

function handleRecyclePageSizeChange() {
  recyclePagination.page = 1
  loadRecycleRows()
}
</script>

<style scoped>
.supplier-detail-page {
  display: grid;
  gap: 16px;
}

.back-link {
  padding: 0;
  margin-bottom: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.summary-card :deep(.el-card__body) {
  display: grid;
  gap: 8px;
  padding: 16px;
}

.summary-card span {
  color: var(--muted);
  font-size: 13px;
}

.summary-card strong {
  color: var(--text);
  font-size: 24px;
  line-height: 1.1;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 1280px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
