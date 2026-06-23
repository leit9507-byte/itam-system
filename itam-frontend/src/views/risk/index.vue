<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">风险分析</h2>
        <p class="page-subtitle">观察风险趋势、部门排行与闲置结构</p>
      </div>
    </div>
    <div class="chart-grid">
      <el-card shadow="never">
        <template #header>风险趋势</template>
        <div ref="trendRef" class="chart" />
      </el-card>
      <el-card shadow="never">
        <template #header>资产闲置统计</template>
        <div ref="idleRef" class="chart" />
      </el-card>
    </div>
    <el-card shadow="never">
      <template #header>部门风险排行</template>
      <el-table :data="analytics.deptRank" border>
        <el-table-column prop="dept" label="部门" />
        <el-table-column prop="score" label="风险分" />
        <el-table-column label="风险等级">
          <template #default="{ row }">
            <el-tag :type="row.score >= 70 ? 'danger' : row.score >= 40 ? 'warning' : 'success'">
              {{ row.score >= 70 ? '高' : row.score >= 40 ? '中' : '低' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { getRiskAnalytics } from '../../api/audit'

const trendRef = ref(null)
const idleRef = ref(null)
const analytics = reactive({ trend: [], deptRank: [], idleStats: [] })

onMounted(async () => {
  Object.assign(analytics, await getRiskAnalytics())
  await nextTick()
  echarts.init(trendRef.value).setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', max: 100 },
    series: [{ type: 'line', smooth: true, data: analytics.trend, areaStyle: {} }]
  })
  echarts.init(idleRef.value).setOption({
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: '65%', data: analytics.idleStats }]
  })
})
</script>
