<template>
  <el-aside class="sidebar" :width="store.collapsed ? '72px' : '236px'">
    <div class="brand">
      <span class="brand-mark">◆</span>
      <strong v-if="!store.collapsed">资产管理系统</strong>
    </div>
    <el-menu :default-active="route.path" router class="menu" :collapse="store.collapsed">
      <el-menu-item index="/dashboard"><el-icon><DataBoard /></el-icon><span>资产总览</span></el-menu-item>
      <el-menu-item index="/todo"><el-icon><Bell /></el-icon><span>待办中心</span></el-menu-item>
      <el-sub-menu index="/asset">
        <template #title><el-icon><Monitor /></el-icon><span>资产运营</span></template>
        <el-menu-item index="/asset/list">资产管理</el-menu-item>
        <el-menu-item index="/stocktake">资产盘点</el-menu-item>
        <el-menu-item index="/repair">维修管理</el-menu-item>
        <el-menu-item index="/scrap">报废审批</el-menu-item>
        <el-menu-item index="/purchase">采购管理</el-menu-item>
      </el-sub-menu>
      <el-sub-menu index="/manage-config">
        <template #title><el-icon><Setting /></el-icon><span>管理配置</span></template>
        <el-menu-item index="/location">位置管理</el-menu-item>
        <el-menu-item index="/supplier">供应商管理</el-menu-item>
        <el-menu-item index="/department">部门管理</el-menu-item>
        <el-menu-item index="/company">公司管理</el-menu-item>
      </el-sub-menu>
      <el-sub-menu index="/system">
        <template #title><el-icon><Tools /></el-icon><span>系统设置</span></template>
        <el-menu-item index="/permission">权限管理</el-menu-item>
        <el-menu-item index="/approval">审批流配置</el-menu-item>
        <el-menu-item index="/personnel">人员管理</el-menu-item>
        <el-menu-item index="/notification">消息通知</el-menu-item>
        <el-menu-item index="/ops">运维面板</el-menu-item>
      </el-sub-menu>
      <el-sub-menu index="/report-audit">
        <template #title><el-icon><View /></el-icon><span>报告审核</span></template>
        <el-menu-item index="/audit">审计中心</el-menu-item>
        <el-menu-item index="/report">报告中心</el-menu-item>
        <el-menu-item index="/lifecycle">生命周期</el-menu-item>
      </el-sub-menu>
    </el-menu>
  </el-aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { Bell, DataBoard, Monitor, Setting, Tools, View } from '@element-plus/icons-vue'
import { useAppStore } from '../store'

const route = useRoute()
const store = useAppStore()
</script>

<style scoped>
.sidebar {
  min-height: 100vh;
  overflow-x: hidden;
  background: linear-gradient(180deg, #0b4ac0 0%, #05358f 46%, #062b75 100%);
  border-radius: 0 18px 18px 0;
  box-shadow: 8px 0 24px rgba(7, 47, 125, 0.2);
  transition: width 0.2s ease;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 64px;
  padding: 0 16px;
  color: #fff;
  white-space: nowrap;
}

.brand-mark {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  font-weight: 800;
  font-size: 24px;
  line-height: 1;
}

.brand strong {
  font-size: 20px;
}

.menu {
  border-right: 0;
  background: transparent;
  padding: 10px 12px 0;
}

:deep(.el-menu-item) {
  height: 54px;
  margin: 4px 0;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 16px;
  font-weight: 700;
}

:deep(.el-sub-menu__title) {
  height: 54px;
  margin: 4px 0;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 16px;
  font-weight: 700;
}

:deep(.el-menu-item.is-active),
:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background: linear-gradient(135deg, #1f85ff, #0b6eff);
  color: #fff;
  box-shadow: 0 8px 18px rgba(0, 56, 160, 0.28);
}

:deep(.el-menu--inline) {
  background: rgba(0, 27, 91, 0.18);
  border-radius: 10px;
}

:deep(.el-icon) {
  font-size: 22px;
}
</style>
