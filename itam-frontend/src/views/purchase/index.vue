<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">采购管理</h2>
        <p class="page-subtitle">一张采购单可包含多种设备，支持供应商、审批单号、验收明细和自动入库</p>
      </div>
      <div class="toolbar">
        <el-button @click="downloadPurchaseAssetsCsv">导出采购资产</el-button>
        <el-button @click="goCatalog('/device-type')">设备类型</el-button>
        <el-button @click="goCatalog('/product')">产品档案</el-button>
        <el-button type="primary" @click="openCreate">创建采购单</el-button>
      </div>
    </div>

    <el-card shadow="never" class="filter-card">
      <div class="filter-grid">
        <el-form-item label="创建时间">
          <el-date-picker
            v-model="filters.createdRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            @change="refreshPurchases"
          />
        </el-form-item>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table :data="purchases" border stripe row-key="purchase_no">
        <el-table-column type="expand">
          <template #default="{ row }">
            <el-table :data="row.items" border size="small" class="inner-table">
              <el-table-column prop="product_name" label="设备名称" />
              <el-table-column prop="category" label="类型" width="110" />
              <el-table-column prop="brand" label="品牌" width="110" />
              <el-table-column prop="model" label="型号" width="130" />
              <el-table-column prop="quantity" label="采购数量" width="110" align="center">
                <template #default="{ row: item }"><el-tag type="primary" effect="plain">{{ item.quantity }} 台</el-tag></template>
              </el-table-column>
              <el-table-column prop="unit_price" label="单价" width="120">
                <template #default="{ row: item }">¥{{ item.unit_price.toLocaleString() }}</template>
              </el-table-column>
              <el-table-column prop="purchase_reason" label="采购原因" min-width="180" show-overflow-tooltip />
              <el-table-column prop="warehouse" label="入库地址" width="140" />
              <el-table-column prop="dept" label="申请部门" width="120" />
            </el-table>
          </template>
        </el-table-column>
        <el-table-column prop="purchase_no" label="采购单号" width="160" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column prop="approval_no" label="审批单号" width="160" />
        <el-table-column prop="company" label="公司" width="150" show-overflow-tooltip />
        <el-table-column prop="supplier_name" label="供应商" width="170" />
        <el-table-column label="采购数量" width="110" align="center">
          <template #default="{ row }"><el-tag type="primary" effect="plain">{{ row.quantity }} 台</el-tag></template>
        </el-table-column>
        <el-table-column prop="purchase_reason" label="采购原因" min-width="180" show-overflow-tooltip />
        <el-table-column label="采购内容" min-width="260">
          <template #default="{ row }">
            <div class="purchase-summary">
              <strong>{{ row.items.length }} 类设备 / 共 {{ row.quantity }} 台</strong>
              <span>{{ row.items.map(item => `${item.product_name} x${item.quantity}`).join('，') }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="total_amount" label="金额" width="130">
          <template #default="{ row }">¥{{ row.total_amount.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="status_label" label="状态" width="110" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="success" link :disabled="row.status === 'received'" @click="openReceive(row)">验收入库</el-button>
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
          @size-change="handlePageSizeChange"
          @current-change="loadPurchases"
        />
      </div>
    </el-card>

    <el-dialog v-model="createDialog" title="创建采购单" width="760px" class="purchase-create-dialog">
      <el-form :model="form" label-width="100px">
        <div class="header-form">
          <el-form-item label="采购单号"><el-input v-model="form.purchase_no" /></el-form-item>
          <el-form-item label="审批单号"><el-input v-model="form.approval_no" /></el-form-item>
          <el-form-item label="公司">
            <el-select v-model="form.company" filterable clearable placeholder="选择公司" style="width: 100%">
              <el-option v-for="item in realCompanies" :key="item.id || item.name" :label="item.name" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="供应商">
            <el-select v-model="form.supplier_name" filterable clearable allow-create default-first-option placeholder="选择或填写供应商" style="width: 100%">
              <el-option v-for="item in suppliers" :key="item.id || item.name" :label="supplierLabel(item)" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="申请部门">
            <el-select v-model="form.dept" filterable clearable placeholder="选择部门" style="width: 100%" @change="syncHeaderDeptToLines">
              <el-option v-for="item in departments" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>

      <div class="dialog-toolbar">
        <strong>采购明细</strong>
        <el-button type="primary" plain @click="addLine">添加设备明细</el-button>
      </div>
      <div class="purchase-line-list">
        <section v-for="(row, index) in form.items" :key="index" class="purchase-line-card">
          <div class="line-card-head">
            <strong>设备明细 {{ index + 1 }}</strong>
            <el-button link type="danger" :disabled="form.items.length === 1" @click="removeLine(index)">删除</el-button>
          </div>
          <el-form-item label="产品档案">
            <el-select v-model="row.product_id" filterable placeholder="选择产品档案自动填充" style="width: 100%" @change="selectProduct(row)">
              <el-option v-for="item in products" :key="item.id" :label="`${item.product_name} / ${item.model}`" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="产品名称">
            <el-input v-model="row.product_name" placeholder="例如 ThinkPad X1 Carbon" />
          </el-form-item>
          <el-form-item label="型号">
            <el-input v-model="row.model" placeholder="例如 X1 Carbon Gen 12" />
          </el-form-item>
          <el-form-item label="类型">
            <el-input v-model="row.category" placeholder="例如 笔记本电脑" />
          </el-form-item>
          <el-form-item label="品牌">
            <el-input v-model="row.brand" placeholder="例如 Lenovo / Apple / Dell" />
          </el-form-item>
          <el-form-item label="数量">
            <el-input-number v-model="row.quantity" :min="1" :step="1" :precision="0" style="width: 100%" />
          </el-form-item>
          <el-form-item label="单价">
            <el-input-number v-model="row.unit_price" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
          <el-form-item label="采购原因">
            <el-input v-model="row.purchase_reason" type="textarea" :rows="2" placeholder="说明采购用途、替换原因或项目需求" />
          </el-form-item>
          <el-form-item label="入库地址">
            <el-select v-model="row.warehouse" filterable clearable placeholder="选择入库地址" style="width: 100%">
              <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
            </el-select>
          </el-form-item>
        </section>
      </div>
      <template #footer>
        <span class="amount">合计：¥{{ totalAmount.toLocaleString() }}</span>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <PurchaseAcceptanceDialog ref="purchaseAcceptanceRef" @completed="loadPurchases" />
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCompanies } from '../../api/company'
import { getLocations } from '../../api/location'
import { createPurchase, getPurchases } from '../../api/purchase'
import { getProducts } from '../../api/product'
import { getSuppliers } from '../../api/supplier'
import { getUsers } from '../../api/user'
import { downloadPurchaseAssetsCsv } from '../../api/reporting'
import PurchaseAcceptanceDialog from '../../components/PurchaseAcceptanceDialog.vue'

const purchases = ref([])
const router = useRouter()
const products = ref([])
const companies = ref([])
const suppliers = ref([])
const locations = ref([])
const users = ref([])
const createDialog = ref(false)
const purchaseAcceptanceRef = ref(null)
const form = reactive(defaultForm())
const filters = reactive({ createdRange: [] })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const totalAmount = computed(() => form.items.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0))
const realCompanies = computed(() => companies.value.filter(item => !item.virtual && item.name !== '未设置公司'))
const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))
const departments = computed(() => {
  const map = new Map()
  users.value.forEach(user => {
    const value = user.dept_id || user.dept_name
    if (!value) return
    const label = user.dept_name && user.dept_id && user.dept_name !== user.dept_id ? `${user.dept_name} / ${user.dept_id}` : value
    map.set(value, { label, value })
  })
  return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'))
})

onMounted(load)

async function load() {
  await loadPurchases().catch(err => console.error('加载采购单失败', err))
  products.value = await getProducts().catch(err => { console.error('加载产品失败', err); return [] })
  companies.value = await getCompanies().catch(err => { console.error('加载公司失败', err); return [] })
  suppliers.value = await getSuppliers().catch(err => { console.error('加载供应商失败', err); return [] })
  locations.value = await getLocations().catch(err => { console.error('加载位置失败', err); return [] })
  users.value = await getUsers().catch(err => { console.error('加载用户失败', err); return [] })
}

async function loadPurchases() {
  const result = await getPurchases({
    created_from: filters.createdRange?.[0] || '',
    created_to: filters.createdRange?.[1] || '',
    page: pagination.page,
    page_size: pagination.pageSize
  })
  purchases.value = result.list
  pagination.total = result.total
}

async function resetFilters() {
  filters.createdRange = []
  pagination.page = 1
  await loadPurchases()
}

function handlePageSizeChange() {
  pagination.page = 1
  loadPurchases()
}

function refreshPurchases() {
  pagination.page = 1
  loadPurchases()
}

function defaultForm() {
  return { purchase_no: `PO-${Date.now()}`, approval_no: '', company: '', supplier_name: '', purchase_reason: '', dept: '', items: [defaultLine()] }
}

function defaultLine() {
  return { product_id: null, product_name: '', category: '', brand: '', model: '', spec: '', quantity: 1, unit_price: 0, purchase_reason: '', warehouse: '', dept: '', retirement_years: null }
}

function supplierLabel(item) {
  const meta = [item.contact, item.phone].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}

function locationLabel(item) {
  const meta = [item.code, item.type].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}

function openCreate() {
  Object.assign(form, defaultForm())
  createDialog.value = true
}

function goCatalog(path) {
  router.push(path)
}

function addLine() {
  form.items.push({ ...defaultLine(), dept: form.dept || '' })
}

function removeLine(index) {
  if (form.items.length === 1) return
  form.items.splice(index, 1)
}

function selectProduct(row) {
  const product = products.value.find(item => item.id === row.product_id)
  if (!product) return
  Object.assign(row, {
    product_name: product.product_name,
    category: product.device_type,
    brand: product.brand,
    model: product.model,
    spec: product.spec,
    unit_price: product.unit_price,
    warehouse: product.default_warehouse,
    retirement_years: product.retirement_years
  })
}

function syncHeaderDeptToLines(value) {
  form.items.forEach(item => {
    if (!item.dept) item.dept = value || ''
  })
}

async function submit() {
  await createPurchase({ ...form, total_amount: totalAmount.value })
  createDialog.value = false
  ElMessage.success('采购单已创建，已进入验收入库环节')
  pagination.page = 1
  await loadPurchases()
}

function openReceive(row) {
  purchaseAcceptanceRef.value?.open(row)
}
</script>

<style scoped>
.purchase-summary,
.line-product {
  display: grid;
  gap: 4px;
}

.purchase-summary span {
  overflow: hidden;
  color: var(--muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filter-card {
  margin-bottom: 12px;
}

.filter-grid {
  display: grid;
  grid-template-columns: minmax(320px, 420px) auto;
  align-items: end;
  justify-content: start;
  gap: 12px;
}

.filter-grid :deep(.el-form-item) {
  margin-bottom: 0;
}

.filter-grid :deep(.el-date-editor) {
  width: 100%;
}

.header-form {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2px;
}

.wide-field {
  grid-column: span 2;
}

.dialog-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 8px 0 12px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}

.purchase-create-dialog :deep(.el-dialog__body) {
  max-height: 72vh;
  overflow: auto;
  padding-top: 18px;
}

.purchase-create-dialog :deep(.el-form-item) {
  margin-bottom: 12px;
}

.purchase-line-list {
  display: grid;
  gap: 12px;
}

.purchase-line-card {
  padding: 14px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #fbfdff;
}

.line-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.line-card-head strong {
  color: var(--text);
  font-size: 15px;
}

.inner-table,
.acceptance-block {
  margin: 12px;
}

.quantity-input {
  width: 112px;
}

.amount {
  float: left;
  color: var(--text);
  font-weight: 700;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 980px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }

  .wide-field {
    grid-column: auto;
  }
}

@media (max-width: 640px) {
  .purchase-create-dialog :deep(.el-dialog) {
    width: calc(100vw - 20px) !important;
  }

  .purchase-create-dialog :deep(.el-form-item__label) {
    width: 86px !important;
  }
}
</style>
