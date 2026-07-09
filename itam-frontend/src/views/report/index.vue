<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">报告中心</h2>
        <p class="page-subtitle">基于正式审计数据生成、预览和下载资产审计报告</p>
      </div>
      <el-space wrap>
        <el-button @click="downloadAssetCsv">导出资产 CSV</el-button>
        <el-button @click="downloadAssetPdf">导出资产 PDF</el-button>
        <el-button @click="handleDownloadAudit">下载审计报告 PDF</el-button>
        <el-button type="primary" class="generate-btn" :loading="generating" @click="handleGenerate">生成审计报告</el-button>
        <el-button @click="downloadAuditReportExcel">下载审计报告 Excel</el-button>
      </el-space>
    </div>

    <el-card shadow="never" class="export-card">
      <template #header>正式台账导出</template>
      <div class="export-grid">
        <el-button @click="downloadDepartmentAssetsCsv">部门资产清单</el-button>
        <el-button @click="downloadPersonHoldingsCsv">人员持有清单</el-button>
        <el-button @click="downloadOverdueBorrowingsCsv">逾期借用清单</el-button>
        <el-button @click="downloadWarrantyExpiringCsv(90)">即将过保清单</el-button>
        <el-button @click="downloadScrapDisposalLedgerCsv">报废处置台账</el-button>
      </div>
    </el-card>

    <div class="analytics-grid">
      <el-card shadow="never">
        <template #header>部门资产占用</template>
        <el-table :data="analytics.department_occupancy" border height="260">
          <el-table-column prop="dept_id" label="部门" min-width="120" />
          <el-table-column prop="asset_count" label="数量" width="90" />
          <el-table-column label="资产价值" width="130">
            <template #default="{ row }">¥{{ Number(row.asset_value || 0).toLocaleString() }}</template>
          </el-table-column>
        </el-table>
      </el-card>
      <el-card shadow="never">
        <template #header>人均资产价值</template>
        <el-table :data="analytics.per_capita_value" border height="260">
          <el-table-column prop="dept_id" label="部门" min-width="120" />
          <el-table-column prop="owner_count" label="人数" width="90" />
          <el-table-column label="人均价值" width="130">
            <template #default="{ row }">¥{{ Number(row.per_capita_value || 0).toLocaleString() }}</template>
          </el-table-column>
        </el-table>
      </el-card>
      <el-card shadow="never">
        <template #header>趋势指标</template>
        <div class="trend-list">
          <div v-for="item in trendRows" :key="item.label" class="trend-row">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </el-card>
    </div>

    <div class="two-column">
      <el-card shadow="never">
        <template #header>报告列表</template>
        <el-table :data="pagedReports" border empty-text="暂无已生成报告，请点击生成审计报告">
          <el-table-column prop="id" label="报告ID" width="170" />
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="status" label="状态" width="110" />
          <el-table-column prop="risk_score" label="风险评分" width="100" />
          <el-table-column prop="created_at" label="日期" width="130" />
          <el-table-column label="操作" width="110">
            <template #default="{ row }">
              <el-button type="primary" link @click="previewHtml = row.html">预览</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="reports.length"
            layout="total, sizes, prev, pager, next"
          />
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>HTML 报告预览</span>
            <el-tag v-if="activeReport" type="success">{{ activeReport.name }}</el-tag>
          </div>
        </template>
        <div v-loading="generating" class="report-preview-shell" element-loading-text="正在生成报告">
          <div v-if="previewHtml" class="report-preview" v-html="previewHtml" />
          <el-empty v-else class="preview-empty" description="生成审计报告后，可在这里预览正式报告内容" />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { generateReport, getReports } from '../../api/audit'
import { downloadAssetCsv, downloadAssetPdf, downloadAuditReport, downloadAuditReportExcel, downloadDepartmentAssetsCsv, downloadOverdueBorrowingsCsv, downloadPersonHoldingsCsv, downloadScrapDisposalLedgerCsv, downloadWarrantyExpiringCsv, getReportAnalytics } from '../../api/reporting'

const reports = ref([])
const previewHtml = ref('')
const generating = ref(false)
const pagination = reactive({ page: 1, pageSize: 10 })
const analytics = reactive({ department_occupancy: [], per_capita_value: [], idle_trend: [], repair_cost_trend: [], stocktake_diff_trend: [] })

const activeReport = computed(() => reports.value.find(item => item.html === previewHtml.value))
const pagedReports = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  return reports.value.slice(start, start + pagination.pageSize)
})
const trendRows = computed(() => [
  { label: '闲置资产趋势', value: latestTrendValue(analytics.idle_trend, 'count') },
  { label: '维修成本趋势', value: `¥${Number(latestTrendValue(analytics.repair_cost_trend, 'cost', 0)).toLocaleString()}` },
  { label: '盘点差异趋势', value: latestTrendValue(analytics.stocktake_diff_trend, 'diff_count') }
])

onMounted(async () => {
  const [reportRows, analyticsResult] = await Promise.all([getReports(), getReportAnalytics()])
  reports.value = reportRows
  Object.assign(analytics, analyticsResult)
})

async function handleGenerate() {
  generating.value = true
  try {
    const report = await generateReport()
    reports.value.unshift(report)
    pagination.page = 1
    previewHtml.value = report.html
    ElMessage.success('审计报告已生成，已包含审计答复和合规判断')
  } finally {
    generating.value = false
  }
}

async function handleDownloadAudit() {
  await downloadAuditReport()
  ElMessage.success('审计报告 PDF 已下载')
}

function latestTrendValue(rows, key, fallback = 0) {
  const row = rows?.[rows.length - 1]
  return row ? row[key] : fallback
}
</script>

<style scoped>
.analytics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.export-card {
  margin-bottom: 16px;
}

.export-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.trend-list {
  display: grid;
  gap: 12px;
}

.trend-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.trend-row strong {
  font-size: 18px;
}

.report-preview {
  height: 100%;
  overflow: auto;
  padding: 0;
}

.report-preview-shell {
  height: min(640px, calc(100vh - 260px));
  min-height: 420px;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}

.report-preview :deep(main) {
  max-width: none;
  border: 0;
  border-radius: 0;
}

.preview-empty {
  height: 100%;
  display: grid;
  place-items: center;
}

.generate-btn {
  min-width: 124px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 1100px) {
  .analytics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
