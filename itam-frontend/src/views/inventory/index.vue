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
        <el-table-column prop="dept_id" label="所属部门" min-width="130" show-overflow-tooltip />
        <el-table-column prop="location" label="位置" min-width="130" show-overflow-tooltip />
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.item_type !== 'license'" link type="primary" @click="openOperate(row)">操作</el-button>
            <el-button v-if="row.item_type === 'license'" link type="primary" @click="openLicenseSeats(row)">授权席位</el-button>
            <el-button v-if="row.item_type === 'component'" link type="primary" @click="openInstallations(row)">安装关系</el-button>
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
          <el-form-item label="所属部门"><el-input v-model="itemDialog.form.dept_id" placeholder="部门负责人保存时自动使用本部门" /></el-form-item>
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

    <el-drawer v-model="seatDrawer.visible" :title="seatDrawer.item ? `${seatDrawer.item.name} / 授权席位` : '授权席位'" size="88%">
      <div class="relation-toolbar">
        <div class="relation-summary">
          <el-tag type="success">可用 {{ seatStats.available }}</el-tag>
          <el-tag type="primary">已分配 {{ seatStats.assigned }}</el-tag>
          <el-tag type="warning">已回收 {{ seatStats.recovered }}</el-tag>
          <el-tag type="info">已停用 {{ seatStats.disabled }}</el-tag>
        </div>
        <el-button type="primary" @click="openAddSeats">新增席位</el-button>
      </div>
      <div class="relation-filters">
        <el-input v-model="seatFilters.keyword" clearable placeholder="搜索席位编号、人员或资产" @keyup.enter="searchLicenseSeats" />
        <el-select v-model="seatFilters.status" clearable placeholder="全部状态" @change="searchLicenseSeats">
          <el-option label="可用" value="available" />
          <el-option label="已分配" value="assigned" />
          <el-option label="已回收" value="recovered" />
          <el-option label="已停用" value="disabled" />
        </el-select>
        <el-button type="primary" @click="searchLicenseSeats">查询</el-button>
      </div>
      <el-table :data="licenseSeats" border stripe>
        <el-table-column prop="seat_code" label="席位编号" min-width="170" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="seatStatusType(row.status)">{{ row.status_label }}</el-tag></template>
        </el-table-column>
        <el-table-column label="当前绑定" min-width="220">
          <template #default="{ row }">{{ [row.assignee_name || row.assignee_user_id, row.asset_id].filter(Boolean).join(' / ') || '-' }}</template>
        </el-table-column>
        <el-table-column prop="dept_id" label="部门" min-width="140" show-overflow-tooltip />
        <el-table-column prop="assigned_at_text" label="分配时间" width="170" />
        <el-table-column prop="returned_at_text" label="最近回收" width="170" />
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button v-if="['available', 'recovered'].includes(row.status)" link type="primary" @click="openSeatAssign(row)">分配</el-button>
            <el-button v-if="row.status === 'assigned'" link type="warning" @click="confirmSeatReturn(row)">回收</el-button>
            <el-button link type="primary" @click="openSeatHistory(row)">历史</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="relation-pagination" background layout="total, prev, pager, next" :total="seatPagination.total" :page-size="seatPagination.pageSize" :current-page="seatPagination.page" @current-change="changeSeatPage" />
    </el-drawer>

    <el-dialog v-model="addSeatDialog.visible" title="新增授权席位" width="560px">
      <el-form :model="addSeatDialog.form" label-width="100px">
        <el-form-item label="新增数量"><el-input-number v-model="addSeatDialog.form.count" :min="1" :max="1000" style="width:100%" /></el-form-item>
        <el-form-item label="指定编号"><el-input v-model="addSeatDialog.form.seat_codes_text" type="textarea" :rows="5" placeholder="可选，每行一个席位编号；不足数量的部分自动生成" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="addSeatDialog.form.remark" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="addSeatDialog.visible = false">取消</el-button><el-button type="primary" :loading="submitting" @click="submitAddSeats">确认新增</el-button></template>
    </el-dialog>

    <el-dialog v-model="seatAssignDialog.visible" title="分配授权席位" width="620px">
      <el-alert v-if="seatAssignDialog.seat" :title="seatAssignDialog.seat.seat_code" type="info" show-icon :closable="false" />
      <el-form :model="seatAssignDialog.form" label-width="96px" class="operate-form">
        <el-form-item label="领用人">
          <el-select v-model="seatAssignDialog.form.assignee_user_id" filterable clearable style="width:100%" @change="selectSeatAssignee">
            <el-option v-for="user in assignees" :key="user.user_id" :label="assigneeLabel(user)" :value="user.user_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定资产">
          <el-select v-model="seatAssignDialog.form.asset_id" filterable remote reserve-keyword clearable :remote-method="searchAssignableAssets" placeholder="输入资产编号或名称搜索" style="width:100%">
            <el-option v-for="asset in assignableAssets" :key="asset.asset_id" :label="`${asset.asset_id} / ${asset.name || '-'}`" :value="asset.asset_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门"><el-input v-model="seatAssignDialog.form.dept_id" disabled /></el-form-item>
        <el-form-item label="备注"><el-input v-model="seatAssignDialog.form.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="seatAssignDialog.visible = false">取消</el-button><el-button type="primary" :loading="submitting" @click="submitSeatAssign">确认分配</el-button></template>
    </el-dialog>

    <el-dialog v-model="seatHistoryDialog.visible" :title="seatHistoryDialog.seat ? `${seatHistoryDialog.seat.seat_code} / 分配历史` : '分配历史'" width="850px">
      <el-table :data="seatHistoryRows" border stripe max-height="520">
        <el-table-column prop="created_at_text" label="时间" width="170" />
        <el-table-column prop="action_label" label="动作" width="90" />
        <el-table-column prop="assignee_name" label="人员" min-width="120" />
        <el-table-column prop="asset_id" label="资产" min-width="130" />
        <el-table-column prop="dept_id" label="部门" min-width="130" />
        <el-table-column prop="operator" label="操作人" min-width="120" />
        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
      </el-table>
    </el-dialog>

    <el-drawer v-model="installationDrawer.visible" :title="installationDrawer.item ? `${installationDrawer.item.name} / 当前安装关系` : '当前安装关系'" size="760px">
      <div class="relation-filters relation-filters--compact">
        <el-input v-model="installationFilters.keyword" clearable placeholder="搜索资产编号或名称" @keyup.enter="searchInstallations" />
        <el-button type="primary" @click="searchInstallations">查询</el-button>
      </div>
      <el-table :data="installationRows" border stripe>
        <el-table-column prop="asset_id" label="资产编号" width="150" />
        <el-table-column prop="asset_name" label="资产名称" min-width="180" />
        <el-table-column prop="quantity" label="安装数量" width="100" />
        <el-table-column prop="dept_id" label="部门" min-width="130" />
        <el-table-column prop="installed_at_text" label="首次安装" width="170" />
        <el-table-column prop="installed_by" label="操作人" min-width="120" />
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
      </el-table>
      <el-pagination class="relation-pagination" background layout="total, prev, pager, next" :total="installationPagination.total" :page-size="installationPagination.pageSize" :current-page="installationPagination.page" @current-change="changeInstallationPage" />
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAssets } from '../../api/asset'
import { assignLicenseSeat, createInventoryItem, createLicenseSeats, getComponentInstallations, getInventoryAssignees, getInventoryItems, getInventoryLedger, getLicenseSeatHistory, getLicenseSeats, inventoryActions, inventoryTypes, operateInventoryItem, returnLicenseSeat, updateInventoryItem } from '../../api/inventory'
import { getLocations } from '../../api/location'

const loading = ref(false)
const route = useRoute()
const isLicensePage = computed(() => route.meta.inventoryMode === 'license')
const submitting = ref(false)
const items = ref([])
const ledgerRows = ref([])
const licenseSeats = ref([])
const seatHistoryRows = ref([])
const installationRows = ref([])
const assignees = ref([])
const assignableAssets = ref([])
const locations = ref([])
const summary = reactive({})
const filters = reactive({ keyword: '', item_type: '', status: '', low_stock: false })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const itemDialog = reactive({ visible: false, form: defaultItemForm() })
const operateDialog = reactive({ visible: false, item: null, form: defaultOperateForm() })
const ledgerDrawer = reactive({ visible: false })
const seatDrawer = reactive({ visible: false, item: null })
const addSeatDialog = reactive({ visible: false, form: { count: 1, seat_codes_text: '', remark: '' } })
const seatAssignDialog = reactive({ visible: false, seat: null, form: defaultSeatAssignForm() })
const seatHistoryDialog = reactive({ visible: false, seat: null })
const installationDrawer = reactive({ visible: false, item: null })
const seatFilters = reactive({ keyword: '', status: '' })
const seatPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const seatStats = reactive({ available: 0, assigned: 0, recovered: 0, disabled: 0 })
const installationFilters = reactive({ keyword: '' })
const installationPagination = reactive({ page: 1, pageSize: 10, total: 0 })

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

async function openLicenseSeats(row) {
  seatDrawer.item = row
  seatDrawer.visible = true
  Object.assign(seatFilters, { keyword: '', status: '' })
  seatPagination.page = 1
  const [, users, assetResult] = await Promise.all([
    loadLicenseSeats(),
    getInventoryAssignees().catch(() => []),
    getAssets({ page: 1, page_size: 50 }).catch(() => ({ list: [] }))
  ])
  assignees.value = users || []
  assignableAssets.value = assetResult.list || []
}

async function searchAssignableAssets(keyword) {
  const result = await getAssets({ keyword, page: 1, page_size: 50 }).catch(() => ({ list: [] }))
  assignableAssets.value = result.list || []
}

async function loadLicenseSeats() {
  if (!seatDrawer.item) return
  const result = await getLicenseSeats(seatDrawer.item.id, { keyword: seatFilters.keyword || undefined, status: seatFilters.status || undefined, page: seatPagination.page, page_size: seatPagination.pageSize })
  licenseSeats.value = result.list || []
  seatPagination.total = result.total || 0
  Object.assign(seatStats, { available: 0, assigned: 0, recovered: 0, disabled: 0 }, result.summary || {})
}

function searchLicenseSeats() {
  seatPagination.page = 1
  loadLicenseSeats()
}

function changeSeatPage(page) {
  seatPagination.page = page
  loadLicenseSeats()
}

function openAddSeats() {
  Object.assign(addSeatDialog.form, { count: 1, seat_codes_text: '', remark: '' })
  addSeatDialog.visible = true
}

async function submitAddSeats() {
  submitting.value = true
  try {
    const seat_codes = addSeatDialog.form.seat_codes_text.split(/\r?\n/).map(value => value.trim()).filter(Boolean)
    await createLicenseSeats(seatDrawer.item.id, { count: Number(addSeatDialog.form.count || 1), seat_codes, remark: addSeatDialog.form.remark })
    ElMessage.success('授权席位已新增')
    addSeatDialog.visible = false
    await Promise.all([loadLicenseSeats(), loadItems()])
  } finally {
    submitting.value = false
  }
}

function openSeatAssign(seat) {
  seatAssignDialog.seat = seat
  seatAssignDialog.form = defaultSeatAssignForm()
  seatAssignDialog.visible = true
}

function selectSeatAssignee(userId) {
  const user = assignees.value.find(item => item.user_id === userId)
  seatAssignDialog.form.assignee_name = user?.display_name || user?.username || ''
  seatAssignDialog.form.dept_id = user?.dept_id || user?.dept_name || ''
}

async function submitSeatAssign() {
  if (!seatAssignDialog.form.assignee_user_id && !seatAssignDialog.form.asset_id) return ElMessage.warning('请选择领用人或绑定资产')
  submitting.value = true
  try {
    await assignLicenseSeat(seatAssignDialog.seat.id, seatAssignDialog.form)
    ElMessage.success('授权席位已分配')
    seatAssignDialog.visible = false
    await Promise.all([loadLicenseSeats(), loadItems()])
  } finally {
    submitting.value = false
  }
}

async function confirmSeatReturn(seat) {
  try {
    const result = await ElMessageBox.prompt('可填写回收原因或交接说明', `回收 ${seat.seat_code}`, { inputPlaceholder: '回收说明', confirmButtonText: '确认回收', cancelButtonText: '取消' })
    await returnLicenseSeat(seat.id, result.value || '')
    ElMessage.success('授权席位已回收')
    await Promise.all([loadLicenseSeats(), loadItems()])
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') throw error
  }
}

async function openSeatHistory(seat) {
  seatHistoryDialog.seat = seat
  seatHistoryRows.value = await getLicenseSeatHistory(seat.id)
  seatHistoryDialog.visible = true
}

async function openInstallations(row) {
  installationDrawer.item = row
  installationFilters.keyword = ''
  installationPagination.page = 1
  installationDrawer.visible = true
  await loadInstallations()
}

async function loadInstallations() {
  if (!installationDrawer.item) return
  const result = await getComponentInstallations(installationDrawer.item.id, { keyword: installationFilters.keyword || undefined, page: installationPagination.page, page_size: installationPagination.pageSize })
  installationRows.value = result.list || []
  installationPagination.total = result.total || 0
}

function searchInstallations() {
  installationPagination.page = 1
  loadInstallations()
}

function changeInstallationPage(page) {
  installationPagination.page = page
  loadInstallations()
}

function defaultItemForm() {
  return { item_type: isLicensePage.value ? 'license' : 'accessory', code: '', name: '', brand: '', model: '', spec: '', total_qty: 0, available_qty: 0, min_qty: 0, unit_cost: 0, license_key: '', expire_date: '', supplier: '', dept_id: '', location: '', status: 'active', remark: '' }
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

function defaultSeatAssignForm() {
  return { assignee_user_id: '', assignee_name: '', dept_id: '', asset_id: '', remark: '' }
}

function seatStatusType(status) {
  return { available: 'success', assigned: 'primary', recovered: 'warning', disabled: 'info' }[status] || 'info'
}

function assigneeLabel(user) {
  const name = user.display_name || user.username || user.user_id
  const dept = user.dept_name || user.dept_id || '未分部门'
  return `${name} / ${dept}`
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

.relation-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.relation-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.relation-filters {
  display: grid;
  grid-template-columns: minmax(240px, 420px) 180px auto;
  gap: 10px;
  margin-bottom: 14px;
}

.relation-filters--compact {
  grid-template-columns: minmax(240px, 420px) auto;
}

.relation-pagination {
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 900px) {
  .inventory-metrics,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .relation-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .relation-filters,
  .relation-filters--compact {
    grid-template-columns: 1fr;
  }
}
</style>
