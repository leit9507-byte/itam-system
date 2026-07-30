<template>
  <div class="mobile-page">
    <header v-if="showMobileAppbar" class="mobile-appbar">
      <button type="button" class="appbar-icon" @click="router.back()">&lt;</button>
      <strong>ITAM Dashboard</strong>
      <span class="appbar-icon" aria-hidden="true"></span>
    </header>

    <section v-if="!store.isAuthenticated" class="mobile-auth-panel">
      <strong>需要登录后使用移动作业</strong>
      <p>请先登录资产管理系统，再进行扫码盘点、入库、出库、维修和待办处理。</p>
      <el-button type="primary" size="large" @click="goMobileLogin">去登录</el-button>
    </section>

    <template v-else>
    <section class="mobile-hero">
      <div>
        <span class="eyebrow">{{ currentSectionTitle }}</span>
        <h1>{{ currentSectionTitle }}</h1>
        <p>{{ sectionSubtitle }}</p>
      </div>
      <div class="hero-stats">
        <span><strong>{{ todos.length }}</strong>待办</span>
        <span v-if="pendingJobs.length"><strong>{{ pendingJobs.length }}</strong>待提交</span>
      </div>
    </section>

    <section v-if="showFieldStatus" class="field-status" :class="[fieldStatus.tone, { online: isOnline }]">
      <div>
        <strong>{{ fieldStatus.title }}</strong>
        <span>{{ fieldStatus.detail }}</span>
      </div>
      <el-button v-if="pendingJobs.length" text type="primary" :loading="queueRetrying" @click="retryPendingJobs">重试</el-button>
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
      <div v-if="todos.length" class="mobile-todo-list">
        <button v-for="item in todos" :key="item.id" type="button" class="mobile-todo-row" @click="goTodo(item)">
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

    <el-card v-if="['work', 'repair', 'stocktake'].includes(activeSection)" shadow="never" class="scan-card mobile-panel">
      <template #header>
        <div class="card-header">
          <span>{{ currentMode.label }}</span>
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
          <el-button class="scan-reset-btn" @click="resetAsset">重选</el-button>
          <button type="button" class="scan-info-btn" aria-label="扫码信息" @click="scanInfoDialogVisible = true">i</button>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="scanInfoDialogVisible" title="扫码信息" width="92%" class="mobile-scan-dialog" append-to-body>
      <div class="scan-dialog-content">
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
        <div v-if="scanFeedback.visible" class="scan-feedback" :class="scanFeedback.tone">
          <strong>{{ scanFeedback.title }}</strong>
          <span>{{ scanFeedback.detail }}</span>
        </div>
        <el-empty v-if="!showScanRuntimeHint && !scanRuntimeError && !scanFeedback.visible" description="暂无扫码信息" :image-size="56" />
      </div>
    </el-dialog>

    <el-dialog
      v-model="browserScannerVisible"
      title="扫描资产二维码"
      width="92%"
      class="mobile-camera-dialog"
      append-to-body
      :close-on-click-modal="false"
      @closed="cancelBrowserScan"
    >
      <div class="camera-preview">
        <video ref="browserVideoRef" muted playsinline></video>
        <span class="camera-frame" aria-hidden="true"></span>
      </div>
      <el-alert
        v-if="browserScanError"
        :title="browserScanError"
        type="error"
        show-icon
        :closable="false"
      />
      <p v-else class="camera-tip">将二维码或条形码放入框内，识别后会自动关闭。</p>
      <template #footer>
        <el-button size="large" @click="cancelBrowserScan">取消扫码</el-button>
      </template>
    </el-dialog>

    <el-card v-if="pendingJobs.length" shadow="never" class="queue-card mobile-panel">
      <template #header>
        <div class="card-header">
          <span>待提交队列</span>
          <el-tag :type="isOnline ? 'warning' : 'info'">{{ isOnline ? '等待重试' : '离线保存' }}</el-tag>
        </div>
      </template>
      <div class="queue-list">
        <div v-for="job in pendingJobs" :key="job.id" class="queue-row">
          <div>
            <strong>{{ job.action_label }} / {{ job.asset_id }}</strong>
            <small>{{ job.asset_name || '-' }} · {{ job.created_at }}</small>
            <small v-if="job.last_error">上次失败：{{ job.last_error }}</small>
          </div>
          <button type="button" @click="retryOneJob(job)">重试</button>
        </div>
      </div>
    </el-card>

    <el-dialog v-if="asset" v-model="assetDialogVisible" :title="currentMode.formTitle" width="92%" class="mobile-asset-dialog" append-to-body>
      <div class="asset-main">
        <div>
          <strong>{{ asset.name }}</strong>
          <span>{{ asset.asset_id }}</span>
        </div>
        <el-tag :type="statusType(asset.status)">{{ statusLabel(asset.status) }}</el-tag>
        <el-button text type="primary" @click="copyAssetId">复制</el-button>
      </div>
      <div class="asset-meta">
        <span>责任人：{{ asset.owner_name || asset.owner || '未分配' }}</span>
        <span>位置：{{ asset.location || asset.warehouse || '-' }}</span>
        <span>SN：{{ asset.sn || '-' }}</span>
        <span>采购审批单号：{{ asset.purchase_approval_no || '-' }}</span>
      </div>

      <div v-if="['work', 'repair', 'stocktake'].includes(activeSection)" class="mobile-dialog-form">
        <el-form label-position="top">
        <template v-if="mode === 'stocktake'">
          <el-form-item label="盘点任务">
            <el-input :model-value="selectedTask ? `${selectedTask.name} (${selectedTask.id})` : '未选择任务'" disabled />
          </el-form-item>
          <el-alert
            class="inline-alert"
            :title="`账面使用人：${stocktakeOwnerLabel(currentStocktakeItem?.book_owner_user_id)}；账面位置：${currentStocktakeItem?.book_location || '-'}`"
            type="info"
            show-icon
            :closable="false"
          />
          <el-form-item label="实盘使用人">
            <el-select
              v-model="form.owner_user_id"
              filterable
              remote
              clearable
              reserve-keyword
              :remote-method="searchUsers"
              :disabled="!canUpdateStocktakeOwner"
              :placeholder="canUpdateStocktakeOwner ? '搜索实际使用人' : '当前状态不能直接调整使用人'"
              class="mobile-select"
              popper-class="mobile-select-popper"
              style="width: 100%"
              @visible-change="visible => visible && searchUsers('')"
              @change="selectUser"
            >
              <el-option v-for="user in filteredUsers" :key="user.user_id" :label="`${user.display_name} (${user.username}) / ${user.dept_name || user.dept_id || '未分部门'}`" :value="user.user_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="实盘位置">
            <el-select
              v-model="form.location"
              filterable
              remote
              clearable
              reserve-keyword
              :remote-method="searchLocations"
              placeholder="搜索实际位置"
              class="mobile-select"
              popper-class="mobile-select-popper"
              style="width: 100%"
              @visible-change="visible => visible && resetLocationOptions()"
            >
              <el-option v-for="item in visibleLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="同步资产台账">
            <el-switch v-model="form.stocktake_update_asset" :disabled="!canReconcileStocktakeAsset" active-text="更新使用人和位置" />
          </el-form-item>
          <el-alert
            class="inline-alert"
            :title="form.stocktake_update_asset ? '提交后同步修正资产使用人、部门和位置，并记录生命周期与审计日志。' : '仅登记盘点结果，不修改资产台账。'"
            :type="form.stocktake_update_asset ? 'warning' : 'info'"
            show-icon
            :closable="false"
          />
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
          <el-form-item v-if="form.outboundTarget === 'user'" label="领用人">
            <el-select v-model="form.owner_user_id" filterable remote clearable reserve-keyword :remote-method="searchUsers" placeholder="搜索姓名/账号" class="mobile-select" popper-class="mobile-select-popper" @visible-change="visible => visible && searchUsers('')" @change="selectUser">
              <el-option v-for="user in filteredUsers" :key="user.user_id" :label="`${user.display_name} (${user.username}) / ${user.dept_name || user.dept_id || '未分部门'}`" :value="user.user_id" />
            </el-select>
          </el-form-item>
          <el-form-item :label="form.outboundTarget === 'location' ? '出库地址' : '使用位置'">
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
          <el-form-item label="维修类型">
            <el-select v-model="form.repair_type" style="width: 100%">
              <el-option label="普通维修" value="普通维修" />
              <el-option label="在保维修" value="在保维修" />
              <el-option label="内部维修" value="内部维修" />
              <el-option label="外部付费维修" value="外部付费维修" />
              <el-option label="返厂维修" value="返厂维修" />
            </el-select>
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

        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="补充说明" />
        </el-form-item>
        </el-form>
        <div class="sticky-submit">
          <el-button type="primary" size="large" class="submit-btn" :loading="submitting" @click="submitWork">{{ currentMode.submitText }}</el-button>
        </div>
      </div>
    </el-dialog>

    <nav class="mobile-bottom-menu" aria-label="移动端菜单">
      <button v-for="item in sectionMenus" :key="item.value" type="button" class="bottom-menu-item" :class="{ active: activeSection === item.value }" @click="selectSection(item.value)">
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
        <small v-if="item.count !== undefined">{{ item.count }}</small>
      </button>
    </nav>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'
import { Box, Camera, CircleCheck, FolderOpened, HomeFilled, Search, Setting } from '@element-plus/icons-vue'
import { getAssets, inboundAsset, outboundAsset } from '../../api/asset'
import { createRepairRecord, getRepairFaultTypes } from '../../api/repair'
import { getLocations } from '../../api/location'
import { getUsers } from '../../api/user'
import { getStocktakeTaskItems, getStocktakeTasks, submitStocktakeItem } from '../../api/stocktake'
import { getTodoItems } from '../../api/todo'
import { resolveScanBinding } from '../../api/scanBinding'
import TodoAssetActions from '../../components/TodoAssetActions.vue'
import { useAppStore } from '../../store'
import { assetCodeCandidates, assetCodeMatches, parseAssetCode } from '../../utils/assetCode'
import { feishuRuntimeStatus, getLastFeishuScanError, isFeishuClient, scanByFeishuSdk } from '../../utils/feishuSdk'
import { getStorageJson, setStorageItem } from '../../utils/storage'

const router = useRouter()
const store = useAppStore()
const SCAN_CANCELLED = Symbol('scan-cancelled')
const QUEUE_STORAGE_KEY = 'itam_mobile_pending_jobs'
const modes = [
  { value: 'stocktake', label: '扫码盘点', hint: '执行后台任务', icon: Search, formTitle: '盘点确认', submitText: '提交盘点' },
  { value: 'inbound', label: '扫码入库', hint: '归还/验收入库', icon: Box, formTitle: '入库信息', submitText: '确认入库' },
  { value: 'outbound', label: '扫码出库', hint: '关联人员或地址', icon: CircleCheck, formTitle: '出库信息', submitText: '确认出库' },
  { value: 'repair', label: '维修登记', hint: '登记设备故障和维修', icon: Setting, formTitle: '维修信息', submitText: '创建维修登记' }
]
const workModes = modes.filter(item => ['inbound', 'outbound'].includes(item.value))
const outboundTargetOptions = [
  { label: '人员', value: 'user' },
  { label: '地址', value: 'location' }
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
const todos = ref([])
const todoLoading = ref(false)
const todoAssetActionsRef = ref(null)
const stocktakeTasks = ref([])
const visibleStocktakeTasks = ref([])
const currentStocktakeItem = ref(null)
const scanRuntimeStatus = ref(feishuRuntimeStatus())
const scanRuntimeError = ref('')
const scanInfoDialogVisible = ref(false)
const browserScannerVisible = ref(false)
const browserVideoRef = ref(null)
const browserScanError = ref('')
const assetDialogVisible = ref(false)
const isOnline = ref(navigator.onLine)
const pendingJobs = ref(loadPendingJobs())
const queueRetrying = ref(false)
const lastScan = reactive({ mode: '', code: '', at: 0 })
const scanFeedback = reactive({ visible: false, tone: 'info', title: '等待扫码', detail: '请扫描或输入资产编号。' })
let browserScannerControls = null
let browserScanResolve = null
let usersRequest = null
let locationsRequest = null
let faultTypesRequest = null
let stocktakeTasksRequest = null
const showMobileAppbar = computed(() => !scanRuntimeStatus.value.isFeishu)
const form = reactive(defaultForm())

const OPEN_STOCKTAKE_STATUSES = ['进行中']
const INBOUND_ALLOWED_STATUSES = ['in_use', 'borrowed', 'out_stock', 'repair']
const OUTBOUND_ALLOWED_STATUSES = ['in_stock', 'idle']
const activeStocktakeTasks = computed(() => stocktakeTasks.value.filter(task => OPEN_STOCKTAKE_STATUSES.includes(task.status)))
const currentMode = computed(() => modes.find(item => item.value === mode.value) || modes[0])
const selectedTask = computed(() => stocktakeTasks.value.find(task => task.id === form.task_id))
const stocktakeProgress = computed(() => (selectedTask.value?.total ? Math.round((Number(selectedTask.value.checked || 0) / Number(selectedTask.value.total || 0)) * 100) : 0))
const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))
const activeFaultTypes = computed(() => faultTypes.value.filter(item => item.enabled !== '停用'))
const currentSectionTitle = computed(() => {
  if (activeSection.value === 'work') return currentMode.value.label
  return ({ todo: '待办处理', repair: '维修登记', stocktake: '资产盘点' })[activeSection.value] || '出入库'
})
const sectionSubtitle = computed(() => {
  if (activeSection.value === 'todo') return '处理入职分配、离职回收和审批待办。'
  if (activeSection.value === 'repair') return '扫码选择故障设备并登记维修。'
  if (activeSection.value === 'stocktake') return '选择后台盘点任务后，现场扫码确认资产。'
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
  return '将使用手机摄像头扫码，也可手动输入资产编号。'
})
const showScanRuntimeHint = computed(() => scanRuntimeError.value || !scanRuntimeStatus.value.hasScanCode)
const sectionMenus = computed(() => [
  { value: 'todo', label: '待办', count: todos.value.length, icon: HomeFilled },
  { value: 'work', label: '出入库', icon: Box },
  { value: 'repair', label: '维修登记', icon: Setting },
  { value: 'stocktake', label: '资产盘点', icon: FolderOpened }
])
const fieldStatus = computed(() => {
  if (!isOnline.value) {
    return {
      tone: 'warning',
      title: '当前离线',
      detail: pendingJobs.value.length ? `已保存 ${pendingJobs.value.length} 条待提交，联网后自动重试。` : '可以继续扫码，提交动作会先保存到本机。'
    }
  }
  if (queueRetrying.value) return { tone: 'info', title: '正在补偿提交', detail: `正在处理 ${pendingJobs.value.length} 条待提交记录。` }
  if (pendingJobs.value.length) return { tone: 'warning', title: '存在待提交', detail: `${pendingJobs.value.length} 条现场操作尚未同步，请点击重试或等待自动提交。` }
  return { tone: 'success', title: '在线作业', detail: '扫码和提交会实时同步到系统。' }
})
const canUpdateStocktakeOwner = computed(() => ['in_use', 'borrowed', 'out_stock'].includes(asset.value?.status))
const canReconcileStocktakeAsset = computed(() => !['scrapped', 'disposed', 'lost'].includes(asset.value?.status))
const showFieldStatus = computed(() => !isOnline.value || queueRetrying.value || pendingJobs.value.length > 0)

onMounted(async () => {
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
  store.syncSessionFromStorage()
  if (!store.isAuthenticated) return
  await loadTodos()
  if (isOnline.value && pendingJobs.value.length) retryPendingJobs()
})

onUnmounted(() => {
  window.removeEventListener('online', handleOnline)
  window.removeEventListener('offline', handleOffline)
  finishBrowserScan('')
})

function defaultForm() {
  return {
    task_id: '',
    stocktake_result: '正常',
    stocktake_update_asset: false,
    location: '',
    owner_user_id: '',
    owner_name: '',
    dept_id: '',
    dept_name: '',
    outboundTarget: 'user',
    repair_time: new Date().toISOString().slice(0, 10),
    repair_type: '普通维修',
    fault_reason: '',
    repair_cost: 0,
    vendor: '',
    remark: ''
  }
}

async function loadStocktakeTasks() {
  stocktakeTasks.value = await getStocktakeTasks({ status: '进行中', includeItems: false })
  resetTaskOptions()
  if (!activeStocktakeTasks.value.some(task => task.id === form.task_id)) {
    form.task_id = activeStocktakeTasks.value[0]?.id || ''
  }
}

function ensureStocktakeTasks() {
  if (!stocktakeTasksRequest) {
    stocktakeTasksRequest = loadStocktakeTasks().catch(() => {
      stocktakeTasks.value = []
      resetTaskOptions()
    })
  }
  return stocktakeTasksRequest
}

function ensureUsers() {
  if (!usersRequest) {
    usersRequest = getUsers()
      .then(rows => {
        users.value = rows
        filteredUsers.value = rows.slice(0, 20)
      })
      .catch(() => {
        users.value = []
        filteredUsers.value = []
      })
  }
  return usersRequest
}

function ensureLocations() {
  if (!locationsRequest) {
    locationsRequest = getLocations()
      .then(rows => {
        locations.value = rows
        visibleLocations.value = activeLocations.value.slice(0, 30)
      })
      .catch(() => {
        locations.value = []
        visibleLocations.value = []
      })
  }
  return locationsRequest
}

function ensureFaultTypes() {
  if (!faultTypesRequest) {
    faultTypesRequest = getRepairFaultTypes()
      .then(rows => {
        faultTypes.value = rows
        visibleFaultTypes.value = activeFaultTypes.value.slice(0, 30)
      })
      .catch(() => {
        faultTypes.value = []
        visibleFaultTypes.value = []
      })
  }
  return faultTypesRequest
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
    ensureStocktakeTasks()
  } else if (value === 'repair') {
    mode.value = 'repair'
  } else if (value === 'work' && mode.value === 'stocktake') {
    mode.value = 'inbound'
  } else if (value === 'work' && mode.value === 'repair') {
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
  if (!navigator.mediaDevices?.getUserMedia) {
    scanRuntimeError.value = window.isSecureContext
      ? '当前浏览器不支持摄像头扫码'
      : '摄像头扫码需要通过 HTTPS 访问'
    return ''
  }

  browserScanError.value = ''
  browserScannerVisible.value = true
  await nextTick()

  let scannerModule
  try {
    scannerModule = await import('@zxing/browser')
  } catch {
    browserScannerVisible.value = false
    scanRuntimeError.value = '扫码组件加载失败，请检查网络后重试'
    return ''
  }

  return new Promise(resolve => {
    browserScanResolve = resolve
    const { BrowserMultiFormatReader } = scannerModule
    const reader = new BrowserMultiFormatReader()
    reader.decodeFromConstraints(
      {
        audio: false,
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      },
      browserVideoRef.value,
      result => {
        if (result?.getText()) finishBrowserScan(result.getText())
      }
    ).then(controls => {
      if (!browserScanResolve) {
        controls.stop()
        return
      }
      browserScannerControls = controls
    }).catch(error => {
      browserScanError.value = browserCameraError(error)
      scanRuntimeError.value = browserScanError.value
    })
  })
}

function cancelBrowserScan() {
  finishBrowserScan('')
}

function finishBrowserScan(value) {
  browserScannerControls?.stop()
  browserScannerControls = null
  browserScannerVisible.value = false
  const resolve = browserScanResolve
  browserScanResolve = null
  resolve?.(value || '')
}

function browserCameraError(error) {
  const name = error?.name || ''
  if (name === 'NotAllowedError' || name === 'SecurityError') return '摄像头权限未开启，请在浏览器设置中允许访问摄像头'
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') return '未检测到可用摄像头'
  if (name === 'NotReadableError' || name === 'TrackStartError') return '摄像头正被其他应用占用'
  if (!window.isSecureContext) return '摄像头扫码需要通过 HTTPS 访问'
  return error?.message || '摄像头启动失败，请检查浏览器权限'
}

function handleScanResult(value) {
  assetCode.value = parseAssetCode(value)
  const duplicate = lastScan.mode === mode.value && lastScan.code === assetCode.value && Date.now() - lastScan.at < 10000
  lastScan.mode = mode.value
  lastScan.code = assetCode.value
  lastScan.at = Date.now()
  if (duplicate) setScanFeedback('warning', '重复扫码', `${assetCode.value} 刚刚已经扫描过，可直接确认提交。`)
  loadAsset()
}

function goMobileLogin() {
  router.push({ path: '/login', query: { redirect: '/mobile' } })
}

async function loadAsset() {
  const code = parseAssetCode(assetCode.value)
  if (!code) return ElMessage.warning('请先扫码或输入资产编号')
  setScanFeedback('info', '正在识别', `正在解析 ${code}。`)
  const resolvedAsset = await resolveAssetFromScan(assetCode.value)
  const candidates = assetCodeCandidates(assetCode.value)
  if (mode.value === 'stocktake') {
    await ensureStocktakeTasks()
    if (!selectedTask.value) return ElMessage.warning('请先选择后台创建的盘点任务')
    const taskItem = await findStocktakeItem(resolvedAsset, candidates)
    if (!taskItem) {
      asset.value = null
      currentStocktakeItem.value = null
      assetDialogVisible.value = false
      setScanFeedback('danger', '不在任务内', `${code} 不属于当前盘点任务，请核对任务或标签。`)
      return ElMessage.error('该资产不在当前盘点任务范围内')
    }
    currentStocktakeItem.value = taskItem
    asset.value = taskItemToAsset(taskItem)
    assetDialogVisible.value = true
    form.location = taskItem.book_location || ''
    form.owner_user_id = taskItem.book_owner_user_id || ''
    form.owner_name = stocktakeOwnerLabel(taskItem.book_owner_user_id, false)
    form.stocktake_update_asset = false
    form.stocktake_result = '正常'
    setScanFeedback(
      taskItem.checked_at ? 'warning' : 'success',
      taskItem.checked_at ? '重复盘点' : '已识别资产',
      taskItem.checked_at ? `${taskItem.asset_id} 已在 ${taskItem.checked_at} 登记。` : `${taskItem.asset_id} 可提交盘点确认。`
    )
    ElMessage[taskItem.checked_at ? 'info' : 'success'](taskItem.checked_at ? '该资产已登记，可重新扫码确认' : '已读取盘点资产')
    return
  }
  if (resolvedAsset) {
    asset.value = resolvedAsset
    assetDialogVisible.value = true
    form.location = resolvedAsset.location || resolvedAsset.warehouse || ''
    setScanFeedback('success', '已识别资产', `${resolvedAsset.asset_id} 已通过二维码绑定识别。`)
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
    assetDialogVisible.value = false
    setScanFeedback('danger', '未找到资产', `${code} 未匹配到资产，请检查二维码内容或资产编号。`)
    return ElMessage.error('未找到资产')
  }
  asset.value = found
  assetDialogVisible.value = true
  form.location = found.location || found.warehouse || ''
  setScanFeedback('success', '已识别资产', `${found.asset_id} 已读取，可继续处理。`)
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
  currentStocktakeItem.value = null
  assetCode.value = ''
  assetDialogVisible.value = false
}

async function findStocktakeItem(resolvedAsset, candidates) {
  const keywords = resolvedAsset?.asset_id
    ? [resolvedAsset.asset_id]
    : candidates
  for (const keyword of keywords) {
    const result = await getStocktakeTaskItems(selectedTask.value.id, {
      keyword,
      page: 1,
      page_size: 20
    })
    const matched = result.list.find(item => assetCodeMatches(item, keyword)) || result.list[0]
    if (matched) return matched
  }
  return null
}

async function searchUsers(query = '') {
  await ensureUsers()
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

async function resetLocationOptions() {
  await ensureLocations()
  visibleLocations.value = activeLocations.value.slice(0, 30)
}

async function searchLocations(query = '') {
  await ensureLocations()
  const keyword = query.trim().toLowerCase()
  visibleLocations.value = activeLocations.value
    .filter(item => !keyword || [item.name, item.code, item.type, item.owner_dept].join(' ').toLowerCase().includes(keyword))
    .slice(0, 30)
}

async function resetFaultTypeOptions() {
  await ensureFaultTypes()
  visibleFaultTypes.value = activeFaultTypes.value.slice(0, 30)
}

async function searchFaultTypes(query = '') {
  await ensureFaultTypes()
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
  const job = buildSubmitJob()
  if (!job) return
  if (!isOnline.value) {
    enqueueJob(job, '当前离线，已保存到待提交队列')
    resetAsset()
    return
  }
  submitting.value = true
  try {
    await runSubmitJob(job)
    setScanFeedback('success', '提交成功', `${job.action_label} 已同步：${job.asset_id}`)
    resetAsset()
  } catch (error) {
    if (shouldQueueError(error)) {
      enqueueJob(job, error?.message || '网络异常，已保存到待提交队列')
      resetAsset()
      return
    }
    setScanFeedback('danger', '提交失败', error?.message || '请检查表单后重试。')
    throw error
  } finally {
    submitting.value = false
  }
}

function buildSubmitJob() {
  if (mode.value === 'stocktake') {
    if (selectedTask.value && !OPEN_STOCKTAKE_STATUSES.includes(selectedTask.value.status)) {
      setScanFeedback('warning', '任务未开启', '移动端只能执行已开启的盘点任务。')
      ElMessage.warning('移动端只能执行已开启的盘点任务')
      return null
    }
    if (!selectedTask.value) {
      ElMessage.warning('请先选择盘点任务')
      return null
    }
    if (!currentStocktakeItem.value) {
      setScanFeedback('danger', '不在任务内', '该资产不在当前盘点任务范围内。')
      ElMessage.error('该资产不在当前盘点任务范围内')
      return null
    }
  }
  if (mode.value === 'inbound' && !INBOUND_ALLOWED_STATUSES.includes(asset.value?.status)) {
    setScanFeedback('warning', '状态不允许', `当前状态为 ${statusLabel(asset.value?.status)}，不能重复入库。`)
    ElMessage.warning(`当前状态为 ${statusLabel(asset.value?.status)}，不能重复入库`)
    return null
  }
  if (mode.value === 'outbound') {
    if (!OUTBOUND_ALLOWED_STATUSES.includes(asset.value?.status)) {
      setScanFeedback('warning', '状态不允许', `当前状态为 ${statusLabel(asset.value?.status)}，不能重复出库。`)
      ElMessage.warning(`当前状态为 ${statusLabel(asset.value?.status)}，不能重复出库；请先归还入库后再出库`)
      return null
    }
    if (form.outboundTarget === 'user' && !form.owner_user_id) {
      ElMessage.warning('请选择领用人')
      return null
    }
    if (form.outboundTarget === 'location' && !form.location) {
      ElMessage.warning('请选择出库地址')
      return null
    }
  }
  if (mode.value === 'repair' && !form.fault_reason) {
    ElMessage.warning('请选择故障类型')
    return null
  }
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    mode: mode.value,
    action_label: currentMode.value.label,
    asset_id: asset.value.asset_id,
    asset_name: asset.value.name,
    asset_snapshot: { ...asset.value },
    asset_code: assetCode.value,
    form: { ...form, book_location: currentStocktakeItem.value?.book_location || form.location || '' },
    created_at: new Date().toLocaleString('zh-CN', { hour12: false }),
    attempts: 0,
    last_error: ''
  }
}

async function runSubmitJob(job) {
  if (job.mode === 'stocktake') return submitStocktakeJob(job)
  if (job.mode === 'inbound') return submitInboundJob(job)
  if (job.mode === 'outbound') return submitOutboundJob(job)
  if (job.mode === 'repair') return submitRepairJob(job)
}

async function submitStocktakeJob(job) {
  const saved = await submitStocktakeItem(job.form.task_id, job.asset_id, {
    actual_location: job.form.location || '',
    actual_owner_user_id: job.form.owner_user_id,
    update_asset_info: Boolean(job.form.stocktake_update_asset),
    result: '正常',
    checker: '移动端扫码',
    remark: job.form.remark,
    scan_raw: job.asset_code,
    parsed_code: parseAssetCode(job.asset_code),
    client_source: isFeishuClient() ? 'feishu_mobile' : 'mobile_browser'
  })
  applyStocktakeItem(saved)
  ElMessage.success(saved.asset_info_updated ? '盘点完成，资产信息已同步更新' : '扫码确认完成')
}

function taskItemToAsset(item) {
  const owner = users.value.find(user => user.user_id === item.book_owner_user_id)
  return {
    asset_id: item.asset_id,
    name: item.name,
    sn: item.sn,
    status: item.book_status,
    owner: item.book_owner_user_id || '',
    owner_user_id: item.book_owner_user_id || '',
    owner_name: owner?.display_name || '',
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
  const wasUnchecked = currentStocktakeItem.value?.result === '未盘'
  const wasAbnormal = ['盘盈', '盘亏', '位置不符', '使用人不符', '状态不符'].includes(currentStocktakeItem.value?.result)
  const isAbnormal = ['盘盈', '盘亏', '位置不符', '使用人不符', '状态不符'].includes(saved.result)
  currentStocktakeItem.value = saved
  if (wasUnchecked && saved.result !== '未盘') task.checked = Number(task.checked || 0) + 1
  if (!wasAbnormal && isAbnormal) task.abnormal = Number(task.abnormal || 0) + 1
  if (wasAbnormal && !isAbnormal) task.abnormal = Math.max(0, Number(task.abnormal || 0) - 1)
  if (task.status !== '已完成' && task.total && task.checked === task.total) task.status = '待确认'
  else if (task.status === '待开始') task.status = '进行中'
}

async function submitInboundJob(job) {
  await inboundAsset(job.asset_id, { warehouse: job.form.location, location: job.form.location, remark: job.form.remark || '移动端扫码入库' })
  ElMessage.success('入库成功')
}

async function submitOutboundJob(job) {
  await outboundAsset(job.asset_id, {
    outboundTarget: job.form.outboundTarget,
    owner_user_id: job.form.owner_user_id,
    owner_name: job.form.owner_name,
    dept_id: job.form.dept_id,
    dept_name: job.form.dept_name,
    location: job.form.location,
    remark: job.form.remark || '移动端扫码出库'
  })
  ElMessage.success('出库成功')
}

async function submitRepairJob(job) {
  await createRepairRecord(job.asset_snapshot, {
    repair_time: job.form.repair_time,
    repair_type: job.form.repair_type,
    fault_reason: job.form.fault_reason,
    repair_cost: job.form.repair_cost,
    vendor: job.form.vendor,
    remark: job.form.remark || '移动端维修登记'
  })
  ElMessage.success('维修登记已创建')
}

function statusLabel(value) {
  return ({ pending_acceptance: '待验收', in_stock: '在库', in_use: '在用', idle: '闲置', borrowed: '借出', repair: '维修中', out_stock: '已出库', ready_scrap: '待报废', pending_scrap: '待处置登记', scrapped: '已报废', disposed: '已处置', lost: '已丢失' })[value] || value
}

function setScanFeedback(tone, title, detail) {
  Object.assign(scanFeedback, { visible: true, tone, title, detail })
}

function loadPendingJobs() {
  const rows = getStorageJson(QUEUE_STORAGE_KEY, [])
  return Array.isArray(rows) ? rows : []
}

function stocktakeOwnerLabel(userId, emptyLabel = true) {
  if (!userId) return emptyLabel ? '未分配' : ''
  const user = users.value.find(item => item.user_id === userId)
  return user ? `${user.display_name || user.username} (${user.username || user.user_id})` : userId
}

function savePendingJobs() {
  setStorageItem(QUEUE_STORAGE_KEY, JSON.stringify(pendingJobs.value))
}

function enqueueJob(job, reason) {
  const exists = pendingJobs.value.some(item => item.mode === job.mode && item.asset_id === job.asset_id && item.asset_code === job.asset_code && item.form.task_id === job.form.task_id)
  if (!exists) {
    pendingJobs.value.unshift({ ...job, last_error: reason || '', attempts: Number(job.attempts || 0) })
    savePendingJobs()
  }
  setScanFeedback('warning', '已进入待提交队列', `${job.action_label} / ${job.asset_id} 将在网络恢复后自动提交。`)
  ElMessage.warning(reason || '网络异常，已保存到待提交队列')
}

function shouldQueueError(error) {
  if (!navigator.onLine) return true
  if (!error?.response) return true
  return [0, 408, 429, 500, 502, 503, 504].includes(Number(error.response.status))
}

function handleOnline() {
  isOnline.value = true
  if (pendingJobs.value.length) retryPendingJobs()
}

function handleOffline() {
  isOnline.value = false
  setScanFeedback('warning', '网络已断开', '后续提交会先保存到本机待提交队列。')
}

async function retryPendingJobs() {
  if (!isOnline.value || queueRetrying.value || !pendingJobs.value.length) return
  queueRetrying.value = true
  const remaining = []
  for (let index = 0; index < pendingJobs.value.length; index += 1) {
    const job = pendingJobs.value[index]
    try {
      await runSubmitJob(job)
    } catch (error) {
      remaining.push({
        ...job,
        attempts: Number(job.attempts || 0) + 1,
        last_error: error?.message || '提交失败'
      })
      if (shouldQueueError(error)) {
        remaining.push(...pendingJobs.value.slice(index + 1))
        break
      }
    }
  }
  const completed = pendingJobs.value.length - remaining.length
  pendingJobs.value = remaining
  savePendingJobs()
  queueRetrying.value = false
  if (completed) {
    setScanFeedback('success', '补偿提交完成', `已同步 ${completed} 条现场操作。`)
    ElMessage.success(`已补偿提交 ${completed} 条`)
  } else if (pendingJobs.value.length) {
    setScanFeedback('warning', '补偿提交失败', pendingJobs.value[0].last_error || '请稍后重试。')
  }
}

async function retryOneJob(job) {
  if (!isOnline.value) return ElMessage.warning('当前离线，联网后再重试')
  queueRetrying.value = true
  try {
    await runSubmitJob(job)
    pendingJobs.value = pendingJobs.value.filter(item => item.id !== job.id)
    savePendingJobs()
    setScanFeedback('success', '补偿提交完成', `${job.action_label} / ${job.asset_id} 已同步。`)
  } catch (error) {
    job.attempts = Number(job.attempts || 0) + 1
    job.last_error = error?.message || '提交失败'
    savePendingJobs()
    setScanFeedback('warning', '补偿提交失败', job.last_error)
  } finally {
    queueRetrying.value = false
  }
}

function statusType(value) {
  return ({ in_stock: 'primary', in_use: 'success', idle: 'warning', borrowed: 'warning', repair: 'danger', ready_scrap: 'warning', pending_scrap: 'danger', scrapped: 'info', disposed: 'info', lost: 'danger' })[value] || 'info'
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

.mobile-auth-panel {
  display: grid;
  gap: 12px;
  margin-top: 18px;
  padding: 22px;
  border: 1px solid #dbeafe;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 34px rgba(31, 86, 150, 0.12);
}

.mobile-auth-panel strong {
  color: #102044;
  font-size: 20px;
}

.mobile-auth-panel p {
  margin: 0;
  color: #64748b;
  line-height: 1.6;
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

.field-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 52px;
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  background: #eff6ff;
  color: #475569;
  box-shadow: 0 8px 18px rgba(40, 83, 130, 0.06);
}

.field-status > div {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.field-status strong {
  color: #172033;
  font-size: 14px;
}

.field-status span {
  overflow: hidden;
  font-size: 12px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.field-status.success {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.field-status.warning {
  border-color: #fde68a;
  background: #fffbeb;
}

.field-status.info {
  border-color: #bfdbfe;
  background: #eff6ff;
}

.field-status.danger {
  border-color: #fecaca;
  background: #fff1f2;
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
  grid-template-columns: 38px minmax(0, 1fr) 50px 40px 28px;
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

.scan-query-btn,
.scan-reset-btn {
  width: 100%;
  min-height: 34px;
  margin: 0;
  border: 0;
  border-radius: 999px;
  padding: 0 6px;
  font-weight: 800;
  font-size: 12px;
}

.scan-query-btn {
  background: #f6a4a4;
}

.scan-query-btn:hover,
.scan-query-btn:focus {
  background: #ef8f8f;
}

.scan-reset-btn {
  background: #fff;
  color: #3b82f6;
  box-shadow: inset 0 0 0 1px #bfdbfe;
}

.scan-reset-btn:hover,
.scan-reset-btn:focus {
  background: #eff6ff;
  color: #2563eb;
}

.scan-info-btn {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 50%;
  background: #eaf2ff;
  color: #3b82f6;
  font-size: 13px;
  font-weight: 900;
}

.scan-info-btn:active {
  background: #dbeafe;
}

.scan-dialog-content {
  display: grid;
  gap: 10px;
}

.mobile-scan-dialog :deep(.el-dialog) {
  border-radius: 16px;
}

.mobile-scan-dialog :deep(.el-dialog__body) {
  padding-top: 4px;
}

.mobile-camera-dialog :deep(.el-dialog) {
  max-width: 420px;
  border-radius: 16px;
}

.mobile-camera-dialog :deep(.el-dialog__body) {
  display: grid;
  gap: 12px;
  padding-top: 6px;
}

.camera-preview {
  position: relative;
  overflow: hidden;
  width: 100%;
  aspect-ratio: 3 / 4;
  max-height: 62vh;
  border-radius: 8px;
  background: #111827;
}

.camera-preview video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-frame {
  position: absolute;
  top: 50%;
  left: 50%;
  width: min(68vw, 250px);
  aspect-ratio: 1;
  border: 2px solid #ffffff;
  border-radius: 8px;
  box-shadow: 0 0 0 999px rgb(15 23 42 / 38%);
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.camera-tip {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
  text-align: center;
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

.scan-feedback {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #eff6ff;
  color: #475569;
  font-size: 12px;
  line-height: 1.35;
}

.scan-feedback strong {
  color: #172033;
  font-size: 14px;
}

.scan-feedback.success {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.scan-feedback.warning {
  border-color: #fde68a;
  background: #fffbeb;
}

.scan-feedback.danger {
  border-color: #fecaca;
  background: #fff1f2;
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

.queue-list {
  display: grid;
  gap: 10px;
}

.queue-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 54px;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border: 1px solid #e6eef8;
  border-radius: 12px;
  background: #fff;
}

.queue-row div {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.queue-row strong,
.queue-row small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-row strong {
  color: #172033;
  font-size: 13px;
}

.queue-row small {
  color: #64748b;
  font-size: 12px;
}

.queue-row button {
  min-height: 36px;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  background: #eff6ff;
  color: #1764e8;
  font-weight: 800;
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
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 10px;
}

.mobile-asset-dialog :deep(.el-dialog) {
  border-radius: 16px;
}

.mobile-asset-dialog :deep(.el-dialog__body) {
  padding-top: 4px;
  max-height: 72vh;
  overflow-y: auto;
}

.mobile-dialog-form {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #edf2f7;
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
}
</style>


