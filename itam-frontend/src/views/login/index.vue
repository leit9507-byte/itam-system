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
        </el-form>

        <div class="login-foot">
          <span>本地账号用于系统管理员维护，LDAP 用于企业目录账号登录。</span>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Box, Lock, Setting, Tickets, User } from '@element-plus/icons-vue'
import { useAppStore } from '../../store'
import { login } from '../../api/user'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const loading = ref(false)
const form = reactive({ provider: 'local', username: 'admin', password: 'admin' })
const providerOptions = [
  { label: '本地账号', value: 'local' },
  { label: 'LDAP', value: 'ldap' }
]
const capabilities = [
  { title: '资产运营', desc: '台账、入库、领用和维修集中处理', icon: Box },
  { title: '流程待办', desc: '入职分配、离职回收和审批统一提醒', icon: Tickets },
  { title: '审计控制', desc: '规则审计、答复和报告闭环管理', icon: Setting }
]

async function submitLogin() {
  loading.value = true
  try {
    const result = await login(form)
    store.setSession(result)
    ElMessage.success('登录成功')
    router.replace(route.query.redirect || '/dashboard')
  } finally {
    loading.value = false
  }
}

</script>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 32px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(243, 247, 253, 0.92)),
    repeating-linear-gradient(90deg, rgba(36, 120, 255, 0.06) 0, rgba(36, 120, 255, 0.06) 1px, transparent 1px, transparent 72px),
    #f3f7fd;
}

.login-shell {
  display: grid;
  grid-template-columns: minmax(360px, 1.05fr) minmax(360px, 440px);
  gap: 28px;
  width: min(1040px, 100%);
  align-items: stretch;
}

.login-panel {
  display: grid;
  align-content: center;
  gap: 22px;
  padding: 36px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
}

.brand-side {
  display: grid;
  align-content: space-between;
  gap: 28px;
  min-height: 560px;
  padding: 40px;
  border: 1px solid #d9e5f4;
  border-radius: 8px;
  background: #0f4ea8;
  color: #fff;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.12);
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
  border-radius: 8px;
  background: #fff;
  color: #0f4ea8;
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
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
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

.login-foot {
  padding-top: 4px;
  font-size: 12px;
}

@media (max-width: 900px) {
  .login-page {
    align-items: start;
    place-items: start center;
  }

  .login-shell {
    grid-template-columns: 1fr;
    gap: 16px;
    width: min(520px, 100%);
  }

  .brand-side {
    min-height: auto;
    align-content: start;
  }

  .capability-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .login-page {
    min-height: 100dvh;
    padding: 14px;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(243, 247, 253, 0.96)),
      #f3f7fd;
  }

  .brand-side,
  .login-panel {
    padding: 18px;
  }

  .brand-head {
    align-items: center;
  }

  .brand-mark {
    width: 42px;
    height: 42px;
  }

  h1,
  h2 {
    font-size: 22px;
  }

  .brand-head p {
    font-size: 12px;
  }

  .brand-copy {
    gap: 8px;
  }

  .brand-copy strong {
    font-size: 20px;
  }

  .brand-copy span {
    display: none;
  }

  .capability-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .capability-item {
    padding: 10px 8px;
    justify-items: center;
    text-align: center;
  }

  .capability-item .el-icon {
    font-size: 20px;
  }

  .capability-item strong {
    font-size: 12px;
  }

  .capability-item span {
    display: none;
  }

  .login-panel {
    gap: 16px;
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
  }

  .form-head p,
  .login-foot {
    font-size: 12px;
  }

  :deep(.el-form-item) {
    margin-bottom: 14px;
  }
}
</style>
