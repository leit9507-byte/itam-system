<template>
  <div class="mobile-page">
    <header class="mobile-header">
      <div>
        <span class="eyebrow">ITAM Mobile</span>
        <h1>移动扫码作业</h1>
      </div>
      <div class="header-status">
        <el-tag type="success">在线</el-tag>
        <small>{{ logs.length }} 条记录</small>
      </div>
    </header>

    <section class="mobile-summary" aria-label="移动端概览">
      <div class="summary-item">
        <strong>{{ todos.length }}</strong>
        <span>待办</span>
      </div>
      <div class="summary-item">
        <strong>{{ currentSectionTitle }}</strong>
        <span>当前页面</span>
      </div>
      <div class="summary-item">
        <strong>{{ stocktakeTasks.length }}</strong>
        <span>盘点任务</span>
      </div>
    </section>

    <nav class="mobile-top-menu" aria-label="移动端菜单">
      <button v-for="item in sectionMenus" :key="item.value" type="button" class="top-menu-item" :class="{ active: activeSection === item.value }" @click="selectSection(item.value)">
        <span>{{ item.label }}</span>
        <small v-if="item.count !== undefined">{{ item.count }}</small>
      </button>
    </nav>

    <el-card v-if="activeSection === 'todo'" shadow="never" class="todo-card mobile-panel">
      <template #header>
        <div class="card-header">
          <span>待办事项</span>
          <div class="todo-actions">
            <el-button text type="primary" :loading="todoLoading" @click="loadTodos">刷新</el-button>
            <el-button text type="primary" @click="router.push('/todo')">全部</el-button>
          </div>
        </div>
      </template>
      <div v-if="mobileTodos.length" class="mobile-todo-list">
        <button v-for="item in mobileTodos" :key="item.id" type="button" class="mobile-todo-row" @click="goTodo(item)">
          <span class="todo-priority" :class="item.priority">{{ priorityLabel(item.priority) }}</span>
          <span class="todo-content">
            <strong>{{ item.title }}</strong>
            <small>{{ item.type_label }} / {{ item.status }}</small>
          </span>
        </button>
      </div>
      <el-empty v-else description="暂无待办事项" :image-size="64" />
    </el-card>
    <TodoAssetActions ref="todoAssetActionsRef" @completed="loadTodos" />

    <section v-if="activeSection === 'work'" class="mode-strip">
      <button v-for="item in workModes" :key="item.value" type="button" class="mode-card" :class="{ active: mode === item.value }" @click="selectMode(item.value)">
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
        <small>{{ item.hint }}</small>
      </button>
    </section>

    <el-card v-if="activeSection === 'stocktake'" shadow="never" class="mobile-panel">
      <template #header>
        <div class="card-header">
          <span>盘点任务</span>
          <el-button text type="primary" @click="loadStocktakeTasks">刷新</el-button>
        </div>
      </template>
      <el-select
        v-model="form.task_id"
        filterable
        remote
        reserve-keyword
        :remote-method="searchTasks"
        placeholder="搜索并选择盘点任务"
        class="mobile-select"
        style="width: 100%"
        @visible-change="visible => visible && resetTaskOptions()"
        @change="selectTask"
      >
        <el-option v-for="task in visibleStocktakeTasks" :key="task.id" :label="taskLabel(task)" :value="task.id" />
      </el-select>
      <div v-if="selectedTask" class="task-progress">
        <span>{{ selectedTask.checked || 0 }}/{{ selectedTask.total || 0 }}</span>
        <el-progress :percentage="stocktakeProgress" />
      </div>
      <p class="tip">盘点必须先在后台「资产盘点」创建任务，移动端只负责扫码执行任务明细。</p>
    </el-card>

    <el-card v-if="activeSection === 'work' || activeSection === 'stocktake'" shadow="never" class="scan-card mobile-panel">
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
          <el-button :icon="Refresh" @click="resetAsset">清空</el-button>
        </div>
        <div class="quick-codes">
          <button v-for="item in recentCodes" :key="item" type="button" @click="quickLoad(item)">{{ item }}</button>
        </div>
        <p class="tip">支持 ITAM-ASSET:ITAM-000001、资产编号、序列号或资产详情链接。</p>
      </div>
    </el-card>

    <el-card v-if="asset && (activeSection === 'work' || activeSection === 'stocktake')" shadow="never" class="asset-card mobile-panel">
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
      <div class="asset-actions">
        <el-button plain @click="copyAssetId">复制编号</el-button>
        <el-button plain @click="router.push(`/asset/detail/${asset.asset_id}`)">查看详情</el-button>
      </div>
    </el-card>

    <el-card v-if="asset && (activeSection === 'work' || activeSection === 'stocktake')" shadow="never" class="form-card mobile-panel">
      <template #header>{{ currentMode.formTitle }}</template>
      <el-form label-position="top">
        <template v-if="mode === 'stocktake'">
          <el-form-item label="盘点任务">
            <el-input :model-value="selectedTask ? `${selectedTask.name} (${selectedTask.id})` : '未选择任务'" disabled />
          </el-form-item>
          <el-alert class="inline-alert" title="扫码读取到任务内资产后，系统会按账面位置自动登记为正常；无需手动填写实盘位置。" type="success" show-icon :closable="false" />
          <el-alert v-if="currentStocktakeItem?.checked_at" class="inline-alert" :title="`该资产已登记：${currentStocktakeItem.result} / ${currentStocktakeItem.checked_at}`" type="info" show-icon :closable="false" />
        </template>

        <template v-if="mode === 'inbound'">
          <el-form-item label="入库地址">
            <el-select
              v-model="form.location"
              filterable
              remote
              clearable
              reserve-keyword
              :remote-method="searchLocations"
              placeholder="搜索入库地址"
              class="mobile-select"
              style="width: 100%"
              @visible-change="visible => visible && resetLocationOptions()"
            >
              <el-option v-for="item in visibleLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
            </el-select>
          </el-form-item>
        </template>

        <template v-if="mode === 'outbound'">
          <el-form-item label="出库对象">
            <el-segmented v-model="form.outboundTarget" :options="outboundTargetOptions" @change="changeOutboundTarget" />
          </el-form-item>
          <el-form-item label="领用人">
            <el-select v-model="form.owner_user_id" :disabled="form.outboundTarget === 'location'" filterable remote clearable reserve-keyword :remote-method="searchUsers" placeholder="搜索姓名/账号" class="mobile-select" @visible-change="visible => visible && searchUsers('')" @change="selectUser">
              <el-option v-for="user in filteredUsers" :key="user.user_id" :label="`${user.display_name} (${user.username}) / ${user.dept_name || user.dept_id || '未分部门'}`" :value="user.user_id" />
            </el-select>
          </el-form-item>
          <el-form-item :label="form.outboundTarget === 'location' ? '公用位置' : '使用位置'">
            <el-select
              v-model="form.location"
              filterable
              remote
              clearable
              reserve-keyword
              :remote-method="searchLocations"
              placeholder="搜索位置"
              class="mobile-select"
              style="width: 100%"
              @visible-change="visible => visible && resetLocationOptions()"
            >
              <el-option v-for="item in visibleLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
            </el-select>
          </el-form-item>
        </template>

        <template v-if="mode === 'repair'">
          <el-form-item label="维修日期">
            <el-date-picker v-model="form.repair_time" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="故障类型">
            <el-select
              v-model="form.fault_reason"
              filterable
              remote
              clearable
              allow-create
              default-first-option
              reserve-keyword
              :remote-method="searchFaultTypes"
              placeholder="搜索或输入故障类型"
              class="mobile-select"
              style="width: 100%"
              @visible-change="visible => visible && resetFaultTypeOptions()"
            >
              <el-option v-for="item in visibleFaultTypes" :key="item.id || item.name" :label="item.name" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="维修费用">
            <el-input-number v-model="form.repair_cost" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
          <el-form-item label="维修供应商">
            <el-input v-model="form.vendor" placeholder="可选" />
          </el-form-item>
        </template>

        <template v-if="mode === 'scrap'">
          <el-form-item label="处置方式">
            <el-select v-model="form.disposal_method" style="width: 100%">
              <el-option label="环保回收" value="环保回收" />
              <el-option label="供应商回收" value="供应商回收" />
              <el-option label="内部拆件" value="内部拆件" />
              <el-option label="销毁处理" value="销毁处理" />
            </el-select>
          </el-form-item>
          <el-form-item label="预计残值">
            <el-input-number v-model="form.estimated_residual_value" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
          <el-form-item label="报废原因">
            <el-input v-model="form.scrap_reason" type="textarea" :rows="3" placeholder="说明报废原因" />
          </el-form-item>
        </template>

        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="补充说明" />
        </el-form-item>
      </el-form>
      <div class="sticky-submit">
        <el-button type="primary" size="large" class="submit-btn" :loading="submitting" @click="submitWork">{{ currentMode.submitText }}</el-button>
      </div>
    </el-card>

    <el-card v-if="activeSection === 'logs'" shadow="never" class="log-card mobile-panel">
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Box, Camera, CircleCheck, Delete, Refresh, Search, Setting } from '@element-plus/icons-vue'
import { createRepairRecord, getRepairFaultTypes } from '../../api/repair'
import { createScrapRequest, getAssets, inboundAsset, outboundAsset } from '../../api/asset'
import { getLocations } from '../../api/location'
import { getUsers } from '../../api/user'
import { getStocktakeTasks, startStocktakeTask, submitStocktakeItem } from '../../api/stocktake'
import { getTodoItems } from '../../api/todo'
import TodoAssetActions from '../../components/TodoAssetActions.vue'
import { assetCodeCandidates, assetCodeMatches, parseAssetCode } from '../../utils/assetCode'
import { isFeishuClient, scanByFeishuSdk } from '../../utils/feishuSdk'

const router = useRouter()
const modes = [
  { value: 'stocktake', label: '扫码盘点', hint: '执行后台任务', icon: Search, formTitle: '盘点确认', submitText: '提交盘点' },
  { value: 'inbound', label: '扫码入库', hint: '归还/验收入库', icon: Box, formTitle: '入库信息', submitText: '确认入库' },
  { value: 'outbound', label: '扫码出库', hint: '关联领用人', icon: CircleCheck, formTitle: '出库信息', submitText: '确认出库' },
  { value: 'repair', label: '扫码维修', hint: '创建今日维修', icon: Setting, formTitle: '维修信息', submitText: '创建维修' },
  { value: 'scrap', label: '扫码报废', hint: '提交审批申请', icon: Delete, formTitle: '报废申请', submitText: '提交报废' }
]
const workModes = modes.filter(item => item.value !== 'stocktake')
const outboundTargetOptions = [
  { label: '人员', value: 'user' },
  { label: '位置', value: 'location' }
]

const activeSection = ref('todo')
const mode = ref('stocktake')
const assetCode = ref('')
const asset = ref(null)
const submitting = ref(false)
const users = ref([])
const filteredUsers = ref([])
const locations = ref([])
const visibleLocations = ref([])
const faultTypes = ref([])
const visibleFaultTypes = ref([])
const logs = ref([])
const todos = ref([])
const todoLoading = ref(false)
const todoAssetActionsRef = ref(null)
const stocktakeTasks = ref([])
const visibleStocktakeTasks = ref([])
const form = reactive(defaultForm())

const currentMode = computed(() => modes.find(item => item.value === mode.value) || modes[0])
const selectedTask = computed(() => stocktakeTasks.value.find(task => task.id === form.task_id))
const currentStocktakeItem = computed(() => {
  if (!selectedTask.value || !asset.value) return null
  return selectedTask.value.items.find(item => item.asset_id === asset.value.asset_id || item.sn === asset.value.sn) || null
})
const stocktakeProgress = computed(() => (selectedTask.value?.total ? Math.round((Number(selectedTask.value.checked || 0) / Number(selectedTask.value.total || 0)) * 100) : 0))
const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))
const activeFaultTypes = computed(() => faultTypes.value.filter(item => item.enabled !== '停用'))
const recentCodes = computed(() => [...new Set(logs.value.map(item => item.asset_id).filter(Boolean))].slice(0, 4))
const mobileTodos = computed(() => todos.value.slice(0, 5))
const currentSectionTitle = computed(() => {
  if (activeSection.value === 'work') return currentMode.value.label
  return ({ todo: '待办中心', stocktake: '扫码盘点', logs: '今日记录' })[activeSection.value] || '移动作业'
})
const sectionMenus = computed(() => [
  { value: 'todo', label: '待办', count: todos.value.length },
  { value: 'work', label: '扫码作业' },
  { value: 'stocktake', label: '盘点' },
  { value: 'logs', label: '记录', count: logs.value.length }
])

onMounted(async () => {
  logs.value = JSON.parse(localStorage.getItem('itam_mobile_logs') || '[]')
  const [userRows, locationRows, faultRows] = await Promise.all([
    getUsers().catch(() => []),
    getLocations().catch(() => []),
    getRepairFaultTypes().catch(() => [])
  ])
  users.value = userRows
  locations.value = locationRows
  faultTypes.value = faultRows
  filteredUsers.value = users.value.slice(0, 20)
  resetLocationOptions()
  resetFaultTypeOptions()
  await Promise.all([loadStocktakeTasks(), loadTodos()])
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
    outboundTarget: 'user',
    repair_time: new Date().toISOString().slice(0, 10),
    fault_reason: '',
    repair_cost: 0,
    vendor: '',
    disposal_method: '环保回收',
    estimated_residual_value: 0,
    scrap_reason: '',
    remark: ''
  }
}

async function loadStocktakeTasks() {
  stocktakeTasks.value = await getStocktakeTasks()
  resetTaskOptions()
  if (!form.task_id && stocktakeTasks.value.length) {
    const activeTask = stocktakeTasks.value.find(task => ['进行中', '待开始', '待确认'].includes(task.status))
    form.task_id = activeTask?.id || stocktakeTasks.value[0].id
  }
}

function taskLabel(task) {
  return `${task.name} / ${task.status} / ${task.checked || 0}/${task.total || 0}`
}

async function loadTodos() {
  todoLoading.value = true
  try {
    todos.value = await getTodoItems()
  } catch {
    todos.value = []
  } finally {
    todoLoading.value = false
  }
}

function priorityLabel(priority) {
  return ({ high: '高', medium: '中', low: '低' })[priority] || '-'
}

function selectSection(value) {
  activeSection.value = value
  if (value === 'stocktake') {
    mode.value = 'stocktake'
  } else if (value === 'work' && mode.value === 'stocktake') {
    mode.value = 'inbound'
  }
}

async function goTodo(item) {
  if (await todoAssetActionsRef.value?.handle(item)) return
  router.push({ path: item.target_path || '/todo', query: item.target_query || {} })
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

function quickLoad(code) {
  assetCode.value = code
  loadAsset()
}

async function scanCode() {
  const fromFeishu = await scanByFeishu()
  if (fromFeishu) return handleScanResult(fromFeishu)
  const fromBrowser = await scanByBrowser()
  if (fromBrowser) return handleScanResult(fromBrowser)
  ElMessage.info(isFeishuClient() ? '飞书扫码未返回内容，请确认已在飞书客户端内打开' : '当前环境暂未开放摄像头扫码，请手动输入资产编号')
}

async function scanByFeishu() {
  try {
    return await scanByFeishuSdk()
  } catch {
    if (isFeishuClient()) ElMessage.warning('飞书 JS SDK 加载失败，已切换到浏览器扫码')
    return ''
  }
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

async function loadAsset() {
  const code = parseAssetCode(assetCode.value)
  if (!code) return ElMessage.warning('请先扫码或输入资产编号')
  const candidates = assetCodeCandidates(assetCode.value)
  if (mode.value === 'stocktake') {
    if (!selectedTask.value) return ElMessage.warning('请先选择后台创建的盘点任务')
    const taskItem = selectedTask.value.items.find(item => assetCodeMatches(item, assetCode.value))
    if (!taskItem) {
      asset.value = null
      return ElMessage.error('该资产不在当前盘点任务范围内')
    }
    asset.value = taskItemToAsset(taskItem)
    form.location = taskItem.book_location || ''
    form.stocktake_result = '正常'
    ElMessage[taskItem.checked_at ? 'info' : 'success'](taskItem.checked_at ? '该资产已登记，可重新扫码确认' : '已读取盘点资产')
    return
  }
  let found = null
  for (const candidate of candidates) {
    const { list } = await getAssets({ keyword: candidate })
    found = list.find(item => assetCodeMatches(item, candidate)) || list[0]
    if (found) break
  }
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

function resetTaskOptions() {
  visibleStocktakeTasks.value = stocktakeTasks.value.slice(0, 30)
}

function searchTasks(query = '') {
  const keyword = query.trim().toLowerCase()
  visibleStocktakeTasks.value = stocktakeTasks.value
    .filter(task => !keyword || [task.id, task.name, task.status].join(' ').toLowerCase().includes(keyword))
    .slice(0, 30)
}

function resetLocationOptions() {
  visibleLocations.value = activeLocations.value.slice(0, 30)
}

function searchLocations(query = '') {
  const keyword = query.trim().toLowerCase()
  visibleLocations.value = activeLocations.value
    .filter(item => !keyword || [item.name, item.code, item.type, item.owner_dept].join(' ').toLowerCase().includes(keyword))
    .slice(0, 30)
}

function resetFaultTypeOptions() {
  visibleFaultTypes.value = activeFaultTypes.value.slice(0, 30)
}

function searchFaultTypes(query = '') {
  const keyword = query.trim().toLowerCase()
  visibleFaultTypes.value = activeFaultTypes.value
    .filter(item => !keyword || [item.name, item.description].join(' ').toLowerCase().includes(keyword))
    .slice(0, 30)
}

function selectUser(userId) {
  const user = users.value.find(item => item.user_id === userId)
  form.owner_name = user?.display_name || ''
  form.dept_id = user?.dept_id || ''
  form.dept_name = user?.dept_name || ''
}

function changeOutboundTarget(value) {
  if (value === 'location') {
    form.owner_user_id = ''
    form.owner_name = ''
    form.dept_id = ''
    form.dept_name = ''
  }
}

function locationLabel(item) {
  const meta = [item.code, item.type].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}

async function copyAssetId() {
  if (!asset.value?.asset_id) return
  await navigator.clipboard?.writeText(asset.value.asset_id).catch(() => null)
  ElMessage.success('资产编号已复制')
}

async function submitWork() {
  if (!asset.value) return ElMessage.warning('请先扫码选择资产')
  submitting.value = true
  try {
    if (mode.value === 'stocktake') await submitStocktake()
    if (mode.value === 'inbound') await submitInbound()
    if (mode.value === 'outbound') await submitOutbound()
    if (mode.value === 'repair') await submitRepair()
    if (mode.value === 'scrap') await submitScrap()
    resetAsset()
  } finally {
    submitting.value = false
  }
}

async function submitStocktake() {
  if (!selectedTask.value) return ElMessage.warning('请先选择盘点任务')
  if (!currentStocktakeItem.value) return ElMessage.error('该资产不在当前盘点任务范围内')
  if (selectedTask.value.status === '待开始') await startStocktakeTask(selectedTask.value.id)
  const saved = await submitStocktakeItem(selectedTask.value.id, asset.value.asset_id, {
    actual_location: currentStocktakeItem.value.book_location || '',
    result: '正常',
    checker: '移动端扫码',
    remark: form.remark,
    scan_raw: assetCode.value,
    parsed_code: parseAssetCode(assetCode.value),
    client_source: isFeishuClient() ? 'feishu_mobile' : 'mobile_browser'
  })
  applyStocktakeItem(saved)
  addLog('扫码盘点', `${selectedTask.value.id} / 正常`)
  ElMessage.success('扫码确认完成')
}

function taskItemToAsset(item) {
  return {
    asset_id: item.asset_id,
    name: item.name,
    sn: item.sn,
    status: item.book_status,
    location: item.book_location,
    warehouse: item.book_location,
    category: '',
    brand: '',
    model: ''
  }
}

function applyStocktakeItem(saved) {
  const task = selectedTask.value
  if (!task) return
  const item = task.items.find(row => row.asset_id === saved.asset_id)
  if (item) Object.assign(item, saved)
  task.checked = task.items.filter(row => row.result !== '未盘').length
  task.abnormal = task.items.filter(row => ['盘盈', '盘亏', '位置不符', '状态不符'].includes(row.result)).length
  if (task.status !== '已完成' && task.total && task.checked === task.total) task.status = '待确认'
  else if (task.status === '待开始') task.status = '进行中'
}

async function submitInbound() {
  const updated = await inboundAsset(asset.value.asset_id, { warehouse: form.location, location: form.location, remark: form.remark || '移动端扫码入库' })
  addLog('扫码入库', updated.location || form.location || '入库成功')
  ElMessage.success('入库成功')
}

async function submitOutbound() {
  if (form.outboundTarget === 'user' && !form.owner_user_id) return ElMessage.warning('请选择领用人')
  if (form.outboundTarget === 'location' && !form.location) return ElMessage.warning('请选择公用位置')
  const updated = await outboundAsset(asset.value.asset_id, {
    outboundTarget: form.outboundTarget,
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
  if (!form.fault_reason) return ElMessage.warning('请选择故障类型')
  await createRepairRecord(asset.value, { repair_time: form.repair_time, fault_reason: form.fault_reason, repair_cost: form.repair_cost, vendor: form.vendor, remark: form.remark || '移动端扫码报修' })
  addLog('扫码维修', form.fault_reason)
  ElMessage.success('维修单已创建')
}

async function submitScrap() {
  if (!form.scrap_reason.trim()) return ElMessage.warning('请填写报废原因')
  await createScrapRequest(asset.value.asset_id, {
    applicant: asset.value.dept_name || asset.value.dept || '移动端扫码',
    disposal_method: form.disposal_method,
    estimated_residual_value: form.estimated_residual_value,
    reason: form.scrap_reason,
    operator: '移动端扫码'
  })
  addLog('扫码报废', form.scrap_reason)
  ElMessage.success('报废申请已提交审批')
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
  return ({ pending_purchase: '待采购', pending_acceptance: '待验收', in_stock: '在库', in_use: '在用', idle: '闲置', borrowed: '借出', repair: '维修中', out_stock: '已出库', ready_scrap: '待报废', pending_scrap: '已提交报废审批', scrapped: '已报废' })[value] || value
}

function statusType(value) {
  return ({ in_stock: 'primary', in_use: 'success', idle: 'warning', borrowed: 'warning', repair: 'danger', ready_scrap: 'warning', pending_scrap: 'danger', scrapped: 'info' })[value] || 'info'
}
</script>

<style scoped>
.mobile-page {
  min-height: 100vh;
  padding: 82px 12px 24px;
  display: grid;
  align-content: start;
  gap: 14px;
  background:
    linear-gradient(180deg, #eef7f6 0, #f7fafc 220px, #f3f6fb 100%);
  color: #172033;
}

.mobile-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 14px;
  border: 1px solid rgba(15, 118, 110, 0.14);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.mobile-header h1 {
  margin: 4px 0 0;
  font-size: 23px;
  line-height: 1.2;
  letter-spacing: 0;
}

.header-status {
  display: grid;
  justify-items: end;
  gap: 5px;
  padding-top: 4px;
}

.header-status small,
.eyebrow,
.tip,
.asset-main span,
.asset-meta,
.todo-content small,
.log-item small {
  color: #64748b;
}

.eyebrow {
  font-size: 12px;
  font-weight: 800;
  color: #0f766e;
}

.mobile-summary {
  display: grid;
  grid-template-columns: 0.72fr 1.28fr 0.9fr;
  gap: 8px;
}

.summary-item {
  min-width: 0;
  padding: 12px 10px;
  border: 1px solid #e1e8f0;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.045);
  display: grid;
  gap: 3px;
}

.summary-item strong {
  min-width: 0;
  color: #102a43;
  font-size: 16px;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-item span {
  color: #64748b;
  font-size: 12px;
}

.mobile-top-menu {
  position: fixed;
  top: 8px;
  left: 10px;
  right: 10px;
  z-index: 20;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 5px;
  padding: 6px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(10px);
}

.top-menu-item {
  min-width: 0;
  min-height: 46px;
  padding: 7px 4px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  display: grid;
  place-items: center;
  gap: 2px;
}

.top-menu-item.active {
  border-color: rgba(15, 118, 110, 0.22);
  background: #0f766e;
  color: #fff;
  box-shadow: 0 8px 18px rgba(15, 118, 110, 0.22);
}

.top-menu-item small {
  min-width: 20px;
  height: 16px;
  padding: 0 5px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
  font-size: 11px;
  line-height: 16px;
}

.top-menu-item.active small {
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
}

.mode-strip {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 1px 1px 6px;
  scroll-snap-type: x proximity;
}

.mode-strip::-webkit-scrollbar,
.quick-codes::-webkit-scrollbar,
.mobile-top-menu::-webkit-scrollbar {
  display: none;
}

.mode-card {
  flex: 0 0 128px;
  min-height: 92px;
  padding: 12px;
  border: 1px solid #dfe8ee;
  border-radius: 8px;
  background: #ffffff;
  text-align: left;
  display: grid;
  gap: 6px;
  scroll-snap-align: start;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.045);
}

.mode-card.active {
  border-color: rgba(15, 118, 110, 0.34);
  background: #f0fdfa;
  box-shadow: 0 12px 26px rgba(15, 118, 110, 0.14);
}

.mode-card .el-icon {
  font-size: 22px;
  color: #0f766e;
}

.mode-card span {
  font-weight: 700;
}

.card-header,
.scan-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.card-header {
  font-weight: 800;
  color: #172033;
}

.scan-actions {
  flex-shrink: 0;
}

.todo-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.todo-card :deep(.el-card__body) {
  padding-top: 10px;
}

.mobile-panel {
  overflow: hidden;
}

.task-progress {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.inline-alert {
  margin-bottom: 12px;
}

.mobile-todo-list {
  display: grid;
  gap: 8px;
}

.mobile-todo-row {
  width: 100%;
  min-width: 0;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 11px;
  border: 1px solid #e0e9f2;
  border-radius: 8px;
  background: #ffffff;
  text-align: left;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.035);
}

.todo-priority {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 12px;
  font-weight: 800;
}

.todo-priority.high {
  background: #fee2e2;
  color: #b91c1c;
}

.todo-priority.medium {
  background: #fef3c7;
  color: #92400e;
}

.todo-priority.low {
  background: #dcfce7;
  color: #166534;
}

.todo-content {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.todo-content strong,
.todo-content small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scan-box,
.asset-main,
.asset-meta,
.log-list,
.log-item {
  display: grid;
  gap: 10px;
}

.quick-codes {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.quick-codes button,
.quick-codes .el-button {
  flex: 0 0 auto;
}

.quick-codes button {
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid #dbe5ef;
  border-radius: 999px;
  background: #fff;
  color: #334155;
  font-size: 12px;
}

.asset-main {
  gap: 4px;
  margin-bottom: 10px;
}

.asset-main strong {
  font-size: 20px;
  line-height: 1.25;
}

.asset-meta {
  gap: 6px;
  font-size: 13px;
}

.asset-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.sticky-submit {
  position: sticky;
  bottom: 0;
  z-index: 2;
  padding-top: 10px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0), #fff 38%);
}

.submit-btn {
  width: 100%;
}

.log-item {
  gap: 3px;
  padding: 10px;
  border: 1px solid #e0e9f2;
  border-radius: 8px;
  background: #fff;
}

:deep(.el-card) {
  border-radius: 8px;
  border-color: #e0e9f2;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
}

:deep(.el-card__header) {
  padding: 13px 14px;
  border-bottom-color: #edf2f7;
}

:deep(.el-card__body) {
  padding: 14px;
}

:deep(.el-button) {
  border-radius: 8px;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper),
:deep(.el-textarea__inner) {
  border-radius: 8px;
}

:deep(.mobile-select .el-select__wrapper) {
  min-height: 44px;
}

:deep(.el-form-item) {
  margin-bottom: 14px;
}

:deep(.el-segmented) {
  width: 100%;
}

:deep(.el-segmented__item) {
  flex: 1;
}

@media (min-width: 760px) {
  .mobile-page {
    max-width: 560px;
    margin: 0 auto;
  }

  .mobile-top-menu {
    left: 50%;
    right: auto;
    width: 536px;
    transform: translateX(-50%);
  }
}

@media (max-width: 380px) {
  .mobile-top-menu {
    display: flex;
    overflow-x: auto;
    scroll-snap-type: x proximity;
  }

  .top-menu-item {
    flex: 0 0 76px;
    scroll-snap-align: start;
  }
}
</style>
