<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">生命周期</h2>
        <p class="page-subtitle">展示采购、入库、出库、维修、报废等真实资产流转记录</p>
      </div>
      <div class="toolbar">
        <el-radio-group v-model="operationType" @change="refresh">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="daily_inventory">日常出入库</el-radio-button>
          <el-radio-button label="other">其他操作</el-radio-button>
        </el-radio-group>
        <el-input v-model="keyword" clearable placeholder="搜索资产ID/名称/公司/操作人" style="width: 280px" @input="refresh" />
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 260px"
          @change="load"
        />
        <el-button @click="load">刷新</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="items" border stripe empty-text="暂无生命周期记录">
        <el-table-column prop="time" label="时间" width="170" />
        <el-table-column prop="company" label="公司" width="140" show-overflow-tooltip />
        <el-table-column prop="asset_id" label="资产ID" width="130" />
        <el-table-column prop="asset_name" label="资产名称" min-width="180" />
        <el-table-column prop="category_label" label="分类" width="120" />
        <el-table-column prop="type_label" label="动作" width="150" />
        <el-table-column prop="responsible_label" label="责任人/对象" width="150" show-overflow-tooltip />
        <el-table-column prop="status_change_label" label="状态变化" width="190" />
        <el-table-column prop="operator" label="操作人" width="130" />
        <el-table-column prop="description" label="说明" min-width="240" show-overflow-tooltip />
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="load"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, onMounted, ref } from 'vue'
import { getLifecycleList } from '../../api/asset'

const items = ref([])
const keyword = ref('')
const dateRange = ref([])
const operationType = ref('all')
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

onMounted(load)

async function load() {
  const [start_date, end_date] = dateRange.value || []
  const result = await getLifecycleList({
    start_date,
    end_date,
    keyword: keyword.value,
    operation_type: operationType.value === 'all' ? '' : operationType.value,
    page: pagination.page,
    page_size: pagination.pageSize
  })
  items.value = result.list
  pagination.total = result.total
}

function refresh() {
  pagination.page = 1
  load()
}

function handlePageSizeChange() {
  pagination.page = 1
  load()
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
