<template>
  <el-header class="header">
    <div class="header-left">
      <el-button class="collapse-button" :icon="store.collapsed ? Expand : Fold" circle @click="store.toggleSidebar()" />
      <div class="title-block">
        <h1>{{ pageTitle }}</h1>
        <p>企业 IT 资产全生命周期管理后台</p>
      </div>
    </div>

    <div class="header-right">
      <el-input v-model="keyword" class="global-search" placeholder="搜索资产、编号、序列号..." clearable @keyup.enter="goSearch">
        <template #suffix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-popover placement="bottom-end" width="380" trigger="click" @show="loadPendingTodos">
        <template #reference>
          <button class="notify-button" type="button" :title="todoCount ? `${todoCount} 个待处理事项` : '暂无待处理事项'">
            <el-icon><Bell /></el-icon>
            <span v-if="todoCount">{{ displayTodoCount }}</span>
          </button>
        </template>
        <div class="notify-panel">
          <div class="notify-panel-head">
            <strong>待处理事项</strong>
            <el-button link type="primary" :loading="todoLoading" @click="loadPendingTodos">刷新</el-button>
          </div>
          <el-empty v-if="!todoLoading && !pendingTodos.length" description="暂无需要处理的事项" :image-size="72" />
          <div v-else class="notify-list">
            <button v-for="item in topPendingTodos" :key="item.id" type="button" class="notify-row" @click="goTodo(item)">
              <el-tag :type="priorityType(item.priority)" size="small">{{ priorityLabel(item.priority) }}</el-tag>
              <div>
                <strong>{{ item.title }}</strong>
                <span>{{ item.type_label }} / {{ item.status }}</span>
              </div>
            </button>
          </div>
          <el-button v-if="pendingTodos.length" class="notify-more" type="primary" plain @click="router.push('/todo')">查看全部 {{ pendingTodos.length }} 项</el-button>
        </div>
      </el-popover>
      <TodoAssetActions ref="todoAssetActionsRef" @completed="loadPendingTodos" />

      <el-dropdown trigger="click" @command="handleUserCommand">
        <button class="user-trigger">
          <el-avatar class="avatar" :size="32">{{ avatarText }}</el-avatar>
          <div class="user-block">
            <strong>{{ store.user.name }}</strong>
            <span>{{ roleLabel }}</span>
          </div>
          <el-icon><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>{{ store.user.username || store.user.source }}</el-dropdown-item>
            <el-dropdown-item command="permission">身份与权限</el-dropdown-item>
            <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-header>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Bell, Expand, Fold, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../store'
import { getTodoItems } from '../api/todo'
import request from '../utils/request'
import TodoAssetActions from '../components/TodoAssetActions.vue'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const backendOnline = ref(false)
const backendLabel = ref('后端检测中')
const keyword = ref('')
const pendingTodos = ref([])
const todoLoading = ref(false)
const todoAssetActionsRef = ref(null)
let todoTimer = null

const today = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  weekday: 'short'
}).format(new Date())

const roleLabel = computed(() => {
  const labels = {
    admin: '系统管理员',
    auditor: '审计员',
    user: '普通用户',
    guest: '未登录'
  }
  return labels[store.user.role] || store.user.role
})

const avatarText = computed(() => (store.user.name || 'U').slice(0, 1).toUpperCase())
const pageTitle = computed(() => (route.path === '/dashboard' ? '资产管理系统' : route.meta.title || 'ITAM Dashboard'))
const todoCount = computed(() => pendingTodos.value.length)
const displayTodoCount = computed(() => (todoCount.value > 99 ? '99+' : todoCount.value))
const topPendingTodos = computed(() => pendingTodos.value.slice(0, 5))

onMounted(async () => {
  try {
    const result = await request.get('/')
    backendOnline.value = Boolean(result?.ok)
    backendLabel.value = backendOnline.value ? '后端已连接' : '后端异常'
  } catch {
    backendOnline.value = false
    backendLabel.value = '后端未连接'
  }
  await loadPendingTodos()
  todoTimer = window.setInterval(loadPendingTodos, 60000)
})

onUnmounted(() => {
  if (todoTimer) window.clearInterval(todoTimer)
})

function handleUserCommand(command) {
  if (command === 'logout') {
    store.logout()
    ElMessage.success('已退出登录')
    router.replace('/login')
  }
  if (command === 'permission') {
    router.push('/permission')
  }
}

function goSearch() {
  const value = keyword.value.trim()
  router.push({ path: '/asset/list', query: value ? { keyword: value } : {} })
}

async function loadPendingTodos() {
  todoLoading.value = true
  try {
    pendingTodos.value = await getTodoItems()
  } catch {
    pendingTodos.value = []
  } finally {
    todoLoading.value = false
  }
}

async function goTodo(item) {
  if (await todoAssetActionsRef.value?.handle(item)) return
  router.push({ path: item.target_path || '/todo', query: item.target_query || {} })
}

function priorityLabel(priority) {
  return { high: '高', medium: '中', low: '低' }[priority] || '待办'
}

function priorityType(priority) {
  return { high: 'danger', medium: 'warning', low: 'info' }[priority] || 'info'
}
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 76px;
  min-width: 0;
  border-bottom: 1px solid var(--line);
  background: #fff;
  box-shadow: 0 6px 18px rgba(22, 44, 82, 0.06);
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.header-left {
  flex: 1;
}

.header-right {
  flex-shrink: 0;
}

.collapse-button {
  flex: 0 0 auto;
}

.title-block {
  min-width: 0;
}

h1 {
  overflow: hidden;
  margin: 0;
  color: var(--text);
  font-size: 26px;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

p {
  display: none;
}

.global-search {
  width: 360px;
}

:deep(.global-search .el-input__wrapper) {
  min-height: 44px;
  border-radius: 10px;
  box-shadow: 0 0 0 1px #dbe4f3 inset;
}

.notify-button {
  position: relative;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 50%;
  background: #f2f7ff;
  color: #0f4ea8;
  font-size: 22px;
  cursor: pointer;
}

.notify-button span {
  position: absolute;
  top: -4px;
  right: -2px;
  display: grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #ff3347;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.notify-panel {
  display: grid;
  gap: 10px;
}

.notify-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.notify-panel-head strong {
  color: var(--text);
}

.notify-list {
  display: grid;
  gap: 8px;
}

.notify-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 10px;
  width: 100%;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.notify-row:hover {
  border-color: #93c5fd;
  background: #f8fbff;
}

.notify-row strong,
.notify-row span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notify-row strong {
  color: var(--text);
  font-size: 13px;
}

.notify-row span {
  margin-top: 3px;
  color: var(--muted);
  font-size: 12px;
}

.notify-more {
  width: 100%;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.avatar {
  flex-shrink: 0;
  background: linear-gradient(135deg, #0c4da2, #2478ff);
}

.user-block {
  display: grid;
  gap: 2px;
  min-width: 72px;
  text-align: left;
}

.user-block strong {
  color: var(--text);
  font-size: 13px;
}

.user-block span {
  color: var(--muted);
  font-size: 12px;
}

@media (max-width: 1060px) {
  .user-block {
    display: none;
  }

  .global-search {
    width: 260px;
  }
}

@media (max-width: 760px) {
  .header {
    height: auto;
    min-height: 64px;
    align-items: stretch;
    flex-direction: column;
    padding-top: 10px;
    padding-bottom: 10px;
  }

  .header-left,
  .header-right {
    width: 100%;
  }

  .header-right {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .global-search {
    width: 100%;
  }
}
</style>
