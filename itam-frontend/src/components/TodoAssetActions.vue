<template>
  <el-dialog v-model="assignDialog.visible" title="入职资产分配" :width="dialogWidth" :class="dialogClass" append-to-body>
    <el-alert :title="`为 ${assignDialog.todo?.name || assignDialog.todo?.owner || '员工'} 分配在库或闲置资产`" type="info" show-icon :closable="false" />
    <el-form :model="assignDialog.form" label-width="100px" class="todo-asset-form">
      <el-form-item label="选择资产" required>
        <el-select
          v-model="assignDialog.form.asset_ids"
          multiple
          filterable
          remote
          reserve-keyword
          clearable
          collapse-tags
          collapse-tags-tooltip
          placeholder="搜索资产编号、名称、序列号"
          :remote-method="searchAssignableAssets"
          :teleported="false"
          popper-class="todo-asset-select-popper"
          style="width: 100%"
        >
          <el-option v-for="item in assignDialog.assets" :key="item.asset_id" :label="assetLabel(item)" :value="item.asset_id">
            <div class="asset-option">
              <strong>{{ item.asset_no || item.asset_id }}</strong>
              <span>{{ item.name || '-' }}</span>
              <small>{{ [item.asset_no ? `ID ${item.asset_id}` : '', item.brand, item.model, item.sn, item.location || '未填写位置'].filter(Boolean).join(' / ') }}</small>
            </div>
          </el-option>
        </el-select>
      </el-form-item>
      <el-form-item v-if="mobile" label="扫码添加">
        <div class="assign-scan-row">
          <el-input
            v-model="assignDialog.scanInput"
            clearable
            placeholder="扫码或输入资产编号"
            @keyup.enter="addAssignAssetByCode(assignDialog.scanInput)"
          />
          <el-button type="primary" :loading="assignDialog.scanning" @click="scanAssignAsset">
            <el-icon><Camera /></el-icon>
            继续扫码
          </el-button>
        </div>
      </el-form-item>
      <el-form-item v-if="selectedAssignAssets.length" :label="`已选 ${selectedAssignAssets.length} 台`">
        <div class="selected-asset-list">
          <div v-for="item in selectedAssignAssets" :key="item.asset_id" class="selected-asset-row">
            <div>
              <strong>{{ item.asset_no || item.asset_id }}</strong>
              <span>{{ item.name || '-' }}</span>
              <small>{{ [item.sn ? `SN ${item.sn}` : '', item.location || '未填写位置'].filter(Boolean).join(' / ') }}</small>
            </div>
            <el-button text type="danger" aria-label="移除资产" @click="removeAssignAsset(item.asset_id)">移除</el-button>
          </div>
        </div>
      </el-form-item>
      <el-form-item label="使用位置">
        <el-select v-model="assignDialog.form.location" filterable clearable placeholder="选择使用位置" :teleported="false" popper-class="todo-location-select-popper" style="width: 100%">
          <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="assignDialog.form.remark" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="assignDialog.visible = false">取消</el-button>
      <el-button :loading="processing" @click="skipAssetAssignment">不需要分配公司资产</el-button>
      <el-button type="primary" :loading="processing" @click="submitAssign">{{ mobile ? '分配' : '确认分配' }} {{ selectedAssignAssets.length }} 台</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="reclaimDialog.visible" title="离职资产回收" :width="reclaimDialogWidth" :class="dialogClass" append-to-body>
    <el-alert :title="`${reclaimDialog.userName || '该人员'} 名下可回收资产 ${reclaimDialog.assets.length} 个`" type="warning" show-icon :closable="false" />
    <el-table class="reclaim-table" :data="reclaimDialog.assets" border @selection-change="rows => (reclaimDialog.selected = rows)">
      <el-table-column type="selection" width="44" />
      <el-table-column prop="asset_id" label="资产编号" width="130" />
      <el-table-column prop="name" label="资产名称" min-width="150" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">{{ statusLabel(row.status) }}</template>
      </el-table-column>
      <el-table-column prop="location" label="位置" min-width="140" show-overflow-tooltip />
    </el-table>
    <el-form :model="reclaimDialog.form" label-width="88px" class="todo-asset-form">
      <el-form-item label="入库位置" required>
        <el-select v-model="reclaimDialog.form.location" filterable clearable placeholder="选择回收入库位置" :teleported="false" style="width: 100%">
          <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="reclaimDialog.form.remark" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="reclaimDialog.visible = false">取消</el-button>
      <el-button type="primary" :disabled="!reclaimDialog.selected.length" :loading="processing" @click="submitUserReclaim">确认回收 {{ reclaimDialog.selected.length }} 个资产</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Camera } from '@element-plus/icons-vue'
import { batchCheckoutAssets, getAssetById, getAssets, inboundAsset } from '../api/asset'
import { getLocations } from '../api/location'
import { resolveScanBinding } from '../api/scanBinding'
import { getUsers, updateUserAssetAssignment } from '../api/user'
import { assetCodeCandidates, assetCodeMatches, parseAssetCode } from '../utils/assetCode'

const emit = defineEmits(['completed'])
const props = defineProps({
  mobile: { type: Boolean, default: false },
  scanCodeProvider: { type: Function, default: null }
})
const processing = ref(false)
const users = ref([])
const locations = ref([])
const assignDialog = reactive({
  visible: false,
  todo: null,
  assets: [],
  scanInput: '',
  scanning: false,
  form: { asset_ids: [], location: '', remark: '入职资产分配' }
})
const reclaimDialog = reactive({
  visible: false,
  user: null,
  userName: '',
  assets: [],
  selected: [],
  form: { location: '', remark: '离职资产回收入库' }
})

const dialogWidth = computed(() => (props.mobile ? 'min(360px, calc(100vw - 28px))' : '620px'))
const reclaimDialogWidth = computed(() => (props.mobile ? 'min(360px, calc(100vw - 28px))' : '760px'))
const dialogClass = computed(() => ['todo-action-dialog', { 'todo-action-dialog--mobile': props.mobile }])

const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))
const selectedAssignAssets = computed(() => {
  const selected = new Set(assignDialog.form.asset_ids)
  return assignDialog.assets.filter(item => selected.has(item.asset_id))
})

async function handle(item) {
  if (item.type === 'onboarding_assign') {
    await openAssignDialog(item)
    return true
  }
  if (item.type === 'offboarding_reclaim') {
    await openUserReclaimDialog(item)
    return true
  }
  if (item.type === 'user_reclaim') {
    await openUserReclaimDialog(item)
    return true
  }
  if (item.type === 'borrow_due_return') {
    await returnBorrowedAsset(item)
    return true
  }
  return false
}

async function openAssignDialog(item) {
  assignDialog.todo = item
  assignDialog.scanInput = ''
  Object.assign(assignDialog.form, { asset_ids: [], location: '', remark: '入职资产分配' })
  await ensureOptions()
  assignDialog.assets = await loadAssignableAssets('')
  assignDialog.visible = true
}

async function searchAssignableAssets(keyword = '') {
  const rows = await loadAssignableAssets(keyword)
  assignDialog.assets = mergeAssetOptions(assignDialog.assets.filter(item => assignDialog.form.asset_ids.includes(item.asset_id)), rows)
}

async function loadAssignableAssets(keyword = '') {
  const { list } = await getAssets({ keyword, page: 1, page_size: 50 })
  return list.filter(item => ['in_stock', 'idle'].includes(item.status))
}

async function submitAssign() {
  if (!assignDialog.form.asset_ids.length) return ElMessage.warning('请至少选择一台要分配的资产')
  const todo = assignDialog.todo
  processing.value = true
  try {
    await ensureUsers()
    const user = users.value.find(item => item.user_id === todo.user_id || item.username === todo.username)
    const result = await batchCheckoutAssets(assignDialog.form.asset_ids, {
      outboundTarget: 'user',
      toStatus: 'in_use',
      owner_user_id: user?.user_id || todo.user_id || todo.username,
      owner_name: user?.display_name || todo.name || todo.owner,
      dept_id: user?.dept_id || user?.dept_name || '',
      dept_name: user?.dept_name || user?.dept_id || '',
      location: assignDialog.form.location,
      remark: assignDialog.form.remark || '入职资产分配'
    })
    const success = Number(result?.success || 0)
    const failed = Number(result?.failed || 0)
    if (failed) {
      const failedIds = new Set((result.errors || []).map(item => item.asset_id))
      assignDialog.form.asset_ids = assignDialog.form.asset_ids.filter(id => failedIds.has(id))
      const first = result.errors?.[0]
      ElMessage.warning(`成功分配 ${success} 台，失败 ${failed} 台${first ? `：${first.asset_id} ${first.message}` : ''}`)
      if (!success) return
    } else {
      ElMessage.success(`已分配 ${success} 台入职资产`)
      assignDialog.visible = false
    }
    emit('completed')
  } catch (error) {
    ElMessage.error(`分配失败：${error?.message || '请稍后重试'}`)
  } finally {
    processing.value = false
  }
}

async function scanAssignAsset() {
  if (assignDialog.scanning) return
  assignDialog.scanning = true
  try {
    let raw = assignDialog.scanInput.trim()
    if (!raw && props.scanCodeProvider) raw = await props.scanCodeProvider()
    if (!raw) {
      if (!props.scanCodeProvider) ElMessage.info('请扫码或输入资产编号')
      return
    }
    await addAssignAssetByCode(raw)
  } finally {
    assignDialog.scanning = false
  }
}

async function addAssignAssetByCode(raw) {
  const code = parseAssetCode(raw)
  if (!code) return ElMessage.warning('未读取到有效的资产编号或二维码内容')
  try {
    const found = await resolveAssignableAsset(raw)
    if (!found) return ElMessage.error(`未找到资产：${code}`)
    if (!['in_stock', 'idle'].includes(found.status)) {
      return ElMessage.warning(`${found.asset_no || found.asset_id} 当前状态不可分配`)
    }
    if (assignDialog.form.asset_ids.includes(found.asset_id)) {
      assignDialog.scanInput = ''
      return ElMessage.info(`${found.asset_no || found.asset_id} 已在待分配清单中`)
    }
    assignDialog.assets = mergeAssetOptions(assignDialog.assets, [found])
    assignDialog.form.asset_ids.push(found.asset_id)
    assignDialog.scanInput = ''
    ElMessage.success(`已添加 ${found.asset_no || found.asset_id}，可继续扫码`)
  } catch (error) {
    ElMessage.error(`资产识别失败：${error?.message || '请稍后重试'}`)
  }
}

async function resolveAssignableAsset(raw) {
  const binding = await resolveScanBinding(raw).catch(() => null)
  if (binding?.bound && binding.asset?.asset_id) {
    return getAssetById(binding.asset.asset_id).catch(() => binding.asset)
  }
  for (const candidate of assetCodeCandidates(raw)) {
    const { list } = await getAssets({ keyword: candidate, page: 1, page_size: 10 })
    const found = list.find(item => assetCodeMatches(item, candidate)) || list[0]
    if (found) return found
  }
  return null
}

function removeAssignAsset(assetId) {
  assignDialog.form.asset_ids = assignDialog.form.asset_ids.filter(id => id !== assetId)
}

function mergeAssetOptions(...groups) {
  const rows = groups.flat().filter(Boolean)
  return [...new Map(rows.map(item => [item.asset_id, item])).values()]
}

async function skipAssetAssignment() {
  const todo = assignDialog.todo
  const userId = todo?.user_id || todo?.username
  if (!userId) return ElMessage.warning('未找到对应用户')
  const confirmed = await ElMessageBox.confirm(
    `确认将 ${todo.name || todo.owner || userId} 标记为不需要分配公司资产？后续入职待办将不再提醒。`,
    '无需资产分配',
    { type: 'warning' }
  ).then(() => true).catch(() => false)
  if (!confirmed) return
  processing.value = true
  try {
    await updateUserAssetAssignment(userId, { asset_assignment_required: false })
    ElMessage.success('已标记为无需分配公司资产')
    assignDialog.visible = false
    emit('completed')
  } catch (error) {
    ElMessage.error(`操作失败：${error?.userMessage || error?.message || '请稍后重试'}`)
  } finally {
    processing.value = false
  }
}

async function openUserReclaimDialog(item) {
  reclaimDialog.user = item
  reclaimDialog.userName = item.name || item.owner || item.display_name || item.username || ''
  reclaimDialog.selected = []
  Object.assign(reclaimDialog.form, { location: '', remark: '离职资产回收入库' })
  processing.value = true
  try {
    const ownerUserId = item.user_id || item.username
    if (!ownerUserId) {
      ElMessage.warning('未找到离职人员标识，无法查询名下资产')
      return
    }
    const [list] = await Promise.all([
      loadReclaimAssets(item, ownerUserId),
      ensureOptions()
    ])
    reclaimDialog.assets = list.filter(asset => {
      if (!['in_use', 'borrowed', 'out_stock', 'repair'].includes(asset.status)) return false
      return true
    })
    if (!reclaimDialog.assets.length) {
      ElMessage.info('该人员当前没有需要回收的资产')
      return
    }
    reclaimDialog.visible = true
  } catch (error) {
    ElMessage.error(`资产加载失败：${error?.message || '请稍后重试'}`)
  } finally {
    processing.value = false
  }
}

async function loadReclaimAssets(item, ownerUserId) {
  const assetIds = [...new Set((item.asset_ids || []).filter(Boolean))]
  if (assetIds.length) {
    return Promise.all(assetIds.map(assetId => getAssetById(assetId)))
  }
  const { list } = await getAssets({ owner_user_id: ownerUserId, page: 1, page_size: 0 })
  return list
}

async function submitUserReclaim() {
  if (!reclaimDialog.selected.length) return ElMessage.warning('请选择要回收的资产')
  if (!reclaimDialog.form.location) return ElMessage.warning('请选择回收入库位置')
  processing.value = true
  try {
    for (const asset of reclaimDialog.selected) {
      await inboundAsset(asset.asset_id, reclaimDialog.form)
    }
    ElMessage.success(`已回收入库 ${reclaimDialog.selected.length} 个资产`)
    reclaimDialog.visible = false
    emit('completed')
  } catch (error) {
    ElMessage.error(`回收失败：${error?.message || '请稍后重试'}`)
  } finally {
    processing.value = false
  }
}

async function returnBorrowedAsset(item) {
  const confirmed = await ElMessageBox.confirm(`确认将 ${item.asset_id} 回收入库？`, '借用资产归还', { type: 'warning' }).then(() => true).catch(() => false)
  if (!confirmed) return
  processing.value = true
  try {
    await inboundAsset(item.asset_id, { location: '', remark: `借用到期归还${item.borrow_due_date ? `，到期时间：${item.borrow_due_date}` : ''}` })
    ElMessage.success('借用资产已回收入库')
    emit('completed')
  } catch (error) {
    ElMessage.error(`回收入库失败：${error?.message || '请稍后重试'}`)
  } finally {
    processing.value = false
  }
}

async function ensureUsers() {
  if (users.value.length) return
  users.value = await getUsers().catch(() => [])
}

async function ensureOptions() {
  const [userRows, locationRows] = await Promise.all([
    users.value.length ? Promise.resolve(users.value) : getUsers().catch(() => []),
    locations.value.length ? Promise.resolve(locations.value) : getLocations().catch(() => [])
  ])
  users.value = userRows
  locations.value = locationRows
}

function assetLabel(item) {
  return `${item.asset_no || item.asset_id} ${item.asset_no ? item.asset_id : ''} ${item.name || ''} ${item.sn || ''} ${item.location || ''}`.trim()
}

function locationLabel(item) {
  const meta = [item.code, item.type].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}

function statusLabel(status) {
  return {
    in_use: '在用',
    borrowed: '借出',
    out_stock: '已出库',
    repair: '维修中'
  }[status] || status || '-'
}

defineExpose({ handle })
</script>

<style scoped>
.todo-asset-form {
  margin-top: 14px;
}

.asset-option {
  display: grid;
  gap: 2px;
  min-width: 0;
  padding: 6px 0;
  line-height: 1.25;
}

.asset-option strong,
.asset-option span,
.asset-option small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-option strong {
  color: #0f172a;
  font-size: 13px;
}

.asset-option span {
  color: #334155;
  font-size: 13px;
}

.asset-option small {
  color: #64748b;
  font-size: 12px;
}

.reclaim-table {
  margin-top: 14px;
}

.assign-scan-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  width: 100%;
}

.selected-asset-list {
  display: grid;
  gap: 8px;
  width: 100%;
}

.selected-asset-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border: 1px solid #dbe7f5;
  border-radius: 6px;
  background: #f8fbff;
}

.selected-asset-row > div {
  display: grid;
  min-width: 0;
  line-height: 1.35;
}

.selected-asset-row strong,
.selected-asset-row span,
.selected-asset-row small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-asset-row small {
  color: #64748b;
}

:deep(.todo-asset-select-popper) {
  max-width: min(560px, calc(100vw - 48px));
}

:deep(.todo-asset-select-popper .el-select-dropdown__item) {
  height: auto;
  min-height: 58px;
  padding: 4px 12px;
}

:global(.todo-action-dialog--mobile) {
  width: min(360px, calc(100vw - 28px)) !important;
  max-width: calc(100vw - 28px);
  max-height: calc(100dvh - 28px);
  margin: 14px auto !important;
  display: flex;
  flex-direction: column;
}

:global(.todo-action-dialog--mobile .el-dialog__header) {
  flex: 0 0 auto;
  padding: 14px 16px;
}

:global(.todo-action-dialog--mobile .el-dialog__body) {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  padding: 14px 16px;
}

:global(.todo-action-dialog--mobile .el-dialog__footer) {
  flex: 0 0 auto;
  padding: 10px 16px 14px;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

:global(.todo-action-dialog--mobile .el-dialog__footer .el-button) {
  min-width: 0;
  margin-left: 0;
  padding-inline: 14px;
}

:global(.todo-action-dialog--mobile .todo-asset-select-popper),
:global(.todo-action-dialog--mobile .todo-location-select-popper) {
  max-width: calc(100vw - 56px);
}

:global(.todo-action-dialog--mobile .el-select-dropdown__wrap) {
  max-height: min(240px, 38dvh);
}

:global(.todo-action-dialog--mobile .reclaim-table) {
  width: 100%;
  overflow-x: auto;
}

@media (max-width: 720px) {
  :deep(.el-dialog__body) {
    max-height: calc(100vh - 170px);
    overflow-y: auto;
    padding: 14px;
  }

  :deep(.el-dialog__footer) {
    padding: 10px 14px 14px;
  }

  .todo-asset-form {
    margin-top: 12px;
  }

  .todo-asset-form :deep(.el-form-item) {
    display: block;
    margin-bottom: 14px;
  }

  .todo-asset-form :deep(.el-form-item__label) {
    justify-content: flex-start;
    width: auto !important;
    height: auto;
    margin-bottom: 6px;
    line-height: 1.4;
  }

  .todo-asset-form :deep(.el-form-item__content) {
    margin-left: 0 !important;
  }

  .assign-scan-row {
    grid-template-columns: minmax(0, 1fr) 112px;
  }
}
</style>
