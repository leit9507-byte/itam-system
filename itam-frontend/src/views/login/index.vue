<template>
  <main class="login-page">
    <section class="login-shell">
      <div class="brand-side">
        <div class="brand-head">
          <span class="brand-mark">IT</span>
          <div>
            <h1>资产管理系统</h1>
            <p>企业 IT 资产全生命周期管理后台</p>
          </div>
        </div>

        <div class="brand-copy">
          <strong>统一管理资产、人员、流程和审计</strong>
          <span>覆盖采购入库、领用归还、维修、盘点、报废和报告审计，让资产状态清晰可追踪。</span>
        </div>

        <div class="capability-grid">
          <div v-for="item in capabilities" :key="item.title" class="capability-item">
            <el-icon><component :is="item.icon" /></el-icon>
            <div>
              <strong>{{ item.title }}</strong>
              <span>{{ item.desc }}</span>
            </div>
          </div>
        </div>
      </div>

      <section class="login-panel">
        <div class="form-head">
          <span>欢迎回来</span>
          <h2>登录系统</h2>
          <p>请选择账号来源后继续，移动端扫码作业会自动返回当前入口。</p>
        </div>

        <el-form :model="form" label-position="top" class="login-form">
          <el-form-item label="登录方式">
            <el-segmented v-model="form.provider" :options="providerOptions" class="provider-segment" />
          </el-form-item>
          <el-alert
            v-if="form.provider === 'feishu' && feishuLoginTip"
            class="login-tip"
            type="warning"
            show-icon
            :closable="false"
            :title="feishuLoginTip"
          />
          <template v-if="form.provider !== 'feishu'">
          <el-form-item label="账号">
            <el-input v-model="form.username" size="large" autocomplete="username" placeholder="请输入账号">
              <template #prefix><el-icon><User /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" size="large" type="password" show-password autocomplete="current-password" placeholder="请输入密码" @keyup.enter="submitLogin">
              <template #prefix><el-icon><Lock /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-button type="primary" size="large" class="login-button" :loading="loading" @click="submitLogin">登录系统</el-button>
          </template>
          <el-button v-else type="primary" size="large" class="login-button" :loading="loading" @click="startFeishuLogin">使用飞书登录</el-button>
        </el-form>

        <div class="login-foot">
          <span>本地账号用于系统管理员维护，LDAP 用于企业目录账号登录。</span>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Box, Lock, Setting, Tickets, User } from '@element-plus/icons-vue'
import { useAppStore } from '../../store'
import { completeSso, feishuLoginFree, getFeishuLoginFreeConfig, login, startSsoWithState } from '../../api/user'
import { isFeishuClient, requestFeishuLoginCode } from '../../utils/feishuSdk'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const loading = ref(false)
const feishuLoginTried = ref(false)
const feishuLoginTip = ref('')
const form = reactive({ provider: 'local', username: '', password: '' })
const providerOptions = [
  { label: '本地账号', value: 'local' },
  { label: 'LDAP', value: 'ldap' },
  { label: '飞书', value: 'feishu' }
]
const capabilities = [
  { title: '资产运营', desc: '台账、入库、领用和维修集中处理', icon: Box },
  { title: '流程待办', desc: '入职分配、离职回收和审批统一提醒', icon: Tickets },
  { title: '审计控制', desc: '规则审计、答复和报告闭环管理', icon: Setting }
]

onMounted(async () => {
  if ((route.query.sso === 'feishu' || route.query.code) && route.query.code) {
    form.provider = 'feishu'
    finishFeishuLogin()
    return
  }
  if (isFeishuClient()) {
    form.provider = 'feishu'
    await startFeishuLogin(true)
  }
})

async function submitLogin() {
  loading.value = true
  try {
    const result = await login(form)
    store.setSession(result)
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') && !route.query.redirect.startsWith('//')
      ? route.query.redirect
      : '/dashboard'
    router.replace(redirect)
  } catch {
    // 错误提示已由 request 拦截器统一展示
  } finally {
    loading.value = false
  }
}

async function startFeishuLogin(auto = false) {
  feishuLoginTip.value = ''
  if (isFeishuClient()) {
    await startFeishuLoginFree(auto)
    return
  }
  loading.value = true
  try {
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') && !route.query.redirect.startsWith('//')
      ? route.query.redirect
      : '/dashboard'
    const result = await startSsoWithState('feishu', redirect, `${window.location.origin}/login`)
    window.location.href = result.redirect_url
  } catch (error) {
    feishuLoginTip.value = error.userMessage || error.message || '飞书登录未配置，请先在权限和账号中保存飞书身份源'
    loading.value = false
  }
}

async function startFeishuLoginFree(auto = false) {
  if (feishuLoginTried.value && auto) return
  feishuLoginTried.value = true
  loading.value = true
  try {
    feishuLoginTip.value = ''
    const config = await getFeishuLoginFreeConfig()
    if (!config?.enabled || !config.app_id) throw new Error(config?.message || '飞书免登未配置')
    const code = await requestFeishuLoginCode(config.app_id, config.scope_list || [])
    const result = await feishuLoginFree({ code, source: 'feishu-webapp' })
    store.setSession(result)
    ElMessage.success('飞书免登成功')
    router.replace(resolveRedirect())
  } catch (error) {
    feishuLoginTip.value = error.userMessage || error.message || '飞书免登失败，请检查飞书应用配置'
    if (!auto) ElMessage.error(error.userMessage || error.message || '飞书免登失败')
  } finally {
    loading.value = false
  }
}

async function finishFeishuLogin() {
  loading.value = true
  try {
    const result = await completeSso('feishu', {
      code: route.query.code,
      state: route.query.state
    })
    store.setSession(result)
    ElMessage.success('飞书登录成功')
    router.replace(resolveRedirect(route.query.state))
  } catch {
    // 错误提示已由 request 拦截器统一展示
  } finally {
    loading.value = false
  }
}

function resolveRedirect(value = route.query.redirect) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/dashboard'
}

</script>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  min-height: 100dvh;
  place-items: center;
  padding: 32px;
  background:
    radial-gradient(circle at 18% 16%, rgba(130, 184, 255, 0.28), transparent 28%),
    radial-gradient(circle at 82% 74%, rgba(25, 117, 252, 0.14), transparent 32%),
    linear-gradient(180deg, #f8fcff 0%, #eef6ff 100%);
}

.login-shell {
  display: grid;
  grid-template-columns: minmax(360px, 1.05fr) minmax(360px, 440px);
  gap: 24px;
  width: min(1080px, 100%);
  align-items: stretch;
}

.login-panel {
  display: grid;
  align-content: center;
  gap: 22px;
  padding: 38px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: var(--shadow-strong);
}

.brand-side {
  display: grid;
  align-content: space-between;
  gap: 28px;
  min-height: 560px;
  padding: 42px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 18px;
  background:
    radial-gradient(circle at 18% 20%, rgba(130, 184, 255, 0.32), transparent 28%),
    linear-gradient(145deg, #0b1f44 0%, #0f3675 52%, #1975fc 100%);
  color: #fff;
  box-shadow: 0 20px 50px rgba(25, 117, 252, 0.22);
}

.brand-head {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-mark {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: #fff;
  color: var(--primary);
  font-weight: 800;
}

h1 {
  margin: 0 0 4px;
  font-size: 28px;
  line-height: 1.2;
}

h2 {
  margin: 6px 0 0;
  color: var(--text);
  font-size: 28px;
  line-height: 1.2;
}

p {
  margin: 0;
}

.brand-head p,
.brand-copy span,
.capability-item span {
  color: rgba(255, 255, 255, 0.78);
}

.brand-copy {
  display: grid;
  gap: 14px;
  max-width: 560px;
}

.brand-copy strong {
  font-size: 34px;
  line-height: 1.22;
}

.brand-copy span {
  max-width: 520px;
  line-height: 1.8;
}

.capability-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.capability-item {
  display: grid;
  gap: 10px;
  min-width: 0;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.12);
}

.capability-item .el-icon {
  font-size: 22px;
}

.capability-item strong,
.capability-item span {
  display: block;
}

.capability-item strong {
  margin-bottom: 4px;
  font-size: 14px;
}

.capability-item span {
  font-size: 12px;
  line-height: 1.5;
}

.form-head {
  display: grid;
  gap: 4px;
}

.form-head > span {
  color: var(--primary);
  font-size: 13px;
  font-weight: 800;
}

.form-head p,
.login-foot {
  color: var(--muted);
  line-height: 1.6;
}

.login-form {
  display: grid;
  gap: 6px;
}

.provider-segment {
  width: 100%;
}

:deep(.provider-segment .el-segmented__group) {
  width: 100%;
}

:deep(.provider-segment .el-segmented__item) {
  flex: 1;
}

.login-button {
  width: 100%;
}

.login-tip {
  margin-bottom: 8px;
}

.login-foot {
  padding-top: 4px;
  font-size: 12px;
}

@media (max-width: 900px) {
  .login-page {
    place-items: start center;
    padding: 20px;
  }

  .login-shell {
    grid-template-columns: 1fr;
    gap: 14px;
    width: min(520px, 100%);
  }

  .brand-side {
    min-height: auto;
    align-content: start;
    padding: 24px;
  }

  .capability-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .login-page {
    display: block;
    padding: max(12px, env(safe-area-inset-top)) 12px max(14px, env(safe-area-inset-bottom));
    background:
      linear-gradient(180deg, rgba(239, 246, 255, 0.92) 0%, rgba(248, 250, 252, 1) 42%),
      var(--app-bg);
    overflow-x: hidden;
  }

  .login-shell {
    width: 100%;
    gap: 10px;
  }

  .brand-side {
    min-height: 0;
    padding: 14px 14px 12px;
    border-radius: 14px;
    background: linear-gradient(135deg, #0f3f78 0%, #1d6ed8 64%, #12a3b8 100%);
    box-shadow: 0 10px 24px rgba(29, 78, 216, 0.18);
  }

  .login-panel {
    padding: 18px 16px;
    border-radius: 14px;
  }

  .brand-head {
    align-items: center;
    gap: 10px;
  }

  .brand-mark {
    width: 40px;
    height: 40px;
    border-radius: 12px;
  }

  h1 {
    font-size: 19px;
  }

  h2 {
    margin-top: 2px;
    font-size: 24px;
  }

  .brand-head p {
    max-width: 240px;
    overflow: hidden;
    font-size: 12px;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .brand-copy,
  .brand-copy span {
    display: none;
  }

  .capability-grid {
    display: none;
  }

  .login-panel {
    gap: 14px;
    min-height: calc(100dvh - 98px - env(safe-area-inset-top) - env(safe-area-inset-bottom));
    align-content: start;
    box-shadow: 0 12px 26px rgba(15, 23, 42, 0.08);
  }

  .form-head {
    gap: 8px;
  }

  .form-head > span {
    font-size: 12px;
  }

  .form-head p {
    display: none;
  }

  .login-form {
    gap: 2px;
  }

  :deep(.el-form-item) {
    margin-bottom: 13px;
  }

  :deep(.el-form-item__label) {
    padding-bottom: 6px;
    font-size: 13px;
    line-height: 1.2;
  }

  :deep(.el-input__wrapper),
  :deep(.el-segmented) {
    min-height: 48px;
    border-radius: 10px;
  }

  :deep(.el-input__inner) {
    font-size: 16px;
  }

  :deep(.provider-segment .el-segmented__item) {
    min-height: 40px;
  }

  .login-button {
    min-height: 48px;
    margin-top: 2px;
    border-radius: 10px;
    font-size: 16px;
    font-weight: 700;
  }

  .login-foot {
    margin-top: auto;
    padding-top: 10px;
    font-size: 12px;
    line-height: 1.55;
  }
}

@media (max-width: 380px) {
  .login-page {
    padding-inline: 10px;
  }

  .login-panel {
    padding-inline: 14px;
  }

  h2 {
    font-size: 22px;
  }
}
</style>
