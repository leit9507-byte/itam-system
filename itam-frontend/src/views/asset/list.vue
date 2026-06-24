<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产管理</h2>
        <p class="page-subtitle">支持批量导入、出入库、使用人绑定、维修登记、报废审批和采购/质保信息维护</p>
      </div>
      <el-button type="primary" @click="importDialog.visible = true">批量导入资产</el-button>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="filters.keyword" clearable placeholder="搜索资产ID/名称/部门/序列号/使用人/供应商" style="width: 340px" @input="loadAssets" />
        <el-select v-model="filters.status" clearable placeholder="状态" style="width: 150px" @change="loadAssets">
          <el-option v-for="item in assetStatuses" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.category" clearable placeholder="设备类型" style="width: 170px" @change="loadAssets">
          <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
        </el-select>
        <el-divider direction="vertical" />
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
        <el-table-column prop="purchase_supplier_name" label="供应商" width="140" show-overflow-tooltip />
        <el-table-column prop="purchase_date" label="采购时间" width="120" />
        <el-table-column prop="owner" label="使用人" width="120">
          <template #default="{ row }">{{ displayUser(row.owner) }}</template>
        </el-table-column>
        <el-table-column prop="dept" label="部门" width="120">
          <template #default="{ row }">{{ row.dept || '未绑定' }}</template>
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
        <div class="edit-grid">
          <el-form-item label="资产名称"><el-input v-model="editDialog.form.name" /></el-form-item>
          <el-form-item label="序列号"><el-input v-model="editDialog.form.sn" /></el-form-item>
          <el-form-item label="设备类型">
            <el-select v-model="editDialog.form.category" filterable allow-create default-first-option style="width: 100%">
              <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="editDialog.form.status" style="width: 100%">
              <el-option v-for="item in assetStatuses" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="品牌"><el-input v-model="editDialog.form.brand" /></el-form-item>
          <el-form-item label="型号"><el-input v-model="editDialog.form.model" /></el-form-item>
          <el-form-item label="规格"><el-input v-model="editDialog.form.spec" /></el-form-item>
          <el-form-item label="价值"><el-input-number v-model="editDialog.form.price" :min="0" style="width: 100%" /></el-form-item>
          <el-form-item label="采购时间">
            <el-date-picker v-model="editDialog.form.purchase_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="采购审批单号"><el-input v-model="editDialog.form.purchase_approval_no" /></el-form-item>
          <el-form-item label="采购供应商"><el-input v-model="editDialog.form.purchase_supplier_name" /></el-form-item>
          <el-form-item label="质保到期">
            <el-date-picker v-model="editDialog.form.warranty_expire_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="质保月数"><el-input-number v-model="editDialog.form.warranty_months" :min="0" style="width: 100%" /></el-form-item>
          <el-form-item label="使用人">
            <el-select v-model="editDialog.form.owner_user_id" filterable clearable style="width: 100%" @change="fillUserToForm(editDialog.form, $event)">
              <el-option v-for="user in users" :key="user.user_id" :label="`${user.display_name} (${user.username})`" :value="user.user_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="部门"><el-input v-model="editDialog.form.dept_id" /></el-form-item>
          <el-form-item label="位置"><el-input v-model="editDialog.form.location" /></el-form-item>
          <el-form-item label="仓库"><el-input v-model="editDialog.form.warehouse" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存调整</el-button>
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
            <el-select v-model="batch.form.owner_user_id" filterable style="width: 100%" placeholder="选择用户目录中的用户" @change="fillUserToForm(batch.form, $event)">
              <el-option v-for="user in users" :key="user.user_id" :label="`${user.display_name} (${user.username}) / ${user.dept_name || user.dept_id || '未分部门'}`" :value="user.user_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="部门"><el-input v-model="batch.form.dept_id" /></el-form-item>
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

    <el-dialog v-model="repairDialog.visible" title="新增维修记录" width="620px">
      <el-descriptions v-if="repairDialog.asset" :column="2" border class="repair-asset">
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assetStatuses, createScrapRequest, getAssets, importAssetsFromExcel, importAssetsFromText, inboundAsset, outboundAsset, statusMap, updateAsset } from '../../api/asset'
import { getDeviceTypes } from '../../api/product'
import { createRepairRecord } from '../../api/repair'
import { getUsers } from '../../api/user'

const router = useRouter()
const assets = ref([])
const selected = ref([])
const categories = ref([])
const users = ref([])
const filters = reactive({ keyword: '', status: '', category: '' })
const batch = reactive({ visible: false, type: 'inbound', assets: [], form: defaultBatchForm() })
const importDialog = reactive({ visible: false, loading: false, content: '', result: null })
const editDialog = reactive({ visible: false, form: {} })
const repairDialog = reactive({ visible: false, asset: null, form: defaultRepairForm() })

const batchTitle = computed(() => ({ inbound: '批量入库', outbound: '批量出库', scrap: '批量申请报废' }[batch.type]))

onMounted(async () => {
  await Promise.all([loadAssets(), loadUsers(), loadTypes()])
})

async function loadAssets() {
  const data = await getAssets(filters)
  assets.value = data.list
}

async function loadUsers() {
  users.value = await getUsers()
}

async function loadTypes() {
  const types = await getDeviceTypes()
  categories.value = types.map(item => item.name)
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

function displayUser(userId) {
  const user = users.value.find(item => item.user_id === userId || item.username === userId)
  return user ? user.display_name : userId || '未分配'
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
  editDialog.visible = true
}

async function submitEdit() {
  await updateAsset(editDialog.form.asset_id, editDialog.form)
  editDialog.visible = false
  ElMessage.success('资产信息已更新')
  await loadAssets()
}

function openRepair(row) {
  if (!canRepair(row)) return
  repairDialog.asset = row
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
  await createRepairRecord(repairDialog.asset, repairDialog.form)
  repairDialog.visible = false
  ElMessage.success('维修单已创建，资产状态已更新为维修中')
  await loadAssets()
}

function openBatch(type) {
  const target = selected.value
  if (!validateBatchAssets(type, target)) return
  batch.type = type
  batch.assets = target
  Object.assign(batch.form, defaultBatchForm())
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

.repair-asset {
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
  .edit-grid {
    grid-template-columns: 1fr;
  }
}
</style>
