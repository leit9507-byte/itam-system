<template>
  <el-table :data="assets" border stripe>
    <el-table-column prop="asset_id" label="资产ID" width="110" />
    <el-table-column label="产品信息" min-width="240">
      <template #default="{ row }">
        <div class="asset-name">
          <strong>{{ row.name }}</strong>
          <span>{{ row.brand }} / {{ row.model }} / {{ row.spec }}</span>
        </div>
      </template>
    </el-table-column>
    <el-table-column prop="sn" label="序列号" width="150" />
    <el-table-column prop="category" label="类别" width="110" />
    <el-table-column prop="owner" label="使用人" width="110">
      <template #default="{ row }">{{ row.owner || '未分配' }}</template>
    </el-table-column>
    <el-table-column prop="dept" label="部门" width="110">
      <template #default="{ row }">{{ row.dept || '未绑定' }}</template>
    </el-table-column>
    <el-table-column prop="warehouse" label="仓库" width="130" />
    <el-table-column prop="status" label="状态" width="110">
      <template #default="{ row }">
        <el-tag :type="statusMap[row.status]?.type || 'info'">{{ statusMap[row.status]?.label || row.status }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="price" label="价值" width="120">
      <template #default="{ row }">¥{{ row.price.toLocaleString() }}</template>
    </el-table-column>
    <el-table-column label="操作" width="260" fixed="right">
      <template #default="{ row }">
        <el-button type="primary" link @click="$emit('detail', row)">详情</el-button>
        <el-button type="success" link :disabled="row.status === 'in_stock' || row.status === 'scrapped'" @click="$emit('inbound', row)">入库</el-button>
        <el-button type="warning" link :disabled="['scrapped', 'pending_scrap'].includes(row.status)" @click="$emit('outbound', row)">出库</el-button>
        <el-button type="danger" link :disabled="['scrapped', 'pending_scrap'].includes(row.status)" @click="$emit('scrap', row)">申请报废</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { statusMap } from '../api/asset'

defineProps({
  assets: {
    type: Array,
    default: () => []
  }
})

defineEmits(['detail', 'inbound', 'outbound', 'scrap'])
</script>

<style scoped>
.asset-name {
  display: grid;
  gap: 4px;
}

.asset-name span {
  color: var(--muted);
  font-size: 12px;
}
</style>
