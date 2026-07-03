<template>
  <div class="page approval-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">审批流配置</h2>
        <p class="page-subtitle">按流程、金额、部门和审批层级维护规则</p>
      </div>
      <el-button type="primary" @click="openDialog()">新增规则</el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="rules" border stripe>
        <el-table-column prop="flow_type" label="流程" width="110">
          <template #default="{ row }">{{ flowLabel(row.flow_type) }}</template>
        </el-table-column>
        <el-table-column prop="name" label="规则名称" min-width="180" />
        <el-table-column label="金额范围" width="180">
          <template #default="{ row }">{{ amountRange(row) }}</template>
        </el-table-column>
        <el-table-column prop="dept_id" label="部门" width="120">
          <template #default="{ row }">{{ row.dept_id || '全部部门' }}</template>
        </el-table-column>
        <el-table-column prop="level" label="层级" width="80" />
        <el-table-column label="审批人" min-width="180">
          <template #default="{ row }">{{ row.approver_user_id || row.approver_role || '-' }}</template>
        </el-table-column>
        <el-table-column label="会签" width="80">
          <template #default="{ row }">{{ row.require_all ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="removeRule(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.form.id ? '编辑审批规则' : '新增审批规则'" width="560px">
      <el-form :model="dialog.form" label-width="96px">
        <el-form-item label="流程">
          <el-select v-model="dialog.form.flow_type" style="width: 100%">
            <el-option v-for="item in flowOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="规则名称"><el-input v-model="dialog.form.name" /></el-form-item>
        <el-form-item label="金额范围">
          <div class="range-row">
            <el-input-number v-model="dialog.form.min_amount" :min="0" placeholder="最小金额" style="width: 100%" />
            <span>至</span>
            <el-input-number v-model="dialog.form.max_amount" :min="0" placeholder="最大金额" style="width: 100%" />
          </div>
        </el-form-item>
        <el-form-item label="部门"><el-input v-model="dialog.form.dept_id" placeholder="为空表示全部部门" /></el-form-item>
        <el-form-item label="审批角色"><el-input v-model="dialog.form.approver_role" placeholder="如 finance_manager" /></el-form-item>
        <el-form-item label="审批用户"><el-input v-model="dialog.form.approver_user_id" placeholder="指定用户 ID，可为空" /></el-form-item>
        <el-form-item label="层级"><el-input-number v-model="dialog.form.level" :min="1" :max="20" /></el-form-item>
        <el-form-item label="会签"><el-switch v-model="dialog.form.require_all" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="dialog.form.enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createApprovalRule, deleteApprovalRule, getApprovalRules, updateApprovalRule } from '../../api/approval'

const flowOptions = [
  { label: '报废', value: 'scrap' },
  { label: '维修', value: 'repair' },
  { label: '采购', value: 'purchase' },
  { label: '回收', value: 'reclaim' }
]

const rules = ref([])
const dialog = reactive({ visible: false, form: blankForm() })

onMounted(loadRules)

async function loadRules() {
  rules.value = await getApprovalRules()
}

function blankForm() {
  return { id: null, flow_type: 'scrap', name: '', enabled: true, min_amount: null, max_amount: null, dept_id: '', approver_role: '', approver_user_id: '', level: 1, require_all: false }
}

function openDialog(row = null) {
  dialog.form = row ? { ...row } : blankForm()
  dialog.visible = true
}

async function saveRule() {
  if (!dialog.form.name) return ElMessage.warning('请填写规则名称')
  const payload = { ...dialog.form, dept_id: dialog.form.dept_id || null, approver_role: dialog.form.approver_role || null, approver_user_id: dialog.form.approver_user_id || null }
  if (payload.id) await updateApprovalRule(payload.id, payload)
  else await createApprovalRule(payload)
  ElMessage.success('审批规则已保存')
  dialog.visible = false
  await loadRules()
}

async function removeRule(row) {
  await ElMessageBox.confirm(`确认删除审批规则 ${row.name}？`, '删除审批规则', { type: 'warning' })
  await deleteApprovalRule(row.id)
  ElMessage.success('审批规则已删除')
  await loadRules()
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
