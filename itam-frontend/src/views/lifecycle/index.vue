<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">生命周期</h2>
        <p class="page-subtitle">展示采购、入库、出库、维修、报废等真实资产流转记录</p>
      </div>
      <div class="toolbar">
        <el-input v-model="keyword" clearable placeholder="搜索资产ID/名称/公司/操作人" style="width: 280px" />
        <el-button @click="load">刷新</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="filteredItems" border stripe empty-text="暂无生命周期记录">
        <el-table-column prop="time" label="时间" width="170" />
        <el-table-column prop="company" label="公司" width="140" show-overflow-tooltip />
        <el-table-column prop="asset_id" label="资产ID" width="130" />
        <el-table-column prop="asset_name" label="资产名称" min-width="180" />
        <el-table-column prop="type" label="动作" width="140" />
        <el-table-column label="状态变化" width="180">
          <template #default="{ row }">{{ row.from_status || '-' }} -> {{ row.to_status || '-' }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="操作人" width="130" />
        <el-table-column prop="description" label="说明" min-width="240" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getLifecycleList } from '../../api/asset'

const items = ref([])
const keyword = ref('')

const filteredItems = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return items.value
  return items.value.filter(item => [item.asset_id, item.asset_name, item.company, item.operator, item.type, item.description].join(' ').toLowerCase().includes(text))
})

onMounted(load)

async function load() {
  items.value = await getLifecycleList()
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
