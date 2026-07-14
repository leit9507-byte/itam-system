<template>
  <el-dialog v-model="assignDialog.visible" title="入职资产分配" width="620px" class="todo-action-dialog" append-to-body>
    <el-alert :title="`为 ${assignDialog.todo?.name || assignDialog.todo?.owner || '员工'} 分配在库或闲置资产`" type="info" show-icon :closable="false" />
    <el-form :model="assignDialog.form" label-width="100px" class="todo-asset-form">
      <el-form-item label="选择资产" required>
        <el-select
          v-model="assignDialog.form.asset_id"
          filterable
          remote
          reserve-keyword
          clearable
          placeholder="搜索资产编号、名称、序列号"
          :remote-method="searchAssignableAssets"
          :teleported="false"
          popper-class="todo-asset-select-popper"
          style="width: 100%"
        >
          <el-option v-for="item in assignDialog.assets" :key="item.asset_id" :label="assetLabel(item)" :value="item.asset_id">
            <div class="asset-option">
              <strong>{{ item.asset_id }}</strong>
              <span>{{ item.name || '-' }}</span>
              <small>{{ [item.brand, item.model, item.sn, item.location || '未填写位置'].filter(Boolean).join(' / ') }}</small>
            </div>
          </el-option>
        </el-select>
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
      <el-button type="primary" :loading="processing" @click="submitAssign">确认分配</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="reclaimDialog.visible" title="离职资产回收" width="760px" class="todo-action-dialog" append-to-body>
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
    <template #footer>
      <el-button @click="reclaimDialog.visible = false">取消</el-button>
      <el-button type="primary" :disabled="!reclaimDialog.selected.length" :loading="processing" @click="submitUserReclaim">确认回收 {{ reclaimDialog.selected.length }} 个资产</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAssets, inboundAsset, outboundAsset, submitReclaimApproval } from '../api/asset'
import { getLocations } from '../api/location'
import { getUsers } from '../api/user'

const emit = defineEmits(['completed'])
const processing = ref(false)
const users = ref([])
const locations = ref([])
const assignDialog = reactive({
  visible: false,
  todo: null,
  assets: [],
  form: { asset_id: '', location: '', remark: '入职资产分配' }
})
const reclaimDialog = reactive({
  visible: false,
  user: null,
  userName: '',
  assets: [],
  selected: []
})

const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))

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
  Object.assign(assignDialog.form, { asset_id: '', location: '', remark: '入职资产分配' })
  await ensureOptions()
  assignDialog.assets = await loadAssignableAssets('')
  assignDialog.visible = true
}

async function searchAssignableAssets(keyword = '') {
  assignDialog.assets = await loadAssignableAssets(keyword)
}

async function loadAssignableAssets(keyword = '') {
  const { list } = await getAssets({ keyword, page: 1, page_size: 50 })
  return list.filter(item => ['in_stock', 'idle'].includes(item.status))
}

async function submitAssign() {
  if (!assignDialog.form.asset_id) return ElMessage.warning('请选择要分配的资产')
  const todo = assignDialog.todo
  processing.value = true
  try {
    await ensureUsers()
    const user = users.value.find(item => item.user_id === todo.user_id || item.username === todo.username)
    await outboundAsset(assignDialog.form.asset_id, {
      outboundTarget: 'user',
      toStatus: 'in_use',
      owner_user_id: user?.user_id || todo.user_id || todo.username,
      owner_name: user?.display_name || todo.name || todo.owner,
      dept_id: user?.dept_id || user?.dept_name || '',
      dept_name: user?.dept_name || user?.dept_id || '',
      location: assignDialog.form.location,
      remark: assignDialog.form.remark || '入职资产分配'
    })
    ElMessage.success('入职资产已分配')
    assignDialog.visible = false
    emit('completed')
  } catch (error) {
    ElMessage.error(`分配失败：${error?.message || '请稍后重试'}`)
  } finally {
    processing.value = false
  }
}

async function openUserReclaimDialog(item) {
  reclaimDialog.user = item
  reclaimDialog.userName = item.name || item.owner || item.display_name || item.username || ''
  reclaimDialog.selected = []
  processing.value = true
  try {
    const { list } = await getAssets({ page: 1, page_size: 500 })
    reclaimDialog.assets = list.filter(asset => {
      if (!['in_use', 'borrowed', 'out_stock', 'repair'].includes(asset.status)) return false
      if (item.asset_ids?.length) return item.asset_ids.includes(asset.asset_id)
      const ownerValues = [asset.owner_user_id, asset.owner, asset.owner_username]
      return ownerValues.includes(item.user_id) || ownerValues.includes(item.username)
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

async function submitUserReclaim() {
  if (!reclaimDialog.selected.length) return ElMessage.warning('请选择要回收的资产')
  processing.value = true
  try {
    for (const asset of reclaimDialog.selected) {
      await submitReclaimApproval(asset.asset_id, { location: '', remark: '离职资产回收审批' })
    }
    ElMessage.success(`已提交 ${reclaimDialog.selected.length} 个资产的飞书回收审批`)
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
  return `${item.asset_id} ${item.name || ''} ${item.sn || ''} ${item.location || ''}`.trim()
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

:deep(.todo-asset-select-popper) {
  max-width: min(560px, calc(100vw - 48px));
}

:deep(.todo-asset-select-popper .el-select-dropdown__item) {
  height: auto;
  min-height: 58px;
  padding: 4px 12px;
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
}
</style>
