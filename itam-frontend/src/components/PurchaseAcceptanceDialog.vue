<template>
  <el-dialog v-model="visible" title="采购验收 / 设备入库" width="1180px">
    <el-alert title="按采购明细逐台完善资产编号、序列号、使用人和位置。选择使用人后，资产会直接进入在用状态；未选择使用人则入库。" type="info" show-icon :closable="false" />
    <div v-for="item in form.items" :key="item.item_id" class="acceptance-block">
      <div class="dialog-toolbar">
        <strong>{{ item.product_name }} / {{ item.model || '-' }}，应验 {{ item.quantity }} 台</strong>
        <div class="acceptance-actions">
          <el-input v-model="item.assetPrefix" size="small" placeholder="资产编号前缀" class="prefix-input" />
          <el-button size="small" @click="fillAssetIds(item)">填充编号</el-button>
          <el-button size="small" @click="openSerialPaste(item)">粘贴 SN</el-button>
          <el-button size="small" @click="fillRows(item)">按数量生成验收行</el-button>
        </div>
      </div>
      <el-table :data="item.assets" border size="small">
        <el-table-column label="资产编号" min-width="150">
          <template #default="{ row }"><el-input v-model="row.asset_id" placeholder="留空自动生成" /></template>
        </el-table-column>
        <el-table-column label="序列号" min-width="150">
          <template #default="{ row }"><el-input v-model="row.sn" placeholder="填写设备 SN" /></template>
        </el-table-column>
        <el-table-column label="资产名称" min-width="150">
          <template #default="{ row }"><el-input v-model="row.name" /></template>
        </el-table-column>
        <el-table-column label="规格" min-width="150">
          <template #default="{ row }"><el-input v-model="row.spec" /></template>
        </el-table-column>
        <el-table-column label="维保年限" width="118">
          <template #default="{ row }"><el-input-number v-model="row.warranty_years" :min="0" :step="1" :precision="0" controls-position="right" class="number-input" /></template>
        </el-table-column>
        <el-table-column label="退役年限" width="118">
          <template #default="{ row }"><el-input-number v-model="row.retirement_years" :min="0" :step="1" :precision="0" controls-position="right" class="number-input" /></template>
        </el-table-column>
        <el-table-column label="使用人" width="210">
          <template #default="{ row }">
            <el-select v-model="row.owner_user_id" filterable clearable placeholder="选择使用人" style="width: 100%" @change="value => selectOwner(row, value)">
              <el-option v-for="user in users" :key="user.user_id" :label="userLabel(user)" :value="user.user_id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="部门" width="150">
          <template #default="{ row }">
            <el-select v-model="row.dept_id" filterable clearable placeholder="选择部门" style="width: 100%">
              <el-option v-for="dept in departments" :key="dept.value" :label="dept.label" :value="dept.value" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="位置" width="180">
          <template #default="{ row }">
            <el-select v-model="row.location" filterable clearable placeholder="选择地址" style="width: 100%">
              <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="92" fixed="right">
          <template #default="{ $index }">
            <el-button link type="primary" :disabled="$index === 0" @click="copyPrevious(item, $index)">复制上行</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="success" :loading="submitting" @click="submit">确认验收并入库</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="serialPaste.visible" title="粘贴序列号" width="520px">
    <el-alert title="每行一个序列号，会按当前验收行顺序依次填入。" type="info" show-icon :closable="false" />
    <el-input v-model="serialPaste.content" type="textarea" :rows="10" class="paste-input" placeholder="SN001&#10;SN002&#10;SN003" />
    <template #footer>
      <el-button @click="serialPaste.visible = false">取消</el-button>
      <el-button type="primary" @click="applySerialPaste">填入序列号</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getLocations } from '../api/location'
import { getProducts } from '../api/product'
import { acceptPurchase } from '../api/purchase'
import { getUsers } from '../api/user'
import { getAssets } from '../api/asset'

const emit = defineEmits(['completed'])
const visible = ref(false)
const submitting = ref(false)
const currentPurchase = ref(null)
const users = ref([])
const locations = ref([])
const products = ref([])
const existingAssets = ref([])
const form = reactive({ items: [] })
const serialPaste = reactive({ visible: false, item: null, content: '' })

const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))
const departments = computed(() => {
  const map = new Map()
  users.value.forEach(user => {
    const value = user.dept_id || user.dept_name
    if (!value) return
    const label = user.dept_name && user.dept_id && user.dept_name !== user.dept_id ? `${user.dept_name} / ${user.dept_id}` : value
    map.set(value, { label, value })
  })
  form.items.forEach(item => {
    if (item.dept) map.set(item.dept, { label: item.dept, value: item.dept })
  })
  return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'))
})

async function open(purchase) {
  currentPurchase.value = purchase
  await ensureOptions()
  form.items = purchase.items.map(item => {
    const product = findProductDefaults(item)
    const enriched = {
      item_id: item.id,
      product_name: item.product_name,
      category: item.category || product?.device_type || '',
      brand: item.brand || product?.brand || '',
      model: item.model || product?.model || '',
      spec: item.spec || product?.spec || '',
      quantity: item.quantity,
      unit_price: item.unit_price || product?.unit_price || 0,
      warehouse: item.warehouse || product?.default_warehouse || '',
      dept: item.dept,
      purchase_reason: item.purchase_reason,
      retirement_years: item.retirement_years ?? product?.retirement_years ?? null
    }
    return { ...enriched, assetPrefix: '', assets: buildAcceptanceAssets(enriched) }
  })
  visible.value = true
}

async function ensureOptions() {
  const [userRows, locationRows, productRows, assetRows] = await Promise.all([
    users.value.length ? Promise.resolve(users.value) : getUsers().catch(() => []),
    locations.value.length ? Promise.resolve(locations.value) : getLocations().catch(() => []),
    products.value.length ? Promise.resolve(products.value) : getProducts().catch(() => []),
    getAssets({ page: 1, page_size: 500 }).then(result => result.list || []).catch(() => [])
  ])
  users.value = userRows
  locations.value = locationRows
  products.value = productRows
  existingAssets.value = assetRows
}

function buildAcceptanceAssets(item) {
  return Array.from({ length: Number(item.quantity || 0) }, (_, index) => ({
    row_id: `${item.id}-${index}`,
    asset_id: '',
    sn: '',
    name: item.product_name,
    category: item.category,
    brand: item.brand,
    model: item.model,
    spec: item.spec,
    location: item.warehouse,
    dept_id: item.dept,
    owner_user_id: '',
    company: currentPurchase.value?.company || '',
    warranty_years: '',
    retirement_years: item.retirement_years,
    purchase_price: item.unit_price
  }))
}

function fillRows(item) {
  item.assets = buildAcceptanceAssets(item)
}

function fillAssetIds(item) {
  const prefix = String(item.assetPrefix || '').trim()
  if (!prefix) return ElMessage.warning('请先填写资产编号前缀')
  item.assets.forEach((asset, index) => {
    asset.asset_id = `${prefix}${String(index + 1).padStart(3, '0')}`
  })
}

function openSerialPaste(item) {
  serialPaste.item = item
  serialPaste.content = item.assets.map(asset => asset.sn).filter(Boolean).join('\n')
  serialPaste.visible = true
}

function applySerialPaste() {
  const item = serialPaste.item
  if (!item) return
  const rows = serialPaste.content.split(/\r?\n/).map(value => value.trim()).filter(Boolean)
  item.assets.forEach((asset, index) => {
    if (rows[index] !== undefined) asset.sn = rows[index]
  })
  serialPaste.visible = false
}

function copyPrevious(item, index) {
  const previous = item.assets[index - 1]
  const current = item.assets[index]
  Object.assign(current, {
    name: previous.name,
    category: previous.category,
    brand: previous.brand,
    model: previous.model,
    spec: previous.spec,
    location: previous.location,
    dept_id: previous.dept_id,
    owner_user_id: previous.owner_user_id,
    company: previous.company,
    warranty_years: previous.warranty_years,
    retirement_years: previous.retirement_years,
    purchase_price: previous.purchase_price
  })
}

function selectOwner(row, userId) {
  const user = users.value.find(item => item.user_id === userId)
  row.dept_id = user?.dept_id || user?.dept_name || row.dept_id || ''
}

function findProductDefaults(item) {
  return products.value.find(product => (
    product.product_name === item.product_name &&
    product.device_type === item.category &&
    (!item.model || product.model === item.model)
  )) || products.value.find(product => product.product_name === item.product_name && (!item.model || product.model === item.model))
}

async function submit() {
  const error = validateForm()
  if (error) return ElMessage.warning(error)
  submitting.value = true
  try {
    const acceptances = form.items.map(item => ({ item_id: item.item_id, assets: item.assets }))
    const result = await acceptPurchase(currentPurchase.value.purchase_no, acceptances)
    visible.value = false
    ElMessage.success(`验收完成，生成 ${result.generated_assets} 个资产`)
    emit('completed', result)
  } catch (error) {
    ElMessage.error(`验收失败：${error?.message || '请稍后重试'}`)
  } finally {
    submitting.value = false
  }
}

function validateForm() {
  for (const item of form.items) {
    if (item.assets.length > Number(item.quantity || 0)) return `${item.product_name} 的验收行不能超过采购数量`
  }
  const assetIds = form.items.flatMap(item => item.assets.map(asset => asset.asset_id).filter(Boolean))
  if (new Set(assetIds).size !== assetIds.length) return '资产编号不能重复'
  const existingAssetIds = new Set(existingAssets.value.map(asset => asset.asset_id).filter(Boolean))
  const duplicatedAssetId = assetIds.find(assetId => existingAssetIds.has(assetId))
  if (duplicatedAssetId) return `资产编号已存在：${duplicatedAssetId}`
  const serialNumbers = form.items.flatMap(item => item.assets.map(asset => asset.sn).filter(Boolean))
  if (new Set(serialNumbers).size !== serialNumbers.length) return '序列号不能重复'
  const existingSerialNumbers = new Set(existingAssets.value.map(asset => asset.sn).filter(Boolean))
  const duplicatedSn = serialNumbers.find(sn => existingSerialNumbers.has(sn))
  if (duplicatedSn) return `序列号已存在：${duplicatedSn}`
  return ''
}

function userLabel(user) {
  const dept = user.dept_name || user.dept_id || '未分部门'
  return `${user.display_name || user.username} (${user.username || user.user_id}) / ${dept}`
}

function locationLabel(item) {
  const meta = [item.code, item.type].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}

defineExpose({ open })
</script>

<style scoped>
.acceptance-block {
  margin: 12px;
}

.dialog-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 12px 0;
}

.acceptance-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.prefix-input {
  width: 150px;
}

.number-input {
  width: 100%;
}

.paste-input {
  margin-top: 12px;
}
</style>
