<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">报废审批</h2>
        <p class="page-subtitle">审核已提交报废审批的资产，并保留报废申请时的资产历史快照</p>
      </div>
      <el-button @click="load">刷新</el-button>
    </div>

    <div class="metric-grid">
      <el-card shadow="never"><el-statistic title="审批中" :value="countByStatus('审批中')" /></el-card>
      <el-card shadow="never"><el-statistic title="已通过" :value="countByStatus('已通过')" /></el-card>
      <el-card shadow="never"><el-statistic title="已驳回" :value="countByStatus('已驳回')" /></el-card>
      <el-card shadow="never"><el-statistic title="预计残值" :value="totalResidual" prefix="¥" /></el-card>
    </div>

    <el-card shadow="never">
      <el-table :data="requests" border stripe>
        <el-table-column prop="request_no" label="流程单号" width="140" />
        <el-table-column prop="company" label="公司" width="120" show-overflow-tooltip />
        <el-table-column prop="asset_id" label="资产ID" width="120" />
        <el-table-column label="资产历史信息" min-width="260">
          <template #default="{ row }">
            <div class="asset-info">
              <strong>{{ row.asset_name }}</strong>
              <span>{{ row.category || '-' }} / {{ row.brand || '-' }} / {{ row.model || '-' }}</span>
              <span>SN：{{ row.sn || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="采购历史" min-width="220">
          <template #default="{ row }">
            <div class="asset-info">
              <span>供应商：{{ row.purchase_supplier_name || '-' }}</span>
              <span>审批单：{{ row.purchase_approval_no || '-' }}</span>
              <span>采购价：¥{{ row.purchase_price.toLocaleString() }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="责任历史" min-width="190">
          <template #default="{ row }">
            <div class="asset-info">
              <span>责任人：{{ row.owner_user_id || '-' }}</span>
              <span>部门：{{ row.dept_id || '-' }}</span>
              <span>位置：{{ row.location || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="报废原因" min-width="220" show-overflow-tooltip />
        <el-table-column prop="disposal_method" label="处置方式" width="120" />
        <el-table-column prop="estimated_residual_value" label="预计残值" width="120">
          <template #default="{ row }">¥{{ row.estimated_residual_value.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建日期" width="120" />
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button type="success" link :disabled="row.status !== '审批中'" @click="approve(row)">通过</el-button>
            <el-button type="danger" link :disabled="row.status !== '审批中'" @click="reject(row)">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { approveScrapRequest, getScrapRequests, rejectScrapRequest } from '../../api/asset'

const requests = ref([])

const totalResidual = computed(() => requests.value.reduce((sum, item) => sum + Number(item.estimated_residual_value || 0), 0))

onMounted(load)

async function load() {
  requests.value = await getScrapRequests()
}

function countByStatus(status) {
  return requests.value.filter(item => item.status === status).length
}

async function approve(row) {
  await ElMessageBox.confirm(`确认通过 ${row.asset_id} 的报废审批？通过后资产将正式报废。`, '审批确认', { type: 'warning' })
  await approveScrapRequest(row.id, '资产负责人')
  ElMessage.success('报废审批已通过，资产已变更为已报废')
  await load()
}

async function reject(row) {
  await ElMessageBox.confirm(`确认驳回 ${row.asset_id} 的报废申请？`, '驳回确认', { type: 'warning' })
  await rejectScrapRequest(row.id, '资产负责人')
  ElMessage.success('报废审批已驳回，资产恢复为闲置')
  await load()
}

function statusType(status) {
  if (status === '已通过') return 'success'
  if (status === '已驳回') return 'danger'
  return 'warning'
}
</script>

<style scoped>
.asset-info {
  display: grid;
  gap: 4px;
}

.asset-info span {
  color: var(--muted);
  font-size: 12px;
}
</style>
