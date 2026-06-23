<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产管理</h2>
        <p class="page-subtitle">支持批量导入、入库、出库、资产资料调整和报废审批</p>
      </div>
      <el-button type="primary" @click="importDialog.visible = true">批量导入资产</el-button>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="filters.keyword" clearable placeholder="搜索资产ID/名称/部门/序列号" style="width: 300px" @input="loadAssets" />
        <el-select v-model="filters.status" clearable placeholder="状态" style="width: 160px" @change="loadAssets">
          <el-option v-for="item in assetStatuses" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.category" clearable placeholder="设备类型" style="width: 160px" @change="loadAssets">
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
        <el-table-column prop="asset_id" label="资产ID" width="130" />
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
        <el-table-column prop="owner" label="使用人" width="120">
          <template #default="{ row }">{{ row.owner || '未分配' }}</template>
        </el-table-column>
        <el-table-column prop="dept" label="部门" width="120">
          <template #default="{ row }">{{ row.dept || '未绑定' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type || 'info'">{{ statusMap[row.status]?.label || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价值" width="120">
          <template #default="{ row }">¥{{ Number(row.price || 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goDetail(row)">详情</el-button>
            <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
            <el-button type="warning" link :disabled="['scrapped', 'pending_scrap'].includes(row.status)" @click="openSingleOutbound(row)">出库</el-button>
            <el-button type="danger" link :disabled="['scrapped', 'pending_scrap'].includes(row.status)" @click="openSingleScrap(row)">报废</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="editDialog.visible" title="调整资产信息" width="760px">
      <el-form :model="editDialog.form" label-width="100px">
        <div class="edit-grid">
          <el-form-item label="资产名称"><el-input v-model="editDialog.form.name" /></el-form-item>
          <el-form-item label="序列号"><el-input v-model="editDialog.form.sn" /></el-form-item>
          <el-form-item label="设备类型">
            <el-select v-model="editDialog.form.category" filterable allow-create style="width: 100%">
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
          <el-form-item label="使用人"><el-input v-model="editDialog.form.owner" /></el-form-item>
          <el-form-item label="部门"><el-input v-model="editDialog.form.dept" /></el-form-item>
          <el-form-item label="位置"><el-input v-model="editDialog.form.location" /></el-form-item>
          <el-form-item label="仓库"><el-input v-model="editDialog.form.warehouse" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存调整</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialog.visible" title="批量导入资产" width="820px">
      <el-alert title="支持从 Excel 复制后直接粘贴，第一行必须是表头。推荐字段：name、category、brand、model、sn、price、owner、dept、warehouse、status。" type="info" show-icon :closable="false" />
      <el-input v-model="importDialog.content" type="textarea" :rows="10" class="import-textarea" />
      <div class="import-actions">
        <el-button @click="fillImportExample">填入示例</el-button>
        <el-button type="primary" :loading="importDialog.loading" @click="submitImport">开始导入</el-button>
      </div>
      <el-table v-if="importDialog.result" :data="importDialog.result.errors" border size="small" class="import-result">
        <el-table-column prop="row" label="行号" width="80" />
        <el-table-column prop="message" label="提示" />
      </el-table>
      <el-result v-if="importDialog.result && !importDialog.result.errors.length" icon="success" :title="`已导入 ${importDialog.result.created} 条资产`" sub-title="资产已写入后端，并生成批量导入生命周期记录" />
    </el-dialog>

    <el-dialog v-model="batch.visible" :title="batchTitle" width="620px">
      <el-alert :title="`本次将处理 ${batch.assets.length} 个资产`" type="info" show-icon :closable="false" />
      <el-form :model="batch.form" label-width="110px" class="batch-form">
        <template v-if="batch.type === 'inbound'">
          <el-form-item label="入库仓库"><el-input v-model="batch.form.warehouse" /></el-form-item>
        </template>
        <template v-if="batch.type === 'outbound'">
          <el-form-item label="出库类型">
            <el-select v-model="batch.form.toStatus" style="width: 100%">
              <el-option label="领用在用" value="in_use" />
              <el-option label="借出" value="borrowed" />
              <el-option label="已出库" value="out_stock" />
            </el-select>
          </el-form-item>
          <el-form-item label="领用人"><el-input v-model="batch.form.owner" /></el-form-item>
          <el-form-item label="部门"><el-input v-model="batch.form.dept" /></el-form-item>
          <el-form-item label="位置"><el-input v-model="batch.form.location" /></el-form-item>
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
        <el-form-item v-if="batch.type !== 'scrap'" label="备注"><el-input v-model="batch.form.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batch.visible = false">取消</el-button>
        <el-button type="primary" @click="submitBatch">确认执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assetStatuses, createScrapRequest, getAssets, importAssetsFromText, inboundAsset, outboundAsset, statusMap, updateAsset } from '../../api/asset'
import { getDeviceTypes } from '../../api/product'

const router = useRouter()
const assets = ref([])
const selected = ref([])
const categories = ref([])
const filters = reactive({ keyword: '', status: '', category: '' })
const batch = reactive({ visible: false, type: 'inbound', assets: [], form: defaultBatchForm() })
const importDialog = reactive({ visible: false, loading: false, content: '', result: null })
const editDialog = reactive({ visible: false, form: {} })

const batchTitle = computed(() => ({ inbound: '批量入库', outbound: '批量出库', scrap: '批量申请报废' }[batch.type]))

onMounted(async () => {
  await loadAssets()
  const types = await getDeviceTypes()
  categories.value = types.map(item => item.name)
})

async function loadAssets() {
  const data = await getAssets(filters)
  assets.value = data.list
}

function defaultBatchForm() {
  return { warehouse: '', toStatus: 'in_use', owner: '', dept: '', location: '', applicant: '', reason: '', disposal_method: '环保回收', estimated_residual_value: 0, remark: '' }
}

function goDetail(row) {
  router.push(`/asset/detail/${row.asset_id}`)
}

function openEdit(row) {
  editDialog.form = { ...row }
  editDialog.visible = true
}

async function submitEdit() {
  await updateAsset(editDialog.form.asset_id, editDialog.form)
  editDialog.visible = false
  ElMessage.success('资产信息已更新')
  await loadAssets()
}

function openBatch(type) {
  batch.type = type
  batch.assets = selected.value
  Object.assign(batch.form, defaultBatchForm())
  batch.visible = true
}

function openSingleOutbound(row) {
  selected.value = [row]
  openBatch('outbound')
}

function openSingleScrap(row) {
  selected.value = [row]
  openBatch('scrap')
}

function fillImportExample() {
  importDialog.content = [
    'name,category,brand,model,sn,price,owner,dept,warehouse,status',
    'ThinkPad X1 Carbon,Laptop,Lenovo,X1 Carbon Gen 12,SN-IMPORT-001,15000,zhang.wei,RD,上海IT库,in_stock',
    'Dell U2723QE,Monitor,Dell,U2723QE,SN-IMPORT-002,3999,li.na,FIN,上海IT库,in_stock'
  ].join('\n')
}

async function submitImport() {
  if (!importDialog.content.trim()) {
    ElMessage.warning('请先粘贴导入内容')
    return
  }
  importDialog.loading = true
  try {
    importDialog.result = await importAssetsFromText(importDialog.content, 'frontend-import')
    ElMessage.success(`导入完成：新增 ${importDialog.result.created} 条，跳过 ${importDialog.result.skipped} 条`)
    await loadAssets()
  } finally {
    importDialog.loading = false
  }
}

async function submitBatch() {
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
.import-result {
  margin-top: 16px;
}

.import-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
}
</style>
