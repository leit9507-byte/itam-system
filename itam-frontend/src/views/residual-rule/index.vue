<template>
  <div class="page residual-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">系统设置</p>
        <h2 class="page-title">残值计算规则</h2>
        <p class="page-subtitle">设置资产当前残值和报废预计残值的计算口径。</p>
      </div>
      <el-button type="primary" :loading="saving" @click="save">保存规则</el-button>
    </div>

    <div class="content-grid">
      <el-card shadow="never">
        <template #header>基础规则</template>
        <el-form label-position="top" class="setting-form">
          <el-form-item label="计算方法">
            <el-radio-group v-model="form.method">
              <el-radio-button label="straight_line">直线折旧法</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="默认最低残值率">
            <el-input-number v-model="defaultRatePercent" :min="0" :max="100" :precision="2" style="width: 220px" />
            <span class="unit">%</span>
            <p class="form-tip">资产会从采购原值按退役年限线性折旧，最低不会低于原值的这个比例。</p>
          </el-form-item>
          <el-form-item label="缺少采购日期或退役年限时">
            <el-radio-group v-model="form.missing_basis_policy">
              <el-radio label="original">按原值计算</el-radio>
              <el-radio label="zero">按 0 计算</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>计算预览</span>
            <el-tag type="info">示例</el-tag>
          </div>
        </template>
        <el-form label-position="top" class="preview-form">
          <el-form-item label="采购原值">
            <el-input-number v-model="preview.price" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
          <el-form-item label="设备类型">
            <el-select v-model="preview.category" clearable filterable placeholder="选择设备类型" style="width: 100%">
              <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="已使用年数 / 退役年限">
            <div class="inline-inputs">
              <el-input-number v-model="preview.elapsedYears" :min="0" :precision="1" />
              <el-input-number v-model="preview.retirementYears" :min="0" :precision="1" />
            </div>
          </el-form-item>
        </el-form>
        <div class="preview-box">
          <span>预计当前残值</span>
          <strong>¥{{ previewResidual.toLocaleString() }}</strong>
          <em>适用最低残值率：{{ activePreviewRatePercent }}%</em>
        </div>
      </el-card>
    </div>

    <el-card shadow="never" class="category-rule-card">
      <template #header>
        <div class="card-header">
          <div>
            <span>设备类型覆盖规则</span>
            <small>为特殊设备类型单独设置最低残值率，未命中的类型使用基础规则。</small>
          </div>
          <el-button type="primary" @click="addCategoryRule">添加类型规则</el-button>
        </div>
      </template>
      <div v-if="form.category_rates.length" class="category-rule-list">
        <section v-for="(row, index) in form.category_rates" :key="index" class="category-rule-item">
          <div class="rule-item-head">
            <strong>覆盖规则 {{ index + 1 }}</strong>
            <el-button type="danger" link @click="form.category_rates.splice(index, 1)">删除</el-button>
          </div>
          <el-form label-position="top" class="rule-item-form">
            <el-form-item label="设备类型">
            <el-select v-model="row.category" filterable allow-create default-first-option placeholder="选择或输入设备类型" style="width: 100%">
              <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
            </el-select>
            </el-form-item>
            <el-form-item label="最低残值率">
              <div class="rate-input">
                <el-input-number v-model="row.rate_percent" :min="0" :max="100" :precision="2" style="width: 100%" />
                <span>%</span>
              </div>
            </el-form-item>
          </el-form>
        </section>
      </div>
      <el-empty v-else description="暂无类型覆盖规则，系统将使用默认最低残值率" :image-size="90">
        <el-button type="primary" @click="addCategoryRule">添加第一条规则</el-button>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDeviceTypes } from '../../api/product'
import { getAssetResidualConfig, saveAssetResidualConfig } from '../../api/settings'

const saving = ref(false)
const categories = ref([])
const form = reactive(defaultForm())
const preview = reactive({ price: 10000, category: '', elapsedYears: 2, retirementYears: 5 })

const defaultRatePercent = computed({
  get: () => rateToPercent(form.minimum_residual_rate),
  set: value => (form.minimum_residual_rate = percentToRate(value))
})
const activePreviewRate = computed(() => {
  const hit = form.category_rates.find(item => item.category && item.category === preview.category)
  return percentToRate(hit?.rate_percent ?? defaultRatePercent.value)
})
const activePreviewRatePercent = computed(() => rateToPercent(activePreviewRate.value))
const previewResidual = computed(() => {
  const original = Number(preview.price || 0)
  if (!original) return 0
  const usefulYears = Number(preview.retirementYears || 0)
  if (!usefulYears) return form.missing_basis_policy === 'original' ? roundMoney(original) : 0
  const progress = Math.min(Number(preview.elapsedYears || 0) / usefulYears, 1)
  const minimum = original * activePreviewRate.value
  return roundMoney(Math.max(minimum, original - ((original - minimum) * progress)))
})

onMounted(async () => {
  await Promise.all([loadConfig(), loadCategories()])
})

async function loadConfig() {
  const data = await getAssetResidualConfig()
  Object.assign(form, {
    method: data.method || 'straight_line',
    minimum_residual_rate: Number(data.minimum_residual_rate ?? 0.05),
    missing_basis_policy: data.missing_basis_policy || 'original',
    category_rates: (data.category_rates || []).map(item => ({
      category: item.category,
      rate_percent: rateToPercent(item.minimum_residual_rate)
    }))
  })
}

async function loadCategories() {
  categories.value = (await getDeviceTypes()).map(item => item.name)
}

function addCategoryRule() {
  form.category_rates.push({ category: '', rate_percent: defaultRatePercent.value })
}

async function save() {
  const categoryRates = []
  const seen = new Set()
  for (const item of form.category_rates) {
    const category = String(item.category || '').trim()
    if (!category || seen.has(category)) continue
    seen.add(category)
    categoryRates.push({ category, minimum_residual_rate: percentToRate(item.rate_percent) })
  }
  saving.value = true
  try {
    await saveAssetResidualConfig({
      method: form.method,
      minimum_residual_rate: form.minimum_residual_rate,
      missing_basis_policy: form.missing_basis_policy,
      category_rates: categoryRates
    })
    form.category_rates = categoryRates.map(item => ({ category: item.category, rate_percent: rateToPercent(item.minimum_residual_rate) }))
    ElMessage.success('残值计算规则已保存')
  } finally {
    saving.value = false
  }
}

function defaultForm() {
  return { method: 'straight_line', minimum_residual_rate: 0.05, missing_basis_policy: 'original', category_rates: [] }
}

function percentToRate(value) {
  return Math.min(Math.max(Number(value || 0), 0), 100) / 100
}

function rateToPercent(value) {
  return Number((Math.min(Math.max(Number(value || 0), 0), 1) * 100).toFixed(2))
}

function roundMoney(value) {
  return Number(Number(value || 0).toFixed(2))
}
</script>

<style scoped>
.residual-page {
  display: grid;
  gap: 16px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header > div {
  display: grid;
  gap: 4px;
}

.card-header span {
  color: var(--text);
  font-weight: 700;
}

.card-header small {
  color: var(--muted);
  font-size: 12px;
  font-weight: 400;
}

.setting-form,
.preview-form {
  max-width: 680px;
}

.unit {
  margin-left: 8px;
  color: var(--muted);
}

.form-tip {
  width: 100%;
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.inline-inputs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  width: 100%;
}

.preview-box {
  display: grid;
  gap: 6px;
  padding: 16px;
  border: 1px solid #e5edf7;
  border-radius: 8px;
  background: var(--panel-soft);
}

.preview-box span,
.preview-box em {
  color: var(--muted);
  font-style: normal;
}

.preview-box strong {
  color: var(--text);
  font-size: 28px;
}

.category-rule-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.category-rule-item {
  padding: 14px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #fbfdff;
}

.rule-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.rule-item-head strong {
  color: var(--text);
  font-size: 15px;
}

.rule-item-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.rule-item-form :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

.rate-input {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 28px;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.rate-input span {
  color: var(--muted);
}

@media (max-width: 900px) {
  .content-grid,
  .inline-inputs {
    grid-template-columns: 1fr;
  }

  .card-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
