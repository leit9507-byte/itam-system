<template>
  <div class="mobile-page">
    <header v-if="showMobileAppbar" class="mobile-appbar">
      <button type="button" class="appbar-icon" @click="router.back()">&lt;</button>
      <strong>ITAM Dashboard</strong>
      <button type="button" class="appbar-icon appbar-dot" @click="selectSection('logs')">...</button>
    </header>

    <section class="mobile-hero">
      <div>
        <span class="eyebrow">{{ currentSectionTitle }}</span>
        <h1>{{ activeSection === 'work' || activeSection === 'stocktake' ? currentMode.label : '移动作业' }}</h1>
        <p>{{ sectionSubtitle }}</p>
      </div>
      <div class="hero-stats">
        <span><strong>{{ todos.length }}</strong>待办</span>
        <span><strong>{{ logs.length }}</strong>记录</span>
      </div>
    </section>

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
    <TodoAssetActions ref="todoAssetActionsRef" mobile @completed="loadTodos" />

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
        class="mobile-select" popper-class="mobile-select-popper"
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
      <p class="tip">盘点必须先在后台“资产盘点”创建并开启任务，移动端只负责扫码执行任务明细。</p>
    </el-card>

    <el-card v-if="activeSection === 'work' || activeSection === 'stocktake'" shadow="never" class="scan-card mobile-panel">
      <template #header>
        <div class="card-header">
          <span>{{ currentMode.label }}</span>
          <el-button text type="primary" @click="resetAsset">重新选择</el-button>
        </div>
      </template>

      <div class="scan-box">
        <div class="scan-searchbar">
          <button type="button" class="scan-trigger" aria-label="扫码" @click="scanCode">
            <el-icon><Camera /></el-icon>
          </button>
          <el-input
            v-model="assetCode"
            class="scan-inline-input"
            clearable
            placeholder="扫码识别或输入资产编号"
            @keyup.enter="loadAsset"
          />
          <el-button type="primary" class="scan-query-btn" @click="loadAsset">查询</el-button>
        </div>
        <el-alert
          v-if="showScanRuntimeHint"
          class="scan-runtime-alert"
          :title="scanRuntimeTitle"
          :description="scanRuntimeDescription"
          :type="scanRuntimeStatus.hasScanCode ? 'success' : scanRuntimeStatus.isFeishu ? 'warning' : 'info'"
          show-icon
          :closable="false"
        />
        <el-alert
          v-if="scanRuntimeError"
          class="scan-runtime-alert"
          title="飞书扫码调用失败"
          :description="scanRuntimeError"
          type="error"
          show-icon
          :closable="false"
        />
        <div class="quick-codes">
          <button v-for="item in recentCodes" :key="item" type="button" @click="quickLoad(item)">{{ item }}</button>
        </div>
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
        <div>
          <strong>{{ asset.name }}</strong>
          <span>{{ asset.asset_id }}</span>
        </div>
        <el-button text type="primary" @click="copyAssetId">复制</el-button>
      </div>
      <div class="asset-meta">
        <span>责任人：{{ asset.owner_name || asset.owner || '未分配' }}</span>
        <span>位置：{{ asset.location || asset.warehouse || '-' }}</span>
        <span>SN：{{ asset.sn || '-' }}</span>
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
              class="mobile-select" popper-class="mobile-select-popper"
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
            <el-select v-model="form.owner_user_id" :disabled="form.outboundTarget === 'location'" filterable remote clearable reserve-keyword :remote-method="searchUsers" placeholder="搜索姓名/账号" class="mobile-select" popper-class="mobile-select-popper" @visible-change="visible => visible && searchUsers('')" @change="selectUser">
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
              class="mobile-select" popper-class="mobile-select-popper"
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
              class="mobile-select" popper-class="mobile-select-popper"
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

        <template v-if="mode === 'bind'">
          <el-alert class="inline-alert" title="先确认上方资产，再读取二维码内容。二维码内容可手动编辑，提交后后续扫码会按这段内容识别当前资产。" type="info" show-icon :closable="false" />
          <el-form-item label="二维码内容">
            <el-input v-model="bindingForm.scan_raw" type="textarea" :rows="3" placeholder="扫描二维码后自动填入，也可以手动输入或修改二维码生成内容" />
          </el-form-item>
          <div class="binding-actions">
            <el-button type="primary" :icon="Camera" @click="scanBindingRaw">读取二维码</el-button>
            <el-button :icon="Refresh" @click="bindingForm.scan_raw = ''">清空内容</el-button>
          </div>
          <div v-if="bindingForm.scan_raw" class="qr-confirm-box">
            <span>将把以下二维码内容绑定到资产</span>
            <strong>{{ asset.asset_id }} / {{ asset.name }}</strong>
          </div>
          <el-form-item label="重新绑定">
            <el-switch v-model="bindingForm.force" active-text="允许覆盖已绑定资产" />
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

    <nav class="mobile-bottom-menu" aria-label="移动端菜单">
      <button v-for="item in sectionMenus" :key="item.value" type="button" class="bottom-menu-item" :class="{ active: activeSection === item.value }" @click="selectSection(item.value)">
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
        <small v-if="item.count !== undefined">{{ item.count }}</small>
      </button>
    </nav>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Box, Camera, CircleCheck, Delete, FolderOpened, HomeFilled, Refresh, Search, Setting, UserFilled } from '@element-plus/icons-vue'
import { createRepairRecord, getRepairFaultTypes } from '../../api/repair'
import { createScrapRequest, getAssets, inboundAsset, outboundAsset } from '../../api/asset'
import { getLocations } from '../../api/location'
import { getUsers } from '../../api/user'
import { getStocktakeTasks, submitStocktakeItem } from '../../api/stocktake'
import { getTodoItems } from '../../api/todo'
import { bindAssetScanCode, resolveScanBinding } from '../../api/scanBinding'
import TodoAssetActions from '../../components/TodoAssetActions.vue'
import { assetCodeCandidates, assetCodeMatches, parseAssetCode } from '../../utils/assetCode'
import { feishuRuntimeStatus, getLastFeishuScanError, isFeishuClient, scanByFeishuSdk } from '../../utils/feishuSdk'

const router = useRouter()
const SCAN_CANCELLED = Symbol('scan-cancelled')
const modes = [
  { value: 'stocktake', label: '扫码盘点', hint: '执行后台任务', icon: Search, formTitle: '盘点确认', submitText: '提交盘点' },
  { value: 'inbound', label: '扫码入库', hint: '归还/验收入库', icon: Box, formTitle: '入库信息', submitText: '确认入库' },
  { value: 'outbound', label: '扫码出库', hint: '关联领用人', icon: CircleCheck, formTitle: '出库信息', submitText: '确认出库' },
  { value: 'repair', label: '扫码维修', hint: '创建今日维修', icon: Setting, formTitle: '维修信息', submitText: '创建维修' },
  { value: 'scrap', label: '扫码报废', hint: '提交审批申请', icon: Delete, formTitle: '报废申请', submitText: '提交报废' },
  { value: 'bind', label: '二维码绑定', hint: '确认二维码内容', icon: Search, formTitle: '二维码绑定', submitText: '确认绑定' }
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
const scanRuntimeStatus = ref(feishuRuntimeStatus())
const scanRuntimeError = ref('')
const showMobileAppbar = computed(() => !scanRuntimeStatus.value.isFeishu)
const form = reactive(defaultForm())
const bindingForm = reactive(defaultBindingForm())

const OPEN_STOCKTAKE_STATUSES = ['进行中']
const INBOUND_ALLOWED_STATUSES = ['in_use', 'borrowed', 'out_stock', 'repair']
const OUTBOUND_ALLOWED_STATUSES = ['in_stock', 'idle']
const activeStocktakeTasks = computed(() => stocktakeTasks.value.filter(task => OPEN_STOCKTAKE_STATUSES.includes(task.status)))
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
const sectionSubtitle = computed(() => {
  if (activeSection.value === 'todo') return '处理入职分配、离职回收和审批待办。'
  if (activeSection.value === 'stocktake') return '选择后台盘点任务后，现场扫码确认资产。'
  if (activeSection.value === 'logs') return '查看本机今日扫码作业记录。'
  return `${currentMode.value.hint}，扫码后按表单确认提交。`
})
const scanRuntimeTitle = computed(() => {
  if (scanRuntimeStatus.value.hasScanCode) return '飞书扫码能力已就绪'
  if (scanRuntimeStatus.value.hasH5Sdk) return '飞书 H5 SDK 已加载，等待扫码能力'
  if (scanRuntimeStatus.value.isFeishu) return '已在飞书内打开，正在加载 H5 SDK'
  return '当前不是飞书客户端环境'
})
const scanRuntimeDescription = computed(() => {
  if (scanRuntimeStatus.value.hasScanCode) return '已连接飞书原生扫码。'
  if (scanRuntimeStatus.value.hasH5Sdk) return '请检查 HTTPS、安全域名和应用发布。'
  if (scanRuntimeStatus.value.isFeishu) return '正在等待飞书扫码能力。'
  return '可手动输入资产编号。'
})
const showScanRuntimeHint = computed(() => scanRuntimeError.value || !scanRuntimeStatus.value.hasScanCode)
const sectionMenus = computed(() => [
  { value: 'todo', label: '首页', count: todos.value.length, icon: HomeFilled },
  { value: 'work', label: '扫码', icon: Search },
  { value: 'stocktake', label: '资产', icon: FolderOpened },
  { value: 'logs', label: '我的', count: logs.value.length, icon: UserFilled }
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

function defaultBindingForm() {
  return {
    scan_raw: '',
    scan_type: 'qrcode',
    force: false
  }
}

async function loadStocktakeTasks() {
  stocktakeTasks.value = await getStocktakeTasks()
  resetTaskOptions()
  if (!activeStocktakeTasks.value.some(task => task.id === form.task_id)) {
    form.task_id = activeStocktakeTasks.value[0]?.id || ''
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
  Object.assign(bindingForm, defaultBindingForm())
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
  refreshScanRuntime()
  scanRuntimeError.value = ''
  const fromFeishu = await scanByFeishu()
  refreshScanRuntime()
  if (fromFeishu === SCAN_CANCELLED) {
    scanRuntimeError.value = ''
    return
  }
  if (fromFeishu) return handleScanResult(fromFeishu)
  const fromBrowser = await scanByBrowser()
  if (fromBrowser) return handleScanResult(fromBrowser)
  ElMessage.info(isFeishuClient() ? '飞书扫码未返回内容，请确认已在飞书客户端内打开' : '当前环境暂未开放摄像头扫码，请手动输入资产编号')
}

async function scanBindingRaw() {
  refreshScanRuntime()
  scanRuntimeError.value = ''
  const fromFeishu = await scanByFeishu()
  refreshScanRuntime()
  if (fromFeishu === SCAN_CANCELLED) {
    scanRuntimeError.value = ''
    return
  }
  if (fromFeishu) {
    bindingForm.scan_raw = fromFeishu
    return ElMessage.success('已读取二维码内容')
  }
  const fromBrowser = await scanByBrowser()
  if (fromBrowser) {
    bindingForm.scan_raw = fromBrowser
    return ElMessage.success('已读取二维码内容')
  }
  ElMessage.info(isFeishuClient() ? '飞书扫码未返回内容，请确认已在飞书客户端内打开' : '当前环境暂未开放摄像头扫码，请手动输入二维码内容')
}

function refreshScanRuntime() {
  scanRuntimeStatus.value = feishuRuntimeStatus()
  scanRuntimeError.value = getLastFeishuScanError()
}

async function scanByFeishu() {
  try {
    const result = await scanByFeishuSdk()
    const lastError = getLastFeishuScanError()
    if (!result && isScanCancelError(lastError)) {
      scanRuntimeError.value = ''
      ElMessage.info('已取消扫码')
      return SCAN_CANCELLED
    }
    return result
  } catch (error) {
    if (isScanCancelError(error)) {
      scanRuntimeError.value = ''
      ElMessage.info('已取消扫码')
      return SCAN_CANCELLED
    }
    scanRuntimeError.value = error?.message || String(error || '')
    if (isFeishuClient()) ElMessage.warning('飞书 JSAPI 鉴权失败，已切换到浏览器扫码')
    return ''
  }
}

function isScanCancelError(error) {
  if (!error) return false
  const text = typeof error === 'string'
    ? error
    : [error.errString, error.errMsg, error.message, error.errno, error.errCode, error.errorCode].filter(Boolean).join(' ')
  return /User canceled scanning|scanCode:fail cancel|cancelled|canceled|cancel/i.test(text) ||
    text.includes('1505002') ||
    text.includes('102')
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
  const resolvedAsset = await resolveAssetFromScan(assetCode.value)
  const candidates = assetCodeCandidates(assetCode.value)
  if (mode.value === 'stocktake') {
    if (!selectedTask.value) return ElMessage.warning('请先选择后台创建的盘点任务')
    const taskItem = resolvedAsset
      ? selectedTask.value.items.find(item => item.asset_id === resolvedAsset.asset_id)
      : selectedTask.value.items.find(item => assetCodeMatches(item, assetCode.value))
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
  if (resolvedAsset) {
    asset.value = resolvedAsset
    form.location = resolvedAsset.location || resolvedAsset.warehouse || ''
    ElMessage.success('已通过二维码内容识别资产')
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

async function resolveAssetFromScan(value) {
  try {
    const result = await resolveScanBinding(value)
    return result?.bound ? result.asset : null
  } catch {
    return null
  }
}

function resetAsset() {
  asset.value = null
  assetCode.value = ''
  Object.assign(bindingForm, defaultBindingForm())
}

function searchUsers(query = '') {
  const keyword = query.trim().toLowerCase()
  filteredUsers.value = users.value
    .filter(user => !keyword || [user.user_id, user.username, user.display_name, user.dept_name, user.dept_id].join(' ').toLowerCase().includes(keyword))
    .slice(0, 30)
}

function resetTaskOptions() {
  visibleStocktakeTasks.value = activeStocktakeTasks.value.slice(0, 30)
}

function searchTasks(query = '') {
  const keyword = query.trim().toLowerCase()
  visibleStocktakeTasks.value = activeStocktakeTasks.value
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
  if (mode.value === 'bind' && !bindingForm.scan_raw.trim()) return ElMessage.warning('请先扫描或输入需要绑定的二维码内容')
  submitting.value = true
  try {
    if (mode.value === 'stocktake') await submitStocktake()
    if (mode.value === 'inbound') await submitInbound()
    if (mode.value === 'outbound') await submitOutbound()
    if (mode.value === 'repair') await submitRepair()
    if (mode.value === 'scrap') await submitScrap()
    if (mode.value === 'bind') await submitScanBinding()
    resetAsset()
  } finally {
    submitting.value = false
  }
}

async function submitStocktake() {
  if (selectedTask.value && !OPEN_STOCKTAKE_STATUSES.includes(selectedTask.value.status)) return ElMessage.warning('移动端只能执行已开启的盘点任务')
  if (!selectedTask.value) return ElMessage.warning('请先选择盘点任务')
  if (!currentStocktakeItem.value) return ElMessage.error('该资产不在当前盘点任务范围内')
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
  if (!INBOUND_ALLOWED_STATUSES.includes(asset.value?.status)) {
    return ElMessage.warning(`当前状态为 ${statusLabel(asset.value?.status)}，不能重复入库`)
  }
  const updated = await inboundAsset(asset.value.asset_id, { warehouse: form.location, location: form.location, remark: form.remark || '移动端扫码入库' })
  addLog('扫码入库', updated.location || form.location || '入库成功')
  ElMessage.success('入库成功')
}

async function submitOutbound() {
  if (!OUTBOUND_ALLOWED_STATUSES.includes(asset.value?.status)) {
    return ElMessage.warning(`当前状态为 ${statusLabel(asset.value?.status)}，不能重复出库；请先归还入库后再出库`)
  }
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

async function submitScanBinding() {
  await bindAssetScanCode(asset.value.asset_id, {
    ...bindingForm,
    scan_type: 'qrcode',
    remark: form.remark || '移动端二维码绑定'
  })
  addLog('二维码绑定', '已绑定二维码内容')
  ElMessage.success('二维码内容已绑定')
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
  padding: 0 12px calc(104px + env(safe-area-inset-bottom));
  display: grid;
  align-content: start;
  gap: 8px;
  background:
    radial-gradient(circle at 14% 0%, rgba(50, 125, 255, 0.18), transparent 28%),
    linear-gradient(180deg, #eef6ff 0%, #f7fbff 36%, #f4f7fb 100%);
  color: #162033;
}

.eyebrow,
.tip,
.asset-main span,
.asset-meta,
.todo-content small,
.log-item small {
  color: #64748b;
}

.mobile-appbar {
  position: sticky;
  top: 0;
  z-index: 18;
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) 44px;
  align-items: center;
  min-height: 58px;
  padding-top: env(safe-area-inset-top);
  background: rgba(245, 250, 255, 0.86);
  backdrop-filter: blur(14px);
}

.mobile-appbar strong {
  overflow: hidden;
  color: #101828;
  font-size: 18px;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.appbar-icon {
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: #152238;
  font-size: 30px;
  line-height: 1;
}

.appbar-dot {
  position: relative;
  color: #0f172a;
  font-size: 22px;
  letter-spacing: 2px;
}

.appbar-dot::after {
  position: absolute;
  top: 5px;
  right: 4px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ff7a2f;
  content: "";
}

.mobile-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid rgba(211, 226, 245, 0.9);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 14px 34px rgba(40, 83, 130, 0.1);
}

.mobile-hero h1 {
  margin: 2px 0 3px;
  color: #101828;
  font-size: 20px;
  line-height: 1.2;
  letter-spacing: 0;
}

.mobile-hero p {
  margin: 0;
  color: #667085;
  font-size: 12px;
  line-height: 1.35;
}

.eyebrow {
  font-size: 12px;
  font-weight: 800;
  color: #2563eb;
}

.hero-stats {
  display: grid;
  gap: 6px;
}

.hero-stats span {
  display: grid;
  place-items: center;
  min-width: 48px;
  padding: 5px 7px;
  border-radius: 12px;
  background: #f0f6ff;
  color: #667085;
  font-size: 11px;
}

.hero-stats strong {
  color: #1764e8;
  font-size: 16px;
  line-height: 1.1;
}

.mobile-bottom-menu {
  position: fixed;
  left: 12px;
  right: 12px;
  bottom: calc(8px + env(safe-area-inset-bottom));
  z-index: 20;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 4px;
  padding: 6px 8px;
  border: 1px solid rgba(209, 224, 242, 0.9);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 -10px 28px rgba(40, 83, 130, 0.16);
  backdrop-filter: blur(14px);
}

.bottom-menu-item {
  position: relative;
  min-width: 0;
  min-height: 48px;
  padding: 4px 4px;
  border: 0;
  border-radius: 16px;
  background: transparent;
  color: #8a96aa;
  font-size: 11px;
  font-weight: 800;
  display: grid;
  place-items: center;
  gap: 3px;
}

.bottom-menu-item .el-icon {
  font-size: 21px;
}

.bottom-menu-item.active {
  color: #1764e8;
}

.bottom-menu-item.active .el-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 30px;
  border-radius: 13px;
  background: linear-gradient(135deg, #2675ff, #00a3d8);
  color: #fff;
  box-shadow: 0 10px 18px rgba(23, 100, 232, 0.26);
}

.bottom-menu-item small {
  position: absolute;
  top: 5px;
  right: 14px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #eef2f8;
  color: #667085;
  font-size: 10px;
  line-height: 18px;
}

.bottom-menu-item.active small {
  background: #e6f0ff;
  color: #1764e8;
}

.mode-strip {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 2px 2px 8px;
  scroll-snap-type: x proximity;
}

.mode-strip::-webkit-scrollbar,
.quick-codes::-webkit-scrollbar,
.mobile-bottom-menu::-webkit-scrollbar {
  display: none;
}

.mode-card {
  flex: 0 0 132px;
  min-height: 74px;
  padding: 12px;
  border: 1px solid #e3edf8;
  border-radius: 16px;
  background: #ffffff;
  text-align: left;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  align-items: center;
  column-gap: 7px;
  row-gap: 2px;
  scroll-snap-align: start;
  box-shadow: 0 10px 22px rgba(40, 83, 130, 0.07);
}

.mode-card.active {
  border-color: rgba(23, 100, 232, 0.28);
  background: linear-gradient(180deg, #ffffff 0%, #edf5ff 100%);
  box-shadow: 0 14px 28px rgba(23, 100, 232, 0.16);
}

.mode-card .el-icon {
  grid-row: span 2;
  font-size: 20px;
  color: #2563eb;
}

.mode-card span {
  font-weight: 700;
  white-space: nowrap;
}

.mode-card small {
  display: block;
  min-width: 0;
  overflow: hidden;
  color: #64748b;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.card-header {
  min-width: 0;
  font-weight: 800;
  color: #172033;
}

.card-header > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scan-card :deep(.el-card__header) {
  padding: 10px 14px;
}

.scan-card :deep(.el-card__body) {
  padding: 12px 14px 14px;
}

.scan-card .scan-box {
  gap: 8px;
}

.scan-card :deep(.el-input__wrapper) {
  min-height: 40px;
}

.scan-searchbar {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) 64px;
  align-items: center;
  gap: 6px;
  min-height: 42px;
  padding: 4px;
  border-radius: 999px;
  background: #f7f9fc;
}

.scan-trigger {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 50%;
  background: #ff6b6b;
  color: #fff;
  font-size: 18px;
}

.scan-inline-input {
  min-width: 0;
}

.scan-searchbar :deep(.el-input__wrapper) {
  min-height: 34px;
  padding: 0 4px;
  border-radius: 999px;
  background: transparent;
  box-shadow: none;
}

.scan-searchbar :deep(.el-input__inner) {
  color: #374151;
  font-size: 14px;
}

.scan-query-btn {
  min-height: 34px;
  margin: 0;
  border: 0;
  border-radius: 999px;
  background: #f6a4a4;
  font-weight: 800;
}

.scan-query-btn:hover,
.scan-query-btn:focus {
  background: #ef8f8f;
}

.scan-runtime-alert {
  margin-top: 4px;
  padding: 8px 10px;
}

.scan-runtime-alert :deep(.el-alert__title) {
  font-size: 13px;
}

.scan-runtime-alert :deep(.el-alert__description) {
  margin-top: 2px;
  font-size: 12px;
  line-height: 1.35;
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
  background: #ffffff;
}

.task-progress {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.inline-alert {
  margin-bottom: 14px;
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
  gap: 8px;
  min-height: 52px;
  padding: 10px;
  border: 1px solid #e6eef8;
  border-radius: 14px;
  background: #ffffff;
  text-align: left;
  box-shadow: 0 8px 18px rgba(40, 83, 130, 0.045);
}

.todo-priority {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 10px;
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
  gap: 12px;
}

.scan-box {
  gap: 12px;
}

.quick-codes {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 2px 0 4px;
}

.quick-codes button,
.quick-codes .el-button {
  flex: 0 0 auto;
}

.quick-codes button {
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid #dbe8f6;
  border-radius: 999px;
  background: #fff;
  color: #334155;
  font-size: 12px;
}

.asset-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}

.asset-main strong {
  display: block;
  font-size: 19px;
  line-height: 1.25;
}

.asset-main span {
  display: block;
  margin-top: 2px;
}

.asset-meta {
  gap: 8px;
  font-size: 13px;
}

.asset-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.asset-actions :deep(.el-button) {
  min-height: 42px;
}

.binding-actions {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  gap: 8px;
  margin: -4px 0 16px;
}

.binding-actions :deep(.el-button) {
  min-height: 48px;
  margin: 0;
  font-weight: 800;
}

.qr-confirm-box {
  display: grid;
  gap: 4px;
  margin: -4px 0 14px;
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #eff6ff;
  color: #64748b;
  font-size: 12px;
  line-height: 1.4;
}

.qr-confirm-box strong {
  overflow-wrap: anywhere;
  color: #172033;
  font-size: 13px;
}

.form-card :deep(.el-switch__label) {
  min-width: 0;
  white-space: normal;
}

.sticky-submit {
  position: static;
  z-index: 1;
  margin-top: 18px;
  padding-top: 0;
  background: transparent;
}

.submit-btn {
  width: 100%;
  min-height: 52px;
  font-weight: 800;
}

.log-item {
  gap: 4px;
  padding: 12px;
  border: 1px solid #e6eef8;
  border-radius: 14px;
  background: #fff;
}

:deep(.el-card) {
  border-radius: 14px;
  border-color: #e3edf8;
  box-shadow: 0 14px 32px rgba(40, 83, 130, 0.08);
}

:deep(.el-card__header) {
  padding: 11px 14px;
  border-bottom-color: #edf2f7;
}

:deep(.el-card__body) {
  padding: 12px 14px;
}

:deep(.el-button) {
  border-radius: 12px;
  min-height: 42px;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper),
:deep(.el-textarea__inner) {
  border-radius: 12px;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  min-height: 48px;
}

:deep(.mobile-select .el-select__wrapper) {
  min-height: 48px;
}

:global(.mobile-select-popper) {
  max-width: min(430px, calc(100vw - 28px));
}

:global(.mobile-select-popper .el-select-dropdown__wrap) {
  max-height: min(240px, 38dvh);
}

:global(.mobile-select-popper .el-select-dropdown__item) {
  height: auto;
  min-height: 36px;
  padding-block: 6px;
  line-height: 1.35;
  white-space: normal;
}

:deep(.el-form-item) {
  margin-bottom: 16px;
}

:deep(.el-form-item__label) {
  padding-bottom: 6px;
  font-weight: 700;
  color: #334155;
}

:deep(.el-textarea__inner) {
  min-height: 92px;
}

:deep(.el-segmented) {
  width: 100%;
}

:deep(.el-segmented__item) {
  flex: 1;
}

@media (min-width: 480px) {
  .mobile-page {
    max-width: 430px;
    margin: 0 auto;
  }

  .mobile-bottom-menu {
    left: 50%;
    right: auto;
    width: min(406px, calc(100vw - 24px));
    transform: translateX(-50%);
  }
}

@media (max-width: 380px) {
  .mobile-page {
    padding-inline: 10px;
  }

  .mobile-bottom-menu {
    display: flex;
    overflow-x: auto;
    scroll-snap-type: x proximity;
  }

  .bottom-menu-item {
    flex: 0 0 82px;
    scroll-snap-align: start;
  }

  .mode-card {
    flex-basis: 118px;
  }

  .binding-actions {
    grid-template-columns: 1fr;
  }
}
</style>


