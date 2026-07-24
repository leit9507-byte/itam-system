<template>
  <div class="department-detail-page">
    <div class="page-header">
      <div>
        <el-button link class="back-link" @click="router.back()">返回部门列表</el-button>
        <h2 class="page-title">{{ deptName || deptId || '部门详情' }}</h2>
        <p class="page-subtitle">查看该部门下的人员目录和资产归属。</p>
      </div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </div>

    <section class="metric-grid">
      <el-card shadow="never"><el-statistic title="人员数" :value="departmentUsers.length" /></el-card>
      <el-card shadow="never"><el-statistic title="在职人员" :value="activeUserCount" /></el-card>
      <el-card shadow="never"><el-statistic title="资产数" :value="departmentAssets.length" /></el-card>
      <el-card shadow="never"><el-statistic title="资产原值" :value="assetValue" prefix="￥" /></el-card>
    </section>

    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="人员目录" name="users">
          <el-table v-loading="loading" :data="pagedUsers" border stripe empty-text="暂无人员数据">
            <el-table-column prop="username" label="账号" width="150" />
            <el-table-column prop="name" label="姓名" width="140" />
            <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
            <el-table-column prop="dept_id" label="部门编码" width="140" />
            <el-table-column prop="dept_name" label="部门名称" width="160" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '在职' : row.status || '未知' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="userPagination.page"
              v-model:page-size="userPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="departmentUsers.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="userPagination.page = 1"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="部门资产" name="assets">
          <el-table v-loading="loading" :data="pagedAssets" border stripe empty-text="暂无资产数据">
            <el-table-column prop="asset_no" label="资产编号" width="140" />
            <el-table-column prop="name" label="资产名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="category" label="类型" width="120" />
            <el-table-column label="产品信息" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">{{ row.brand || '-' }} / {{ row.model || '-' }}</template>
            </el-table-column>
            <el-table-column prop="sn" label="序列号" width="150" show-overflow-tooltip />
            <el-table-column prop="company" label="公司" width="160" show-overflow-tooltip />
            <el-table-column prop="location" label="位置" width="160" show-overflow-tooltip />
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="statusMap[row.status]?.type || 'info'">{{ row.status_label || statusMap[row.status]?.label || row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="purchase_price" label="原值" width="120">
              <template #default="{ row }">￥{{ Number(row.purchase_price || 0).toLocaleString() }}</template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="assetPagination.page"
              v-model:page-size="assetPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="departmentAssets.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="assetPagination.page = 1"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAssets, statusMap } from '../../api/asset'
import { getUsers } from '../../api/user'

const route = useRoute()
const router = useRouter()
const deptId = computed(() => String(route.query.dept_id || ''))
const deptName = computed(() => String(route.query.name || ''))
const loading = ref(false)
const users = ref([])
const assets = ref([])
const activeTab = ref('users')
const userPagination = reactive({ page: 1, pageSize: 10 })
const assetPagination = reactive({ page: 1, pageSize: 10 })
const DETAIL_LIMIT = 2000

const departmentUsers = computed(() => users.value.filter(user => matchDepartment(user.dept_id, user.dept_name)))
const departmentAssets = computed(() => assets.value.filter(asset => matchDepartment(asset.dept_id || asset.dept, asset.dept_name)))
const activeUserCount = computed(() => departmentUsers.value.filter(user => user.status === 'active').length)
const assetValue = computed(() => departmentAssets.value.reduce((sum, asset) => sum + Number(asset.price || asset.purchase_price || 0), 0))
const pagedUsers = computed(() => paginate(departmentUsers.value, userPagination))
const pagedAssets = computed(() => paginate(departmentAssets.value, assetPagination))

onMounted(load)

async function load() {
  loading.value = true
  try {
    const [userRows, assetResult] = await Promise.all([getUsers(), getAssets({ page: 1, page_size: DETAIL_LIMIT })])
    users.value = userRows
    assets.value = assetResult.list || []
  } finally {
    loading.value = false
  }
}

function matchDepartment(id, name) {
  if (deptId.value === '未绑定') return !id && !name
  return [id, name].filter(Boolean).includes(deptId.value) || [id, name].filter(Boolean).includes(deptName.value)
}

function paginate(rows, pagination) {
  const start = (pagination.page - 1) * pagination.pageSize
  return rows.slice(start, start + pagination.pageSize)
}
</script>

<style scoped>
.department-detail-page {
  display: grid;
  gap: 16px;
}

.back-link {
  padding: 0;
  margin-bottom: 8px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
