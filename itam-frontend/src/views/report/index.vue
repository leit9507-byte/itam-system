<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">报告中心</h2>
        <p class="page-subtitle">生成和预览审计报告</p>
      </div>
      <el-button type="primary" @click="handleGenerate">生成审计报告</el-button>
    </div>
    <div class="two-column">
      <el-card shadow="never">
        <template #header>报告列表</template>
        <el-table :data="reports" border>
          <el-table-column prop="id" label="报告ID" width="140" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="created_at" label="日期" width="120" />
        </el-table>
      </el-card>
      <el-card shadow="never">
        <template #header>HTML报告预览</template>
        <div class="report-preview" v-html="previewHtml" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { generateReport, getReports } from '../../api/audit'

const reports = ref([])
const previewHtml = ref('<p>点击“生成审计报告”后预览 HTML 报告。</p>')

onMounted(async () => {
  reports.value = await getReports()
})

async function handleGenerate() {
  const report = await generateReport()
  reports.value.unshift({ id: report.id, name: report.name, type: '审计报告', status: '已生成', created_at: new Date().toISOString().slice(0, 10) })
  previewHtml.value = report.html
  ElMessage.success('模拟审计报告已生成')
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
