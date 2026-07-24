<template>
  <div class="supplier-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">供应商管理</h2>
        <p class="page-subtitle">维护供应商档案，进入详情查看采购信息和回收资产。</p>
      </div>
      <el-button type="primary" @click="openCreate">新增供应商</el-button>
    </div>

    <section class="summary-grid">
      <el-card shadow="never" class="summary-card">
        <span>供应商总数</span>
        <strong>{{ supplierPagination.total }}</strong>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <span>当前页采购单数</span>
        <strong>{{ summary.purchaseCount }}</strong>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <span>当前页采购设备数</span>
        <strong>{{ summary.deviceCount }}</strong>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <span>当前页采购金额</span>
        <strong>￥{{ summary.totalAmount.toLocaleString() }}</strong>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <span>当前页回收金额</span>
        <strong>￥{{ summary.recycleAmount.toLocaleString() }}</strong>
      </el-card>
    </section>

    <section class="supplier-layout">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>供应商列表</span>
            <el-input v-model="keyword" clearable placeholder="搜索供应商" style="width: 240px" @input="refreshSuppliers" />
          </div>
        </template>
        <el-table :data="suppliers" border stripe>
          <el-table-column label="供应商" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">
              <el-button link type="primary" class="supplier-link" @click="goDetail(row)">{{ row.name }}</el-button>
              <div class="supplier-meta">{{ [row.contact, row.phone].filter(Boolean).join(' / ') || '未维护联系人' }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="level" label="等级" width="100" />
          <el-table-column prop="purchase_count" label="采购单" width="100" />
          <el-table-column prop="device_count" label="设备数" width="100" />
          <el-table-column prop="recycle_count" label="回收数" width="100" />
          <el-table-column prop="total_amount" label="采购金额" width="150">
            <template #default="{ row }">￥{{ Number(row.total_amount || 0).toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="recycle_amount" label="回收金额" width="150">
            <template #default="{ row }">￥{{ Number(row.recycle_amount || 0).toLocaleString() }}</template>
          </el-table-column>
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="goDetail(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="supplierPagination.page"
            v-model:page-size="supplierPagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="supplierPagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSupplierPageSizeChange"
            @current-change="load"
          />
        </div>
      </el-card>
    </section>

    <el-dialog v-model="dialog.visible" title="供应商档案" width="560px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="供应商"><el-input v-model="dialog.form.name" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="dialog.form.contact" /></el-form-item>
        <el-form-item label="电话"><el-input v-model="dialog.form.phone" /></el-form-item>
        <el-form-item label="等级">
          <el-select v-model="dialog.form.level" style="width: 100%">
            <el-option label="核心" value="核心" />
            <el-option label="普通" value="普通" />
            <el-option label="观察" value="观察" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getSuppliersPaged, saveSupplier } from '../../api/supplier'

const router = useRouter()
const suppliers = ref([])
const keyword = ref('')
const dialog = reactive({ visible: false, form: defaultForm() })
const supplierPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const summary = computed(() => suppliers.value.reduce((acc, item) => {
  acc.purchaseCount += Number(item.purchase_count || 0)
  acc.deviceCount += Number(item.device_count || 0)
  acc.totalAmount += Number(item.total_amount || 0)
  acc.recycleAmount += Number(item.recycle_amount || 0)
  return acc
}, { purchaseCount: 0, deviceCount: 0, totalAmount: 0, recycleAmount: 0 }))

onMounted(load)

async function load() {
  const result = await getSuppliersPaged({ keyword: keyword.value, page: supplierPagination.page, page_size: supplierPagination.pageSize })
  suppliers.value = result.list
  supplierPagination.total = result.total
}

async function refreshSuppliers() {
  supplierPagination.page = 1
  await load()
}

function handleSupplierPageSizeChange() {
  supplierPagination.page = 1
  load()
}

function openCreate() {
  dialog.form = defaultForm()
  dialog.visible = true
}

function goDetail(row) {
  router.push({ name: 'SupplierDetail', query: { name: row.name } })
}

async function save() {
  if (!dialog.form.name.trim()) {
    ElMessage.warning('请填写供应商名称')
    return
  }
  await saveSupplier(dialog.form)
  dialog.visible = false
  ElMessage.success('供应商已保存')
  supplierPagination.page = 1
  await load()
}

function defaultForm() {
  return { id: '', name: '', contact: '', phone: '', level: '普通', status: '启用' }
}
</script>

<style scoped>
.supplier-page {
  display: grid;
  gap: 16px;
}

.supplier-layout {
  display: grid;
  grid-template-columns: 1fr;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.summary-card :deep(.el-card__body) {
  display: grid;
  gap: 8px;
  padding: 16px;
}

.summary-card span {
  color: var(--muted);
  font-size: 13px;
}

.summary-card strong {
  color: var(--text);
  font-size: 24px;
  line-height: 1.1;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.supplier-link {
  max-width: 100%;
  padding: 0;
  white-space: normal;
  text-align: left;
}

.supplier-meta {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
  margin-top: 4px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 1280px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .card-header {
    align-items: stretch;
    flex-direction: column;
  }

  .card-header :deep(.el-input) {
    width: 100% !important;
  }
}
</style>
