<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">权限与身份源</h2>
        <p class="page-subtitle">统一管理本地账号、LDAP/OIDC/SAML 登录、账号锁定和 RBAC 权限</p>
      </div>
      <div class="header-actions">
        <el-button @click="openLocalUserDialog">新增本地账户</el-button>
        <el-button type="primary" @click="syncFromProvider">从身份源同步用户</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="用户目录" name="users">
        <el-card shadow="never">
          <el-table :data="pagedUsers" border stripe>
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
              <template #default="{ row }"><el-tag :type="userStatusType(row.status)">{{ userStatusLabel(row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="230" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status === 'active'" link type="primary" @click="goAssetAssign(row)">资产分配</el-button>
                <el-button v-if="isInactiveUser(row.status)" link type="warning" @click="goAssetReclaim(row)">离职回收</el-button>
                <el-button link type="danger" :disabled="row.source !== 'local' || row.username === 'admin'" @click="removeUser(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="userPagination.page"
              v-model:page-size="userPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="users.length"
              layout="total, sizes, prev, pager, next, jumper"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="RBAC 权限" name="rbac">
        <el-card shadow="never">
          <el-table :data="pagedPermissions" border stripe>
            <el-table-column prop="role" label="角色" width="130" />
            <el-table-column prop="resource" label="资源" width="150" />
            <el-table-column prop="action" label="动作" width="120" />
            <el-table-column prop="allowed" label="允许" width="100">
              <template #default="{ row }"><el-tag :type="row.allowed ? 'success' : 'danger'">{{ row.allowed ? '允许' : '拒绝' }}</el-tag></template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="permissionPagination.page"
              v-model:page-size="permissionPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="permissions.length"
              layout="total, sizes, prev, pager, next, jumper"
            />
          </div>
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
                title="OpenLDAP 常用 uid/cn/mail/ou；AD 常用 sAMAccountName/displayName/mail/department。若报 invalid attribute sAMAccountName，请把 username_attr 和 user_filter 一起改为 uid。"
              />
              <el-form-item>
                <el-button @click="resetProviderForm">清空</el-button>
                <el-button type="primary" @click="saveProvider">保存配置</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>已配置身份源</template>
            <el-table :data="pagedProviders" border>
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
              <el-table-column label="操作" width="230">
                <template #default="{ row }">
                  <el-button link type="primary" @click="editProvider(row)">编辑</el-button>
                  <el-button link type="warning" @click="testProvider(row)">测试</el-button>
                  <el-button link type="success" @click="syncFromProvider(row)">同步</el-button>
                  <el-button link type="danger" @click="removeProvider(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-bar">
              <el-pagination
                v-model:current-page="providerPagination.page"
                v-model:page-size="providerPagination.pageSize"
                :page-sizes="[10, 20, 50, 100]"
                :total="providers.length"
                layout="total, sizes, prev, pager, next"
              />
            </div>
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

    <el-dialog v-model="accountDialog.visible" title="新增本地账户" width="560px">
      <el-form :model="accountDialog.form" label-width="90px">
        <el-form-item label="账号" required><el-input v-model="accountDialog.form.username" /></el-form-item>
        <el-form-item label="姓名" required><el-input v-model="accountDialog.form.display_name" /></el-form-item>
        <el-form-item label="密码" required><el-input v-model="accountDialog.form.password" type="password" show-password /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="accountDialog.form.email" /></el-form-item>
        <el-form-item label="部门编码"><el-input v-model="accountDialog.form.dept_id" /></el-form-item>
        <el-form-item label="部门名称"><el-input v-model="accountDialog.form.dept_name" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="accountDialog.form.role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="审计员" value="auditor" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="accountDialog.form.status" style="width: 100%">
            <el-option label="在职" value="active" />
            <el-option label="停用" value="disabled" />
            <el-option label="离职" value="resigned" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="accountDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitLocalUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '../../store'
import {
  createIdentityProvider,
  deleteUser,
  deleteIdentityProvider,
  getIdentityProviders,
  getRolePermissions,
  getUsers,
  login,
  saveUser,
  startSso,
  syncUsers,
  testIdentityProvider,
  updateIdentityProvider
} from '../../api/user'

const activeTab = ref('users')
const router = useRouter()
const store = useAppStore()
const users = ref([])
const providers = ref([])
const permissions = ref([])
const loginResult = ref(null)
const providerConfigText = ref('')
const providerForm = reactive(defaultProviderForm())
const loginForm = reactive({ provider: 'local', username: 'admin', password: 'admin' })
const accountDialog = reactive({ visible: false, form: defaultLocalUserForm() })
const userPagination = reactive({ page: 1, pageSize: 20 })
const permissionPagination = reactive({ page: 1, pageSize: 20 })
const providerPagination = reactive({ page: 1, pageSize: 20 })
const pagedUsers = computed(() => paginate(users.value, userPagination))
const pagedPermissions = computed(() => paginate(permissions.value, permissionPagination))
const pagedProviders = computed(() => paginate(providers.value, providerPagination))

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

function defaultLocalUserForm() {
  return {
    username: '',
    display_name: '',
    password: '',
    email: '',
    dept_id: '',
    dept_name: '',
    role: 'user',
    status: 'active'
  }
}

function openLocalUserDialog() {
  Object.assign(accountDialog.form, defaultLocalUserForm())
  accountDialog.visible = true
}

async function submitLocalUser() {
  if (!accountDialog.form.username.trim() || !accountDialog.form.display_name.trim() || !accountDialog.form.password) {
    ElMessage.warning('请填写账号、姓名和密码')
    return
  }
  const createdUser = await saveUser(accountDialog.form)
  accountDialog.visible = false
  try {
    await ElMessageBox.confirm('入职账户已创建。是否现在进入资产管理，为该员工分配设备？', '入职提醒', {
      confirmButtonText: '去资产分配',
      cancelButtonText: '稍后处理',
      type: 'success'
    })
    goAssetAssign(createdUser || accountDialog.form)
  } catch {
    ElMessage.success('入职账户已创建，请后续在用户目录中执行资产分配')
  }
  await loadUsers()
}

function userStatusLabel(status) {
  return {
    active: '在职',
    disabled: '停用',
    resigned: '离职',
    inactive: '停用',
    locked: '锁定',
    left: '离职',
    offboarded: '离职'
  }[status] || status || '-'
}

function userStatusType(status) {
  if (status === 'active') return 'success'
  if (isInactiveUser(status)) return 'warning'
  return 'info'
}

function isInactiveUser(status) {
  return ['inactive', 'disabled', 'locked', 'resigned', 'left', 'offboarded', '离职', '停用', '禁用'].includes(String(status || '').toLowerCase())
}

function goAssetAssign(row) {
  router.push({ path: '/asset/list', query: { action: 'assign', user_id: row.user_id, username: row.username, name: row.display_name } })
}

function goAssetReclaim(row) {
  router.push({ path: '/asset/list', query: { action: 'reclaim', user_id: row.user_id, username: row.username, name: row.display_name } })
}

async function removeUser(row) {
  if (row.source !== 'local') {
    ElMessage.warning('LDAP / 飞书同步账户不能手动删除，请通过身份源同步标记离职')
    return
  }
  if (row.username === 'admin') {
    ElMessage.warning('内置管理员账户不能删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除账户“${row.display_name || row.username}”吗？`, '删除账户', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteUser(row.user_id)
  ElMessage.success('账户已删除')
  await loadUsers()
}

function defaultConfig(type = 'ldap') {
  const samples = {
    ldap: {
      host: '',
      port: null,
      use_ssl: false,
      start_tls: false,
      tls_validate: false,
      bind_dn: '',
      bind_password: '',
      base_dn: '',
      user_filter: '',
      sync_filter: '',
      username_attr: '',
      display_name_attr: '',
      email_attr: '',
      dept_id_attr: '',
      dept_name_attr: '',
      default_role: 'user',
      sync_limit: 200,
      test_username: ''
    },
    oidc: {
      issuer: '',
      authorization_endpoint: '',
      client_id: '',
      redirect_uri: '',
      scopes: ''
    },
    saml: { sso_url: '', entity_id: '' },
    feishu: {
      app_id: '',
      app_secret: '',
      root_department_id: '0',
      department_id_type: 'open_department_id',
      user_id_type: 'user_id',
      default_role: 'user',
      sync_limit: 200,
      department_limit: 200,
      page_size: 50
    },
    wechat_work: { corp_id: '', agent_id: '' }
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

async function removeProvider(row) {
  try {
    await ElMessageBox.confirm(`确认删除身份源“${row.name}”？删除后不会影响已同步用户。`, '删除身份源', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteIdentityProvider(row.id)
  if (providerForm.id === row.id) resetProviderForm()
  ElMessage.success('身份源已删除')
  await loadProviders()
}

async function syncFromProvider(row = null) {
  const provider = row?.id ? row : providers.value.find(item => item.enabled)
  if (!provider) {
    ElMessage.warning('请先配置并启用一个身份源')
    return
  }
  if (!['ldap', 'feishu'].includes(provider.provider_type)) {
    ElMessage.warning('当前仅 LDAP 和飞书身份源支持从目录同步用户')
    return
  }
  const result = await syncUsers({ provider_id: provider?.id })
  ElMessage.success(`同步完成：新增 ${result.created} 人，更新 ${result.updated} 人，标记离职 ${result.offboarded || 0} 人`)
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

function paginate(rows, pagination) {
  const start = (pagination.page - 1) * pagination.pageSize
  return rows.slice(start, start + pagination.pageSize)
}
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

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

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 1100px) {
  .provider-grid {
    grid-template-columns: 1fr;
  }
}
</style>
