<template>
  <div class="mobile-page">
    <header class="mobile-header">
      <div>
        <span class="eyebrow">ITAM Mobile</span>
        <h1>移动扫码作业</h1>
      </div>
      <el-tag type="success">在线</el-tag>
    </header>

    <section class="mode-grid">
      <button v-for="item in modes" :key="item.value" type="button" class="mode-card" :class="{ active: mode === item.value }" @click="selectMode(item.value)">
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
        <small>{{ item.hint }}</small>
      </button>
    </section>

    <el-card v-if="mode === 'stocktake'" shadow="never">
      <template #header>
        <div class="card-header">
          <span>盘点任务</span>
          <el-button text type="primary" @click="loadStocktakeTasks">刷新</el-button>
        </div>
      </template>
      <el-select v-model="form.task_id" placeholder="请选择后台创建的盘点任务" style="width: 100%" @change="selectTask">
        <el-option v-for="task in stocktakeTasks" :key="task.id" :label="`${task.name} / ${task.status} / ${task.checked || 0}/${task.total || 0}`" :value="task.id" />
      </el-select>
      <p class="tip">盘点必须先在后台「资产盘点」创建任务，移动端只负责扫码执行任务明细。</p>
    </el-card>

    <el-card shadow="never" class="scan-card">
      <template #header>
        <div class="card-header">
          <span>{{ currentMode.label }}</span>
          <el-button text type="primary" @click="resetAsset">重新选择</el-button>
        </div>
      </template>

      <div class="scan-box">
        <el-input v-model="assetCode" clearable placeholder="扫码或输入资产编号 / 二维码内容" @keyup.enter="loadAsset">
          <template #append>
            <el-button @click="loadAsset">查询</el-button>
          </template>
        </el-input>
        <div class="scan-actions">
          <el-button type="primary" :icon="Camera" @click="scanCode">扫码</el-button>
          <el-button @click="fillExample">示例</el-button>
        </div>
        <p class="tip">支持二维码内容：ITAM-ASSET:ITAM-000001，或直接使用资产编号。</p>
      </div>
    </el-card>

    <el-card v-if="asset" shadow="never" class="asset-card">
      <template #header>
        <div class="card-header">
          <span>资产信息</span>
          <el-tag :type="statusType(asset.status)">{{ statusLabel(asset.status) }}</el-tag>
        </div>
      </template>
      <div class="asset-main">
        <strong>{{ asset.name }}</strong>
        <span>{{ asset.asset_id }}</span>
      </div>
      <div class="asset-meta">
        <span>序列号：{{ asset.sn || '-' }}</span>
        <span>类型：{{ asset.category || '-' }}</span>
        <span>型号：{{ asset.brand || '-' }} {{ asset.model || '' }}</span>
        <span>责任人：{{ asset.owner_name || asset.owner || '未分配' }}</span>
        <span>部门：{{ asset.dept_name || asset.dept || '未绑定' }}</span>
        <span>位置：{{ asset.location || asset.warehouse || '-' }}</span>
      </div>
    </el-card>

    <el-card v-if="asset" shadow="never" class="form-card">
      <template #header>{{ currentMode.formTitle }}</template>
      <el-form label-position="top">
        <template v-if="mode === 'stocktake'">
          <el-form-item label="盘点任务">
            <el-input :model-value="selectedTask ? `${selectedTask.name} (${selectedTask.id})` : '未选择任务'" disabled />
          </el-form-item>
          <el-form-item label="盘点结果">
            <el-segmented v-model="form.stocktake_result" :options="['正常', '盘盈', '盘亏', '位置不符', '状态不符']" />
          </el-form-item>
          <el-form-item label="实际位置">
            <el-input v-model="form.location" placeholder="例如：上海IT仓 / 工位 A-12" />
          </el-form-item>
        </template>

        <template v-if="mode === 'inbound'">
          <el-form-item label="入库仓库">
            <el-input v-model="form.location" placeholder="例如：上海IT仓" />
          </el-form-item>
        </template>

        <template v-if="mode === 'outbound'">
          <el-form-item label="领用人">
            <el-select v-model="form.owner_user_id" filterable remote clearable reserve-keyword :remote-method="searchUsers" placeholder="搜索姓名/账号" @change="selectUser">
              <el-option v-for="user in filteredUsers" :key="user.user_id" :label="`${user.display_name} (${user.username}) / ${user.dept_name || user.dept_id || '未分部门'}`" :value="user.user_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="使用位置">
            <el-input v-model="form.location" placeholder="例如：研发中心 5F" />
          </el-form-item>
        </template>

        <template v-if="mode === 'repair'">
          <el-form-item label="维修日期">
            <el-date-picker v-model="form.repair_time" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="故障原因">
            <el-input v-model="form.fault_reason" placeholder="例如：无法开机、屏幕损坏" />
          </el-form-item>
          <el-form-item label="维修费用">
            <el-input-number v-model="form.repair_cost" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
          <el-form-item label="维修供应商">
            <el-input v-model="form.vendor" placeholder="可选" />
          </el-form-item>
        </template>

        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="补充说明" />
        </el-form-item>
      </el-form>
      <el-button type="primary" size="large" class="submit-btn" :loading="submitting" @click="submitWork">{{ currentMode.submitText }}</el-button>
    </el-card>

    <el-card shadow="never" class="log-card">
      <template #header>
        <div class="card-header">
          <span>今日操作</span>
          <el-button text type="primary" @click="clearLogs">清空</el-button>
        </div>
      </template>
      <el-empty v-if="!logs.length" description="暂无扫码操作记录" />
      <div v-else class="log-list">
        <div v-for="item in logs" :key="item.id" class="log-item">
          <strong>{{ item.action }}</strong>
          <span>{{ item.asset_id }} / {{ item.asset_name }}</span>
          <small>{{ item.time }} - {{ item.remark || '操作成功' }}</small>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Box, Camera, CircleCheck, Search, Setting } from '@element-plus/icons-vue'
import { createRepairRecord } from '../../api/repair'
import { getAssets, inboundAsset, outboundAsset } from '../../api/asset'
import { getUsers } from '../../api/user'
import { getStocktakeTasks, startStocktakeTask, submitStocktakeItem } from '../../api/stocktake'

const modes = [
  { value: 'stocktake', label: '扫码盘点', hint: '执行后台任务', icon: Search, formTitle: '盘点确认', submitText: '提交盘点' },
  { value: 'inbound', label: '扫码入库', hint: '归还/验收入库', icon: Box, formTitle: '入库信息', submitText: '确认入库' },
  { value: 'outbound', label: '扫码出库', hint: '关联领用人', icon: CircleCheck, formTitle: '出库信息', submitText: '确认出库' },
  { value: 'repair', label: '扫码维修', hint: '创建今日维修', icon: Setting, formTitle: '维修信息', submitText: '创建维修' }
]

const mode = ref('stocktake')
const assetCode = ref('')
const asset = ref(null)
const submitting = ref(false)
const users = ref([])
const filteredUsers = ref([])
const logs = ref([])
const stocktakeTasks = ref([])
const form = reactive(defaultForm())

const currentMode = computed(() => modes.find(item => item.value === mode.value) || modes[0])
const selectedTask = computed(() => stocktakeTasks.value.find(task => task.id === form.task_id))

onMounted(async () => {
  logs.value = JSON.parse(localStorage.getItem('itam_mobile_logs') || '[]')
  users.value = await getUsers().catch(() => [])
  filteredUsers.value = users.value.slice(0, 20)
  await loadStocktakeTasks()
})

function defaultForm() {
  return {
    task_id: '',
    stocktake_result: '正常',
    location: '',
    owner_user_id: '',
    owner_name: '',
    dept_id: '',
    dept_name: '',
    repair_time: new Date().toISOString().slice(0, 10),
    fault_reason: '',
    repair_cost: 0,
    vendor: '',
    remark: ''
  }
}

async function loadStocktakeTasks() {
  stocktakeTasks.value = await getStocktakeTasks()
  if (!form.task_id && stocktakeTasks.value.length) {
    const activeTask = stocktakeTasks.value.find(task => ['进行中', '待开始', '待确认'].includes(task.status))
    form.task_id = activeTask?.id || stocktakeTasks.value[0].id
  }
}

function selectTask() {
  resetAsset()
}

function selectMode(value) {
  mode.value = value
  const taskId = form.task_id
  Object.assign(form, defaultForm(), { task_id: taskId })
}

function fillExample() {
  assetCode.value = 'ITAM-000001'
  loadAsset()
}

async function scanCode() {
  const fromFeishu = await scanByFeishu()
  if (fromFeishu) return handleScanResult(fromFeishu)
  const fromBrowser = await scanByBrowser()
  if (fromBrowser) return handleScanResult(fromBrowser)
  ElMessage.info('当前环境暂未开放摄像头扫码，请手动输入资产编号')
}

function scanByFeishu() {
  return new Promise(resolve => {
    const tt = window.tt || window.lark || null
    if (!tt?.scanCode) return resolve('')
    tt.scanCode({ success: res => resolve(res?.result || res?.text || ''), fail: () => resolve('') })
  })
}

async function scanByBrowser() {
  if (!('BarcodeDetector' in window) || !navigator.mediaDevices?.getUserMedia) return ''
  let stream
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
    const video = document.createElement('video')
    video.srcObject = stream
    video.muted = true
    await video.play()
    const detector = new window.BarcodeDetector({ formats: ['qr_code', 'code_128'] })
    const deadline = Date.now() + 8000
    while (Date.now() < deadline) {
      const codes = await detector.detect(video)
      if (codes.length) return codes[0].rawValue
      await new Promise(resolve => setTimeout(resolve, 300))
    }
  } catch {
    return ''
  } finally {
    stream?.getTracks().forEach(track => track.stop())
  }
  return ''
}

function handleScanResult(value) {
  assetCode.value = parseAssetCode(value)
  loadAsset()
}

function parseAssetCode(value) {
  const text = String(value || '').trim()
  if (!text) return ''
  if (text.includes('ITAM-ASSET:')) return text.split('ITAM-ASSET:').pop().trim()
  try {
    const url = new URL(text)
    return url.searchParams.get('asset_id') || url.pathname.split('/').filter(Boolean).pop() || text
  } catch {
    return text
  }
}

async function loadAsset() {
  const code = parseAssetCode(assetCode.value)
  if (!code) return ElMessage.warning('请先扫码或输入资产编号')
  if (mode.value === 'stocktake') {
    if (!selectedTask.value) return ElMessage.warning('请先选择后台创建的盘点任务')
    const taskItem = selectedTask.value.items.find(item => item.asset_id === code || item.sn === code)
    if (!taskItem) {
      asset.value = null
      return ElMessage.error('该资产不在当前盘点任务范围内')
    }
  }
  const { list } = await getAssets({ keyword: code })
  const found = list.find(item => item.asset_id === code || item.sn === code) || list[0]
  if (!found) {
    asset.value = null
    return ElMessage.error('未找到资产')
  }
  asset.value = found
  form.location = found.location || found.warehouse || ''
  ElMessage.success('已读取资产信息')
}

function resetAsset() {
  asset.value = null
  assetCode.value = ''
}

function searchUsers(query = '') {
  const keyword = query.trim().toLowerCase()
  filteredUsers.value = users.value
    .filter(user => !keyword || [user.user_id, user.username, user.display_name, user.dept_name, user.dept_id].join(' ').toLowerCase().includes(keyword))
    .slice(0, 30)
}

function selectUser(userId) {
  const user = users.value.find(item => item.user_id === userId)
  form.owner_name = user?.display_name || ''
  form.dept_id = user?.dept_id || ''
  form.dept_name = user?.dept_name || ''
}

async function submitWork() {
  if (!asset.value) return ElMessage.warning('请先扫码选择资产')
  submitting.value = true
  try {
    if (mode.value === 'stocktake') await submitStocktake()
    if (mode.value === 'inbound') await submitInbound()
    if (mode.value === 'outbound') await submitOutbound()
    if (mode.value === 'repair') await submitRepair()
    resetAsset()
  } finally {
    submitting.value = false
  }
}

async function submitStocktake() {
  if (!selectedTask.value) return ElMessage.warning('请先选择盘点任务')
  if (selectedTask.value.status === '待开始') await startStocktakeTask(selectedTask.value.id)
  await submitStocktakeItem(selectedTask.value.id, asset.value.asset_id, {
    actual_location: form.location,
    result: form.stocktake_result,
    checker: '移动端扫码',
    remark: form.remark
  })
  addLog('扫码盘点', `${selectedTask.value.id} / ${form.stocktake_result}`)
  await loadStocktakeTasks()
  ElMessage.success('盘点结果已提交到任务明细')
}

async function submitInbound() {
  const updated = await inboundAsset(asset.value.asset_id, { warehouse: form.location, location: form.location, remark: form.remark || '移动端扫码入库' })
  addLog('扫码入库', updated.location || form.location || '入库成功')
  ElMessage.success('入库成功')
}

async function submitOutbound() {
  if (!form.owner_user_id) return ElMessage.warning('请选择领用人')
  const updated = await outboundAsset(asset.value.asset_id, {
    owner_user_id: form.owner_user_id,
    owner_name: form.owner_name,
    dept_id: form.dept_id,
    dept_name: form.dept_name,
    location: form.location,
    remark: form.remark || '移动端扫码出库'
  })
  addLog('扫码出库', `${updated.owner_name || form.owner_name} / ${updated.dept_name || form.dept_name}`)
  ElMessage.success('出库成功')
}

async function submitRepair() {
  if (!form.fault_reason) return ElMessage.warning('请填写故障原因')
  await createRepairRecord(asset.value, { repair_time: form.repair_time, fault_reason: form.fault_reason, repair_cost: form.repair_cost, vendor: form.vendor, remark: form.remark || '移动端扫码报修' })
  addLog('扫码维修', form.fault_reason)
  ElMessage.success('维修单已创建')
}

function addLog(action, remark) {
  logs.value.unshift({ id: `${Date.now()}-${Math.random()}`, action, asset_id: asset.value.asset_id, asset_name: asset.value.name, remark, time: new Date().toLocaleString('zh-CN', { hour12: false }) })
  logs.value = logs.value.slice(0, 30)
  localStorage.setItem('itam_mobile_logs', JSON.stringify(logs.value))
}

async function clearLogs() {
  const confirmed = await ElMessageBox.confirm('确认清空移动端今日操作记录？', '提示', { type: 'warning' }).then(() => true).catch(() => false)
  if (!confirmed) return
  logs.value = []
  localStorage.removeItem('itam_mobile_logs')
}

function statusLabel(value) {
  return ({ pending_purchase: '待采购', pending_acceptance: '待验收', in_stock: '在库', in_use: '在用', idle: '闲置', borrowed: '借出', repair: '维修中', out_stock: '已出库', pending_scrap: '待报废', scrapped: '已报废' })[value] || value
}

function statusType(value) {
  return ({ in_stock: 'primary', in_use: 'success', idle: 'warning', borrowed: 'warning', repair: 'danger', pending_scrap: 'warning', scrapped: 'info' })[value] || 'info'
}
</script>

<style scoped>
.mobile-page { min-height: 100vh; padding: 14px; display: grid; gap: 12px; background: #f4f7f6; }
.mobile-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 2px; }
.mobile-header h1 { margin: 4px 0 0; font-size: 24px; }
.eyebrow, .tip, .asset-main span, .asset-meta, .log-item small { color: #64748b; }
.mode-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.mode-card { min-height: 104px; padding: 14px; border: 1px solid #d9e2df; border-radius: 8px; background: #fff; text-align: left; display: grid; gap: 6px; }
.mode-card.active { border-color: #0f766e; box-shadow: 0 8px 24px rgba(15, 118, 110, 0.14); }
.mode-card .el-icon { font-size: 22px; color: #0f766e; }
.mode-card span { font-weight: 700; }
.card-header, .scan-actions { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.scan-box, .asset-main, .asset-meta, .log-list, .log-item { display: grid; gap: 10px; }
.asset-main { gap: 4px; margin-bottom: 10px; }
.asset-main strong { font-size: 20px; }
.asset-meta { gap: 6px; font-size: 13px; }
.submit-btn { width: 100%; }
.log-item { gap: 3px; padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; }
@media (min-width: 760px) { .mobile-page { max-width: 560px; margin: 0 auto; } }
</style>
