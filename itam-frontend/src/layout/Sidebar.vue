<template>
  <el-aside class="sidebar" :class="{ 'is-collapsed': store.collapsed }" :width="store.collapsed ? '72px' : '236px'">
    <div class="brand">
      <span class="brand-mark">◆</span>
      <strong v-if="!store.collapsed">资产管理系统</strong>
    </div>
    <el-menu :default-active="route.path" router class="menu" :collapse="store.collapsed">
      <el-menu-item v-if="canAny(['asset', 'purchase', 'repair', 'audit', 'report'])" index="/dashboard"><el-icon><DataBoard /></el-icon><span>资产总览</span></el-menu-item>
      <el-menu-item v-if="canRead('asset')" index="/todo"><el-icon><Bell /></el-icon><span>待办中心</span></el-menu-item>
      <el-sub-menu v-if="assetGroupVisible" index="/asset">
        <template #title><el-icon><Monitor /></el-icon><span>资产运营</span></template>
        <el-menu-item v-if="canRead('asset')" index="/asset/list">资产台账</el-menu-item>
        <el-menu-item v-if="canRead('asset')" index="/checkout">借用登记</el-menu-item>
        <el-menu-item v-if="canRead('purchase')" index="/purchase">采购入库</el-menu-item>
        <el-menu-item v-if="canRead('asset')" index="/stocktake">资产盘点</el-menu-item>
        <el-menu-item v-if="canRead('repair')" index="/repair">维修管理</el-menu-item>
        <el-menu-item v-if="canRead('asset')" index="/scrap">报废处置</el-menu-item>
      </el-sub-menu>

      <el-sub-menu v-if="resourceGroupVisible" index="/asset-resource">
        <template #title><el-icon><Box /></el-icon><span>资产资源</span></template>
        <el-menu-item v-if="canRead('asset')" index="/inventory">配件管理</el-menu-item>
        <el-menu-item v-if="canRead('asset')" index="/software-license">软件许可</el-menu-item>
        <el-menu-item v-if="canRead('catalog')" index="/device-type">设备类型</el-menu-item>
        <el-menu-item v-if="canRead('catalog')" index="/product">产品档案</el-menu-item>
      </el-sub-menu>

      <el-sub-menu v-if="masterDataGroupVisible" index="/master-data">
        <template #title><el-icon><Setting /></el-icon><span>组织与主数据</span></template>
        <el-menu-item v-if="canRead('asset')" index="/company">公司管理</el-menu-item>
        <el-menu-item v-if="canRead('identity')" index="/department">部门管理</el-menu-item>
        <el-menu-item v-if="canRead('asset')" index="/location">位置管理</el-menu-item>
        <el-menu-item v-if="canRead('supplier')" index="/supplier">供应商管理</el-menu-item>
      </el-sub-menu>

      <el-sub-menu v-if="reportGroupVisible" index="/report-audit">
        <template #title><el-icon><View /></el-icon><span>报告与审计</span></template>
        <el-menu-item v-if="canRead('audit')" index="/audit">审计中心</el-menu-item>
        <el-menu-item v-if="canRead('report')" index="/report">报告中心</el-menu-item>
        <el-menu-item v-if="canRead('asset')" index="/lifecycle">生命周期</el-menu-item>
      </el-sub-menu>

      <el-sub-menu v-if="systemGroupVisible" index="/system">
        <template #title><el-icon><Tools /></el-icon><span>系统设置</span></template>
        <el-menu-item v-if="canRead('rbac')" index="/permission">权限管理</el-menu-item>
        <el-menu-item v-if="canRead('identity')" index="/personnel">人员管理</el-menu-item>
        <el-menu-item v-if="canRead('identity')" index="/notification">消息通知</el-menu-item>
        <el-menu-item v-if="canRead('asset')" index="/residual-rule">残值规则</el-menu-item>
        <el-menu-item v-if="canRead('ops')" index="/ops">运维面板</el-menu-item>
        <el-menu-item v-if="canRead('ops')" index="/operation-log">日志中心</el-menu-item>
      </el-sub-menu>
    </el-menu>
  </el-aside>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Bell, Box, DataBoard, Monitor, Setting, Tools, View } from '@element-plus/icons-vue'
import { useAppStore } from '../store'

const route = useRoute()
const store = useAppStore()

const assetGroupVisible = computed(() => canAny(['asset', 'purchase', 'repair']))
const resourceGroupVisible = computed(() => canAny(['asset', 'catalog']))
const masterDataGroupVisible = computed(() => canAny(['asset', 'supplier', 'identity']))
const systemGroupVisible = computed(() => canAny(['identity', 'rbac', 'asset', 'ops']))
const reportGroupVisible = computed(() => canAny(['audit', 'report', 'asset']))

onMounted(() => {
  store.loadPermissions()
})

function canRead(resource) {
  return store.canReadResource(resource)
}

function canAny(resources) {
  return resources.some(resource => canRead(resource))
}
</script>

<style scoped>
.sidebar {
  min-height: 100vh;
  overflow-x: hidden;
  border-right: 0;
  background: linear-gradient(180deg, #0c1d3c 0%, #112b5b 52%, #0d3474 100%);
  box-shadow: 4px 0 18px rgba(15, 42, 92, 0.14);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 68px;
  padding: 0 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  color: #fff;
  white-space: nowrap;
}

.brand-mark {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #1975fc, #82b8ff);
  color: #fff;
  font-weight: 800;
  font-size: 20px;
  line-height: 1;
}

.brand strong {
  font-size: 17px;
  letter-spacing: 0.2px;
}

.menu {
  height: calc(100vh - 68px);
  overflow-y: auto;
  border-right: 0;
  background: transparent;
  padding: 14px 12px 20px;
}

.menu::-webkit-scrollbar {
  width: 4px;
}

.menu::-webkit-scrollbar-thumb {
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.22);
}

:deep(.el-menu-item) {
  height: 42px;
  margin: 4px 0;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
  font-weight: 700;
}

:deep(.el-sub-menu__title) {
  height: 42px;
  margin: 4px 0;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
  font-weight: 700;
}

:deep(.el-menu-item.is-active),
:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background: linear-gradient(135deg, #1975fc, #3b8bff);
  color: #fff;
  box-shadow: none;
}

:deep(.el-menu--inline) {
  background: rgba(2, 10, 31, 0.22);
  border-radius: 12px;
  padding: 5px;
}

:deep(.el-sub-menu .el-menu-item) {
  color: rgba(255, 255, 255, 0.72);
}

:deep(.el-icon) {
  font-size: 18px;
}

.sidebar.is-collapsed .brand {
  justify-content: center;
  padding: 0;
}

.sidebar.is-collapsed .menu {
  width: 100%;
  padding: 12px 0 20px;
}

.sidebar.is-collapsed :deep(.el-menu--collapse) {
  width: 100%;
}

.sidebar.is-collapsed :deep(.el-menu-item),
.sidebar.is-collapsed :deep(.el-sub-menu__title) {
  display: flex;
  justify-content: center;
  width: 48px;
  height: 48px;
  margin: 6px auto;
  padding: 0 !important;
  border-radius: 14px;
}

.sidebar.is-collapsed :deep(.el-menu-item .el-icon),
.sidebar.is-collapsed :deep(.el-sub-menu__title .el-icon) {
  margin: 0;
}

.sidebar.is-collapsed :deep(.el-menu-item span),
.sidebar.is-collapsed :deep(.el-sub-menu__title span),
.sidebar.is-collapsed :deep(.el-sub-menu__icon-arrow) {
  display: none !important;
}

.sidebar.is-collapsed :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  background: linear-gradient(135deg, #1975fc, #3b8bff);
  color: #fff;
}
</style>
