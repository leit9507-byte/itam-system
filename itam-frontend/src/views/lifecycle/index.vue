<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">生命周期</h2>
        <p class="page-subtitle">展示采购、分配、调拨、报废等资产流转记录</p>
      </div>
    </div>
    <el-card shadow="never">
      <Timeline :items="items" />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import Timeline from '../../components/Timeline.vue'
import { getLifecycleList } from '../../api/asset'

const items = ref([])

onMounted(async () => {
  items.value = await getLifecycleList()
})
</script>
