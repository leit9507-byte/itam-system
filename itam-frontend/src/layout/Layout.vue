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
  background: var(--app-bg);
}

.content-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-width: 0;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(244, 248, 255, 0.72)),
    var(--app-bg);
}

.layout-main {
  flex: 1;
  min-width: 0;
  padding: 22px 26px 28px;
  background: transparent;
}

@media (max-width: 760px) {
  .layout {
    display: block;
  }

  .layout-main {
    padding: 14px;
  }
}
</style>
