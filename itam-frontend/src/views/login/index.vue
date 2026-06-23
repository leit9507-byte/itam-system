<template>
  <main class="login-page">
    <section class="login-panel">
      <div>
        <span class="brand-mark">IT</span>
        <h1>ITAM Dashboard</h1>
        <p>企业 IT 资产全生命周期管理系统</p>
      </div>

      <el-form :model="form" label-position="top" class="login-form">
        <el-form-item label="登录方式">
          <el-radio-group v-model="form.provider">
            <el-radio-button label="local">本地</el-radio-button>
            <el-radio-button label="ldap">LDAP</el-radio-button>
            <el-radio-button label="oidc">OIDC</el-radio-button>
            <el-radio-button label="saml">SAML</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="账号">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" @keyup.enter="submitLogin" />
        </el-form-item>
        <el-button type="primary" class="login-button" :loading="loading" @click="submitLogin">登录系统</el-button>
        <el-button class="login-button" @click="submitSso">模拟 SSO 登录</el-button>
      </el-form>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../../store'
import { login, startSso } from '../../api/user'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const loading = ref(false)
const form = reactive({ provider: 'local', username: 'admin', password: 'admin' })

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

async function submitSso() {
  const result = await startSso(form.provider)
  ElMessage.info(result.message)
}
</script>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background: #eef2f6;
}

.login-panel {
  display: grid;
  gap: 24px;
  width: min(440px, 100%);
  padding: 32px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: #2dd4bf;
  color: #10201d;
  font-weight: 800;
}

h1 {
  margin: 16px 0 6px;
  font-size: 24px;
}

p {
  margin: 0;
  color: var(--muted);
}

.login-form {
  display: grid;
  gap: 4px;
}

.login-button {
  width: 100%;
}
</style>
