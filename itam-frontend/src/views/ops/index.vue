<template>
  <div class="page ops-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">运维面板</h2>
        <p class="page-subtitle">健康检查、定时任务、备份恢复脚本和数据库配置状态</p>
      </div>
      <el-button type="primary" @click="loadAll">刷新</el-button>
    </div>

    <div class="ops-grid">
      <el-card shadow="never">
        <template #header>健康检查</template>
        <el-descriptions v-if="health" :column="1" border>
          <el-descriptions-item label="服务">{{ health.service }}</el-descriptions-item>
          <el-descriptions-item label="检查时间">{{ health.checked_at }}</el-descriptions-item>
          <el-descriptions-item label="数据库">
            <el-tag :type="health.database?.ok ? 'success' : 'danger'">{{ health.database?.message }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="上传目录">
            {{ health.upload_dir?.exists ? '正常' : '不存在' }} / {{ health.upload_dir?.path }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>定时任务</template>
        <el-table :data="jobs" border>
          <el-table-column prop="name" label="任务" min-width="160" />
          <el-table-column prop="schedule" label="计划" width="130" />
          <el-table-column prop="status" label="状态" width="110" />
        </el-table>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>数据库配置</span>
          <el-tag v-if="dbConfig.source === 'saved'" type="warning">已保存，重启后生效</el-tag>
          <el-tag v-else type="info">使用环境变量</el-tag>
        </div>
      </template>
      <el-alert
        type="warning"
        :closable="false"
        title="正式环境不建议运行中热切数据库。这里会先测试连接，再保存配置；保存后需要重启后端容器，所有 worker 才会使用新数据库。"
        class="config-alert"
      />
      <el-form :model="dbForm" label-width="112px" class="db-form">
        <el-form-item label="当前连接">
          <el-input :model-value="dbConfig.runtime_url || '-'" readonly />
        </el-form-item>
        <div class="db-grid">
          <el-form-item label="数据库主机" required><el-input v-model.trim="dbForm.host" placeholder="例如 mysql 或 10.0.0.12" /></el-form-item>
          <el-form-item label="端口" required><el-input-number v-model="dbForm.port" :min="1" :max="65535" style="width: 100%" /></el-form-item>
          <el-form-item label="数据库名" required><el-input v-model.trim="dbForm.database" /></el-form-item>
          <el-form-item label="用户名" required><el-input v-model.trim="dbForm.username" /></el-form-item>
          <el-form-item label="密码"><el-input v-model="dbForm.password" show-password placeholder="留空表示空密码；保存后会隐藏" /></el-form-item>
          <el-form-item label="字符集"><el-input v-model.trim="dbForm.charset" placeholder="utf8mb4" /></el-form-item>
          <el-form-item label="数据库时区（UTC）"><el-input v-model.trim="dbForm.timezone" disabled /></el-form-item>
          <el-form-item label="连接超时"><el-input-number v-model="dbForm.connect_timeout" :min="1" :max="120" style="width: 100%" /></el-form-item>
          <el-form-item label="连接池大小"><el-input-number v-model="dbForm.pool_size" :min="1" :max="200" style="width: 100%" /></el-form-item>
          <el-form-item label="溢出连接数"><el-input-number v-model="dbForm.max_overflow" :min="0" :max="500" style="width: 100%" /></el-form-item>
        </div>
      </el-form>
      <div class="db-actions">
        <el-button :loading="testingDb" @click="handleTestDatabase">测试连接</el-button>
        <el-button type="primary" :loading="savingDb" @click="handleSaveDatabase">保存数据库配置</el-button>
      </div>
      <el-alert
        v-if="dbTest.message"
        class="test-result"
        :type="dbTest.ok ? 'success' : 'error'"
        :title="dbTest.ok ? `连接成功：${dbTest.database || dbForm.database} / ${dbTest.version || ''}` : dbTest.message"
        show-icon
        :closable="false"
      />
      <el-divider />
      <div class="init-panel">
        <div>
          <strong>数据库初始化</strong>
          <p>当前 {{ dbStatus.table_count || 0 }} 张表；初始化会创建基础表并补齐管理员、权限、审计规则、通知配置、故障类型和产品基础资料。</p>
        </div>
        <el-input v-model="initToken" show-password placeholder="INIT_DATABASE_TOKEN" class="init-token" />
        <el-checkbox v-model="initForce">强制补齐种子数据</el-checkbox>
        <el-button type="warning" :loading="initializingDb" @click="handleInitDatabase">初始化数据库</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>备份恢复</template>
      <el-alert type="info" :closable="false" title="正式环境可使用 scripts/backup.ps1 备份数据库与上传目录，使用 scripts/restore.ps1 按备份文件恢复。" />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDatabaseConfig, getDatabaseStatus, getOpsHealth, getScheduledJobs, initDatabase, saveDatabaseConfig, testDatabaseConfig } from '../../api/ops'

const health = ref(null)
const jobs = ref([])
const dbConfig = ref({})
const dbForm = ref(defaultDbForm())
const dbTest = ref({})
const testingDb = ref(false)
const savingDb = ref(false)
const dbStatus = ref({})
const initToken = ref('')
const initForce = ref(true)
const initializingDb = ref(false)

onMounted(loadAll)

async function loadAll() {
  const [healthResult, jobsResult, dbConfigResult, dbStatusResult] = await Promise.all([
    getOpsHealth().catch(err => { console.error('加载健康检查失败', err); return null }),
    getScheduledJobs().catch(err => { console.error('加载定时任务失败', err); return [] }),
    getDatabaseConfig().catch(err => { console.error('加载数据库配置失败', err); return {} }),
    getDatabaseStatus().catch(err => { console.error('加载数据库状态失败', err); return {} })
  ])
  health.value = healthResult
  jobs.value = jobsResult
  dbConfig.value = dbConfigResult
  dbStatus.value = dbStatusResult
  dbForm.value = normalizeDbForm(dbConfigResult)
}

function defaultDbForm() {
  return {
    host: '',
    port: 3306,
    database: '',
    username: '',
    password: '',
    charset: 'utf8mb4',
    timezone: '+00:00',
    pool_size: 10,
    max_overflow: 20,
    pool_recycle: 1800,
    pool_timeout: 30,
    connect_timeout: 10
  }
}

function normalizeDbForm(config = {}) {
  return {
    ...defaultDbForm(),
    host: config.host || '',
    port: Number(config.port || 3306),
    database: config.database || '',
    username: config.username || '',
    password: config.password || '',
    charset: config.charset || 'utf8mb4',
    timezone: '+00:00',
    pool_size: Number(config.pool_size || 10),
    max_overflow: Number(config.max_overflow || 20),
    pool_recycle: Number(config.pool_recycle || 1800),
    pool_timeout: Number(config.pool_timeout || 30),
    connect_timeout: Number(config.connect_timeout || 10)
  }
}

async function handleTestDatabase() {
  testingDb.value = true
  try {
    dbTest.value = await testDatabaseConfig(dbForm.value)
    ElMessage[dbTest.value.ok ? 'success' : 'error'](dbTest.value.message)
  } finally {
    testingDb.value = false
  }
}

async function handleSaveDatabase() {
  savingDb.value = true
  try {
    const result = await saveDatabaseConfig(dbForm.value)
    dbConfig.value = result
    dbForm.value = normalizeDbForm(result)
    dbTest.value = result.test || {}
    ElMessage.success('数据库配置已保存，请重启后端容器使配置生效')
  } finally {
    savingDb.value = false
  }
}

async function handleInitDatabase() {
  initializingDb.value = true
  try {
    const result = await initDatabase({ force: initForce.value }, initToken.value)
    dbStatus.value = result
    ElMessage.success(result.message || '数据库初始化完成')
    await loadAll()
  } finally {
    initializingDb.value = false
  }
}
</script>

<style scoped>
.ops-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}

.card-header,
.db-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.config-alert,
.test-result {
  margin-bottom: 14px;
}

.db-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

.db-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.init-panel {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(220px, 320px) auto auto;
  align-items: center;
  gap: 12px;
}

.init-panel p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

@media (max-width: 900px) {
  .ops-grid,
  .db-grid,
  .init-panel {
    grid-template-columns: 1fr;
  }

  .db-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
