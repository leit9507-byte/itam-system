<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产详情</h2>
        <p class="page-subtitle">{{ detail.asset?.asset_id }} · {{ detail.asset?.name }}</p>
      </div>
      <el-button @click="$router.back()">返回</el-button>
    </div>

    <div class="two-column">
      <div class="page">
        <el-card shadow="never">
          <template #header>基本信息</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="资产ID">{{ detail.asset?.asset_id }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusMap[detail.asset?.status]?.type">{{ statusMap[detail.asset?.status]?.label }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="产品名称">{{ detail.asset?.name }}</el-descriptions-item>
            <el-descriptions-item label="类别">{{ detail.asset?.category }}</el-descriptions-item>
            <el-descriptions-item label="品牌">{{ detail.asset?.brand }}</el-descriptions-item>
            <el-descriptions-item label="型号">{{ detail.asset?.model }}</el-descriptions-item>
            <el-descriptions-item label="规格">{{ detail.asset?.spec }}</el-descriptions-item>
            <el-descriptions-item label="序列号">{{ detail.asset?.sn }}</el-descriptions-item>
            <el-descriptions-item label="使用人">{{ detail.asset?.owner || '未分配' }}</el-descriptions-item>
            <el-descriptions-item label="部门">{{ detail.asset?.dept || '未绑定' }}</el-descriptions-item>
            <el-descriptions-item label="位置">{{ detail.asset?.location }}</el-descriptions-item>
            <el-descriptions-item label="仓库">{{ detail.asset?.warehouse }}</el-descriptions-item>
            <el-descriptions-item label="价值">¥{{ detail.asset?.price?.toLocaleString() }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never">
          <template #header>生命周期时间轴</template>
          <Timeline :items="detail.lifecycles" />
        </el-card>
      </div>

      <div class="page">
        <el-card shadow="never">
          <template #header>出入库记录</template>
          <el-table :data="detail.inventoryRecords" border>
            <el-table-column prop="type" label="类型" width="80" />
            <el-table-column prop="target" label="目标" />
            <el-table-column prop="operator" label="操作人" width="100" />
            <el-table-column prop="time" label="时间" width="170" />
          </el-table>
        </el-card>
        <el-card shadow="never">
          <template #header>使用人记录</template>
          <el-table :data="detail.usageRecords" border>
            <el-table-column prop="user" label="用户" />
            <el-table-column prop="dept" label="部门" />
            <el-table-column prop="from" label="开始" />
            <el-table-column prop="to" label="结束" />
          </el-table>
        </el-card>
        <el-card shadow="never">
          <template #header>风险提示</template>
          <el-space direction="vertical" alignment="stretch" style="width: 100%">
            <el-alert v-for="risk in detail.risks" :key="risk.message" :type="risk.level === 'high' ? 'error' : risk.level === 'medium' ? 'warning' : 'success'" :title="risk.message" show-icon :closable="false" />
          </el-space>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import Timeline from '../../components/Timeline.vue'
import { getAssetDetail, statusMap } from '../../api/asset'

const route = useRoute()
const detail = reactive({ asset: null, lifecycles: [], usageRecords: [], inventoryRecords: [], risks: [] })

onMounted(async () => {
  Object.assign(detail, await getAssetDetail(route.params.id))
})
</script>
