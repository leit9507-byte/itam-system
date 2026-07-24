<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">部门管理</h2>
        <p class="page-subtitle">按人员目录和资产归属汇总部门，点击部门名称查看人员和资产清单</p>
      </div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </div>

    <div class="metric-grid">
      <el-card shadow="never"><el-statistic title="部门数量" :value="departments.length" /></el-card>
      <el-card shadow="never"><el-statistic title="在职人员" :value="activeUserCount" /></el-card>
      <el-card shadow="never"><el-statistic title="绑定资产" :value="assignedAssetCount" /></el-card>
      <el-card shadow="never"><el-statistic title="未绑定部门资产" :value="unboundAssetCount" /></el-card>
    </div>

    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <el-input v-model="keyword" clearable placeholder="搜索部门编码/名称" style="width: 280px" />
        <el-button @click="keyword = ''">重置</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="pagedDepartments" border stripe empty-text="暂无部门数据">
        <el-table-column prop="dept_id" label="部门编码" min-width="150" />
        <el-table-column label="部门名称" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" class="entity-link" @click="goDetail(row)">{{ row.dept_name }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="user_count" label="人员数" width="100" />
        <el-table-column prop="active_user_count" label="在职人员" width="110" />
        <el-table-column prop="asset_count" label="资产数" width="100" />
        <el-table-column prop="asset_value" label="资产原值" width="140">
          <template #default="{ row }">¥{{ Number(row.asset_value || 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.active_user_count ? 'success' : 'info'">{{ row.active_user_count ? '使用中' : '暂无在职' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredDepartments.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="pagination.page = 1"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getAssets } from '../../api/asset'
import { getUsers } from '../../api/user'

const router = useRouter()
const loading = ref(false)
const users = ref([])
const assets = ref([])
const keyword = ref('')
const pagination = reactive({ page: 1, pageSize: 10 })
const DEPARTMENT_ASSET_LIMIT = 1000

const departments = computed(() => {
  const map = new Map()
  const ensure = (deptId, deptName) => {
    const id = deptId || deptName || '未绑定'
    if (!map.has(id)) {
      map.set(id, {
        dept_id: deptId || '未绑定',
        dept_name: deptName || deptId || '未绑定',
        user_count: 0,
        active_user_count: 0,
        asset_count: 0,
        asset_value: 0
      })
    }
    return map.get(id)
  }

  users.value.forEach(user => {
    const row = ensure(user.dept_id, user.dept_name)
    row.user_count += 1
    if (user.status === 'active') row.active_user_count += 1
  })

  assets.value.forEach(asset => {
    const row = ensure(asset.dept_id || asset.dept, asset.dept_name)
    row.asset_count += 1
    row.asset_value += Number(asset.price || asset.purchase_price || 0)
  })

  return Array.from(map.values()).sort((a, b) => b.asset_count - a.asset_count || b.active_user_count - a.active_user_count)
})

const filteredDepartments = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return departments.value
  return departments.value.filter(item => [item.dept_id, item.dept_name].join(' ').toLowerCase().includes(text))
})

const pagedDepartments = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  return filteredDepartments.value.slice(start, start + pagination.pageSize)
})

const activeUserCount = computed(() => users.value.filter(item => item.status === 'active').length)
const assignedAssetCount = computed(() => assets.value.filter(item => item.dept_id || item.dept || item.dept_name).length)
const unboundAssetCount = computed(() => assets.value.length - assignedAssetCount.value)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const [userRows, assetResult] = await Promise.all([getUsers(), getAssets({ page: 1, page_size: DEPARTMENT_ASSET_LIMIT })])
    users.value = userRows
    assets.value = assetResult.list || []
  } catch (error) {
    ElMessage.error(`部门数据加载失败：${error?.message || '请稍后重试'}`)
  } finally {
    loading.value = false
  }
}

function goDetail(row) {
  router.push({ name: 'DepartmentDetail', query: { dept_id: row.dept_id, name: row.dept_name } })
}
</script>

<style scoped>
.entity-link {
  padding: 0;
  white-space: normal;
  text-align: left;
}
</style>
