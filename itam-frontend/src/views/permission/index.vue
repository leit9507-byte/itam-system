<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">权限与身份源</h2>
        <p class="page-subtitle">统一管理本地账号、LDAP/OIDC/SAML 登录、账号锁定和 RBAC 权限</p>
      </div>
      <el-button type="primary" @click="syncFromProvider">从身份源同步用户</el-button>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="用户目录" name="users">
        <el-card shadow="never">
          <el-table :data="users" border stripe>
            <el-table-column prop="display_name" label="姓名" min-width="130" />
            <el-table-column prop="username" label="账号" min-width="120" />
            <el-table-column prop="email" label="邮箱" min-width="180" />
            <el-table-column prop="dept_name" label="部门" min-width="140">
              <template #default="{ row }">{{ row.dept_name || row.dept_id || '-' }}</template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="100">
              <template #default="{ row }"><el-tag>{{ row.source }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="role" label="角色" width="120" />
            <el-table-column prop="failed_login_count" label="失败次数" width="100" />
            <el-table-column prop="locked_until" label="锁定至" min-width="160">
              <template #default="{ row }">{{ row.locked_until || '未锁定' }}</template>
            </el-table-column>
            <el-table-column prop="last_login_at" label="最后登录" min-width="160">
              <template #default="{ row }">{{ row.last_login_at || '-' }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="RBAC 权限" name="rbac">
        <el-card shadow="never">
          <el-table :data="permissions" border stripe>
            <el-table-column prop="role" label="角色" width="130" />
            <el-table-column prop="resource" label="资源" width="150" />
            <el-table-column prop="action" label="动作" width="120" />
            <el-table-column prop="allowed" label="允许" width="100">
              <template #default="{ row }"><el-tag :type="row.allowed ? 'success' : 'danger'">{{ row.allowed ? '允许' : '拒绝' }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="身份源配置" name="providers">
        <div class="provider-grid">
          <el-card shadow="never">
            <template #header>新增/编辑身份源</template>
            <el-form :model="providerForm" label-width="110px">
              <el-form-item label="名称"><el-input v-model="providerForm.name" placeholder="例如：公司 LDAP" /></el-form-item>
              <el-form-item label="类型">
                <el-select v-model="providerForm.provider_type" style="width: 100%">
                  <el-option label="LDAP / AD" value="ldap" />
                  <el-option label="OIDC" value="oidc" />
                  <el-option label="SAML" value="saml" />
                  <el-option label="飞书" value="feishu" />
                  <el-option label="企业微信" value="wechat_work" />
                </el-select>
              </el-form-item>
              <el-form-item label="启用"><el-switch v-model="providerForm.enabled" /></el-form-item>
              <el-form-item label="连接配置">
                <el-input v-model="providerConfigText" type="textarea" :rows="16" />
              </el-form-item>
              <el-alert
                v-if="providerForm.provider_type === 'ldap'"
                class="config-help"
                type="info"
                show-icon
                :closable="false"
                title="OpenLDAP 常用 uid/cn/mail/ou；AD 常用 sAMAccountName/displayName/mail/department。若某字段报 invalid attribute type，请改成真实存在的属性或留空。"
              />
              <el-form-item>
                <el-button @click="resetProviderForm">清空</el-button>
                <el-button type="primary" @click="saveProvider">保存配置</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>已配置身份源</template>
            <el-table :data="providers" border>
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="provider_type" label="类型" width="110" />
              <el-table-column prop="enabled" label="启用" width="80">
                <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '是' : '否' }}</el-tag></template>
              </el-table-column>
              <el-table-column prop="last_test_status" label="测试状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="row.last_test_status === 'success' ? 'success' : row.last_test_status === 'failed' ? 'danger' : 'info'">{{ row.last_test_status || '-' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="last_test_message" label="测试信息" min-width="220" show-overflow-tooltip />
              <el-table-column label="操作" width="190">
                <template #default="{ row }">
                  <el-button link type="primary" @click="editProvider(row)">编辑</el-button>
                  <el-button link type="warning" @click="testProvider(row)">测试</el-button>
                  <el-button link type="success" @click="syncFromProvider(row)">同步</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="登录测试" name="login">
        <el-card shadow="never" class="login-card">
          <el-form :model="loginForm" label-width="100px">
            <el-form-item label="登录方式">
              <el-radio-group v-model="loginForm.provider">
                <el-radio-button label="local">本地</el-radio-button>
                <el-radio-button label="ldap">LDAP</el-radio-button>
                <el-radio-button label="oidc">OIDC</el-radio-button>
                <el-radio-button label="saml">SAML</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="账号"><el-input v-model="loginForm.username" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="loginForm.password" type="password" show-password /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="submitLogin">账号登录</el-button>
              <el-button @click="submitSso">SSO 跳转地址</el-button>
            </el-form-item>
          </el-form>
          <el-descriptions v-if="loginResult" title="登录结果" border :column="1">
            <el-descriptions-item label="Token">{{ loginResult.access_token }}</el-descriptions-item>
            <el-descriptions-item label="有效期">{{ loginResult.expires_in }} 秒</el-descriptions-item>
            <el-descriptions-item label="用户">{{ loginResult.user.display_name }} / {{ loginResult.user.role }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ loginResult.user.source }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../../store'
import {
  createIdentityProvider,
  getIdentityProviders,
  getRolePermissions,
  getUsers,
  login,
  startSso,
  syncUsers,
  testIdentityProvider,
  updateIdentityProvider
} from '../../api/user'

const activeTab = ref('users')
const store = useAppStore()
const users = ref([])
const providers = ref([])
const permissions = ref([])
const loginResult = ref(null)
const providerConfigText = ref('')
const providerForm = reactive(defaultProviderForm())
const loginForm = reactive({ provider: 'local', username: 'admin', password: 'admin' })

onMounted(async () => {
  await Promise.all([loadUsers(), loadProviders(), loadPermissions()])
  resetProviderForm()
})

watch(
  () => providerForm.provider_type,
  type => {
    if (!providerForm.id) {
      providerConfigText.value = JSON.stringify(defaultConfig(type), null, 2)
    }
  }
)

async function loadUsers() {
  users.value = await getUsers()
}

async function loadProviders() {
  providers.value = await getIdentityProviders()
}

async function loadPermissions() {
  permissions.value = await getRolePermissions()
}

function defaultProviderForm() {
  return { id: null, name: '', provider_type: 'ldap', enabled: true }
}

function defaultConfig(type = 'ldap') {
  const samples = {
    ldap: {
      host: 'ldap://ldap.example.com',
      port: 389,
      use_ssl: false,
      start_tls: false,
      tls_validate: false,
      bind_dn: 'CN=ldap-reader,OU=Service Accounts,DC=example,DC=com',
      bind_password: 'change-me',
      base_dn: 'DC=example,DC=com',
      user_filter: '(&(objectClass=person)(uid={username}))',
      sync_filter: '(objectClass=person)',
      username_attr: 'uid',
      display_name_attr: 'cn',
      email_attr: 'mail',
      dept_id_attr: 'ou',
      dept_name_attr: 'ou',
      default_role: 'user',
      sync_limit: 200,
      test_username: ''
    },
    oidc: {
      issuer: 'https://sso.example.com',
      authorization_endpoint: 'https://sso.example.com/oauth2/authorize',
      client_id: 'itam-dashboard',
      redirect_uri: 'http://127.0.0.1:8000/auth/callback/oidc',
      scopes: 'openid profile email'
    },
    saml: { sso_url: 'https://sso.example.com/saml/login', entity_id: 'itam-dashboard' },
    feishu: { app_id: 'cli_xxx', tenant_key: 'tenant_xxx' },
    wechat_work: { corp_id: 'ww_xxx', agent_id: '1000001' }
  }
  return samples[type] || {}
}

function resetProviderForm() {
  Object.assign(providerForm, defaultProviderForm())
  providerConfigText.value = JSON.stringify(defaultConfig(providerForm.provider_type), null, 2)
}

function editProvider(row) {
  Object.assign(providerForm, { id: row.id, name: row.name, provider_type: row.provider_type, enabled: row.enabled })
  providerConfigText.value = JSON.stringify(row.config || defaultConfig(row.provider_type), null, 2)
}

async function saveProvider() {
  let config = {}
  try {
    config = JSON.parse(providerConfigText.value || '{}')
  } catch {
    ElMessage.error('连接配置必须是合法 JSON')
    return
  }
  const payload = {
    name: providerForm.name,
    provider_type: providerForm.provider_type,
    enabled: providerForm.enabled,
    config
  }
  if (providerForm.id) await updateIdentityProvider(providerForm.id, payload)
  else await createIdentityProvider(payload)
  ElMessage.success('身份源配置已保存')
  await loadProviders()
}

async function testProvider(row) {
  const result = await testIdentityProvider(row.id)
  ElMessage[result.last_test_status === 'success' ? 'success' : 'warning'](result.last_test_message)
  await loadProviders()
}

async function syncFromProvider(row = null) {
  const provider = row?.id ? row : providers.value.find(item => item.enabled)
  const result = await syncUsers({ provider_id: provider?.id })
  ElMessage.success(`同步完成：新增 ${result.created} 人，更新 ${result.updated} 人`)
  await loadUsers()
}

async function submitLogin() {
  loginResult.value = await login(loginForm)
  store.setSession(loginResult.value)
  ElMessage.success('登录成功，JWT 已写入本地会话')
  await loadUsers()
}

async function submitSso() {
  const result = await startSso(loginForm.provider)
  ElMessage.success(result.message)
}
</script>

<style scoped>
.provider-grid {
  display: grid;
  grid-template-columns: minmax(400px, 0.9fr) minmax(520px, 1.1fr);
  gap: 16px;
}

.config-help {
  margin: -4px 0 16px;
}

.login-card {
  max-width: 760px;
}

@media (max-width: 1100px) {
  .provider-grid {
    grid-template-columns: 1fr;
  }
}
</style>
