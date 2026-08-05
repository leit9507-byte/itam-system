<template>
  <div class="page feishu-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">系统设置</p>
        <h1>飞书配置</h1>
        <p class="page-subtitle">管理移动端扫码所需的应用凭证和 JSAPI 运行状态。</p>
      </div>
      <el-tag :type="statusType" effect="light">{{ statusText }}</el-tag>
    </header>

    <section class="status-grid">
      <div class="status-item">
        <span>应用凭证</span>
        <strong>{{ form.app_id ? '已填写' : '未填写' }}</strong>
      </div>
      <div class="status-item">
        <span>App Secret</span>
        <strong>{{ secretConfigured ? '已保存' : '未保存' }}</strong>
      </div>
      <div class="status-item">
        <span>页面协议</span>
        <strong>{{ isSecureContext ? 'HTTPS' : runtimeProtocol.replace(':', '').toUpperCase() || '-' }}</strong>
      </div>
      <div class="status-item">
        <span>JS SDK</span>
        <strong>{{ sdkConfigured ? '已配置' : '未配置' }}</strong>
      </div>
    </section>

    <div class="content-grid">
      <el-card shadow="never" class="config-panel">
        <template #header>
          <div class="panel-heading">
            <div>
              <strong>应用凭证</strong>
              <span>飞书企业自建应用</span>
            </div>
            <el-switch v-model="form.enabled" inline-prompt active-text="启用" inactive-text="停用" />
          </div>
        </template>

        <el-form label-position="top" @submit.prevent="save">
          <el-form-item label="App ID" required>
            <el-input v-model="form.app_id" placeholder="cli_xxxxxxxxxxxxxxxx" autocomplete="off" />
          </el-form-item>
          <el-form-item label="App Secret" :required="!secretConfigured">
            <el-input
              v-model="form.app_secret"
              type="password"
              show-password
              autocomplete="new-password"
              :placeholder="secretConfigured ? '已配置，留空不会修改' : '填写飞书应用 App Secret'"
            />
          </el-form-item>
          <div class="form-actions">
            <el-button :loading="testing" :disabled="!configExists" @click="testConnection">测试连接</el-button>
            <el-button type="primary" native-type="submit" :loading="saving">保存配置</el-button>
          </div>
        </el-form>

        <el-alert
          v-if="lastTestMessage"
          class="test-result"
          :type="lastTestStatus === 'success' ? 'success' : 'error'"
          :title="lastTestMessage"
          show-icon
          :closable="false"
        />
      </el-card>

      <el-card shadow="never" class="runtime-panel">
        <template #header>
          <div class="panel-heading">
            <div>
              <strong>JSAPI 运行环境</strong>
              <span>当前生产页面</span>
            </div>
          </div>
        </template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="移动端地址">{{ mobileUrl }}</el-descriptions-item>
          <el-descriptions-item label="安全域名">{{ runtimeHost || '-' }}</el-descriptions-item>
          <el-descriptions-item label="SDK 地址">{{ sdkUrl || '未配置' }}</el-descriptions-item>
          <el-descriptions-item label="自动加载">{{ sdkAutoLoad ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="最近测试">{{ lastTestMessage || '尚未测试' }}</el-descriptions-item>
        </el-descriptions>
        <div class="runtime-actions">
          <el-button @click="openMobile">打开移动端</el-button>
          <el-button type="primary" plain @click="router.push('/notification')">消息通知</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { getFeishuConfig, saveFeishuConfig, testFeishuConfig } from '../../api/settings'

const router = useRouter()
const saving = ref(false)
const testing = ref(false)
const configExists = ref(false)
const secretConfigured = ref(false)
const lastTestStatus = ref('')
const lastTestMessage = ref('')
const form = reactive({ enabled: false, app_id: '', app_secret: '' })
const runtimeProtocol = typeof window !== 'undefined' ? window.location.protocol : ''
const runtimeHost = typeof window !== 'undefined' ? window.location.host : ''
const runtimeOrigin = typeof window !== 'undefined' ? window.location.origin : ''
const mobileUrl = import.meta.env.VITE_MOBILE_PUBLIC_URL || `${runtimeOrigin}/mobile`
const sdkUrl = import.meta.env.VITE_FEISHU_SDK_URL || ''
const sdkAutoLoad = import.meta.env.VITE_FEISHU_SDK_AUTO_LOAD === 'true'
const sdkConfigured = computed(() => Boolean(sdkUrl || sdkAutoLoad))
const isSecureContext = computed(() => runtimeProtocol === 'https:' || ['localhost', '127.0.0.1'].includes(runtimeHost.split(':')[0]?.toLowerCase()))
const statusText = computed(() => {
  if (!form.enabled) return '未启用'
  if (!form.app_id || !secretConfigured.value) return '待配置'
  if (lastTestStatus.value === 'success') return '连接正常'
  if (lastTestStatus.value === 'failed') return '连接失败'
  return '待测试'
})
const statusType = computed(() => ({ '连接正常': 'success', '连接失败': 'danger', '待配置': 'warning', '待测试': 'warning' })[statusText.value] || 'info')

onMounted(load)

async function load() {
  const result = await getFeishuConfig()
  configExists.value = Boolean(result.id)
  secretConfigured.value = Boolean(result.app_secret_configured)
  lastTestStatus.value = result.last_test_status || ''
  lastTestMessage.value = result.last_test_message || ''
  Object.assign(form, { enabled: Boolean(result.enabled), app_id: result.app_id || '', app_secret: '' })
}

async function save() {
  if (form.enabled && !form.app_id.trim()) return ElMessage.warning('请填写 App ID')
  if (form.enabled && !secretConfigured.value && !form.app_secret.trim()) return ElMessage.warning('请填写 App Secret')
  saving.value = true
  try {
    const result = await saveFeishuConfig({ ...form, app_id: form.app_id.trim(), app_secret: form.app_secret.trim() })
    configExists.value = Boolean(result.id)
    secretConfigured.value = Boolean(result.app_secret_configured)
    lastTestStatus.value = result.last_test_status || ''
    lastTestMessage.value = result.last_test_message || ''
    form.app_secret = ''
    ElMessage.success('飞书配置已保存')
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  try {
    const result = await testFeishuConfig()
    lastTestStatus.value = result.last_test_status || ''
    lastTestMessage.value = result.last_test_message || ''
    ElMessage[lastTestStatus.value === 'success' ? 'success' : 'warning'](lastTestMessage.value || '测试完成')
  } finally {
    testing.value = false
  }
}

function openMobile() {
  window.open(mobileUrl, '_blank', 'noopener,noreferrer')
}
</script>

<style scoped>
.feishu-page {
  display: grid;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid var(--el-border-color-light);
  background: #fff;
}

.status-item {
  min-width: 0;
  padding: 16px 18px;
  border-right: 1px solid var(--el-border-color-light);
}

.status-item:last-child {
  border-right: 0;
}

.status-item span,
.panel-heading span {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.status-item strong {
  display: block;
  margin-top: 6px;
  color: #14213d;
  font-size: 18px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 16px;
}

.config-panel,
.runtime-panel {
  border-radius: 6px;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.panel-heading strong {
  display: block;
  margin-bottom: 3px;
}

.form-actions,
.runtime-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.test-result,
.runtime-actions {
  margin-top: 18px;
}

@media (max-width: 900px) {
  .status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .status-item:nth-child(2) {
    border-right: 0;
  }

  .status-item:nth-child(-n + 2) {
    border-bottom: 1px solid var(--el-border-color-light);
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .page-header {
    align-items: flex-start;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }

  .status-item,
  .status-item:nth-child(2) {
    border-right: 0;
    border-bottom: 1px solid var(--el-border-color-light);
  }

  .status-item:last-child {
    border-bottom: 0;
  }

  .form-actions,
  .runtime-actions {
    flex-direction: column-reverse;
  }

  .form-actions :deep(.el-button),
  .runtime-actions :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }
}
</style>
