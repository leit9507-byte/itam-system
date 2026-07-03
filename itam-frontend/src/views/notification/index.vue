<template>
  <div class="notification-page">
    <section class="page-head">
      <div>
        <p class="eyebrow">系统设置</p>
        <h2>消息通知</h2>
        <p class="subtext">配置飞书自定义机器人 Webhook，用于接收系统待办、审批和运维提醒。</p>
      </div>
      <el-tag :type="form.enabled ? 'success' : 'info'" size="large">
        {{ form.enabled ? '已启用' : '未启用' }}
      </el-tag>
    </section>

    <div class="content-grid">
      <el-card class="panel" shadow="never">
        <template #header>
          <div class="panel-title">
            <span>飞书 Webhook</span>
            <el-switch v-model="form.enabled" active-text="启用" inactive-text="停用" />
          </div>
        </template>

        <el-form label-position="top" class="setting-form">
          <el-form-item label="Webhook 地址">
            <el-input
              v-model="form.webhook_url"
              clearable
              placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
            />
          </el-form-item>
          <el-form-item label="签名密钥">
            <el-input
              v-model="form.secret"
              clearable
              show-password
              placeholder="飞书机器人开启签名校验后填写，可留空"
            />
          </el-form-item>
          <el-form-item label="通知类型">
            <div class="event-list">
              <label v-for="item in eventOptions" :key="item.key" class="event-item">
                <el-switch v-model="form.event_types[item.key]" />
                <span>
                  <strong>{{ item.label }}</strong>
                  <em>{{ item.description }}</em>
                </span>
              </label>
            </div>
          </el-form-item>
          <el-form-item label="测试消息">
            <el-input
              v-model="testMessage"
              type="textarea"
              :rows="4"
              maxlength="500"
              show-word-limit
              placeholder="请输入要发送到飞书群的测试内容"
            />
          </el-form-item>
        </el-form>

        <div class="actions">
          <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
          <el-button :loading="testing" @click="handleTest">发送测试</el-button>
        </div>
      </el-card>

      <el-card class="panel guide" shadow="never">
        <template #header>
          <div class="panel-title">
            <span>配置引导</span>
          </div>
        </template>
        <ol class="steps">
          <li>在飞书群里添加“自定义机器人”，复制机器人 Webhook 地址。</li>
          <li>如果机器人启用了签名校验，把签名密钥填入“签名密钥”。</li>
          <li>按业务场景打开通知类型，保存后系统会在对应业务动作发生时自动发送。</li>
          <li>点击“发送测试”只校验 Webhook，不受总开关和类型开关限制。</li>
        </ol>
        <div class="status-box">
          <div>
            <span class="muted">最近测试</span>
            <strong>{{ lastStatusText }}</strong>
          </div>
          <p>{{ setting.last_test_message || '暂无测试记录' }}</p>
        </div>
      </el-card>
    </div>

    <el-card class="panel preview-panel" shadow="never">
      <template #header>
        <div class="panel-title">
          <span>发送格式预览</span>
          <el-segmented v-model="previewType" :options="previewTabs" />
        </div>
      </template>
      <div class="preview-layout">
        <div class="feishu-preview">
          <div class="bot-line">
            <span class="bot-avatar">飞</span>
            <div>
              <strong>资产管理系统</strong>
              <span>机器人</span>
            </div>
          </div>
          <pre>{{ activePreview?.message || '暂无预览' }}</pre>
        </div>
        <div class="preview-note">
          <strong>{{ activePreview?.label || '消息预览' }}</strong>
          <p>这里展示的是系统实际发送到飞书机器人的文本内容。飞书安全关键词校验会按这段文本匹配。</p>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getNotificationPreviews, getNotificationSetting, saveNotificationSetting, testNotification } from '../../api/notification'

const form = reactive({
  enabled: false,
  webhook_url: '',
  secret: '',
  event_types: {
    inbound: true,
    outbound: true,
    stocktake: true,
    risk: true
  }
})
const setting = reactive({
  last_test_status: '',
  last_test_message: ''
})
const saving = ref(false)
const testing = ref(false)
const previews = ref([])
const previewType = ref('inbound')
const testMessage = ref(`资产管理系统消息通知测试\n发送时间：${new Date().toLocaleString('zh-CN', { hour12: false })}`)
const eventOptions = [
  { key: 'inbound', label: '入库通知', description: '资产回收入库、扫码入库、验收入库后发送' },
  { key: 'outbound', label: '出库通知', description: '资产领用、借出、公用设备出库后发送' },
  { key: 'stocktake', label: '盘点通知', description: '盘点任务开始后发送任务范围和数量' },
  { key: 'risk', label: '风险通知', description: '审计发现风险时发送风险摘要' }
]

const lastStatusText = computed(() => {
  if (setting.last_test_status === 'success') return '发送成功'
  if (setting.last_test_status === 'failed') return '发送失败'
  return '未测试'
})
const previewTabs = computed(() => previews.value.map(item => ({ label: item.label, value: item.event_type })))
const activePreview = computed(() => previews.value.find(item => item.event_type === previewType.value) || previews.value[0])

onMounted(loadSetting)

async function loadSetting() {
  const [data, previewRows] = await Promise.all([
    getNotificationSetting(),
    getNotificationPreviews().catch(() => [])
  ])
  applySetting(data)
  previews.value = previewRows
  if (!previews.value.some(item => item.event_type === previewType.value) && previews.value.length) {
    previewType.value = previews.value[0].event_type
  }
}

async function handleSave() {
  saving.value = true
  try {
    const data = await saveNotificationSetting({
      enabled: form.enabled,
      webhook_url: form.webhook_url,
      secret: form.secret,
      event_types: { ...form.event_types }
    })
    applySetting(data)
    ElMessage.success('消息通知配置已保存')
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testing.value = true
  try {
    await handleSave()
    const data = await testNotification(testMessage.value)
    applySetting(data)
    ElMessage.success('测试消息已发送到飞书')
  } catch (error) {
    const message = error.response?.data?.detail || error.message || '测试消息发送失败'
    setting.last_test_status = 'failed'
    setting.last_test_message = message
    ElMessage.error(message)
  } finally {
    testing.value = false
  }
}

function applySetting(data = {}) {
  form.enabled = Boolean(data.enabled)
  form.webhook_url = data.webhook_url || ''
  form.secret = data.secret || ''
  form.event_types = {
    inbound: data.event_types?.inbound ?? true,
    outbound: data.event_types?.outbound ?? true,
    stocktake: data.event_types?.stocktake ?? true,
    risk: data.event_types?.risk ?? true
  }
  setting.last_test_status = data.last_test_status || ''
  setting.last_test_message = data.last_test_message || ''
}
</script>

<style scoped>
.notification-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #2f73ff;
  font-weight: 800;
}

h2 {
  margin: 0;
  color: #10244d;
  font-size: 28px;
}

.subtext {
  margin: 8px 0 0;
  color: #65758f;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.8fr);
  gap: 18px;
}

.panel {
  border: 1px solid #e6edf7;
  border-radius: 8px;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  color: #10244d;
  font-weight: 800;
}

.setting-form {
  max-width: 760px;
}

.actions {
  display: flex;
  gap: 10px;
}

.event-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

.event-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 72px;
  padding: 14px;
  border: 1px solid #e6edf7;
  border-radius: 8px;
  background: #f8fbff;
}

.event-item span {
  display: grid;
  gap: 4px;
}

.event-item strong {
  color: #10244d;
  line-height: 1.25;
}

.event-item em {
  color: #65758f;
  font-size: 13px;
  font-style: normal;
  line-height: 1.45;
}

.steps {
  display: grid;
  gap: 14px;
  margin: 0;
  padding-left: 20px;
  color: #394968;
  line-height: 1.7;
}

.status-box {
  margin-top: 22px;
  padding: 16px;
  border-radius: 8px;
  background: #f5f8fd;
}

.status-box div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.status-box p {
  margin: 10px 0 0;
  color: #65758f;
  word-break: break-word;
}

.preview-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 18px;
}

.feishu-preview {
  padding: 18px;
  border: 1px solid #e6edf7;
  border-radius: 8px;
  background: #f7f9fc;
}

.bot-line {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.bot-avatar {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #2f73ff;
  color: #fff;
  font-weight: 800;
}

.bot-line div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.bot-line strong {
  color: #10244d;
}

.bot-line span:last-child {
  color: #7d8ba3;
  font-size: 12px;
}

.feishu-preview pre {
  margin: 0;
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  border-radius: 8px;
  background: #fff;
  color: #20314f;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  line-height: 1.7;
}

.preview-note {
  padding: 16px;
  border-radius: 8px;
  background: #f5f8fd;
}

.preview-note strong {
  color: #10244d;
}

.preview-note p {
  margin: 10px 0 0;
  color: #65758f;
  line-height: 1.7;
}

.muted {
  color: #7d8ba3;
}

@media (max-width: 960px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .page-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .event-list {
    grid-template-columns: 1fr;
  }

  .preview-layout {
    grid-template-columns: 1fr;
  }
}
</style>
