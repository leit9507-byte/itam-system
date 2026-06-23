<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">审计中心</h2>
        <p class="page-subtitle">触发规则引擎，识别超配、闲置和责任归属风险</p>
      </div>
      <el-button type="primary" :loading="loading" @click="handleRun">立即审计</el-button>
    </div>

    <AuditPanel :result="result" :loading="loading" @run="handleRun" />

    <el-card shadow="never">
      <template #header>优化建议</template>
      <el-space direction="vertical" alignment="stretch" style="width: 100%">
        <el-alert v-for="item in result?.suggestions || []" :key="item" :title="item" type="info" show-icon :closable="false" />
      </el-space>
    </el-card>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import AuditPanel from '../../components/AuditPanel.vue'
import { runAudit } from '../../api/audit'

const loading = ref(false)
const result = ref(null)

onMounted(handleRun)

async function handleRun() {
  loading.value = true
  result.value = await runAudit()
  loading.value = false
  ElMessage.success('审计已完成')
}
</script>
