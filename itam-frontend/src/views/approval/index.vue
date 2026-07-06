<template>
  <div class="page approval-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">飞书审批对接</h2>
        <p class="page-subtitle">系统只保存飞书接口配置，审批流程在飞书审批后台维护</p>
      </div>
      <el-button type="primary" @click="openDialog()">新增配置</el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="configs" border stripe>
        <el-table-column prop="flow_type" label="业务类型" width="110">
          <template #default="{ row }">{{ flowLabel(row.flow_type) }}</template>
        </el-table-column>
        <el-table-column prop="name" label="配置名称" min-width="160" />
        <el-table-column prop="approval_code" label="飞书 approval_code" min-width="220" show-overflow-tooltip />
        <el-table-column prop="app_id" label="App ID" min-width="160" show-overflow-tooltip />
        <el-table-column label="金额/部门匹配" min-width="180">
          <template #default="{ row }">{{ amountRange(row) }} / {{ row.dept_id || '全部部门' }}</template>
        </el-table-column>
        <el-table-column label="密钥" width="90">
          <template #default="{ row }">
            <el-tag :type="row.app_secret_set ? 'success' : 'danger'">{{ row.app_secret_set ? '已配置' : '未配置' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="success" @click="openSubmit(row)">测试发起</el-button>
            <el-button link type="danger" @click="removeConfig(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>最近飞书审批提交</template>
      <el-table :data="instances" border stripe>
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column prop="flow_type" label="业务" width="100">
          <template #default="{ row }">{{ flowLabel(row.flow_type) }}</template>
        </el-table-column>
        <el-table-column prop="business_id" label="业务单号" width="150" />
        <el-table-column prop="approval_code" label="approval_code" min-width="180" show-overflow-tooltip />
        <el-table-column prop="instance_code" label="instance_code" min-width="180" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="130" />
        <el-table-column prop="error_message" label="错误" min-width="180" show-overflow-tooltip />
      </el-table>
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.form.id ? '编辑飞书审批配置' : '新增飞书审批配置'" width="760px">
      <el-form :model="dialog.form" label-width="150px">
        <el-form-item label="业务类型">
          <el-select v-model="dialog.form.flow_type" style="width: 100%">
            <el-option v-for="item in flowOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="配置名称"><el-input v-model="dialog.form.name" /></el-form-item>
        <el-form-item label="飞书 App ID"><el-input v-model="dialog.form.app_id" placeholder="cli_xxx" /></el-form-item>
        <el-form-item label="飞书 App Secret">
          <el-input v-model="dialog.form.app_secret" show-password placeholder="编辑时留空表示继续使用已保存密钥" />
        </el-form-item>
        <el-form-item label="approval_code"><el-input v-model="dialog.form.approval_code" placeholder="飞书审批定义 Code" /></el-form-item>
        <el-form-item label="提交人 user_id"><el-input v-model="dialog.form.submitter_user_id" placeholder="可在发起时覆盖" /></el-form-item>
        <el-form-item label="提交人 open_id"><el-input v-model="dialog.form.submitter_open_id" placeholder="user_id 和 open_id 二选一" /></el-form-item>
        <el-form-item label="金额范围">
          <div class="range-row">
            <el-input-number v-model="dialog.form.min_amount" :min="0" placeholder="最小金额" style="width: 100%" />
            <span>至</span>
            <el-input-number v-model="dialog.form.max_amount" :min="0" placeholder="最大金额" style="width: 100%" />
          </div>
        </el-form-item>
        <el-form-item label="部门匹配"><el-input v-model="dialog.form.dept_id" placeholder="为空表示全部部门" /></el-form-item>
        <el-form-item label="Token 接口"><el-input v-model="dialog.form.tenant_access_token_url" /></el-form-item>
        <el-form-item label="发起审批接口"><el-input v-model="dialog.form.instance_create_url" /></el-form-item>
        <el-form-item label="默认表单 JSON">
          <el-input v-model="dialog.form.form_template" type="textarea" :rows="6" placeholder='例如 [{"id":"asset_id","value":"ITAM-000001"}]' />
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="dialog.form.enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="submitDialog.visible" title="测试发起飞书审批" width="640px">
      <el-form :model="submitDialog.form" label-width="120px">
        <el-form-item label="业务单号"><el-input v-model="submitDialog.form.business_id" /></el-form-item>
        <el-form-item label="金额"><el-input-number v-model="submitDialog.form.amount" :min="0" style="width: 100%" /></el-form-item>
        <el-form-item label="部门"><el-input v-model="submitDialog.form.dept_id" /></el-form-item>
        <el-form-item label="提交人 user_id"><el-input v-model="submitDialog.form.user_id" /></el-form-item>
        <el-form-item label="提交人 open_id"><el-input v-model="submitDialog.form.open_id" /></el-form-item>
        <el-form-item label="表单 JSON">
          <el-input v-model="submitDialog.form.formText" type="textarea" :rows="6" placeholder='留空使用配置中的默认表单 JSON' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="submitDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="submitDialog.loading" @click="submitApproval">发起</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createApprovalConfig, deleteApprovalConfig, getApprovalConfigs, getApprovalInstances, submitFeishuApproval, updateApprovalConfig } from '../../api/approval'

const flowOptions = [
  { label: '报废', value: 'scrap' },
  { label: '维修', value: 'repair' },
  { label: '采购', value: 'purchase' },
  { label: '回收', value: 'reclaim' }
]

const configs = ref([])
const instances = ref([])
const dialog = reactive({ visible: false, form: blankForm() })
const submitDialog = reactive({ visible: false, loading: false, config: null, form: blankSubmitForm() })

onMounted(loadAll)

async function loadAll() {
  const [configRows, instanceRows] = await Promise.all([getApprovalConfigs(), getApprovalInstances({ limit: 50 })])
  configs.value = configRows
  instances.value = instanceRows
}

function blankForm() {
  return {
    id: null,
    flow_type: 'scrap',
    name: '',
    enabled: true,
    min_amount: null,
    max_amount: null,
    dept_id: '',
    provider: 'feishu',
    approval_code: '',
    app_id: '',
    app_secret: '',
    tenant_access_token_url: 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    instance_create_url: 'https://open.feishu.cn/open-apis/approval/v4/instances',
    submitter_user_id: '',
    submitter_open_id: '',
    form_template: ''
  }
}

function blankSubmitForm() {
  return { business_id: `TEST-${Date.now()}`, amount: 0, dept_id: '', user_id: '', open_id: '', formText: '' }
}

function openDialog(row = null) {
  dialog.form = row ? { ...blankForm(), ...row, app_secret: '' } : blankForm()
  dialog.visible = true
}

async function saveConfig() {
  if (!dialog.form.name) return ElMessage.warning('请填写配置名称')
  if (!dialog.form.app_id || (!dialog.form.app_secret && !dialog.form.app_secret_set)) return ElMessage.warning('请填写飞书 App ID 和 App Secret')
  if (!dialog.form.approval_code) return ElMessage.warning('请填写飞书 approval_code')
  validateJson(dialog.form.form_template, '默认表单 JSON')
  const payload = normalizePayload(dialog.form)
  if (payload.id) await updateApprovalConfig(payload.id, payload)
  else await createApprovalConfig(payload)
  ElMessage.success('飞书审批配置已保存')
  dialog.visible = false
  await loadAll()
}

async function removeConfig(row) {
  await ElMessageBox.confirm(`确认删除飞书审批配置 ${row.name}？`, '删除配置', { type: 'warning' })
  await deleteApprovalConfig(row.id)
  ElMessage.success('配置已删除')
  await loadAll()
}

function openSubmit(row) {
  submitDialog.config = row
  submitDialog.form = { ...blankSubmitForm(), amount: Number(row.min_amount || 0), dept_id: row.dept_id || '' }
  submitDialog.visible = true
}

async function submitApproval() {
  const row = submitDialog.config
  const form = submitDialog.form.formText ? validateJson(submitDialog.form.formText, '表单 JSON') : null
  submitDialog.loading = true
  try {
    const result = await submitFeishuApproval({
      flow_type: row.flow_type,
      business_id: submitDialog.form.business_id,
      amount: Number(submitDialog.form.amount || 0),
      dept_id: submitDialog.form.dept_id || null,
      user_id: submitDialog.form.user_id || null,
      open_id: submitDialog.form.open_id || null,
      form
    })
    ElMessage.success(`飞书审批已发起：${result.instance?.instance_code || '已提交'}`)
    submitDialog.visible = false
    await loadAll()
  } finally {
    submitDialog.loading = false
  }
}

function normalizePayload(form) {
  return {
    ...form,
    dept_id: form.dept_id || null,
    min_amount: form.min_amount ?? null,
    max_amount: form.max_amount ?? null,
    submitter_user_id: form.submitter_user_id || null,
    submitter_open_id: form.submitter_open_id || null,
    app_secret: form.app_secret || null,
    form_template: form.form_template || null
  }
}

function validateJson(value, label) {
  if (!value) return null
  try {
    return JSON.parse(value)
  } catch {
    ElMessage.warning(`${label} 格式不正确`)
    throw new Error(`${label} 格式不正确`)
  }
}

function flowLabel(value) {
  return flowOptions.find(item => item.value === value)?.label || value
}

function amountRange(row) {
  const min = row.min_amount == null ? '0' : Number(row.min_amount).toLocaleString()
  const max = row.max_amount == null ? '不限' : Number(row.max_amount).toLocaleString()
  return `${min} - ${max}`
}
</script>

<style scoped>
.range-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 10px;
  align-items: center;
  width: 100%;
}
</style>
