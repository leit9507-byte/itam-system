<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ pageTitle }}</h2>
        <p class="page-subtitle">{{ pageSubtitle }}</p>
      </div>
      <el-button type="primary" @click="openCreate">{{ createButtonText }}</el-button>
    </div>

    <section class="metric-grid inventory-metrics">
      <el-card v-for="card in summaryCards" :key="card.label" shadow="never">
        <el-statistic :title="card.label" :value="card.value" />
      </el-card>
    </section>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="filters.keyword" clearable placeholder="搜索编码/名称/品牌/型号/供应商" style="width: 280px" @keyup.enter="refresh" @clear="refresh" />
        <el-select v-if="!isLicensePage" v-model="filters.item_type" clearable placeholder="类型" style="width: 140px" @change="refresh">
          <el-option v-for="item in availableInventoryTypes" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.status" clearable placeholder="状态" style="width: 130px" @change="refresh">
          <el-option label="启用" value="active" />
          <el-option label="停用" value="disabled" />
        </el-select>
        <el-checkbox v-model="filters.low_stock" @change="refresh">只看低库存</el-checkbox>
        <el-button @click="resetFilters">重置</el-button>
        <el-button type="primary" @click="refresh">查询</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="items" border stripe>
        <el-table-column prop="code" label="编码" width="130" />
        <el-table-column label="名称" min-width="220">
          <template #default="{ row }">
            <div class="item-name">
              <strong>{{ row.name }}</strong>
              <span>{{ row.brand || '-' }} / {{ row.model || '-' }} / {{ row.spec || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="type_label" label="类型" width="100" />
        <el-table-column prop="total_qty" label="总量" width="90" />
        <el-table-column prop="available_qty" label="可用" width="90">
          <template #default="{ row }">
            <el-tag :type="row.low_stock ? 'danger' : 'success'" effect="light">{{ row.available_qty }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="assigned_qty" label="已分配/装配" width="120" />
        <el-table-column prop="min_qty" label="低库存线" width="100" />
        <el-table-column prop="expire_date_text" label="到期" width="120">
          <template #default="{ row }">{{ row.expire_date_text || '-' }}</template>
        </el-table-column>
        <el-table-column prop="location" label="位置" min-width="130" show-overflow-tooltip />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openOperate(row)">操作</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="primary" @click="openLedger(row)">流水</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :page-sizes="[10, 20, 50, 100]" :total="pagination.total" layout="total, sizes, prev, pager, next, jumper" @size-change="refresh" @current-change="loadItems" />
      </div>
    </el-card>

    <el-dialog v-model="itemDialog.visible" :title="itemDialog.form.id ? `编辑${objectName}` : `新增${objectName}`" width="820px">
      <el-form :model="itemDialog.form" label-width="98px">
        <div class="form-grid">
          <el-form-item label="类型" required>
            <el-select v-model="itemDialog.form.item_type" :disabled="isLicensePage" style="width:100%">
              <el-option v-for="item in availableInventoryTypes" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="编码" required><el-input v-model="itemDialog.form.code" /></el-form-item>
          <el-form-item label="名称" required><el-input v-model="itemDialog.form.name" /></el-form-item>
          <el-form-item label="品牌"><el-input v-model="itemDialog.form.brand" /></el-form-item>
          <el-form-item label="型号"><el-input v-model="itemDialog.form.model" /></el-form-item>
          <el-form-item label="规格"><el-input v-model="itemDialog.form.spec" /></el-form-item>
          <el-form-item label="总量"><el-input-number v-model="itemDialog.form.total_qty" :min="0" style="width:100%" /></el-form-item>
          <el-form-item label="可用"><el-input-number v-model="itemDialog.form.available_qty" :min="0" style="width:100%" /></el-form-item>
          <el-form-item label="低库存线"><el-input-number v-model="itemDialog.form.min_qty" :min="0" style="width:100%" /></el-form-item>
          <el-form-item label="单价"><el-input-number v-model="itemDialog.form.unit_cost" :min="0" style="width:100%" /></el-form-item>
          <el-form-item v-if="isLicensePage" label="许可证Key"><el-input v-model="itemDialog.form.license_key" /></el-form-item>
          <el-form-item v-if="isLicensePage" label="到期日期"><el-date-picker v-model="itemDialog.form.expire_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="供应商"><el-input v-model="itemDialog.form.supplier" /></el-form-item>
          <el-form-item label="位置">
            <el-select v-model="itemDialog.form.location" filterable clearable placeholder="选择位置" style="width: 100%">
              <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="备注"><el-input v-model="itemDialog.form.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitItem">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="operateDialog.visible" title="库存操作" width="620px">
      <el-alert :title="operateDialog.item ? `${operateDialog.item.name} / 当前可用 ${operateDialog.item.available_qty}` : ''" type="info" show-icon :closable="false" />
      <el-form :model="operateDialog.form" label-width="96px" class="operate-form">
        <el-form-item label="操作类型"><el-select v-model="operateDialog.form.action" style="width:100%"><el-option v-for="item in inventoryActions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="数量"><el-input-number v-model="operateDialog.form.quantity" :min="1" style="width:100%" /></el-form-item>
        <el-form-item label="人员"><el-input v-model="operateDialog.form.assignee_name" placeholder="分配/归还人员" /></el-form-item>
        <el-form-item label="部门"><el-input v-model="operateDialog.form.dept_id" /></el-form-item>
        <el-form-item label="资产ID"><el-input v-model="operateDialog.form.asset_id" :placeholder="isLicensePage ? '许可证绑定设备时填写' : '组件装配/配件绑定到资产时填写'" /></el-form-item>
        <el-form-item label="位置">
          <el-select v-model="operateDialog.form.location" filterable clearable placeholder="选择位置" style="width: 100%">
            <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="operateDialog.form.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="operateDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitOperate">确认</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="ledgerDrawer.visible" title="库存流水" size="720px">
      <el-table :data="ledgerRows" border stripe>
        <el-table-column prop="created_at_text" label="时间" width="170" />
        <el-table-column prop="action_label" label="动作" width="110" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="assignee_name" label="人员" width="120" />
        <el-table-column prop="asset_id" label="资产ID" width="130" />
        <el-table-column prop="operator" label="操作人" width="110" />
        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createInventoryItem, getInventoryItems, getInventoryLedger, inventoryActions, inventoryTypes, operateInventoryItem, updateInventoryItem } from '../../api/inventory'
import { getLocations } from '../../api/location'

const loading = ref(false)
const route = useRoute()
const submitting = ref(false)
const items = ref([])
const ledgerRows = ref([])
const locations = ref([])
const summary = reactive({})
const filters = reactive({ keyword: '', item_type: '', status: '', low_stock: false })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const itemDialog = reactive({ visible: false, form: defaultItemForm() })
const operateDialog = reactive({ visible: false, item: null, form: defaultOperateForm() })
const ledgerDrawer = reactive({ visible: false })

const isLicensePage = computed(() => route.meta.inventoryMode === 'license')
const scopedTypes = computed(() => (isLicensePage.value ? ['license'] : ['consumable', 'accessory', 'component']))
const availableInventoryTypes = computed(() => inventoryTypes.filter(item => scopedTypes.value.includes(item.value)))
const pageTitle = computed(() => (isLicensePage.value ? '软件许可' : '配件管理'))
const pageSubtitle = computed(() => (isLicensePage.value ? '管理软件授权数量、许可证Key、到期时间、分配绑定和许可流水' : '管理耗材、配件、组件的库存数量、领用归还、装配拆卸和低库存提醒'))
const createButtonText = computed(() => (isLicensePage.value ? '新增软件许可' : '新增配件库存'))
const objectName = computed(() => (isLicensePage.value ? '软件许可' : '库存对象'))
const summaryCards = computed(() => [
  ...(isLicensePage.value
    ? [
        { label: '软件许可', value: summary.license || 0 },
        { label: '可用授权', value: summary.total_available_qty || 0 },
        { label: '已分配', value: summary.assigned_qty || 0 },
        { label: '即将到期', value: summary.expiring || 0 }
      ]
    : [
        { label: '库存对象', value: summary.total || 0 },
        { label: '耗材', value: summary.consumable || 0 },
        { label: '配件', value: summary.accessory || 0 },
        { label: '低库存', value: summary.low_stock || 0 }
      ])
])
const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))

onMounted(async () => {
  await Promise.all([loadItems(), loadLocations()])
})

watch(() => route.path, () => {
  resetFilters()
})

async function loadLocations() {
  locations.value = await getLocations().catch(() => [])
}

async function loadItems() {
  loading.value = true
  try {
    const result = await getInventoryItems({ ...buildInventoryQuery(), page: pagination.page, pageSize: pagination.pageSize })
    items.value = result.list
    pagination.total = result.total
    Object.assign(summary, result.summary || {})
  } finally {
    loading.value = false
  }
}

function refresh() {
  pagination.page = 1
  loadItems()
}

function resetFilters() {
  Object.assign(filters, { keyword: '', item_type: '', status: '', low_stock: false })
  refresh()
}

function openCreate() {
  itemDialog.form = defaultItemForm()
  itemDialog.visible = true
}

function openEdit(row) {
  itemDialog.form = { ...row, expire_date: row.expire_date_text || '' }
  itemDialog.visible = true
}

async function submitItem() {
  if (!itemDialog.form.code || !itemDialog.form.name) return ElMessage.warning('请填写编码和名称')
  submitting.value = true
  try {
    if (itemDialog.form.id) await updateInventoryItem(itemDialog.form.id, itemDialog.form)
    else await createInventoryItem(itemDialog.form)
    ElMessage.success('保存成功')
    itemDialog.visible = false
    await loadItems()
  } finally {
    submitting.value = false
  }
}

function openOperate(row) {
  operateDialog.item = row
  operateDialog.form = defaultOperateForm()
  operateDialog.visible = true
}

async function submitOperate() {
  submitting.value = true
  try {
    await operateInventoryItem(operateDialog.item.id, operateDialog.form)
    ElMessage.success('库存流水已记录')
    operateDialog.visible = false
    await loadItems()
  } finally {
    submitting.value = false
  }
}

async function openLedger(row) {
  ledgerRows.value = await getInventoryLedger(row.id)
  ledgerDrawer.visible = true
}

function defaultItemForm() {
  return { item_type: isLicensePage.value ? 'license' : 'accessory', code: '', name: '', brand: '', model: '', spec: '', total_qty: 0, available_qty: 0, min_qty: 0, unit_cost: 0, license_key: '', expire_date: '', supplier: '', location: '', status: 'active', remark: '' }
}

function buildInventoryQuery() {
  const query = { ...filters }
  if (isLicensePage.value) {
    query.item_type = 'license'
    return query
  }
  if (!query.item_type) query.item_types = scopedTypes.value.join(',')
  return query
}

function defaultOperateForm() {
  return { action: 'in', quantity: 1, assignee_user_id: '', assignee_name: '', dept_id: '', asset_id: '', location: '', remark: '' }
}

function locationLabel(item) {
  const meta = [item.code, item.type].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}
</script>

<style scoped>
.inventory-metrics {
  grid-template-columns: repeat(4, minmax(150px, 1fr));
}

.item-name {
  display: grid;
  gap: 4px;
}

.item-name span {
  color: var(--muted);
  font-size: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px 14px;
}

.operate-form {
  margin-top: 14px;
}

@media (max-width: 900px) {
  .inventory-metrics,
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
