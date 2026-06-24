<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产管理</h2>
        <p class="page-subtitle">支持批量导入、批量编辑、批量维修、出入库、责任人绑定、供应商关联和报废审批</p>
      </div>
      <el-button type="primary" @click="importDialog.visible = true">批量导入资产</el-button>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="filters.keyword" clearable placeholder="搜索资产ID/名称/部门/序列号/使用人/供应商" style="width: 340px" @input="loadAssets" />
        <el-select v-model="filters.status" clearable placeholder="状态" style="width: 140px" @change="loadAssets">
          <el-option v-for="item in assetStatuses" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.category" clearable filterable placeholder="设备类型" style="width: 160px" @change="loadAssets">
          <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.supplier" clearable filterable placeholder="供应商" style="width: 180px" @change="loadAssets">
          <el-option v-for="item in suppliers" :key="item.id || item.name" :label="item.name" :value="item.name" />
        </el-select>
        <el-divider direction="vertical" />
        <el-button :disabled="!selected.length" @click="openBatchEdit">批量编辑</el-button>
        <el-button :disabled="!selected.length" @click="openBatchRepair">批量维修</el-button>
        <el-button :disabled="!selected.length" @click="openBatch('inbound')">批量入库</el-button>
        <el-button :disabled="!selected.length" @click="openBatch('outbound')">批量出库</el-button>
        <el-button type="danger" :disabled="!selected.length" @click="openBatch('scrap')">批量申请报废</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-alert v-if="selected.length" :title="`已选择 ${selected.length} 个资产`" type="info" show-icon :closable="false" class="selection-alert" />
      <el-table :data="assets" border stripe @selection-change="selected = $event">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="asset_id" label="资产ID" width="132" />
        <el-table-column prop="company" label="公司" width="140" show-overflow-tooltip />
        <el-table-column label="产品信息" min-width="240">
          <template #default="{ row }">
            <div class="asset-name">
              <strong>{{ row.name }}</strong>
              <span>{{ row.brand || '-' }} / {{ row.model || '-' }} / {{ row.spec || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="sn" label="序列号" width="150" />
        <el-table-column prop="category" label="类型" width="110" />
        <el-table-column prop="purchase_supplier_name" label="供应商" width="150" show-overflow-tooltip />
        <el-table-column prop="purchase_date" label="采购时间" width="120" />
        <el-table-column label="使用人" width="150">
          <template #default="{ row }">{{ displayUser(row) }}</template>
        </el-table-column>
        <el-table-column label="部门" width="140">
          <template #default="{ row }">{{ displayDept(row) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type || 'info'">{{ statusMap[row.status]?.label || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价值" width="120">
          <template #default="{ row }">¥{{ Number(row.price || 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goDetail(row)">详细</el-button>
            <el-button type="primary" link :disabled="!canInbound(row)" @click="openSingleInbound(row)">入库</el-button>
            <el-button type="warning" link :disabled="!canOutbound(row)" @click="openSingleOutbound(row)">出库</el-button>
            <el-dropdown trigger="click" @command="command => handleMoreCommand(command, row)">
              <el-button type="primary" link>
                更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">编辑</el-dropdown-item>
                  <el-dropdown-item command="repair" :disabled="!canRepair(row)">维修</el-dropdown-item>
                  <el-dropdown-item command="scrap" :disabled="!canScrap(row)">报废</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="editDialog.visible" title="调整资产信息" width="900px">
      <el-form :model="editDialog.form" label-width="112px">
        <AssetEditFields
          :form="editDialog.form"
          :categories="categories"
          :suppliers="suppliers"
          :users="filteredUsers"
          @search-users="searchUsers"
          @select-user="userId => fillUserToForm(editDialog.form, userId)"
        />
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存调整</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchEdit.visible" title="批量编辑资产" width="760px">
      <el-alert :title="`本次将更新 ${selected.length} 个资产；未勾选的字段不会覆盖原资产信息。`" type="info" show-icon :closable="false" />
      <el-form :model="batchEdit.form" label-width="118px" class="batch-form">
        <div class="batch-edit-grid">
          <el-checkbox v-model="batchEdit.fields.category">设备类型</el-checkbox>
          <el-select v-model="batchEdit.form.category" filterable allow-create default-first-option :disabled="!batchEdit.fields.category">
            <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
          </el-select>

          <el-checkbox v-model="batchEdit.fields.status">状态</el-checkbox>
          <el-select v-model="batchEdit.form.status" :disabled="!batchEdit.fields.status">
            <el-option v-for="item in assetStatuses" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>

          <el-checkbox v-model="batchEdit.fields.purchase_supplier_name">供应商</el-checkbox>
          <el-select v-model="batchEdit.form.purchase_supplier_name" filterable clearable allow-create default-first-option :disabled="!batchEdit.fields.purchase_supplier_name">
            <el-option v-for="item in suppliers" :key="item.id || item.name" :label="supplierLabel(item)" :value="item.name" />
          </el-select>

          <el-checkbox v-model="batchEdit.fields.owner_user_id">责任人</el-checkbox>
          <el-select v-model="batchEdit.form.owner_user_id" filterable remote clearable reserve-keyword :remote-method="searchUsers" :disabled="!batchEdit.fields.owner_user_id" @change="fillUserToForm(batchEdit.form, $event)">
            <el-option v-for="user in filteredUsers" :key="user.user_id" :label="userLabel(user)" :value="user.user_id" />
          </el-select>

          <el-checkbox v-model="batchEdit.fields.location">位置</el-checkbox>
          <el-input v-model="batchEdit.form.location" :disabled="!batchEdit.fields.location" />

          <el-checkbox v-model="batchEdit.fields.warehouse">仓库</el-checkbox>
          <el-input v-model="batchEdit.form.warehouse" :disabled="!batchEdit.fields.warehouse" />
        </div>
      </el-form>
      <template #footer>
        <el-button @click="batchEdit.visible = false">取消</el-button>
        <el-button type="primary" @click="submitBatchEdit">确认批量更新</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batch.visible" :title="batchTitle" width="660px">
      <el-alert :title="`本次将处理 ${batch.assets.length} 个资产`" type="info" show-icon :closable="false" />
      <el-form :model="batch.form" label-width="110px" class="batch-form">
        <template v-if="batch.type === 'inbound'">
          <el-form-item label="入库仓库"><el-input v-model="batch.form.warehouse" /></el-form-item>
          <el-form-item label="备注"><el-input v-model="batch.form.remark" type="textarea" :rows="3" placeholder="例如：归还入库、调拨回库" /></el-form-item>
        </template>
        <template v-if="batch.type === 'outbound'">
          <el-form-item label="出库类型">
            <el-select v-model="batch.form.toStatus" style="width: 100%">
              <el-option label="领用在用" value="in_use" />
              <el-option label="借出" value="borrowed" />
              <el-option label="已出库" value="out_stock" />
            </el-select>
          </el-form-item>
          <el-form-item label="领用人" required>
            <el-select v-model="batch.form.owner_user_id" filterable remote reserve-keyword style="width: 100%" placeholder="搜索用户姓名/账号/部门" :remote-method="searchUsers" @change="fillUserToForm(batch.form, $event)">
              <el-option v-for="user in filteredUsers" :key="user.user_id" :label="userLabel(user)" :value="user.user_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="部门"><el-input v-model="batch.form.dept_id" disabled /></el-form-item>
          <el-form-item label="位置"><el-input v-model="batch.form.location" /></el-form-item>
          <el-form-item label="备注"><el-input v-model="batch.form.remark" type="textarea" :rows="3" /></el-form-item>
        </template>
        <template v-if="batch.type === 'scrap'">
          <el-form-item label="申请人/部门"><el-input v-model="batch.form.applicant" /></el-form-item>
          <el-form-item label="处置方式">
            <el-select v-model="batch.form.disposal_method" style="width: 100%">
              <el-option label="环保回收" value="环保回收" />
              <el-option label="供应商回收" value="供应商回收" />
              <el-option label="内部拆件" value="内部拆件" />
              <el-option label="销毁处理" value="销毁处理" />
            </el-select>
          </el-form-item>
          <el-form-item label="预计残值"><el-input-number v-model="batch.form.estimated_residual_value" :min="0" style="width: 100%" /></el-form-item>
          <el-form-item label="报废原因"><el-input v-model="batch.form.reason" type="textarea" :rows="4" /></el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="batch.visible = false">取消</el-button>
        <el-button type="primary" @click="submitBatch">确认执行</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="repairDialog.visible" :title="repairDialog.assets.length > 1 ? '批量新增维修记录' : '新增维修记录'" width="620px">
      <el-alert v-if="repairDialog.assets.length > 1" :title="`本次将为 ${repairDialog.assets.length} 个资产创建维修记录，并更新为维修中。`" type="warning" show-icon :closable="false" class="dialog-alert" />
      <el-descriptions v-else-if="repairDialog.asset" :column="2" border class="repair-asset">
        <el-descriptions-item label="资产ID">{{ repairDialog.asset.asset_id }}</el-descriptions-item>
        <el-descriptions-item label="资产名称">{{ repairDialog.asset.name }}</el-descriptions-item>
        <el-descriptions-item label="序列号">{{ repairDialog.asset.sn || '-' }}</el-descriptions-item>
        <el-descriptions-item label="当前状态">{{ statusMap[repairDialog.asset.status]?.label || repairDialog.asset.status }}</el-descriptions-item>
      </el-descriptions>
      <el-form :model="repairDialog.form" label-width="100px" class="repair-form">
        <el-form-item label="维修时间" required>
          <el-date-picker v-model="repairDialog.form.repair_time" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="故障原因" required>
          <el-input v-model="repairDialog.form.fault_reason" type="textarea" :rows="4" placeholder="例如：无法开机、屏幕损坏、主板故障" />
        </el-form-item>
        <el-form-item label="维修费用" required>
          <el-input-number v-model="repairDialog.form.repair_cost" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="维修商"><el-input v-model="repairDialog.form.vendor" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="repairDialog.form.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="repairDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitRepair">创建维修单</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialog.visible" title="批量导入资产" width="900px">
      <el-alert title="支持上传 .xlsx/.xlsm，也支持从 Excel 复制粘贴。推荐表头：资产名称、设备类型、品牌、型号、序列号、价格、采购日期、采购审批单号、采购供应商、质保到期、使用人、部门、仓库、状态。" type="info" show-icon :closable="false" />
      <div class="upload-row">
        <el-upload :show-file-list="false" accept=".xlsx,.xlsm" :before-upload="submitExcelImport">
          <el-button type="primary">上传 Excel 文件</el-button>
        </el-upload>
        <el-button @click="fillImportExample">填入粘贴示例</el-button>
      </div>
      <el-input v-model="importDialog.content" type="textarea" :rows="9" class="import-textarea" placeholder="也可以把 Excel 表格复制后粘贴到这里" />
      <div class="import-actions">
        <el-button type="primary" :loading="importDialog.loading" @click="submitTextImport">导入粘贴内容</el-button>
      </div>
      <el-table v-if="importDialog.result?.errors?.length" :data="importDialog.result.errors" border size="small" class="import-result">
        <el-table-column prop="row" label="行号" width="80" />
        <el-table-column prop="message" label="提示" />
      </el-table>
      <el-result v-if="importDialog.result && !importDialog.result.errors.length" icon="success" :title="`已导入 ${importDialog.result.created} 条资产`" sub-title="资产已写入后端，并生成批量导入生命周期记录" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ArrowDown } from '@element-plus/icons-vue'
import { computed, defineComponent, h, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assetStatuses, batchUpdateAssets, createScrapRequest, getAssets, importAssetsFromExcel, importAssetsFromText, inboundAsset, outboundAsset, statusMap, updateAsset } from '../../api/asset'
import { getDeviceTypes } from '../../api/product'
import { createRepairRecords } from '../../api/repair'
import { getSuppliers } from '../../api/supplier'
import { getUsers } from '../../api/user'

const router = useRouter()
const assets = ref([])
const selected = ref([])
const categories = ref([])
const users = ref([])
const filteredUsers = ref([])
const suppliers = ref([])
const filters = reactive({ keyword: '', status: '', category: '', supplier: '' })
const batch = reactive({ visible: false, type: 'inbound', assets: [], form: defaultBatchForm() })
const batchEdit = reactive({ visible: false, form: defaultBatchEditForm(), fields: defaultBatchEditFields() })
const importDialog = reactive({ visible: false, loading: false, content: '', result: null })
const editDialog = reactive({ visible: false, form: {} })
const repairDialog = reactive({ visible: false, asset: null, assets: [], form: defaultRepairForm() })

const batchTitle = computed(() => ({ inbound: '批量入库', outbound: '批量出库', scrap: '批量申请报废' }[batch.type]))

onMounted(async () => {
  await Promise.all([loadAssets(), loadUsers(), loadTypes(), loadSuppliers()])
})

async function loadAssets() {
  const data = await getAssets(filters)
  assets.value = data.list
}

async function loadUsers() {
  users.value = await getUsers()
  filteredUsers.value = users.value
}

async function loadTypes() {
  const types = await getDeviceTypes()
  categories.value = types.map(item => item.name)
}

async function loadSuppliers() {
  suppliers.value = await getSuppliers()
}

function defaultBatchForm() {
  return {
    warehouse: '',
    toStatus: 'in_use',
    owner_user_id: '',
    owner_name: '',
    dept_id: '',
    dept_name: '',
    location: '',
    applicant: '',
    reason: '',
    disposal_method: '环保回收',
    estimated_residual_value: 0,
    remark: ''
  }
}

function defaultBatchEditForm() {
  return {
    category: '',
    status: '',
    purchase_supplier_name: '',
    owner_user_id: '',
    owner_name: '',
    dept_id: '',
    dept_name: '',
    location: '',
    warehouse: ''
  }
}

function defaultBatchEditFields() {
  return {
    category: false,
    status: false,
    purchase_supplier_name: false,
    owner_user_id: false,
    location: false,
    warehouse: false
  }
}

function defaultRepairForm() {
  return {
    repair_time: new Date().toISOString().slice(0, 10),
    fault_reason: '',
    repair_cost: 0,
    vendor: '',
    operator: '资产管理员',
    remark: ''
  }
}

function displayUser(row) {
  if (row.owner_name) return row.owner_name
  const user = findUser(row.owner_user_id || row.owner)
  return user ? user.display_name : row.owner || '未分配'
}

function displayDept(row) {
  if (row.dept_name) return row.dept_name
  const user = findUser(row.owner_user_id || row.owner)
  return user?.dept_name || row.dept || '未绑定'
}

function findUser(value) {
  if (!value) return null
  const lower = String(value).toLowerCase()
  const cn = lower.includes('cn=') ? lower.split('cn=', 2)[1].split(',', 1)[0] : ''
  return users.value.find(user => [user.user_id, user.username, user.external_id, user.email].filter(Boolean).map(String).map(item => item.toLowerCase()).includes(lower) || (cn && String(user.username).toLowerCase() === cn))
}

function userLabel(user) {
  return `${user.display_name} (${user.username}) / ${user.dept_name || user.dept_id || '未分部门'}`
}

function supplierLabel(item) {
  const meta = [item.contact, item.phone].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}

function searchUsers(query = '') {
  const keyword = query.trim().toLowerCase()
  filteredUsers.value = !keyword
    ? users.value
    : users.value.filter(user =>
        [user.user_id, user.username, user.display_name, user.email, user.dept_id, user.dept_name, user.external_id]
          .join(' ')
          .toLowerCase()
          .includes(keyword)
      )
}

function fillUserToForm(form, userId) {
  const user = users.value.find(item => item.user_id === userId)
  form.owner_user_id = userId || ''
  form.owner_name = user?.display_name || ''
  form.dept_id = user?.dept_id || user?.dept_name || ''
  form.dept_name = user?.dept_name || user?.dept_id || ''
  if (!form.location && user?.dept_name) form.location = user.dept_name
}

function canInbound(row) {
  return !['in_stock', 'pending_scrap', 'scrapped'].includes(row.status)
}

function canOutbound(row) {
  return ['in_stock', 'idle'].includes(row.status)
}

function canRepair(row) {
  return !['scrapped', 'pending_scrap', 'repair'].includes(row.status)
}

function canScrap(row) {
  return !['scrapped', 'pending_scrap'].includes(row.status)
}

function goDetail(row) {
  router.push(`/asset/detail/${row.asset_id}`)
}

function openEdit(row) {
  editDialog.form = { ...row, owner_user_id: row.owner_user_id || row.owner, dept_id: row.dept_id || row.dept }
  searchUsers('')
  editDialog.visible = true
}

async function submitEdit() {
  await updateAsset(editDialog.form.asset_id, editDialog.form)
  editDialog.visible = false
  ElMessage.success('资产信息已更新')
  await loadAssets()
}

function openBatchEdit() {
  batchEdit.form = defaultBatchEditForm()
  batchEdit.fields = defaultBatchEditFields()
  searchUsers('')
  batchEdit.visible = true
}

async function submitBatchEdit() {
  const payload = {}
  Object.keys(batchEdit.fields).forEach(key => {
    if (batchEdit.fields[key]) payload[key] = batchEdit.form[key]
  })
  if (batchEdit.fields.owner_user_id) {
    payload.dept_id = batchEdit.form.dept_id
    payload.location = batchEdit.form.location
  }
  if (!Object.keys(payload).length) {
    ElMessage.warning('请至少勾选一个要更新的字段')
    return
  }
  await batchUpdateAssets(selected.value, payload)
  batchEdit.visible = false
  selected.value = []
  ElMessage.success('批量编辑完成')
  await loadAssets()
}

function openRepair(row) {
  if (!canRepair(row)) return
  repairDialog.asset = row
  repairDialog.assets = [row]
  Object.assign(repairDialog.form, defaultRepairForm())
  repairDialog.visible = true
}

function openBatchRepair() {
  if (selected.value.some(row => !canRepair(row))) {
    ElMessage.warning('已报废、待报废或维修中的资产不能重复创建维修单')
    return
  }
  repairDialog.asset = selected.value[0] || null
  repairDialog.assets = [...selected.value]
  Object.assign(repairDialog.form, defaultRepairForm())
  repairDialog.visible = true
}

async function submitRepair() {
  if (!repairDialog.form.repair_time) {
    ElMessage.warning('请选择维修时间')
    return
  }
  if (!repairDialog.form.fault_reason.trim()) {
    ElMessage.warning('请填写故障原因')
    return
  }
  await createRepairRecords(repairDialog.assets, repairDialog.form)
  repairDialog.visible = false
  selected.value = []
  ElMessage.success('维修单已创建，资产状态已更新为维修中')
  await loadAssets()
}

function openBatch(type) {
  const target = selected.value
  if (!validateBatchAssets(type, target)) return
  batch.type = type
  batch.assets = target
  Object.assign(batch.form, defaultBatchForm())
  searchUsers('')
  batch.visible = true
}

function openSingleInbound(row) {
  if (!canInbound(row)) return
  selected.value = [row]
  openBatch('inbound')
}

function openSingleOutbound(row) {
  if (!canOutbound(row)) return
  selected.value = [row]
  openBatch('outbound')
}

function openSingleScrap(row) {
  if (!canScrap(row)) return
  selected.value = [row]
  openBatch('scrap')
}

function handleMoreCommand(command, row) {
  if (command === 'edit') openEdit(row)
  if (command === 'repair') openRepair(row)
  if (command === 'scrap') openSingleScrap(row)
}

function validateBatchAssets(type, rows) {
  if (type === 'outbound' && rows.some(row => !canOutbound(row))) {
    ElMessage.warning('只有在库或闲置资产可以出库；在用资产不能再次出库，请先入库回收。')
    return false
  }
  if (type === 'inbound' && rows.some(row => !canInbound(row))) {
    ElMessage.warning('在库、待报废或已报废资产不能执行入库。')
    return false
  }
  if (type === 'scrap' && rows.some(row => !canScrap(row))) {
    ElMessage.warning('待报废或已报废资产不能重复发起报废。')
    return false
  }
  return true
}

function fillImportExample() {
  importDialog.content = [
    '资产名称,设备类型,品牌,型号,序列号,价格,采购日期,采购审批单号,采购供应商,质保到期,使用人,部门,仓库,状态',
    'ThinkPad X1 Carbon,笔记本电脑,Lenovo,X1 Carbon Gen 12,SN-IMPORT-001,15000,2026-06-24,OA-20260624-001,联想授权供应商,2029-06-24,U-ADMIN,IT,上海IT仓,in_stock',
    'Dell U2723QE,显示器,Dell,U2723QE,SN-IMPORT-002,3999,2026-06-24,OA-20260624-001,Dell渠道商,2029-06-24,U-AUDITOR,AUDIT,上海IT仓,in_stock'
  ].join('\n')
}

async function submitExcelImport(file) {
  importDialog.loading = true
  try {
    importDialog.result = await importAssetsFromExcel(file, 'frontend-excel-import')
    ElMessage.success(`Excel 导入完成：新增 ${importDialog.result.created} 条，跳过 ${importDialog.result.skipped} 条`)
    await loadAssets()
  } finally {
    importDialog.loading = false
  }
  return false
}

async function submitTextImport() {
  if (!importDialog.content.trim()) {
    ElMessage.warning('请先粘贴导入内容')
    return
  }
  importDialog.loading = true
  try {
    importDialog.result = await importAssetsFromText(importDialog.content, 'frontend-text-import')
    ElMessage.success(`导入完成：新增 ${importDialog.result.created} 条，跳过 ${importDialog.result.skipped} 条`)
    await loadAssets()
  } finally {
    importDialog.loading = false
  }
}

async function submitBatch() {
  if (!validateBatchAssets(batch.type, batch.assets)) return
  if (batch.type === 'outbound' && !batch.form.owner_user_id) {
    ElMessage.warning('请选择领用人')
    return
  }
  for (const asset of batch.assets) {
    if (batch.type === 'inbound') await inboundAsset(asset.asset_id, batch.form)
    if (batch.type === 'outbound') await outboundAsset(asset.asset_id, batch.form)
    if (batch.type === 'scrap') await createScrapRequest(asset.asset_id, batch.form)
  }
  ElMessage.success(`${batchTitle.value}完成`)
  batch.visible = false
  selected.value = []
  await loadAssets()
}

const AssetEditFields = defineComponent({
  props: {
    form: { type: Object, required: true },
    categories: { type: Array, required: true },
    suppliers: { type: Array, required: true },
    users: { type: Array, required: true }
  },
  emits: ['search-users', 'select-user'],
  setup(props, { emit }) {
    return () =>
      h('div', { class: 'edit-grid' }, [
        field('资产名称', h(resolveInput(), { modelValue: props.form.name, 'onUpdate:modelValue': value => (props.form.name = value) })),
        field('所属公司', h(resolveInput(), { modelValue: props.form.company, 'onUpdate:modelValue': value => (props.form.company = value), placeholder: '例如：总部 / 子公司A' })),
        field('序列号', h(resolveInput(), { modelValue: props.form.sn, 'onUpdate:modelValue': value => (props.form.sn = value) })),
        field('设备类型', h(resolveSelect(), { modelValue: props.form.category, 'onUpdate:modelValue': value => (props.form.category = value), filterable: true, allowCreate: true, defaultFirstOption: true, style: 'width:100%' }, () => props.categories.map(item => h(resolveOption(), { key: item, label: item, value: item })))),
        field('状态', h(resolveSelect(), { modelValue: props.form.status, 'onUpdate:modelValue': value => (props.form.status = value), style: 'width:100%' }, () => assetStatuses.map(item => h(resolveOption(), { key: item.value, label: item.label, value: item.value })))),
        field('品牌', h(resolveInput(), { modelValue: props.form.brand, 'onUpdate:modelValue': value => (props.form.brand = value) })),
        field('型号', h(resolveInput(), { modelValue: props.form.model, 'onUpdate:modelValue': value => (props.form.model = value) })),
        field('规格', h(resolveInput(), { modelValue: props.form.spec, 'onUpdate:modelValue': value => (props.form.spec = value) })),
        field('价值', h(resolveInputNumber(), { modelValue: props.form.price, 'onUpdate:modelValue': value => (props.form.price = value), min: 0, style: 'width:100%' })),
        field('采购时间', h(resolveDatePicker(), { modelValue: props.form.purchase_date, 'onUpdate:modelValue': value => (props.form.purchase_date = value), type: 'date', valueFormat: 'YYYY-MM-DD', style: 'width:100%' })),
        field('采购审批单号', h(resolveInput(), { modelValue: props.form.purchase_approval_no, 'onUpdate:modelValue': value => (props.form.purchase_approval_no = value) })),
        field('采购供应商', h(resolveSelect(), { modelValue: props.form.purchase_supplier_name, 'onUpdate:modelValue': value => (props.form.purchase_supplier_name = value), filterable: true, clearable: true, allowCreate: true, defaultFirstOption: true, style: 'width:100%' }, () => props.suppliers.map(item => h(resolveOption(), { key: item.id || item.name, label: item.name, value: item.name })))),
        field('质保到期', h(resolveDatePicker(), { modelValue: props.form.warranty_expire_date, 'onUpdate:modelValue': value => (props.form.warranty_expire_date = value), type: 'date', valueFormat: 'YYYY-MM-DD', style: 'width:100%' })),
        field('质保月数', h(resolveInputNumber(), { modelValue: props.form.warranty_months, 'onUpdate:modelValue': value => (props.form.warranty_months = value), min: 0, style: 'width:100%' })),
        field('责任人', h(resolveSelect(), { modelValue: props.form.owner_user_id, 'onUpdate:modelValue': value => (props.form.owner_user_id = value), filterable: true, remote: true, clearable: true, reserveKeyword: true, remoteMethod: value => emit('search-users', value), style: 'width:100%', onChange: value => emit('select-user', value) }, () => props.users.map(user => h(resolveOption(), { key: user.user_id, label: `${user.display_name} (${user.username}) / ${user.dept_name || user.dept_id || '未分部门'}`, value: user.user_id })))),
        field('部门', h(resolveInput(), { modelValue: props.form.dept_id, 'onUpdate:modelValue': value => (props.form.dept_id = value), disabled: true })),
        field('位置', h(resolveInput(), { modelValue: props.form.location, 'onUpdate:modelValue': value => (props.form.location = value) })),
        field('仓库', h(resolveInput(), { modelValue: props.form.warehouse, 'onUpdate:modelValue': value => (props.form.warehouse = value) }))
      ])
  }
})

function field(label, child) {
  return h(resolveFormItem(), { label }, () => child)
}

function resolveFormItem() { return 'el-form-item' }
function resolveInput() { return 'el-input' }
function resolveInputNumber() { return 'el-input-number' }
function resolveSelect() { return 'el-select' }
function resolveOption() { return 'el-option' }
function resolveDatePicker() { return 'el-date-picker' }
</script>

<style scoped>
.selection-alert {
  margin-bottom: 12px;
}

.asset-name {
  display: grid;
  gap: 4px;
}

.asset-name span {
  color: var(--muted);
  font-size: 12px;
}

.edit-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.batch-form,
.import-textarea,
.import-result,
.repair-form {
  margin-top: 16px;
}

.batch-edit-grid {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.repair-asset,
.dialog-alert {
  margin-bottom: 16px;
}

.upload-row,
.import-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
}

.upload-row {
  justify-content: flex-start;
}

@media (max-width: 900px) {
  .edit-grid,
  .batch-edit-grid {
    grid-template-columns: 1fr;
  }
}
</style>
