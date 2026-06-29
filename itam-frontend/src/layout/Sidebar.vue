<template>
  <el-aside class="sidebar" :width="store.collapsed ? '72px' : '236px'">
    <div class="brand">
      <span class="brand-mark">IT</span>
      <strong v-if="!store.collapsed">ITAM Dashboard</strong>
    </div>
    <el-menu :default-active="route.path" router class="menu" :collapse="store.collapsed">
      <el-menu-item index="/dashboard"><el-icon><DataBoard /></el-icon><span>资产总览</span></el-menu-item>
      <el-sub-menu index="/asset">
        <template #title><el-icon><Monitor /></el-icon><span>资产运营</span></template>
        <el-menu-item index="/asset/list">资产管理</el-menu-item>
        <el-menu-item index="/location">位置管理</el-menu-item>
        <el-menu-item index="/stocktake">资产盘点</el-menu-item>
        <el-menu-item index="/lifecycle">生命周期</el-menu-item>
      </el-sub-menu>
      <el-sub-menu index="/purchase-group">
        <template #title><el-icon><ShoppingCart /></el-icon><span>采购供应</span></template>
        <el-menu-item index="/purchase">采购管理</el-menu-item>
        <el-menu-item index="/supplier">供应商管理</el-menu-item>
      </el-sub-menu>
      <el-sub-menu index="/workflow">
        <template #title><el-icon><Tools /></el-icon><span>流程处理</span></template>
        <el-menu-item index="/repair">维修管理</el-menu-item>
        <el-menu-item index="/scrap">报废审批</el-menu-item>
      </el-sub-menu>
      <el-sub-menu index="/system">
        <template #title><el-icon><Setting /></el-icon><span>管理配置</span></template>
        <el-menu-item index="/company">公司管理</el-menu-item>
        <el-menu-item index="/permission">权限管理</el-menu-item>
      </el-sub-menu>
      <el-menu-item index="/audit"><el-icon><View /></el-icon><span>审计中心</span></el-menu-item>
      <el-menu-item index="/report"><el-icon><Document /></el-icon><span>报告中心</span></el-menu-item>
    </el-menu>
  </el-aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { DataBoard, Document, Monitor, Setting, ShoppingCart, Tools, View } from '@element-plus/icons-vue'
import { useAppStore } from '../store'

const route = useRoute()
const store = useAppStore()
</script>

<style scoped>
.sidebar {
  min-height: 100vh;
  overflow-x: hidden;
  background: #1f2937;
  transition: width 0.2s ease;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 64px;
  padding: 0 18px;
  color: #fff;
  white-space: nowrap;
}

.brand-mark {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #2dd4bf;
  color: #10201d;
  font-weight: 800;
}

.menu {
  border-right: 0;
  background: transparent;
}

:deep(.el-menu-item) {
  color: #cbd5e1;
}

:deep(.el-sub-menu__title) {
  color: #cbd5e1;
}

:deep(.el-menu-item.is-active),
:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

:deep(.el-menu--inline) {
  background: rgba(15, 23, 42, 0.35);
}
</style>
