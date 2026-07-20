<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">设备类型</h2>
        <p class="page-subtitle">维护资产分类，用于产品档案、采购入库和资产归类。</p>
      </div>
      <div class="toolbar">
        <el-button @click="resetKeyword">清空</el-button>
        <el-button type="primary" @click="openCreateType">创建设备类型</el-button>
      </div>
    </div>

    <el-dialog v-model="typeDialog.visible" :title="form.id ? '编辑设备类型' : '创建设备类型'" width="560px" class="device-type-dialog" destroy-on-close>
      <el-form :model="form" label-width="86px">
        <el-form-item label="类型名称" required>
          <el-input v-model.trim="form.name" placeholder="例如 笔记本、显示器、服务器" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model.trim="form.description" type="textarea" :rows="4" placeholder="可填写适用范围、管理说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeTypeDialog">取消</el-button>
        <el-button @click="resetForm">清空表单</el-button>
        <el-button type="primary" :loading="typeDialog.saving" @click="saveType">{{ form.id ? '保存修改' : '创建设备类型' }}</el-button>
      </template>
    </el-dialog>

    <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>类型列表</span>
            <el-input v-model.trim="keyword" clearable placeholder="搜索类型" class="search-input" />
          </div>
        </template>
        <el-table :data="pagedRows" border stripe>
          <el-table-column prop="name" label="类型名称" min-width="160" />
          <el-table-column prop="description" label="说明" min-width="260" show-overflow-tooltip />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="editType(row)">编辑</el-button>
              <el-button link type="danger" @click="removeType(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="filteredRows.length"
            layout="total, sizes, prev, pager, next, jumper"
          />
        </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createDeviceType, deleteDeviceType, getDeviceTypes, updateDeviceType } from '../../api/product'

const rows = ref([])
const keyword = ref('')
const form = reactive(defaultForm())
const typeDialog = reactive({ visible: false, saving: false })
const pagination = reactive({ page: 1, pageSize: 10 })

const filteredRows = computed(() => {
  const q = keyword.value.toLowerCase()
  if (!q) return rows.value
  return rows.value.filter(item => [item.name, item.description].some(value => String(value || '').toLowerCase().includes(q)))
})

const pagedRows = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  return filteredRows.value.slice(start, start + pagination.pageSize)
})

watch(keyword, () => {
  pagination.page = 1
})

onMounted(load)

function defaultForm() {
  return { id: null, name: '', description: '' }
}

async function load() {
  rows.value = await getDeviceTypes()
}

function resetForm() {
  Object.assign(form, defaultForm())
}

function resetKeyword() {
  keyword.value = ''
}

function openCreateType() {
  resetForm()
  typeDialog.visible = true
}

function closeTypeDialog() {
  typeDialog.visible = false
  resetForm()
}

function editType(row) {
  Object.assign(form, row)
  typeDialog.visible = true
}

async function saveType() {
  if (!form.name) {
    ElMessage.warning('请填写设备类型名称')
    return
  }
  typeDialog.saving = true
  try {
    if (form.id) await updateDeviceType(form.id, form)
    else await createDeviceType(form)
    typeDialog.visible = false
    resetForm()
    ElMessage.success('设备类型已保存')
    await load()
  } finally {
    typeDialog.saving = false
  }
}

async function removeType(row) {
  await ElMessageBox.confirm(`确认删除设备类型「${row.name}」？已有资产不会被删除。`, '删除设备类型', { type: 'warning' })
  await deleteDeviceType(row.id)
  if (form.id === row.id) resetForm()
  ElMessage.success('设备类型已删除')
  await load()
}
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.search-input {
  max-width: 260px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 980px) {
  .card-header {
    grid-template-columns: 1fr;
  }

  .card-header {
    align-items: stretch;
    flex-direction: column;
  }

  .search-input {
    max-width: none;
  }
}
</style>
