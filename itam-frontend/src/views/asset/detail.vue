<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产详情</h2>
        <p class="page-subtitle">{{ detail.asset?.asset_id }} / {{ detail.asset?.name }}</p>
      </div>
      <el-button @click="$router.back()">返回</el-button>
    </div>

    <div class="detail-grid">
      <div class="page">
        <el-card shadow="never">
          <template #header>基本信息</template>
          <div class="basic-info-layout">
            <el-descriptions class="basic-info-table" :column="2" border>
              <el-descriptions-item label="资产ID">{{ detail.asset?.asset_id }}</el-descriptions-item>
              <el-descriptions-item label="资产编号">{{ detail.asset?.asset_no || '-' }}</el-descriptions-item>
              <el-descriptions-item label="所属公司">{{ detail.asset?.company || '-' }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="statusMap[detail.asset?.status]?.type">{{ statusMap[detail.asset?.status]?.label || detail.asset?.status }}</el-tag>
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
              <el-descriptions-item label="备注" :span="2">{{ detail.asset?.remark || '-' }}</el-descriptions-item>
            </el-descriptions>

            <div v-if="detail.asset" class="qr-box qr-box-inline">
              <img :src="qrUrl" alt="资产二维码" />
              <span>扫码识别资产编号、名称和序列号</span>
            </div>
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>采购与质保</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="采购时间">{{ detail.asset?.purchase_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="采购审批单号">{{ detail.asset?.purchase_approval_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="采购供应商">{{ detail.asset?.purchase_supplier_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="质保到期">{{ detail.asset?.warranty_expire_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="质保月数">{{ detail.asset?.warranty_months || '-' }}</el-descriptions-item>
            <el-descriptions-item label="退役年限">{{ detail.asset?.retirement_years ? `${detail.asset.retirement_years} 年` : '-' }}</el-descriptions-item>
            <el-descriptions-item label="预计退役时间">{{ detail.asset?.retirement_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="质保状态">
              <el-tag :type="warrantyTag.type">{{ warrantyTag.text }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="history-header">
              <span>完整历史时间线</span>
              <el-segmented v-model="historyFilter" :options="historyFilterOptions" />
            </div>
          </template>
          <Timeline :items="filteredTimeline" />
        </el-card>
      </div>

      <div class="page">
        <el-card shadow="never">
          <template #header>风险提示</template>
          <el-space direction="vertical" alignment="stretch" style="width: 100%">
            <el-alert
              v-for="risk in detail.risks"
              :key="risk.message"
              :type="risk.level === 'high' ? 'error' : risk.level === 'medium' ? 'warning' : 'success'"
              :title="risk.message"
              show-icon
              :closable="false"
            />
          </el-space>
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
            <el-table-column prop="filename" label="文件名" min-width="160" />
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import Timeline from '../../components/Timeline.vue'
import { getAssetDetail, statusMap } from '../../api/asset'
import { archiveAssetFile, deleteAssetFile, downloadAssetFile, listAssetFiles, loadAssetQrCode, restoreAssetFile, uploadAssetFile } from '../../api/file'

const route = useRoute()
const detail = reactive({ asset: null, lifecycles: [], changes: [], checkouts: [], timeline: [], usageRecords: [], inventoryRecords: [], risks: [] })
const attachments = ref([])
const qrUrl = ref('')
const historyFilter = ref('all')
const historyFilterOptions = [
  { label: '全部', value: 'all' },
  { label: '领用归还', value: 'checkout' },
  { label: '字段变更', value: 'change' },
  { label: '维修报废', value: 'repair_scrap' },
  { label: '出入库', value: 'inventory' }
]
const attachmentPagination = reactive({ page: 1, pageSize: 10, total: 0 })

const ownerName = computed(() => detail.asset?.owner_name || detail.asset?.owner_username || detail.asset?.owner || '未分配')
const deptName = computed(() => detail.asset?.dept_name || detail.asset?.dept || '未绑定')
const filteredTimeline = computed(() => {
  if (historyFilter.value === 'all') return detail.timeline
  if (historyFilter.value === 'repair_scrap') return detail.timeline.filter(item => ['repair', 'scrap'].includes(item.group))
  return detail.timeline.filter(item => item.group === historyFilter.value)
})
const pagedAttachments = computed(() => attachments.value)

const warrantyTag = computed(() => {
  const value = detail.asset?.warranty_expire_date
  if (!value) return { type: 'info', text: '未设置' }
  return new Date(value) >= new Date() ? { type: 'success', text: '在保' } : { type: 'danger', text: '已过保' }
})

onMounted(async () => {
  Object.assign(detail, await getAssetDetail(route.params.id))
  qrUrl.value = await loadAssetQrCode(route.params.id)
  await loadAttachments()
})

async function loadAttachments() {
  if (!route.params.id) return
  const result = await listAssetFiles(route.params.id, { page: attachmentPagination.page, page_size: attachmentPagination.pageSize })
  attachments.value = result.list || result
  attachmentPagination.total = result.total ?? attachments.value.length
}

function handleAttachmentSizeChange() {
  attachmentPagination.page = 1
  loadAttachments()
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
.detail-grid {
  display: grid;
  grid-template-columns: minmax(520px, 1.35fr) minmax(360px, 0.65fr);
  gap: 16px;
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

.basic-info-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 196px;
  align-items: start;
  gap: 16px;
}

.basic-info-table {
  min-width: 0;
}

.qr-box {
  display: grid;
  justify-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 13px;
  text-align: center;
}

.qr-box-inline {
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.qr-box img {
  width: 168px;
  height: 168px;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 1180px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .basic-info-layout {
    grid-template-columns: 1fr;
  }

  .qr-box-inline {
    justify-self: stretch;
  }
}
</style>
