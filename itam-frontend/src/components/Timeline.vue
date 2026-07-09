<template>
  <el-empty v-if="!items.length" description="暂无历史记录" :image-size="72" />
  <el-timeline v-else class="asset-timeline">
    <el-timeline-item
      v-for="item in items"
      :key="`${item.source || item.asset_id || ''}-${item.source_id || ''}-${item.event || item.type}-${item.time}`"
      :timestamp="item.time"
      placement="top"
      :type="timelineType(item)"
    >
      <div class="timeline-event">
        <div class="event-heading">
          <strong>{{ item.title || item.type }}</strong>
          <el-tag size="small" :type="tagType(item)">{{ item.type }}</el-tag>
        </div>
        <p>{{ item.description }}</p>
        <div v-if="item.meta?.length" class="event-meta">
          <span v-for="meta in item.meta" :key="meta">{{ meta }}</span>
        </div>
        <span class="operator">操作人：{{ item.operator || '-' }}</span>
      </div>
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

function timelineType(item) {
  return ({ primary: 'primary', success: 'success', warning: 'warning', danger: 'danger', info: 'info' })[item.tone] || 'primary'
}

function tagType(item) {
  return item.tone === 'primary' ? '' : timelineType(item)
}
</script>

<style scoped>
.asset-timeline {
  padding: 4px 0 0;
}

.timeline-event {
  display: grid;
  gap: 7px;
  padding: 12px 0;
}

.event-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.event-heading strong {
  color: var(--text);
  font-size: 15px;
  line-height: 1.35;
}

p {
  margin: 0;
  color: var(--text);
  line-height: 1.55;
}

.event-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.event-meta span {
  padding: 2px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-size: 12px;
}

.operator {
  color: var(--muted);
  font-size: 13px;
}
</style>
