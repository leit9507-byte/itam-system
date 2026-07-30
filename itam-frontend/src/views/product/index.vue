<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">产品档案</h2>
        <p class="page-subtitle">维护可采购、可入库的标准产品，采购单可直接引用这些档案。</p>
      </div>
      <div class="toolbar">
        <el-button @click="resetFilters">清空</el-button>
        <el-button :disabled="!selectedProducts.length" @click="openBatchRetirementDialog">批量设置退役年限</el-button>
        <el-button type="primary" @click="openCreateProduct">创建产品</el-button>
      </div>
    </div>

    <el-dialog v-model="productDialog.visible" :title="productForm.id ? '编辑产品' : '创建产品'" width="560px" class="product-dialog" destroy-on-close>
      <el-form :model="productForm" label-width="108px">
        <div class="product-form">
          <el-form-item label="产品名称" required>
            <el-input v-model.trim="productForm.product_name" placeholder="例如 ThinkPad X1 Carbon" />
          </el-form-item>
          <el-form-item label="设备类型" required>
            <el-select v-model="productForm.device_type" filterable placeholder="选择设备类型" style="width: 100%">
              <el-option v-for="item in deviceTypes" :key="item.id" :label="item.name" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="品牌">
            <el-select
              v-model="productForm.brand"
              filterable
              allow-create
              default-first-option
              clearable
              placeholder="选择品牌或输入新品牌"
              style="width: 100%"
            >
              <el-option v-for="item in brandOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="型号">
            <el-input v-model.trim="productForm.model" placeholder="例如 X1 Carbon Gen 12" />
          </el-form-item>
          <el-form-item label="规格">
            <el-input v-model.trim="productForm.spec" placeholder="例如 i7 / 16G / 512G" />
          </el-form-item>
          <el-form-item label="参考单价">
            <div class="number-with-unit">
              <el-input-number v-model="productForm.unit_price" :min="0" :precision="2" controls-position="right" style="width: 100%" />
              <span>元</span>
            </div>
          </el-form-item>
          <el-form-item label="默认入库地">
            <el-select v-model="productForm.default_warehouse" filterable clearable placeholder="选择默认入库地址" style="width: 100%">
              <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="退役年限">
            <div class="number-with-unit">
              <el-input-number v-model="productForm.retirement_years" :min="0" :step="1" :precision="0" controls-position="right" placeholder="不设置" style="width: 100%" />
              <span>年</span>
            </div>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="closeProductDialog">取消</el-button>
        <el-button @click="resetProductForm">清空表单</el-button>
        <el-button type="primary" :loading="productDialog.saving" @click="saveProduct">{{ productForm.id ? '保存修改' : '创建产品' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="batchRetirementDialog.visible"
      title="批量设置退役年限"
      width="460px"
      class="batch-retirement-dialog"
      destroy-on-close
    >
      <el-alert
        :title="`已选择 ${selectedProducts.length} 个产品`"
        description="保存后会同步更新这些产品名称对应资产的退役年限，并重新计算预计退役时间和当前残值。"
        type="info"
        show-icon
        :closable="false"
      />
      <el-form label-position="top" class="batch-retirement-form">
        <el-form-item label="统一退役年限" required>
          <div class="number-with-unit">
            <el-input-number
              v-model="batchRetirementDialog.retirement_years"
              :min="1"
              :max="100"
              :step="1"
              :precision="0"
              controls-position="right"
              style="width: 100%"
            />
            <span>年</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchRetirementDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="batchRetirementDialog.saving" @click="saveBatchRetirementYears">确认设置</el-button>
      </template>
    </el-dialog>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>产品列表</span>
          <div class="filters">
            <el-select v-model="filters.device_type" clearable filterable placeholder="设备类型">
              <el-option v-for="item in deviceTypes" :key="item.id" :label="item.name" :value="item.name" />
            </el-select>
            <el-input v-model.trim="filters.keyword" clearable placeholder="搜索名称/品牌/型号" />
          </div>
        </div>
      </template>
      <el-table ref="productTableRef" :data="pagedProducts" row-key="id" border stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="48" reserve-selection />
        <el-table-column prop="product_name" label="产品名称" min-width="180" />
        <el-table-column prop="device_type" label="设备类型" width="130" />
        <el-table-column prop="brand" label="品牌" width="120" />
        <el-table-column prop="model" label="型号" width="160" />
        <el-table-column prop="spec" label="规格" min-width="180" show-overflow-tooltip />
        <el-table-column prop="unit_price" label="参考单价" width="120">
          <template #default="{ row }">¥{{ Number(row.unit_price || 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="default_warehouse" label="默认入库地" width="160" show-overflow-tooltip />
        <el-table-column prop="retirement_years" label="退役年限" width="110">
          <template #default="{ row }">{{ row.retirement_years ? `${row.retirement_years} 年` : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="editProduct(row)">编辑</el-button>
            <el-button link type="danger" @click="removeProduct(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredProducts.length"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getLocations } from '../../api/location'
import { batchUpdateProductRetirementYears, createProduct, deleteProduct, getDeviceTypes, getProducts, updateProduct } from '../../api/product'

const products = ref([])
const deviceTypes = ref([])
const locations = ref([])
const productTableRef = ref(null)
const productForm = reactive(defaultProductForm())
const productDialog = reactive({ visible: false, saving: false })
const batchRetirementDialog = reactive({ visible: false, saving: false, retirement_years: 5 })
const selectedProducts = ref([])
const filters = reactive({ keyword: '', device_type: '' })
const pagination = reactive({ page: 1, pageSize: 10 })

const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))
const brandOptions = computed(() => {
  const brands = new Set()
  products.value.forEach(item => {
    const brand = String(item.brand || '').trim()
    if (brand) brands.add(brand)
  })
  return Array.from(brands).sort((a, b) => a.localeCompare(b, 'zh-CN'))
})
const filteredProducts = computed(() => {
  const q = filters.keyword.toLowerCase()
  return products.value.filter(item => {
    const matchesType = !filters.device_type || item.device_type === filters.device_type
    const matchesKeyword = !q || [item.product_name, item.brand, item.model, item.spec].some(value => String(value || '').toLowerCase().includes(q))
    return matchesType && matchesKeyword
  })
})
const pagedProducts = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  return filteredProducts.value.slice(start, start + pagination.pageSize)
})

watch(filters, () => {
  pagination.page = 1
})

onMounted(load)

function defaultProductForm() {
  return { id: null, product_name: '', device_type: '', brand: '', model: '', spec: '', unit_price: 0, default_warehouse: '', retirement_years: null }
}

async function load() {
  products.value = await getProducts()
  deviceTypes.value = await getDeviceTypes()
  locations.value = await getLocations()
}

function locationLabel(item) {
  const meta = [item.code, item.type].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}

function editProduct(row) {
  Object.assign(productForm, row)
  productDialog.visible = true
}

function openCreateProduct() {
  resetProductForm()
  productDialog.visible = true
}

function handleSelectionChange(rows) {
  selectedProducts.value = rows
}

function openBatchRetirementDialog() {
  if (!selectedProducts.value.length) {
    ElMessage.warning('请先选择产品')
    return
  }
  const years = selectedProducts.value[0]?.retirement_years
  batchRetirementDialog.retirement_years = Number(years || 5)
  batchRetirementDialog.visible = true
}

async function saveBatchRetirementYears() {
  if (!selectedProducts.value.length) {
    ElMessage.warning('请选择需要设置的产品')
    return
  }
  const years = Number(batchRetirementDialog.retirement_years || 0)
  if (!Number.isInteger(years) || years < 1 || years > 100) {
    ElMessage.warning('退役年限必须是 1 至 100 的整数')
    return
  }
  batchRetirementDialog.saving = true
  try {
    const result = await batchUpdateProductRetirementYears(selectedProducts.value.map(item => item.id), years)
    batchRetirementDialog.visible = false
    ElMessage.success(`已更新 ${result.updated_products} 个产品，并同步 ${result.updated_assets} 台资产`)
    await load()
    productTableRef.value?.clearSelection()
    selectedProducts.value = []
  } finally {
    batchRetirementDialog.saving = false
  }
}

function closeProductDialog() {
  productDialog.visible = false
  resetProductForm()
}

function resetFilters() {
  filters.keyword = ''
  filters.device_type = ''
}

function resetProductForm() {
  Object.assign(productForm, defaultProductForm())
}

async function saveProduct() {
  if (!productForm.product_name || !productForm.device_type) {
    ElMessage.warning('请填写产品名称和设备类型')
    return
  }
  productDialog.saving = true
  try {
    if (productForm.id) await updateProduct(productForm.id, productForm)
    else await createProduct(productForm)
    productDialog.visible = false
    resetProductForm()
    ElMessage.success('产品档案已保存')
    await load()
  } finally {
    productDialog.saving = false
  }
}

async function removeProduct(row) {
  await ElMessageBox.confirm(`确认删除产品档案「${row.product_name} / ${row.model || '-'}」？已有资产不会被删除。`, '删除产品档案', { type: 'warning' })
  await deleteProduct(row.id)
  if (productForm.id === row.id) resetProductForm()
  ElMessage.success('产品档案已删除')
  await load()
}
</script>

<style scoped>
.product-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
}

.product-dialog :deep(.el-dialog__body) {
  padding-bottom: 10px;
}

.batch-retirement-dialog :deep(.el-dialog__body) {
  display: grid;
  gap: 18px;
  padding-bottom: 8px;
}

.batch-retirement-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.product-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.number-with-unit {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 34px;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.number-with-unit span {
  color: #64748b;
  font-size: 13px;
  text-align: center;
}

.card-header,
.filters {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.filters {
  width: min(560px, 100%);
}

.filters :deep(.el-select),
.filters :deep(.el-input) {
  flex: 1;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 1180px) {
  .product-form {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 760px) {
  .product-form,
  .card-header,
  .filters {
    display: grid;
    grid-template-columns: 1fr;
  }

  .filters {
    width: 100%;
  }

  .batch-retirement-dialog :deep(.el-dialog) {
    width: calc(100vw - 24px) !important;
  }
}
</style>
