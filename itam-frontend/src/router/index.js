import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '../store'
import Layout from '../layout/Layout.vue'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/login/index.vue'), meta: { public: true, title: '登录' } },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/dashboard/index.vue'), meta: { title: '资产总览' } },
      { path: 'company', name: 'Company', component: () => import('../views/company/index.vue'), meta: { title: '公司管理' } },
      { path: 'asset/list', name: 'AssetList', component: () => import('../views/asset/list.vue'), meta: { title: '资产管理' } },
      { path: 'asset/detail/:id', name: 'AssetDetail', component: () => import('../views/asset/detail.vue'), meta: { title: '资产详情' } },
      { path: 'purchase', name: 'Purchase', component: () => import('../views/purchase/index.vue'), meta: { title: '采购管理' } },
      { path: 'supplier', name: 'Supplier', component: () => import('../views/supplier/index.vue'), meta: { title: '供应商管理' } },
      { path: 'stocktake', name: 'Stocktake', component: () => import('../views/stocktake/index.vue'), meta: { title: '资产盘点' } },
      { path: 'repair', name: 'Repair', component: () => import('../views/repair/index.vue'), meta: { title: '维修管理' } },
      { path: 'audit', name: 'Audit', component: () => import('../views/audit/index.vue'), meta: { title: '审计中心' } },
      { path: 'risk', redirect: '/audit' },
      { path: 'lifecycle', name: 'Lifecycle', component: () => import('../views/lifecycle/index.vue'), meta: { title: '生命周期' } },
      { path: 'scrap', name: 'ScrapApproval', component: () => import('../views/scrap/index.vue'), meta: { title: '报废审批' } },
      { path: 'report', name: 'Report', component: () => import('../views/report/index.vue'), meta: { title: '报告中心' } },
      { path: 'permission', name: 'Permission', component: () => import('../views/permission/index.vue'), meta: { title: '权限管理' } }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(to => {
  const store = useAppStore()
  store.syncSessionFromStorage()
  if (!to.meta.public && !store.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && store.isAuthenticated) {
    return { path: '/dashboard' }
  }
  return true
})

export default router
