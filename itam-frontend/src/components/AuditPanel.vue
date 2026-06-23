<template>
  <div class="audit-panel">
    <RiskCard :score="result?.risk_score || 0" title="审计风险评分" description="high=30, medium=15, low=5，最高100分" />
    <el-card shadow="never">
      <template #header>
        <div class="panel-header">
          <span>违规列表</span>
          <el-button type="primary" :loading="loading" @click="$emit('run')">触发审计</el-button>
        </div>
      </template>
      <el-table :data="result?.violations || []" border>
        <el-table-column prop="asset_id" label="资产ID" width="120" />
        <el-table-column prop="type" label="违规类型" width="180" />
        <el-table-column prop="severity" label="级别" width="120">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="说明" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import RiskCard from './RiskCard.vue'

defineProps({
  result: { type: Object, default: null },
  loading: { type: Boolean, default: false }
})

defineEmits(['run'])

function severityType(severity) {
  return severity === 'high' ? 'danger' : severity === 'medium' ? 'warning' : 'success'
}
</script>

<style scoped>
.audit-panel {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 16px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

@media (max-width: 900px) {
  .audit-panel {
    grid-template-columns: 1fr;
  }
}
</style>
