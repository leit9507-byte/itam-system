<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">报告中心</h2>
        <p class="page-subtitle">基于正式审计数据生成、预览和下载资产审计报告</p>
      </div>
      <el-space>
        <el-button @click="downloadAssetCsv">导出资产 CSV</el-button>
        <el-button @click="downloadAssetPdf">导出资产 PDF</el-button>
        <el-button :disabled="!previewHtml" @click="handleDownloadAudit">下载审计报告</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">生成审计报告</el-button>
      </el-space>
    </div>

    <div class="two-column">
      <el-card shadow="never">
        <template #header>报告列表</template>
        <el-table :data="reports" border empty-text="暂无已生成报告，请点击生成审计报告">
          <el-table-column prop="id" label="报告ID" width="170" />
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="status" label="状态" width="110" />
          <el-table-column prop="risk_score" label="风险评分" width="100" />
          <el-table-column prop="created_at" label="日期" width="130" />
          <el-table-column label="操作" width="110">
            <template #default="{ row }">
              <el-button type="primary" link @click="previewHtml = row.html">预览</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>HTML 报告预览</span>
            <el-tag v-if="activeReport" type="success">{{ activeReport.name }}</el-tag>
          </div>
        </template>
        <div v-if="previewHtml" class="report-preview" v-html="previewHtml" />
        <el-empty v-else description="生成审计报告后，可在这里预览正式报告内容" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { generateReport, getReports } from '../../api/audit'
import { downloadAssetCsv, downloadAssetPdf, downloadAuditReport } from '../../api/reporting'

const reports = ref([])
const previewHtml = ref('')
const generating = ref(false)

const activeReport = computed(() => reports.value.find(item => item.html === previewHtml.value))

onMounted(async () => {
  reports.value = await getReports()
})

async function handleGenerate() {
  generating.value = true
  try {
    const report = await generateReport()
    reports.value.unshift(report)
    previewHtml.value = report.html
    ElMessage.success('审计报告已生成，已包含审计答复和合规判断')
  } finally {
    generating.value = false
  }
}

async function handleDownloadAudit() {
  await downloadAuditReport()
  ElMessage.success('审计报告已下载')
}
</script>

<style scoped>
.report-preview {
  min-height: 420px;
  max-height: calc(100vh - 260px);
  overflow: auto;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}

.report-preview :deep(main) {
  max-width: none;
  border: 0;
  border-radius: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
</style>
