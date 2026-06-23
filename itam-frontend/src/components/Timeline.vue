<template>
  <el-timeline>
    <el-timeline-item
      v-for="item in items"
      :key="`${item.asset_id || ''}-${item.type}-${item.time}`"
      :timestamp="item.time"
      placement="top"
    >
      <el-card shadow="never">
        <strong>{{ item.type }}</strong>
        <p>{{ item.description }}</p>
        <span>操作人：{{ item.operator }}</span>
      </el-card>
    </el-timeline-item>
  </el-timeline>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
p {
  margin: 6px 0;
  color: var(--text);
}

span {
  color: var(--muted);
  font-size: 13px;
}
</style>
