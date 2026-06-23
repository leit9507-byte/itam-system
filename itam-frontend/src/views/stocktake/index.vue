<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产盘点</h2>
        <p class="page-subtitle">创建盘点任务，登记实盘结果，输出盘盈、盘亏、位置不符等差异</p>
      </div>
      <el-button type="primary" @click="openCreate">创建盘点任务</el-button>
    </div>

    <div class="metric-grid">
      <el-card shadow="never"><el-statistic title="任务数" :value="tasks.length" /></el-card>
      <el-card shadow="never"><el-statistic title="盘点资产" :value="summary.total" /></el-card>
      <el-card shadow="never"><el-statistic title="已盘点" :value="summary.checked" /></el-card>
      <el-card shadow="never"><el-statistic title="差异项" :value="summary.abnormal" /></el-card>
    </div>

    <el-card shadow="never">
      <el-table :data="tasks" border stripe>
        <el-table-column prop="id" label="任务编号" width="140" />
        <el-table-column prop="name" label="任务名称" min-width="220" />
        <el-table-column prop="scope" label="范围类型" width="100" />
        <el-table-column prop="target" label="盘点范围" width="150" />
        <el-table-column prop="owner" label="负责人" width="110" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="taskStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="180">
          <template #default="{ row }">
            <el-progress :percentage="progress(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="abnormal" label="差异" width="80" />
        <el-table-column prop="created_at" label="创建日期" width="120" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :disabled="row.status !== '待开始'" @click="start(row)">开始</el-button>
            <el-button type="primary" link @click="openDetail(row)">盘点</el-button>
            <el-button type="success" link :disabled="!['待确认', '进行中'].includes(row.status)" @click="finish(row)">完成</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialog" title="创建盘点任务" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="范围类型">
          <el-select v-model="form.scope" style="width: 100%">
            <el-option label="全部资产" value="全部" />
            <el-option label="按部门" value="部门" />
            <el-option label="按仓库" value="仓库" />
            <el-option label="按状态" value="状态" />
          </el-select>
        </el-form-item>
        <el-form-item label="盘点范围">
          <el-input v-model="form.target" placeholder="如：研发部、上海 IT 库、in_stock；全部资产可留空" />
        </el-form-item>
        <el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" @click="createTask">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialog" :title="currentTask ? `盘点明细：${currentTask.name}` : '盘点明细'" width="1100px">
      <el-table :data="currentTask?.items || []" border stripe>
        <el-table-column prop="asset_id" label="资产ID" width="100" />
        <el-table-column prop="name" label="资产名称" min-width="160" />
        <el-table-column prop="sn" label="序列号" width="140" />
        <el-table-column prop="book_location" label="账面位置" width="160" />
        <el-table-column prop="book_status" label="账面状态" width="100" />
        <el-table-column prop="actual_location" label="实盘位置" width="160">
          <template #default="{ row }">
            <el-input v-model="row.actual_location" placeholder="实盘位置" />
          </template>
        </el-table-column>
        <el-table-column prop="result" label="结果" width="130">
          <template #default="{ row }">
            <el-select v-model="row.result">
              <el-option label="未盘" value="未盘" />
              <el-option label="正常" value="正常" />
              <el-option label="盘盈" value="盘盈" />
              <el-option label="盘亏" value="盘亏" />
              <el-option label="位置不符" value="位置不符" />
              <el-option label="状态不符" value="状态不符" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="170">
          <template #default="{ row }">
            <el-input v-model="row.remark" placeholder="备注" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="submitItem(row)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { createStocktakeTask, finishStocktakeTask, getStocktakeTasks, startStocktakeTask, submitStocktakeItem } from '../../api/stocktake'

const tasks = ref([])
const createDialog = ref(false)
const detailDialog = ref(false)
const currentTask = ref(null)
const form = reactive(defaultForm())

const summary = computed(() => tasks.value.reduce((acc, task) => {
  acc.total += task.total
  acc.checked += task.checked
  acc.abnormal += task.abnormal
  return acc
}, { total: 0, checked: 0, abnormal: 0 }))

onMounted(load)

async function load() {
  tasks.value = await getStocktakeTasks()
}

function defaultForm() {
  return {
    name: '月度资产盘点',
    scope: '全部',
    target: '',
    owner: '资产管理员'
  }
}

function openCreate() {
  Object.assign(form, defaultForm())
  createDialog.value = true
}

async function createTask() {
  await createStocktakeTask(form)
  createDialog.value = false
  ElMessage.success('盘点任务已创建')
  await load()
}

async function start(row) {
  await startStocktakeTask(row.id)
  ElMessage.success('盘点任务已开始')
  await load()
}

function openDetail(row) {
  currentTask.value = row
  detailDialog.value = true
}

async function submitItem(row) {
  if (!row.actual_location && row.result !== '盘亏') {
    ElMessage.warning('请填写实盘位置，盘亏可留空')
    return
  }
  await submitStocktakeItem(currentTask.value.id, row.asset_id, row)
  ElMessage.success('盘点结果已保存')
  await load()
}

async function finish(row) {
  await ElMessageBox.confirm(`确认完成盘点任务 ${row.id}？完成后将汇总差异结果。`, '完成盘点', { type: 'warning' })
  await finishStocktakeTask(row.id)
  ElMessage.success('盘点任务已完成')
  await load()
}

function progress(row) {
  return row.total ? Math.round((row.checked / row.total) * 100) : 0
}

function taskStatusType(status) {
  if (status === '已完成') return 'success'
  if (status === '待确认') return 'warning'
  if (status === '进行中') return 'primary'
  return 'info'
}
</script>
