<template>
  <div class="page residual-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">系统设置</p>
        <h2 class="page-title">残值计算规则</h2>
        <p class="page-subtitle">统一设置资产台账当前残值和报废预计残值的计算口径。</p>
      </div>
      <el-button type="primary" :loading="saving" @click="save">保存规则</el-button>
    </div>

    <el-card shadow="never" class="method-card">
      <template #header>
        <div class="card-header">
          <div>
            <span>计算方法</span>
            <small>选择全系统默认采用的残值算法，设备类型仅覆盖最低残值率。</small>
          </div>
          <el-tag type="primary">{{ selectedMethod.label }}</el-tag>
        </div>
      </template>
      <div class="method-grid">
        <button
          v-for="item in methods"
          :key="item.value"
          type="button"
          class="method-option"
          :class="{ active: form.method === item.value }"
          @click="form.method = item.value"
        >
          <div class="method-option-head">
            <strong>{{ item.label }}</strong>
            <el-tag v-if="item.recommended" size="small" type="success">推荐</el-tag>
          </div>
          <span>{{ item.summary }}</span>
          <small>{{ item.suitable }}</small>
        </button>
      </div>
      <div class="formula-panel">
        <div>
          <span class="formula-label">计算公式</span>
          <strong>{{ selectedMethod.formula }}</strong>
        </div>
        <p>{{ selectedMethod.description }}</p>
      </div>
    </el-card>

    <div class="content-grid">
      <el-card shadow="never">
        <template #header>基础参数</template>
        <el-form label-position="top" class="setting-form">
          <el-form-item label="默认最低残值率">
            <div class="rate-field">
              <el-input-number v-model="defaultRatePercent" :min="0" :max="100" :precision="2" />
              <span>%</span>
            </div>
            <p class="form-tip">最低残值 = 采购原值 × 最低残值率。任何折旧算法都不会低于该金额。</p>
          </el-form-item>
          <el-form-item v-if="form.method !== 'fixed_rate'" label="缺少采购日期或退役年限时">
            <el-radio-group v-model="form.missing_basis_policy">
              <el-radio value="original">保留采购原值</el-radio>
              <el-radio value="zero">按 0 计算</el-radio>
            </el-radio-group>
            <p class="form-tip">建议正式数据使用“保留采购原值”，并通过数据质量审计补齐缺失字段。</p>
          </el-form-item>
          <el-alert
            :title="selectedMethod.rule"
            type="info"
            show-icon
            :closable="false"
          />
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>计算预览</span>
            <el-tag type="info">实时示例</el-tag>
          </div>
        </template>
        <el-form label-position="top" class="preview-form">
          <div class="preview-fields">
            <el-form-item label="采购原值">
              <el-input-number v-model="preview.price" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
            <el-form-item label="设备类型">
              <el-select v-model="preview.category" clearable filterable placeholder="选择设备类型" style="width: 100%">
                <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
            <el-form-item label="已使用年数">
              <el-input-number v-model="preview.elapsedYears" :min="0" :precision="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="退役年限">
              <el-input-number v-model="preview.retirementYears" :min="0" :precision="1" style="width: 100%" />
            </el-form-item>
          </div>
        </el-form>
        <div class="preview-box">
          <div>
            <span>预计当前残值</span>
            <strong>¥{{ formatMoney(previewResidual) }}</strong>
          </div>
          <div class="preview-meta">
            <span>最低残值 ¥{{ formatMoney(previewMinimumValue) }}</span>
            <span>适用残值率 {{ activePreviewRatePercent }}%</span>
            <span>使用进度 {{ previewProgressPercent }}%</span>
          </div>
        </div>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <span>计算方法对比</span>
            <small>使用右上方同一组预览参数计算，方便确认不同方法的金额差异。</small>
          </div>
        </div>
      </template>
      <el-table :data="comparisonRows" border>
        <el-table-column prop="label" label="方法" width="170">
          <template #default="{ row }">
            <strong>{{ row.label }}</strong>
            <el-tag v-if="row.value === form.method" size="small" type="primary" class="current-tag">当前</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="calculation" label="计算逻辑" min-width="330" />
        <el-table-column prop="suitable" label="适用场景" min-width="220" />
        <el-table-column prop="residual" label="示例残值" width="150" align="right">
          <template #default="{ row }"><strong>¥{{ formatMoney(row.residual) }}</strong></template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="category-rule-card">
      <template #header>
        <div class="card-header">
          <div>
            <span>设备类型覆盖规则</span>
            <small>指定类型可使用独立最低残值率；算法仍采用上方选择的全局计算方法。</small>
          </div>
          <el-button type="primary" @click="addCategoryRule">添加类型规则</el-button>
        </div>
      </template>
      <el-table v-if="form.category_rates.length" :data="form.category_rates" border>
        <el-table-column type="index" label="序号" width="70" />
        <el-table-column label="设备类型" min-width="260">
          <template #default="{ row }">
            <el-select v-model="row.category" filterable allow-create default-first-option placeholder="选择或输入设备类型" style="width: 100%">
              <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="最低残值率" min-width="220">
          <template #default="{ row }">
            <div class="rate-field table-rate-field">
              <el-input-number v-model="row.rate_percent" :min="0" :max="100" :precision="2" />
              <span>%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="最低残值示例" width="170">
          <template #default="{ row }">¥{{ formatMoney(Number(preview.price || 0) * percentToRate(row.rate_percent)) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ $index }"><el-button type="danger" link @click="form.category_rates.splice($index, 1)">删除</el-button></template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无类型覆盖规则，所有设备使用默认最低残值率" :image-size="80">
        <el-button type="primary" @click="addCategoryRule">添加第一条规则</el-button>
      </el-empty>
    </el-card>

    <el-card shadow="never">
      <template #header>统一计算约定</template>
      <div class="convention-grid">
        <div><strong>时间口径</strong><span>按采购日期至计算日期的实际天数 ÷ 365.2425，支持不足一年的折旧。</span></div>
        <div><strong>到期口径</strong><span>达到或超过退役年限后，残值直接取最低残值。</span></div>
        <div><strong>金额口径</strong><span>采购原值小于 0 时按 0 处理，最终金额四舍五入保留两位小数。</span></div>
        <div><strong>类型覆盖</strong><span>优先匹配设备类型残值率，未匹配时采用默认最低残值率。</span></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDeviceTypes } from '../../api/product'
import { getAssetResidualConfig, saveAssetResidualConfig } from '../../api/settings'

const methods = [
  {
    value: 'straight_line',
    label: '直线折旧法',
    summary: '在整个退役年限内平均折旧。',
    suitable: '办公电脑、显示器、通用设备',
    formula: 'max(最低残值，原值 - (原值 - 最低残值) × 已使用年数 ÷ 退役年限)',
    calculation: '可折旧金额按使用进度平均扣减。',
    description: '每个使用周期折旧金额相同，结果平稳、易解释，是固定资产管理最常用的默认方法。',
    rule: '达到退役年限前按时间比例平均折旧；达到退役年限后取最低残值。',
    recommended: true
  },
  {
    value: 'double_declining',
    label: '双倍余额递减法',
    summary: '前期折旧快，后期折旧慢。',
    suitable: '笔记本、手机、高迭代电子设备',
    formula: 'max(最低残值，原值 × (1 - 2 ÷ 退役年限) ^ 已使用年数)',
    calculation: '每年按期初账面价值和双倍直线折旧率计算。',
    description: '适合技术迭代快、购入后前几年价值下降明显的设备；到退役年限时统一收敛到最低残值。',
    rule: '年度折旧率为 2 ÷ 退役年限，按剩余账面价值递减计算。'
  },
  {
    value: 'sum_of_years_digits',
    label: '年数总和法',
    summary: '按剩余使用年限分配折旧权重。',
    suitable: '服务器、网络设备、专业仪器',
    formula: 'max(最低残值，原值 - 可折旧金额 × 累计年数权重 ÷ 年数总和)',
    calculation: '首年权重最高，随后逐年下降，速度介于直线法和双倍余额法之间。',
    description: '同样属于加速折旧，但变化比双倍余额递减法温和，适合前期效能贡献更高的设备。',
    rule: '5 年资产的年度权重依次为 5/15、4/15、3/15、2/15、1/15。'
  },
  {
    value: 'fixed_rate',
    label: '固定残值率法',
    summary: '不考虑使用时间，直接按固定比例估值。',
    suitable: '历史数据不完整、已充分折旧资产',
    formula: '当前残值 = 原值 × 最低残值率',
    calculation: '采购日期和退役年限不参与计算。',
    description: '适合无法可靠取得采购日期或退役年限的历史资产，也可用于只关注处置底价的管理口径。',
    rule: '保存后所有资产直接按原值和适用最低残值率计算。'
  }
]

const saving = ref(false)
const categories = ref([])
const form = reactive(defaultForm())
const preview = reactive({ price: 10000, category: '', elapsedYears: 2, retirementYears: 5 })

const selectedMethod = computed(() => methods.find(item => item.value === form.method) || methods[0])
const defaultRatePercent = computed({
  get: () => rateToPercent(form.minimum_residual_rate),
  set: value => (form.minimum_residual_rate = percentToRate(value))
})
const activePreviewRate = computed(() => {
  const hit = form.category_rates.find(item => item.category && item.category === preview.category)
  return percentToRate(hit?.rate_percent ?? defaultRatePercent.value)
})
const activePreviewRatePercent = computed(() => rateToPercent(activePreviewRate.value))
const previewMinimumValue = computed(() => roundMoney(Number(preview.price || 0) * activePreviewRate.value))
const previewProgressPercent = computed(() => {
  const life = Number(preview.retirementYears || 0)
  if (!life) return 0
  return Number((Math.min(Math.max(Number(preview.elapsedYears || 0) / life, 0), 1) * 100).toFixed(1))
})
const previewResidual = computed(() => calculatePreview(form.method))
const comparisonRows = computed(() => methods.map(item => ({
  ...item,
  residual: calculatePreview(item.value)
})))

onMounted(async () => {
  await Promise.all([loadConfig(), loadCategories()])
})

async function loadConfig() {
  const data = await getAssetResidualConfig()
  Object.assign(form, {
    method: methods.some(item => item.value === data.method) ? data.method : 'straight_line',
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

function calculatePreview(method) {
  const original = Math.max(Number(preview.price || 0), 0)
  if (!original) return 0
  const minimum = original * activePreviewRate.value
  if (method === 'fixed_rate') return roundMoney(minimum)
  const usefulYears = Number(preview.retirementYears || 0)
  if (!usefulYears) return form.missing_basis_policy === 'original' ? roundMoney(original) : 0
  const elapsedYears = Math.min(Math.max(Number(preview.elapsedYears || 0), 0), usefulYears)
  const progress = Math.min(elapsedYears / usefulYears, 1)
  if (progress >= 1) return roundMoney(minimum)
  let current
  if (method === 'double_declining') {
    const annualRate = Math.min(2 / usefulYears, 1)
    current = original * ((1 - annualRate) ** elapsedYears)
  } else if (method === 'sum_of_years_digits') {
    current = original - ((original - minimum) * sumOfYearsFraction(elapsedYears, usefulYears))
  } else {
    current = original - ((original - minimum) * progress)
  }
  return roundMoney(Math.max(minimum, current))
}

function sumOfYearsFraction(elapsedYears, usefulYears) {
  const periods = Math.max(Math.ceil(usefulYears), 1)
  const denominator = periods * (periods + 1) / 2
  const fullYears = Math.min(Math.floor(elapsedYears), periods)
  let weightedYears = 0
  for (let index = 0; index < fullYears; index += 1) weightedYears += periods - index
  const fraction = elapsedYears - fullYears
  if (fullYears < periods && fraction > 0) weightedYears += (periods - fullYears) * fraction
  return Math.min(weightedYears / denominator, 1)
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

function formatMoney(value) {
  return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<style scoped>
.residual-page {
  display: grid;
  gap: 16px;
}

.card-header,
.method-option-head,
.preview-box {
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

.card-header small,
.method-option small,
.method-option span {
  color: var(--muted);
  font-size: 12px;
}

.method-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.method-option {
  min-width: 0;
  padding: 14px;
  border: 1px solid #dce7f5;
  border-radius: 8px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.method-option:hover,
.method-option.active {
  border-color: #409eff;
  background: #f4f9ff;
}

.method-option.active {
  box-shadow: inset 0 0 0 1px #409eff;
}

.method-option > span,
.method-option > small {
  display: block;
  margin-top: 8px;
  line-height: 1.5;
}

.formula-panel {
  display: grid;
  grid-template-columns: minmax(360px, 1.2fr) minmax(260px, 0.8fr);
  gap: 18px;
  margin-top: 14px;
  padding: 14px 16px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;
}

.formula-panel > div {
  display: grid;
  gap: 8px;
}

.formula-label {
  color: #2563eb;
  font-size: 12px;
}

.formula-panel strong {
  line-height: 1.6;
}

.formula-panel p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(320px, 0.8fr) minmax(420px, 1.2fr);
  gap: 16px;
}

.setting-form,
.preview-form {
  width: 100%;
}

.rate-field {
  display: grid;
  grid-template-columns: minmax(0, 220px) 30px;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.rate-field :deep(.el-input-number) {
  width: 100%;
}

.rate-field span,
.form-tip {
  color: var(--muted);
}

.form-tip {
  width: 100%;
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.6;
}

.preview-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 12px;
}

.preview-box {
  padding: 16px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f4f8ff;
}

.preview-box > div:first-child {
  display: grid;
  gap: 5px;
}

.preview-box span {
  color: var(--muted);
}

.preview-box strong {
  color: var(--text);
  font-size: 28px;
}

.preview-meta {
  display: grid;
  gap: 5px;
  text-align: right;
}

.current-tag {
  margin-left: 8px;
}

.table-rate-field {
  grid-template-columns: minmax(0, 180px) 28px;
}

.convention-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 24px;
}

.convention-grid > div {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  gap: 10px;
  line-height: 1.6;
}

.convention-grid span {
  color: var(--muted);
}

@media (max-width: 1180px) {
  .method-grid {
    grid-template-columns: 1fr 1fr;
  }

  .content-grid,
  .formula-panel {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .method-grid,
  .preview-fields,
  .convention-grid {
    grid-template-columns: 1fr;
  }

  .card-header,
  .preview-box {
    align-items: stretch;
    flex-direction: column;
  }

  .preview-meta {
    text-align: left;
  }
}
</style>
