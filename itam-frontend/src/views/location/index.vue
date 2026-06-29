<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">位置管理</h2>
        <p class="page-subtitle">维护办公区、会议室、公共区域和仓库位置，支持资产出库到公用位置</p>
      </div>
      <el-button type="primary" @click="openCreate">新增位置</el-button>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="keyword" clearable placeholder="搜索位置名称" style="width: 280px" @input="refresh" />
      </div>
      <el-table :data="pagedLocations" border stripe>
        <el-table-column prop="name" label="位置名称" min-width="180" />
        <el-table-column prop="code" label="位置编码" width="130" />
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="owner_dept" label="负责部门" width="150" />
        <el-table-column prop="asset_count" label="资产数量" width="110" align="center">
          <template #default="{ row }"><el-tag type="primary" effect="plain">{{ row.asset_count || 0 }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="locations.length"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.form.id ? '编辑位置' : '新增位置'" width="560px">
      <el-form :model="dialog.form" label-width="92px">
        <el-form-item label="位置名称" required><el-input v-model="dialog.form.name" /></el-form-item>
        <el-form-item label="位置编码"><el-input v-model="dialog.form.code" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="dialog.form.type" allow-create filterable default-first-option style="width: 100%">
            <el-option label="办公位置" value="办公位置" />
            <el-option label="会议室" value="会议室" />
            <el-option label="公共区域" value="公共区域" />
            <el-option label="仓库" value="仓库" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责部门"><el-input v-model="dialog.form.owner_dept" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="dialog.form.status" style="width: 100%">
            <el-option label="启用" value="启用" />
            <el-option label="停用" value="停用" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="dialog.form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createLocation, deleteLocation, getLocations, updateLocation } from '../../api/location'

const locations = ref([])
const keyword = ref('')
const dialog = reactive({ visible: false, form: defaultForm() })
const pagination = reactive({ page: 1, pageSize: 20 })
const pagedLocations = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  return locations.value.slice(start, start + pagination.pageSize)
})

onMounted(load)

async function load() {
  locations.value = await getLocations(keyword.value)
}

async function refresh() {
  pagination.page = 1
  await load()
}

function defaultForm() {
  return { id: null, name: '', code: '', type: '办公位置', owner_dept: '', description: '', status: '启用' }
}

function openCreate() {
  dialog.form = defaultForm()
  dialog.visible = true
}

function openEdit(row) {
  dialog.form = { ...row }
  dialog.visible = true
}

async function save() {
  if (!dialog.form.name.trim()) {
    ElMessage.warning('请填写位置名称')
    return
  }
  if (dialog.form.id) await updateLocation(dialog.form.id, dialog.form)
  else await createLocation(dialog.form)
  dialog.visible = false
  ElMessage.success('位置已保存')
  await load()
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除位置「${row.name}」？已有资产使用的位置不能删除。`, '删除位置', { type: 'warning' })
  await deleteLocation(row.id)
  ElMessage.success('位置已删除')
  await load()
}
</script>

<style scoped>
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
