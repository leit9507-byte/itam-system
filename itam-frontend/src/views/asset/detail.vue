<template>
  <div class="page asset-detail-page">
    <div class="page-header asset-detail-header">
      <div>
        <h2 class="page-title">资产详情</h2>
        <p class="page-subtitle">{{ detail.asset?.asset_id }} / {{ detail.asset?.name }}</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="openEdit">编辑资产</el-button>
        <el-button @click="$router.back()">返回</el-button>
      </div>
    </div>

    <div class="detail-grid">
      <main class="detail-main">
        <el-card shadow="never" class="risk-card">
          <template #header>
            <div class="card-header">
              <span>风险提示</span>
              <el-tag :type="riskSummary.type">{{ riskSummary.text }}</el-tag>
            </div>
          </template>
          <div class="risk-list">
            <el-alert
              v-for="risk in detail.risks"
              :key="risk.message"
              :type="risk.level === 'high' ? 'error' : risk.level === 'medium' ? 'warning' : 'success'"
              :title="risk.message"
              :description="risk.detail"
              show-icon
              :closable="false"
            />
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>基本信息</template>
          <div class="basic-info-layout">
            <el-descriptions class="basic-info-table" :column="2" border>
              <el-descriptions-item label="ID">{{ detail.asset?.display_id || '-' }}</el-descriptions-item>
              <el-descriptions-item label="资产编码">{{ detail.asset?.asset_id || '-' }}</el-descriptions-item>
              <el-descriptions-item label="所属公司">{{ detail.asset?.company || '-' }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <div class="status-tags">
                  <el-tag :type="statusMap[detail.asset?.status]?.type">{{ statusMap[detail.asset?.status]?.label || detail.asset?.status }}</el-tag>
                  <el-tag v-if="detail.scrapInfo" :type="scrapDisposalTag.type" effect="plain">{{ scrapDisposalTag.text }}</el-tag>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="产品名称">{{ detail.asset?.name }}</el-descriptions-item>
              <el-descriptions-item label="设备类型">{{ detail.asset?.category }}</el-descriptions-item>
              <el-descriptions-item label="品牌">{{ detail.asset?.brand || '-' }}</el-descriptions-item>
              <el-descriptions-item label="型号">{{ detail.asset?.model || '-' }}</el-descriptions-item>
              <el-descriptions-item label="规格">{{ detail.asset?.spec || '-' }}</el-descriptions-item>
              <el-descriptions-item label="序列号">{{ detail.asset?.sn || '-' }}</el-descriptions-item>
              <el-descriptions-item label="责任人">{{ ownerName }}</el-descriptions-item>
              <el-descriptions-item label="部门">{{ deptName }}</el-descriptions-item>
              <el-descriptions-item label="位置">{{ detail.asset?.location || '-' }}</el-descriptions-item>
              <el-descriptions-item label="价值">¥{{ Number(detail.asset?.price || 0).toLocaleString() }}</el-descriptions-item>
              <el-descriptions-item label="当前残值">¥{{ Number(detail.asset?.current_residual_value || 0).toLocaleString() }}</el-descriptions-item>
              <el-descriptions-item label="备注" :span="2">{{ detail.asset?.remark || '-' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>采购与质保</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="采购时间">{{ detail.asset?.purchase_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="采购审批单号">{{ detail.asset?.purchase_approval_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="采购单号">{{ detail.asset?.config?.purchase_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="采购供应商">{{ detail.asset?.purchase_supplier_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="付款时间">{{ detail.asset?.payment_time || '-' }}</el-descriptions-item>
            <el-descriptions-item label="付款单号">{{ detail.asset?.payment_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="质保到期">{{ detail.asset?.warranty_expire_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="质保月数">{{ detail.asset?.warranty_months || '-' }}</el-descriptions-item>
            <el-descriptions-item label="退役年限">{{ detail.asset?.retirement_years ? `${detail.asset.retirement_years} 年` : '-' }}</el-descriptions-item>
            <el-descriptions-item label="预计退役时间">{{ detail.asset?.retirement_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="质保状态">
              <el-tag :type="warrantyTag.type">{{ warrantyTag.text }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card v-if="detail.scrapInfo" shadow="never" class="scrap-info-card">
          <template #header>
            <div class="card-header">
              <span>报废处置信息</span>
              <el-tag :type="scrapDisposalTag.type">{{ scrapDisposalTag.text }}</el-tag>
            </div>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="报废单号">{{ detail.scrapInfo.request_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="报废单状态">{{ detail.scrapInfo.status || '-' }}</el-descriptions-item>
            <el-descriptions-item label="报废原因" :span="2">{{ detail.scrapInfo.reason || '-' }}</el-descriptions-item>
            <el-descriptions-item label="退役时间">{{ detail.scrapInfo.retirement_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="退役审批单号">{{ detail.scrapInfo.retirement_approval_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="处置方式">{{ detail.scrapInfo.disposal_method || (detail.scrapInfo.disposal_status === '未处置' ? '未处置' : '-') }}</el-descriptions-item>
            <el-descriptions-item label="报废领走人">{{ detail.scrapInfo.dispose_recipient_name || detail.scrapInfo.dispose_recipient_user_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="预计残值">¥{{ Number(detail.scrapInfo.estimated_residual_value || 0).toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="实际残值">¥{{ Number(detail.scrapInfo.final_residual_value || 0).toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="处置人">{{ detail.scrapInfo.disposed_by || '-' }}</el-descriptions-item>
            <el-descriptions-item label="处置时间">{{ detail.scrapInfo.disposed_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="处置说明" :span="2">{{ detail.scrapInfo.disposal_remark || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>附件</span>
              <el-upload :show-file-list="false" :before-upload="handleUpload">
                <el-button type="primary" size="small">上传附件</el-button>
              </el-upload>
            </div>
          </template>
          <el-table :data="pagedAttachments" border empty-text="暂无附件">
            <el-table-column prop="filename" label="文件名" min-width="160" show-overflow-tooltip />
            <el-table-column prop="size" label="大小" width="100">
              <template #default="{ row }">{{ formatSize(row.size) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'archived' ? 'warning' : 'success'">{{ row.status === 'archived' ? '已归档' : '有效' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" width="170" />
            <el-table-column label="操作" width="210">
              <template #default="{ row }">
                <el-button link type="primary" @click="downloadFile(row)">下载</el-button>
                <el-button v-if="row.status !== 'archived'" link type="warning" @click="archiveFile(row)">归档</el-button>
                <el-button v-else link type="success" @click="restoreFile(row)">恢复</el-button>
                <el-button link type="danger" @click="removeFile(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="attachmentPagination.page"
              v-model:page-size="attachmentPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="attachmentPagination.total"
              layout="total, sizes, prev, pager, next"
              @current-change="loadAttachments"
              @size-change="handleAttachmentSizeChange"
            />
          </div>
        </el-card>
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>二维码绑定</span>
              <el-tag type="info">二维码识别</el-tag>
            </div>
          </template>
          <div class="scan-binding-panel">
            <el-alert class="scan-binding-tip" title="填写扫码实际返回的文字，一行一个；后续扫码返回内容与这里任一内容一致时，都会识别为当前资产。" type="info" show-icon :closable="false" />
            <el-form :model="scanForm" label-width="92px" class="scan-binding-form">
              <el-form-item label="二维码内容">
                <el-input v-model="scanForm.scan_raw" type="textarea" :rows="4" placeholder="粘贴或输入扫码出来的原始文字；支持多行，每行绑定一个二维码内容" />
              </el-form-item>
              <el-row :gutter="12">
                <el-col :xs="24" :sm="8">
                  <el-form-item label="识别类型">
                    <el-input model-value="二维码" disabled />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="10">
                  <el-form-item label="备注">
                    <el-input v-model="scanForm.remark" clearable placeholder="例如二维码版本、标签批次、打印说明" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="6">
                  <el-form-item label="重新绑定">
                    <el-switch v-model="scanForm.force" />
                  </el-form-item>
                </el-col>
              </el-row>
              <div class="scan-binding-actions">
                <el-button type="primary" :loading="scanBindingSaving" @click="submitScanBinding">绑定二维码内容</el-button>
              </div>
            </el-form>

            <el-table :data="scanBindings" border empty-text="暂无二维码绑定">
              <el-table-column prop="scan_raw" label="二维码内容" min-width="220" show-overflow-tooltip />
              <el-table-column prop="scan_type" label="类型" width="100">
                <template #default="{ row }">{{ scanTypeLabel(row.scan_type) }}</template>
              </el-table-column>
              <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
              <el-table-column prop="updated_at" label="更新时间" width="170" />
              <el-table-column label="操作" width="90">
                <template #default="{ row }">
                  <el-button link type="danger" @click="removeScanBinding(row)">解绑</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </main>

      <aside class="timeline-side">
        <el-card shadow="never" class="timeline-card">
          <template #header>
            <div class="history-header">
              <div>
                <span>完整历史时间线</span>
                <small>{{ filteredTimeline.length }} 条记录</small>
              </div>
              <el-segmented v-model="historyFilter" :options="historyFilterOptions" />
            </div>
          </template>
          <Timeline :items="pagedTimeline" />
          <div class="pagination-bar timeline-pagination">
            <el-pagination
              v-model:current-page="timelinePagination.page"
              v-model:page-size="timelinePagination.pageSize"
              :page-sizes="[10, 20, 50]"
              :total="filteredTimeline.length"
              layout="total, sizes, prev, pager, next"
              small
              @size-change="handleTimelineSizeChange"
            />
          </div>
        </el-card>
      </aside>
    </div>

    <el-dialog v-model="editDialog.visible" title="编辑资产信息" width="980px">
      <el-form :model="editDialog.form" label-width="112px" class="asset-edit-form">
        <el-row :gutter="14">
          <el-col :xs="24" :sm="12"><el-form-item label="资产编码"><el-input v-model="editDialog.form.asset_id" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="产品档案">
              <el-select v-model="editDialog.form.product_id" filterable clearable placeholder="选择产品后自动带出规格" style="width: 100%" @change="applyProductToEdit">
                <el-option v-for="item in products" :key="item.id" :label="`${item.product_name} / ${item.model || '-'} / ${item.spec || '-'}`" :value="item.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="产品名称"><el-input v-model="editDialog.form.name" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="设备类型">
              <el-select v-model="editDialog.form.category" filterable allow-create default-first-option style="width: 100%">
                <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="品牌"><el-input v-model="editDialog.form.brand" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="型号"><el-input v-model="editDialog.form.model" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="规格"><el-input v-model="editDialog.form.spec" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="序列号"><el-input v-model="editDialog.form.sn" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="所属公司">
              <el-select v-model="editDialog.form.company" filterable clearable style="width: 100%">
                <el-option v-for="item in realCompanies" :key="item.id || item.name" :label="item.name" :value="item.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="状态">
              <el-select v-model="editDialog.form.status" style="width: 100%">
                <el-option v-for="item in editableAssetStatuses" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="采购金额"><el-input-number v-model="editDialog.form.price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="采购时间"><el-date-picker v-model="editDialog.form.purchase_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="审批单号"><el-input v-model="editDialog.form.purchase_approval_no" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="供应商">
              <el-select v-model="editDialog.form.purchase_supplier_name" filterable clearable allow-create default-first-option style="width: 100%">
                <el-option v-for="item in suppliers" :key="item.id || item.name" :label="supplierLabel(item)" :value="item.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="维保年限"><el-input-number v-model="editDialog.form.warranty_years" :min="0" :step="1" :precision="0" style="width: 100%" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="维保到期"><el-input :model-value="warrantyExpirePreview(editDialog.form)" disabled /></el-form-item></el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="退役年限"><el-input-number v-model="editDialog.form.retirement_years" :min="0" :step="1" :precision="0" style="width: 100%" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="预计退役"><el-input :model-value="retirementDatePreview(editDialog.form)" disabled /></el-form-item></el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="责任人">
              <el-select v-model="editDialog.form.owner_user_id" filterable remote clearable reserve-keyword :remote-method="searchUsers" style="width: 100%" @visible-change="visible => visible && searchUsers('')" @change="fillUserToForm">
                <el-option v-for="user in filteredUsers" :key="user.user_id" :label="userLabel(user)" :value="user.user_id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="部门"><el-input v-model="editDialog.form.dept_id" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="位置">
              <el-select v-model="editDialog.form.location" filterable clearable style="width: 100%">
                <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24"><el-form-item label="备注"><el-input v-model="editDialog.form.remark" type="textarea" :rows="3" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="editDialog.saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import Timeline from '../../components/Timeline.vue'
import { editableAssetStatuses, getAssetDetail, statusMap, updateAsset } from '../../api/asset'
import { archiveAssetFile, deleteAssetFile, downloadAssetFile, listAssetFiles, restoreAssetFile, uploadAssetFile } from '../../api/file'
import { bindAssetScanCode, deleteAssetScanBinding, getAssetScanBindings } from '../../api/scanBinding'
import { getCompanies } from '../../api/company'
import { getDeviceTypes, getProducts } from '../../api/product'
import { getLocations } from '../../api/location'
import { getSuppliers } from '../../api/supplier'
import { getUsers } from '../../api/user'

const route = useRoute()
const router = useRouter()
const detail = reactive({ asset: null, scrapInfo: null, scrapRequests: [], lifecycles: [], changes: [], checkouts: [], timeline: [], usageRecords: [], inventoryRecords: [], risks: [] })
const attachments = ref([])
const categories = ref([])
const products = ref([])
const companies = ref([])
const suppliers = ref([])
const locations = ref([])
const users = ref([])
const filteredUsers = ref([])
const editDialog = reactive({ visible: false, saving: false, form: {} })
const scanBindings = ref([])
const scanBindingSaving = ref(false)
const scanForm = reactive({ scan_raw: '', scan_type: 'qrcode', remark: '', force: false })
const historyFilter = ref('all')
const historyFilterOptions = [
  { label: '全部', value: 'all' },
  { label: '领用归还', value: 'checkout' },
  { label: '字段变更', value: 'change' },
  { label: '维修报废', value: 'repair_scrap' },
  { label: '出入库', value: 'inventory' }
]
const attachmentPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const timelinePagination = reactive({ page: 1, pageSize: 10 })

const ownerName = computed(() => detail.asset?.owner_name || detail.asset?.owner_username || detail.asset?.owner || '未分配')
const deptName = computed(() => detail.asset?.dept_name || detail.asset?.dept || '未绑定')
const filteredTimeline = computed(() => {
  if (historyFilter.value === 'all') return detail.timeline
  if (historyFilter.value === 'repair_scrap') return detail.timeline.filter(item => ['repair', 'scrap'].includes(item.group))
  return detail.timeline.filter(item => item.group === historyFilter.value)
})
const pagedTimeline = computed(() => {
  const start = (timelinePagination.page - 1) * timelinePagination.pageSize
  return filteredTimeline.value.slice(start, start + timelinePagination.pageSize)
})
const pagedAttachments = computed(() => attachments.value)
const realCompanies = computed(() => companies.value.filter(item => !item.virtual))
const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用' && item.status !== '禁用'))
const riskSummary = computed(() => {
  if (detail.risks.some(item => item.level === 'high')) return { type: 'danger', text: '高风险' }
  if (detail.risks.some(item => item.level === 'medium')) return { type: 'warning', text: '需关注' }
  return { type: 'success', text: '正常' }
})

const warrantyTag = computed(() => {
  const value = detail.asset?.warranty_expire_date
  if (!value) return { type: 'info', text: '未设置' }
  return new Date(value) >= new Date() ? { type: 'success', text: '在保' } : { type: 'danger', text: '已过保' }
})

const scrapDisposalTag = computed(() => {
  if (!detail.scrapInfo) return { type: 'info', text: '' }
  return detail.scrapInfo.disposal_status === '已处置'
    ? { type: 'success', text: `已处置${detail.scrapInfo.disposal_method ? ` / ${detail.scrapInfo.disposal_method}` : ''}` }
    : { type: 'warning', text: '未处置' }
})

watch(historyFilter, () => {
  timelinePagination.page = 1
})

onMounted(async () => {
  await Promise.all([loadReferenceData(), loadDetail(route.params.id), loadAttachments(route.params.id), loadScanBindings(route.params.id)])
})

async function loadDetail(assetId = route.params.id) {
  Object.assign(detail, await getAssetDetail(assetId))
}

async function loadReferenceData() {
  const [typeRows, productRows, companyRows, supplierRows, locationRows, userRows] = await Promise.all([
    getDeviceTypes().catch(() => []),
    getProducts().catch(() => []),
    getCompanies().catch(() => []),
    getSuppliers().catch(() => []),
    getLocations().catch(() => []),
    getUsers().catch(() => [])
  ])
  categories.value = typeRows.map(item => item.name)
  products.value = productRows
  companies.value = companyRows
  suppliers.value = supplierRows
  locations.value = locationRows
  users.value = userRows
  filteredUsers.value = userRows.slice(0, 30)
}

async function loadAttachments(assetId = route.params.id) {
  if (!assetId) return
  const result = await listAssetFiles(assetId, { page: attachmentPagination.page, page_size: attachmentPagination.pageSize })
  attachments.value = result.list || result
  attachmentPagination.total = result.total ?? attachments.value.length
}

async function loadScanBindings(assetId = route.params.id) {
  if (!assetId) return
  scanBindings.value = await getAssetScanBindings(assetId).catch(() => [])
}

async function submitScanBinding() {
  if (!detail.asset?.asset_id) return
  const scanRaws = parseScanRawLines(scanForm.scan_raw)
  if (!scanRaws.length) return ElMessage.warning('请先填写二维码内容')
  scanBindingSaving.value = true
  try {
    for (const scanRaw of scanRaws) {
      await bindAssetScanCode(detail.asset.asset_id, { ...scanForm, scan_raw: scanRaw, scan_type: 'qrcode' })
    }
    Object.assign(scanForm, { scan_raw: '', scan_type: 'qrcode', remark: '', force: false })
    ElMessage.success(scanRaws.length > 1 ? `已绑定 ${scanRaws.length} 个二维码内容` : '二维码内容已绑定')
    await loadScanBindings(detail.asset.asset_id)
  } finally {
    scanBindingSaving.value = false
  }
}

function parseScanRawLines(value) {
  return [...new Set((value || '').split(/\r?\n/).map(item => item.trim()).filter(Boolean))]
}

async function removeScanBinding(row) {
  await ElMessageBox.confirm(`确认解绑该二维码内容？解绑后现场扫码将不再直接关联 ${row.asset_id}。`, '解绑二维码', { type: 'warning' })
  await deleteAssetScanBinding(row.id)
  ElMessage.success('二维码绑定已解绑')
  await loadScanBindings(detail.asset?.asset_id)
}

function scanTypeLabel(value) {
  return ({ generic: '通用', qrcode: '二维码', barcode: '条码', legacy: '旧标签' })[value] || value || '-'
}

function handleAttachmentSizeChange() {
  attachmentPagination.page = 1
  loadAttachments()
}

function handleTimelineSizeChange() {
  timelinePagination.page = 1
}

function openEdit() {
  if (!detail.asset) return
  editDialog.form = {
    ...detail.asset,
    product_id: resolveProductId(detail.asset),
    original_asset_id: detail.asset.asset_id,
    owner_user_id: detail.asset.owner_user_id || detail.asset.owner || '',
    dept_id: detail.asset.dept_id || detail.asset.dept || ''
  }
  searchUsers('')
  editDialog.visible = true
}

function resolveProductId(asset) {
  const product = products.value.find(item =>
    item.product_name === asset.name &&
    item.device_type === asset.category &&
    (item.brand || '') === (asset.brand || '') &&
    (item.model || '') === (asset.model || '')
  )
  return product?.id || null
}

function applyProductToEdit(productId) {
  const product = products.value.find(item => item.id === productId)
  if (!product) return
  Object.assign(editDialog.form, {
    product_id: product.id,
    name: product.product_name || editDialog.form.name,
    category: product.device_type || editDialog.form.category,
    brand: product.brand || '',
    model: product.model || '',
    spec: product.spec || '',
    price: Number(product.unit_price || editDialog.form.price || 0),
    location: product.default_warehouse || editDialog.form.location || '',
    retirement_years: product.retirement_years ?? editDialog.form.retirement_years
  })
}

async function submitEdit() {
  const oldAssetId = editDialog.form.original_asset_id || detail.asset?.asset_id
  const newAssetId = String(editDialog.form.asset_id || '').trim()
  if (!newAssetId) return ElMessage.warning('资产编码不能为空')
  editDialog.form.asset_no = editDialog.form.asset_no || newAssetId
  if (['in_use', 'borrowed'].includes(editDialog.form.status) && !editDialog.form.owner_user_id) return ElMessage.warning('在用或借出资产必须选择责任人')
  if (['in_stock', 'idle', 'ready_scrap'].includes(editDialog.form.status) && editDialog.form.owner_user_id) return ElMessage.warning('在库、闲置、待报废资产不能绑定责任人')
  editDialog.saving = true
  try {
    await updateAsset(oldAssetId, { ...editDialog.form, asset_id: newAssetId })
    editDialog.visible = false
    ElMessage.success('资产信息已更新')
    if (newAssetId !== oldAssetId) await router.replace(`/asset/detail/${newAssetId}`)
    await loadDetail(newAssetId)
    attachmentPagination.page = 1
    await loadAttachments(newAssetId)
    await loadScanBindings(newAssetId)
  } finally {
    editDialog.saving = false
  }
}

function searchUsers(query = '') {
  const keyword = query.trim().toLowerCase()
  filteredUsers.value = users.value
    .filter(user => !keyword || [user.user_id, user.username, user.display_name, user.dept_name, user.dept_id].join(' ').toLowerCase().includes(keyword))
    .slice(0, 30)
}

function fillUserToForm(userId) {
  const user = users.value.find(item => item.user_id === userId)
  editDialog.form.dept_id = user?.dept_id || user?.dept_name || editDialog.form.dept_id || ''
}

function userLabel(user) {
  return `${user.display_name || user.username} (${user.username || user.user_id}) / ${user.dept_name || user.dept_id || '未分部门'}`
}

function supplierLabel(item) {
  return [item.name, item.supplier_no].filter(Boolean).join(' / ')
}

function locationLabel(item) {
  const meta = [item.code, item.type].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}

function warrantyExpirePreview(form) {
  if (!form?.purchase_date || !form?.warranty_years) return form?.warranty_expire_date || ''
  return addYears(form.purchase_date, Number(form.warranty_years))
}

function retirementDatePreview(form) {
  if (!form?.purchase_date || !form?.retirement_years) return form?.retirement_date || ''
  return addYears(form.purchase_date, Number(form.retirement_years))
}

function addYears(value, years) {
  if (!value || !years) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  date.setFullYear(date.getFullYear() + Number(years))
  return date.toISOString().slice(0, 10)
}

async function handleUpload(file) {
  await uploadAssetFile(route.params.id, file)
  ElMessage.success('附件已上传')
  await loadAttachments()
  return false
}

function downloadFile(row) {
  downloadAssetFile(row)
}

async function archiveFile(row) {
  await archiveAssetFile(row.id)
  ElMessage.success('附件已归档')
  await loadAttachments()
}

async function restoreFile(row) {
  await restoreAssetFile(row.id)
  ElMessage.success('附件已恢复')
  await loadAttachments()
}

async function removeFile(row) {
  await ElMessageBox.confirm(`确认删除附件 ${row.filename}？文件会标记为删除并保留审计追踪。`, '删除附件', { type: 'warning' })
  await deleteAssetFile(row.id)
  ElMessage.success('附件已删除')
  await loadAttachments()
}

function formatSize(size = 0) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.asset-detail-page {
  min-width: 0;
}

.asset-detail-header {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto;
  align-items: start;
  gap: 16px;
}

.risk-list {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.risk-card :deep(.el-alert__description) {
  margin-top: 4px;
  line-height: 1.55;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.asset-edit-form {
  max-height: 66vh;
  overflow: auto;
  padding-right: 6px;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(420px, 0.52fr);
  align-items: start;
  gap: 16px;
}

.detail-main,
.timeline-side {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.timeline-card {
  position: sticky;
  top: 16px;
}

.card-header,
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-header {
  flex-wrap: wrap;
}

.history-header > div {
  display: grid;
  gap: 3px;
}

.history-header small {
  color: var(--muted);
  font-size: 12px;
}

.basic-info-layout {
  display: block;
}

.basic-info-table {
  min-width: 0;
}

.status-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.scan-binding-panel {
  display: grid;
  gap: 14px;
}

.scan-binding-tip {
  margin-bottom: 2px;
}

.scan-binding-form {
  padding: 2px 0 4px;
}

.scan-binding-actions {
  display: flex;
  justify-content: flex-end;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
  overflow-x: auto;
}

.timeline-pagination {
  justify-content: center;
}

@media (max-width: 1280px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .timeline-card {
    position: static;
  }
}

@media (max-width: 760px) {
  .asset-detail-header {
    grid-template-columns: 1fr;
  }

  .card-header,
  .history-header,
  .header-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
