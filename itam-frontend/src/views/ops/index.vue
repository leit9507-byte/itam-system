<template>
  <div class="page ops-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">运维面板</h2>
        <p class="page-subtitle">健康检查、操作日志、定时任务和备份恢复脚本状态</p>
      </div>
      <el-button type="primary" @click="loadAll">刷新</el-button>
    </div>

    <div class="ops-grid">
      <el-card shadow="never">
        <template #header>健康检查</template>
        <el-descriptions v-if="health" :column="1" border>
          <el-descriptions-item label="服务">{{ health.service }}</el-descriptions-item>
          <el-descriptions-item label="检查时间">{{ health.checked_at }}</el-descriptions-item>
          <el-descriptions-item label="数据库">
            <el-tag :type="health.database?.ok ? 'success' : 'danger'">{{ health.database?.message }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="上传目录">{{ health.upload_dir?.exists ? '正常' : '不存在' }} / {{ health.upload_dir?.path }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>定时任务</template>
        <el-table :data="jobs" border>
          <el-table-column prop="name" label="任务" min-width="160" />
          <el-table-column prop="schedule" label="计划" width="130" />
          <el-table-column prop="status" label="状态" width="110" />
        </el-table>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>错误与操作日志</template>
      <el-table :data="logs" border stripe>
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column prop="module" label="模块" width="100" />
        <el-table-column prop="action" label="动作" width="100" />
        <el-table-column prop="target_id" label="对象" width="140" />
        <el-table-column prop="operator" label="操作人" width="150" />
        <el-table-column prop="summary" label="摘要" min-width="220" show-overflow-tooltip />
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>备份恢复</template>
      <el-alert type="info" :closable="false" title="正式环境可使用 scripts/backup.ps1 备份数据库与上传目录，使用 scripts/restore.ps1 按备份文件恢复。" />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getOperationLogs, getOpsHealth, getScheduledJobs } from '../../api/ops'

const health = ref(null)
const jobs = ref([])
const logs = ref([])

onMounted(loadAll)

async function loadAll() {
  const [healthResult, jobsResult, logsResult] = await Promise.all([getOpsHealth(), getScheduledJobs(), getOperationLogs({ limit: 100 })])
  health.value = healthResult
  jobs.value = jobsResult
  logs.value = logsResult
}
</script>

<style scoped>
.ops-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}

@media (max-width: 900px) {
  .ops-grid {
    grid-template-columns: 1fr;
  }
}
</style>
