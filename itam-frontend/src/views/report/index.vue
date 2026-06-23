<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">报告中心</h2>
        <p class="page-subtitle">生成、预览和导出资产审计报告</p>
      </div>
      <el-space>
        <el-button @click="downloadAssetCsv">导出资产 CSV</el-button>
        <el-button @click="downloadAssetPdf">导出资产 PDF</el-button>
        <el-button type="primary" @click="handleGenerate">生成审计报告</el-button>
      </el-space>
    </div>

    <div class="two-column">
      <el-card shadow="never">
        <template #header>报告列表</template>
        <el-table :data="reports" border>
          <el-table-column prop="id" label="报告ID" width="150" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="status" label="状态" width="110" />
          <el-table-column prop="created_at" label="日期" width="130" />
        </el-table>
      </el-card>
      <el-card shadow="never">
        <template #header>HTML 报告预览</template>
        <div class="report-preview" v-html="previewHtml" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { generateReport, getReports } from '../../api/audit'
import { downloadAssetCsv, downloadAssetPdf } from '../../api/reporting'

const reports = ref([])
const previewHtml = ref('<p>点击“生成审计报告”后可在这里预览 HTML 报告；CSV/PDF 会由后端实时导出。</p>')

onMounted(async () => {
  reports.value = await getReports()
})

async function handleGenerate() {
  const report = await generateReport()
  reports.value.unshift({ id: report.id, name: report.name, type: '审计报告', status: '已生成', created_at: new Date().toISOString().slice(0, 10) })
  previewHtml.value = report.html
  ElMessage.success('审计报告已生成')
}
</script>

<style scoped>
.report-preview {
  min-height: 260px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
</style>
