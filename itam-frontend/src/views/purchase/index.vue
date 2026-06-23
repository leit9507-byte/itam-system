<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">采购管理</h2>
        <p class="page-subtitle">一张采购单可包含多种设备，验收时按明细填写序列号并自动入库生成资产</p>
      </div>
      <div class="toolbar">
        <el-button @click="catalogDialog = true">基础资料</el-button>
        <el-button type="primary" @click="openCreate">创建采购单</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="purchases" border stripe row-key="purchase_no">
        <el-table-column type="expand">
          <template #default="{ row }">
            <el-table :data="row.items" border size="small" class="inner-table">
              <el-table-column prop="product_name" label="设备名称" />
              <el-table-column prop="category" label="类型" width="110" />
              <el-table-column prop="brand" label="品牌" width="110" />
              <el-table-column prop="model" label="型号" width="130" />
              <el-table-column prop="quantity" label="数量" width="80" />
              <el-table-column prop="unit_price" label="单价" width="120">
                <template #default="{ row: item }">¥{{ item.unit_price.toLocaleString() }}</template>
              </el-table-column>
              <el-table-column prop="warehouse" label="入库仓库" width="140" />
              <el-table-column prop="dept" label="申请部门" width="120" />
            </el-table>
          </template>
        </el-table-column>
        <el-table-column prop="purchase_no" label="采购单号" width="160" />
        <el-table-column prop="approval_no" label="审批单号" width="160" />
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
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :disabled="row.status !== 'created'" @click="approve(row)">审批通过</el-button>
            <el-button type="success" link :disabled="row.status === 'received'" @click="openReceive(row)">验收入库</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialog" title="创建采购单" width="1080px">
      <el-form :model="form" label-width="100px">
        <div class="header-form">
          <el-form-item label="采购单号"><el-input v-model="form.purchase_no" /></el-form-item>
          <el-form-item label="审批单号"><el-input v-model="form.approval_no" /></el-form-item>
          <el-form-item label="申请部门"><el-input v-model="form.dept" /></el-form-item>
        </div>
      </el-form>

      <div class="dialog-toolbar">
        <strong>采购明细</strong>
        <el-button type="primary" plain @click="addLine">添加设备明细</el-button>
      </div>
      <el-table :data="form.items" border>
        <el-table-column label="产品档案" min-width="220">
          <template #default="{ row }">
            <el-select v-model="row.product_id" filterable placeholder="选择产品" style="width: 100%" @change="selectProduct(row)">
              <el-option v-for="item in products" :key="item.id" :label="`${item.product_name} / ${item.model}`" :value="item.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="名称/型号" min-width="220">
          <template #default="{ row }">
            <div class="line-product">
              <el-input v-model="row.product_name" placeholder="产品名称" />
              <el-input v-model="row.model" placeholder="型号" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="130">
          <template #default="{ row }"><el-input v-model="row.category" /></template>
        </el-table-column>
        <el-table-column label="品牌" width="130">
          <template #default="{ row }"><el-input v-model="row.brand" /></template>
        </el-table-column>
        <el-table-column label="数量" width="110">
          <template #default="{ row }"><el-input-number v-model="row.quantity" :min="1" style="width: 100%" /></template>
        </el-table-column>
        <el-table-column label="单价" width="140">
          <template #default="{ row }"><el-input-number v-model="row.unit_price" :min="0" style="width: 100%" /></template>
        </el-table-column>
        <el-table-column label="仓库" width="150">
          <template #default="{ row }"><el-input v-model="row.warehouse" /></template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ $index }"><el-button link type="danger" @click="removeLine($index)">删除</el-button></template>
        </el-table-column>
      </el-table>
      <template #footer>
        <span class="amount">合计：¥{{ totalAmount.toLocaleString() }}</span>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="receiveDialog" title="采购验收 / 设备入库" width="1120px">
      <el-alert title="按采购明细逐台填写序列号，可补充资产名称、责任部门、使用人和位置。提交后自动生成资产并入库。" type="info" show-icon :closable="false" />
      <div v-for="item in receiveForm.items" :key="item.item_id" class="acceptance-block">
        <div class="dialog-toolbar">
          <strong>{{ item.product_name }} / {{ item.model }}，应验 {{ item.quantity }} 台</strong>
          <el-button size="small" @click="fillRows(item)">按数量生成验收行</el-button>
        </div>
        <el-table :data="item.assets" border size="small">
          <el-table-column label="序列号" min-width="150"><template #default="{ row }"><el-input v-model="row.sn" /></template></el-table-column>
          <el-table-column label="资产名称" min-width="160"><template #default="{ row }"><el-input v-model="row.name" /></template></el-table-column>
          <el-table-column label="规格" min-width="160"><template #default="{ row }"><el-input v-model="row.spec" /></template></el-table-column>
          <el-table-column label="部门" width="130"><template #default="{ row }"><el-input v-model="row.dept_id" /></template></el-table-column>
          <el-table-column label="使用人" width="130"><template #default="{ row }"><el-input v-model="row.owner_user_id" /></template></el-table-column>
          <el-table-column label="位置/仓库" width="150"><template #default="{ row }"><el-input v-model="row.location" /></template></el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="receiveDialog = false">取消</el-button>
        <el-button type="success" @click="receive">确认验收并入库</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="catalogDialog" title="设备类型与产品档案" width="980px">
      <div class="catalog-grid">
        <el-card shadow="never">
          <template #header>设备类型</template>
          <div class="inline-form">
            <el-input v-model="typeForm.name" placeholder="类型名称，如 Laptop" />
            <el-input v-model="typeForm.description" placeholder="说明" />
            <el-button type="primary" @click="saveType">保存</el-button>
          </div>
          <el-table :data="deviceTypes" border>
            <el-table-column prop="name" label="类型" />
            <el-table-column prop="description" label="说明" />
            <el-table-column label="操作" width="90">
              <template #default="{ row }"><el-button link type="primary" @click="editType(row)">编辑</el-button></template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never">
          <template #header>产品档案</template>
          <div class="product-form">
            <el-input v-model="productForm.product_name" placeholder="产品名称" />
            <el-select v-model="productForm.device_type" placeholder="设备类型">
              <el-option v-for="item in deviceTypes" :key="item.id" :label="item.name" :value="item.name" />
            </el-select>
            <el-input v-model="productForm.brand" placeholder="品牌" />
            <el-input v-model="productForm.model" placeholder="型号" />
            <el-input v-model="productForm.spec" placeholder="规格" />
            <el-input-number v-model="productForm.unit_price" :min="0" placeholder="单价" style="width: 100%" />
            <el-input v-model="productForm.default_warehouse" placeholder="默认仓库" />
            <el-button type="primary" @click="saveProduct">保存产品</el-button>
          </div>
          <el-table :data="products" border>
            <el-table-column prop="product_name" label="产品名称" />
            <el-table-column prop="device_type" label="类型" width="100" />
            <el-table-column prop="brand" label="品牌" width="100" />
            <el-table-column prop="model" label="型号" width="130" />
            <el-table-column label="操作" width="90">
              <template #default="{ row }"><el-button link type="primary" @click="editProduct(row)">编辑</el-button></template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { acceptPurchase, approvePurchase, createPurchase, getPurchases } from '../../api/purchase'
import { createDeviceType, createProduct, getDeviceTypes, getProducts, updateDeviceType, updateProduct } from '../../api/product'

const purchases = ref([])
const products = ref([])
const deviceTypes = ref([])
const createDialog = ref(false)
const receiveDialog = ref(false)
const catalogDialog = ref(false)
const currentPurchase = ref(null)
const form = reactive(defaultForm())
const receiveForm = reactive({ items: [] })
const typeForm = reactive({ id: null, name: '', description: '' })
const productForm = reactive(defaultProductForm())

const totalAmount = computed(() => form.items.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0))

onMounted(load)

async function load() {
  purchases.value = await getPurchases()
  products.value = await getProducts()
  deviceTypes.value = await getDeviceTypes()
}

function defaultForm() {
  return { purchase_no: `PO-${Date.now()}`, approval_no: '', dept: '', items: [defaultLine()] }
}

function defaultLine() {
  return { product_id: null, product_name: '', category: '', brand: '', model: '', spec: '', quantity: 1, unit_price: 0, warehouse: '', dept: '' }
}

function defaultProductForm() {
  return { id: null, product_name: '', device_type: '', brand: '', model: '', spec: '', unit_price: 0, default_warehouse: '' }
}

function openCreate() {
  Object.assign(form, defaultForm())
  createDialog.value = true
}

function addLine() {
  form.items.push(defaultLine())
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
    warehouse: product.default_warehouse
  })
}

async function submit() {
  await createPurchase({ ...form, total_amount: totalAmount.value })
  createDialog.value = false
  ElMessage.success('采购单已创建')
  await load()
}

async function approve(row) {
  await approvePurchase(row)
  ElMessage.success('审批已通过，可进行验收')
}

function openReceive(row) {
  currentPurchase.value = row
  receiveForm.items = row.items.map(item => ({
    item_id: item.id,
    product_name: item.product_name,
    category: item.category,
    brand: item.brand,
    model: item.model,
    spec: item.spec,
    quantity: item.quantity,
    unit_price: item.unit_price,
    warehouse: item.warehouse,
    dept: item.dept,
    assets: buildAcceptanceAssets(item)
  }))
  receiveDialog.value = true
}

function buildAcceptanceAssets(item) {
  return Array.from({ length: item.quantity }, () => ({
    sn: '',
    name: item.product_name,
    category: item.category,
    brand: item.brand,
    model: item.model,
    spec: item.spec,
    location: item.warehouse,
    dept_id: item.dept,
    owner_user_id: '',
    purchase_price: item.unit_price
  }))
}

function fillRows(item) {
  item.assets = buildAcceptanceAssets(item)
}

async function receive() {
  const acceptances = receiveForm.items.map(item => ({ item_id: item.item_id, assets: item.assets }))
  const result = await acceptPurchase(currentPurchase.value.purchase_no, acceptances)
  receiveDialog.value = false
  ElMessage.success(`验收完成，生成 ${result.generated_assets} 个资产`)
  await load()
}

function editType(row) {
  Object.assign(typeForm, row)
}

async function saveType() {
  if (typeForm.id) await updateDeviceType(typeForm.id, typeForm)
  else await createDeviceType(typeForm)
  Object.assign(typeForm, { id: null, name: '', description: '' })
  ElMessage.success('设备类型已保存')
  await load()
}

function editProduct(row) {
  Object.assign(productForm, row)
}

async function saveProduct() {
  if (productForm.id) await updateProduct(productForm.id, productForm)
  else await createProduct(productForm)
  Object.assign(productForm, defaultProductForm())
  ElMessage.success('产品档案已保存')
  await load()
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

.header-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.dialog-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 12px 0;
}

.inner-table,
.acceptance-block {
  margin: 12px;
}

.amount {
  float: left;
  color: var(--text);
  font-weight: 700;
}

.catalog-grid {
  display: grid;
  grid-template-columns: minmax(320px, 0.8fr) minmax(460px, 1.2fr);
  gap: 16px;
}

.inline-form,
.product-form {
  display: grid;
  gap: 10px;
  margin-bottom: 12px;
}

.product-form {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
</style>
