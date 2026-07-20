<template>
  <div class="page forbidden-page">
    <el-result icon="warning" title="无权访问" sub-title="当前账号没有访问该页面的权限">
      <template #extra>
        <el-button type="primary" @click="$router.replace('/dashboard')">返回首页</el-button>
      </template>
    </el-result>
  </div>
</template>

<style scoped>
.forbidden-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #f5f7fb;
}
</style>
