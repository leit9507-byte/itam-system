<template>
  <el-header class="header">
    <div class="header-left">
      <el-button class="collapse-button" :icon="store.collapsed ? Expand : Fold" circle @click="store.toggleSidebar()" />
      <div class="title-block">
        <h1>{{ route.meta.title || 'ITAM Dashboard' }}</h1>
        <p>企业 IT 资产全生命周期管理后台</p>
      </div>
    </div>

    <div class="header-right">
      <el-tag class="status-tag" type="success" effect="light">
        <span class="status-dot status-ok" />前端运行中
      </el-tag>
      <el-tag class="status-tag" :type="backendOnline ? 'success' : 'danger'" effect="light">
        <span class="status-dot" :class="backendOnline ? 'status-ok' : 'status-error'" />{{ backendLabel }}
      </el-tag>
      <el-tag class="status-tag" type="info" effect="light">容器部署</el-tag>
      <span class="today">{{ today }}</span>
      <el-divider direction="vertical" />

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
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Expand, Fold } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../store'
import request from '../utils/request'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const backendOnline = ref(false)
const backendLabel = ref('后端检测中')

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

onMounted(async () => {
  try {
    const result = await request.get('/')
    backendOnline.value = Boolean(result?.ok)
    backendLabel.value = backendOnline.value ? '后端已连接' : '后端异常'
  } catch {
    backendOnline.value = false
    backendLabel.value = '后端未连接'
  }
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
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 64px;
  min-width: 0;
  border-bottom: 1px solid var(--line);
  background: #fff;
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
  font-size: 18px;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

p {
  overflow: hidden;
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-tag {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.status-dot {
  width: 7px;
  height: 7px;
  margin-right: 6px;
  border-radius: 50%;
}

.status-ok {
  background: #16a34a;
}

.status-error {
  background: #dc2626;
}

.today {
  flex-shrink: 0;
  color: var(--muted);
  font-size: 13px;
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
  background: var(--primary);
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
  .today,
  .user-block {
    display: none;
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
}
</style>
