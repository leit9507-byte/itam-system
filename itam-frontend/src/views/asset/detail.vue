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
          <el-descriptions :column="2" border>
            <el-descriptions-item label="资产ID">{{ detail.asset?.asset_id }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusMap[detail.asset?.status]?.type">{{ statusMap[detail.asset?.status]?.label || detail.asset?.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="产品名称">{{ detail.asset?.name }}</el-descriptions-item>
            <el-descriptions-item label="设备类型">{{ detail.asset?.category }}</el-descriptions-item>
            <el-descriptions-item label="品牌">{{ detail.asset?.brand || '-' }}</el-descriptions-item>
            <el-descriptions-item label="型号">{{ detail.asset?.model || '-' }}</el-descriptions-item>
            <el-descriptions-item label="规格">{{ detail.asset?.spec || '-' }}</el-descriptions-item>
            <el-descriptions-item label="序列号">{{ detail.asset?.sn || '-' }}</el-descriptions-item>
            <el-descriptions-item label="责任人">{{ detail.asset?.owner || '未分配' }}</el-descriptions-item>
            <el-descriptions-item label="部门">{{ detail.asset?.dept || '未绑定' }}</el-descriptions-item>
            <el-descriptions-item label="位置">{{ detail.asset?.location || '-' }}</el-descriptions-item>
            <el-descriptions-item label="仓库">{{ detail.asset?.warehouse || '-' }}</el-descriptions-item>
            <el-descriptions-item label="价值">¥{{ Number(detail.asset?.price || 0).toLocaleString() }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never">
          <template #header>采购与质保</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="采购时间">{{ detail.asset?.purchase_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="采购审批单号">{{ detail.asset?.purchase_approval_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="采购供应商">{{ detail.asset?.purchase_supplier_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="质保到期">{{ detail.asset?.warranty_expire_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="质保月数">{{ detail.asset?.warranty_months || '-' }}</el-descriptions-item>
            <el-descriptions-item label="质保状态">
              <el-tag :type="warrantyTag.type">{{ warrantyTag.text }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never">
          <template #header>生命周期时间轴</template>
          <Timeline :items="detail.lifecycles" />
        </el-card>
      </div>

      <div class="page">
        <el-card shadow="never">
          <template #header>资产二维码</template>
          <div v-if="detail.asset" class="qr-box">
            <img :src="qrUrl" alt="资产二维码" />
            <span>扫码识别资产编号、名称和序列号</span>
          </div>
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
          <el-table :data="attachments" border empty-text="暂无附件">
            <el-table-column prop="filename" label="文件名" min-width="160" />
            <el-table-column prop="size" label="大小" width="100">
              <template #default="{ row }">{{ formatSize(row.size) }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" width="170" />
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button link type="primary" @click="downloadFile(row)">下载</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never">
          <template #header>出入库记录</template>
          <el-table :data="detail.inventoryRecords" border empty-text="暂无出入库记录">
            <el-table-column prop="type" label="类型" width="80" />
            <el-table-column prop="target" label="目标" />
            <el-table-column prop="operator" label="操作人" width="110" />
            <el-table-column prop="time" label="时间" width="170" />
          </el-table>
        </el-card>

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
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import Timeline from '../../components/Timeline.vue'
import { getAssetDetail, statusMap } from '../../api/asset'
import { downloadAssetFile, listAssetFiles, loadAssetQrCode, uploadAssetFile } from '../../api/file'

const route = useRoute()
const detail = reactive({ asset: null, lifecycles: [], usageRecords: [], inventoryRecords: [], risks: [] })
const attachments = ref([])
const qrUrl = ref('')

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
  attachments.value = await listAssetFiles(route.params.id)
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

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.qr-box {
  display: grid;
  justify-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 13px;
}

.qr-box img {
  width: 168px;
  height: 168px;
  border: 1px solid var(--line);
  border-radius: 8px;
}

@media (max-width: 1180px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
