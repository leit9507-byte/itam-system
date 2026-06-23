<template>
  <el-container class="layout">
    <Sidebar />
    <el-container class="content-shell">
      <Header />
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
</script>

<style scoped>
.layout {
  min-height: 100vh;
}

.content-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-width: 0;
}

.layout-main {
  flex: 1;
  min-width: 0;
  padding: 20px;
  background: var(--app-bg);
}
</style>
