<template>
  <div class="supplier-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">供应商管理</h2>
        <p class="page-subtitle">管理供应商档案，并查询每个供应商采购过的设备明细</p>
      </div>
      <el-button type="primary" @click="openCreate">新增供应商</el-button>
    </div>

    <section class="supplier-layout">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>供应商列表</span>
            <el-input v-model="keyword" clearable placeholder="搜索供应商" style="width: 220px" @input="refreshSuppliers" />
          </div>
        </template>
        <el-table :data="pagedSuppliers" border stripe highlight-current-row @current-change="selectSupplier">
          <el-table-column prop="name" label="供应商" min-width="170" />
          <el-table-column prop="level" label="等级" width="90" />
          <el-table-column prop="purchase_count" label="采购单" width="90" />
          <el-table-column prop="device_count" label="设备数" width="90" />
          <el-table-column prop="total_amount" label="采购金额" width="130">
            <template #default="{ row }">¥{{ Number(row.total_amount || 0).toLocaleString() }}</template>
          </el-table-column>
        </el-table>
        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="supplierPagination.page"
            v-model:page-size="supplierPagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="suppliers.length"
            layout="total, sizes, prev, pager, next"
          />
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>{{ currentSupplier?.name || '供应商采购设备' }}</span>
            <el-tag type="info">{{ devices.length }} 条明细</el-tag>
          </div>
        </template>
        <div v-if="currentSupplier" class="supplier-summary">
          <el-statistic title="采购单数" :value="currentSupplier.purchase_count" />
          <el-statistic title="采购设备数" :value="currentSupplier.device_count" />
          <el-statistic title="采购金额" :value="currentSupplier.total_amount" prefix="¥" />
        </div>
        <el-table :data="pagedDevices" border stripe empty-text="请选择供应商或当前供应商暂无采购设备">
          <el-table-column prop="purchase_no" label="采购单号" width="150" />
          <el-table-column prop="product_name" label="设备名称" min-width="170" />
          <el-table-column prop="category" label="类型" width="110" />
          <el-table-column prop="brand" label="品牌" width="110" />
          <el-table-column prop="model" label="型号" width="130" />
          <el-table-column prop="quantity" label="数量" width="80" />
          <el-table-column prop="unit_price" label="单价" width="120">
            <template #default="{ row }">¥{{ Number(row.unit_price || 0).toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="total_amount" label="金额" width="130">
            <template #default="{ row }">¥{{ Number(row.total_amount || 0).toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="warehouse" label="入库仓库" width="130" />
          <el-table-column prop="status" label="采购状态" width="110" />
        </el-table>
        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="devicePagination.page"
            v-model:page-size="devicePagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="devices.length"
            layout="total, sizes, prev, pager, next"
          />
        </div>
      </el-card>
    </section>

    <el-dialog v-model="dialog.visible" title="供应商档案" width="560px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="供应商"><el-input v-model="dialog.form.name" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="dialog.form.contact" /></el-form-item>
        <el-form-item label="电话"><el-input v-model="dialog.form.phone" /></el-form-item>
        <el-form-item label="等级">
          <el-select v-model="dialog.form.level" style="width: 100%">
            <el-option label="核心" value="核心" />
            <el-option label="普通" value="普通" />
            <el-option label="观察" value="观察" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { getSupplierPurchaseDevices, getSuppliers, saveSupplier } from '../../api/supplier'

const suppliers = ref([])
const devices = ref([])
const currentSupplier = ref(null)
const keyword = ref('')
const dialog = reactive({ visible: false, form: defaultForm() })
const supplierPagination = reactive({ page: 1, pageSize: 20 })
const devicePagination = reactive({ page: 1, pageSize: 20 })
const pagedSuppliers = computed(() => paginate(suppliers.value, supplierPagination))
const pagedDevices = computed(() => paginate(devices.value, devicePagination))

onMounted(load)

async function load() {
  suppliers.value = await getSuppliers({ keyword: keyword.value })
  if (!currentSupplier.value && suppliers.value.length) await selectSupplier(suppliers.value[0])
}

async function refreshSuppliers() {
  supplierPagination.page = 1
  currentSupplier.value = null
  devices.value = []
  await load()
}

async function selectSupplier(row) {
  if (!row) return
  currentSupplier.value = row
  devices.value = await getSupplierPurchaseDevices(row.name)
  devicePagination.page = 1
}

function openCreate() {
  dialog.form = defaultForm()
  dialog.visible = true
}

async function save() {
  if (!dialog.form.name.trim()) {
    ElMessage.warning('请填写供应商名称')
    return
  }
  await saveSupplier(dialog.form)
  dialog.visible = false
  ElMessage.success('供应商已保存')
  currentSupplier.value = null
  await load()
}

function defaultForm() {
  return { id: '', name: '', contact: '', phone: '', level: '普通', status: '启用' }
}

function paginate(rows, pagination) {
  const start = (pagination.page - 1) * pagination.pageSize
  return rows.slice(start, start + pagination.pageSize)
}
</script>

<style scoped>
.supplier-page {
  display: grid;
  gap: 16px;
}

.supplier-layout {
  display: grid;
  grid-template-columns: minmax(420px, 0.9fr) minmax(520px, 1.1fr);
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.supplier-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.supplier-summary :deep(.el-statistic) {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 1280px) {
  .supplier-layout,
  .supplier-summary {
    grid-template-columns: 1fr;
  }
}
</style>
