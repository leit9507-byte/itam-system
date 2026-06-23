<template>
  <el-card shadow="never">
    <template #header>
      <div class="risk-header">
        <span>{{ title }}</span>
        <el-tag :type="tagType">{{ levelText }}</el-tag>
      </div>
    </template>
    <el-progress type="dashboard" :percentage="score" :color="colors" />
    <p>{{ description }}</p>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '风险评分' },
  score: { type: Number, default: 0 },
  description: { type: String, default: '基于审计规则自动计算' }
})

const levelText = computed(() => (props.score >= 70 ? '高风险' : props.score >= 40 ? '中风险' : '低风险'))
const tagType = computed(() => (props.score >= 70 ? 'danger' : props.score >= 40 ? 'warning' : 'success'))
const colors = [
  { color: '#16a34a', percentage: 39 },
  { color: '#d97706', percentage: 69 },
  { color: '#dc2626', percentage: 100 }
]
</script>

<style scoped>
.risk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

p {
  margin: 12px 0 0;
  color: var(--muted);
}
</style>
