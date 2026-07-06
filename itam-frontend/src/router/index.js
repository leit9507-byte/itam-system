import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '../store'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/login/index.vue'), meta: { public: true, title: '登录' } },
  { path: '/mobile', name: 'MobileWork', component: () => import('../views/mobile/index.vue'), meta: { title: '移动扫码作业' } },
  {
    path: '/',
    component: () => import('../layout/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/dashboard/index.vue'), meta: { title: '资产总览' } },
      { path: 'company', name: 'Company', component: () => import('../views/company/index.vue'), meta: { title: '公司管理' } },
      { path: 'department', name: 'Department', component: () => import('../views/department/index.vue'), meta: { title: '部门管理' } },
      { path: 'asset/list', name: 'AssetList', component: () => import('../views/asset/list.vue'), meta: { title: '资产管理' } },
      { path: 'asset/detail/:id', name: 'AssetDetail', component: () => import('../views/asset/detail.vue'), meta: { title: '资产详情' } },
      { path: 'location', name: 'Location', component: () => import('../views/location/index.vue'), meta: { title: '位置管理' } },
      { path: 'purchase', name: 'Purchase', component: () => import('../views/purchase/index.vue'), meta: { title: '采购管理' } },
      { path: 'supplier', name: 'Supplier', component: () => import('../views/supplier/index.vue'), meta: { title: '供应商管理' } },
      { path: 'stocktake', name: 'Stocktake', component: () => import('../views/stocktake/index.vue'), meta: { title: '资产盘点' } },
      { path: 'todo', name: 'TodoCenter', component: () => import('../views/todo/index.vue'), meta: { title: '待办中心' } },
      { path: 'repair', name: 'Repair', component: () => import('../views/repair/index.vue'), meta: { title: '维修管理' } },
      { path: 'audit', name: 'Audit', component: () => import('../views/audit/index.vue'), meta: { title: '审计中心' } },
      { path: 'risk', redirect: '/audit' },
      { path: 'lifecycle', name: 'Lifecycle', component: () => import('../views/lifecycle/index.vue'), meta: { title: '生命周期' } },
      { path: 'scrap', name: 'ScrapApproval', component: () => import('../views/scrap/index.vue'), meta: { title: '报废审批' } },
      { path: 'report', name: 'Report', component: () => import('../views/report/index.vue'), meta: { title: '报告中心' } },
      { path: 'approval', name: 'ApprovalConfig', component: () => import('../views/approval/index.vue'), meta: { title: '飞书审批对接' } },
      { path: 'permission', name: 'Permission', component: () => import('../views/permission/index.vue'), props: { mode: 'permission' }, meta: { title: '权限管理' } },
      { path: 'personnel', name: 'Personnel', component: () => import('../views/permission/index.vue'), props: { mode: 'personnel' }, meta: { title: '人员管理' } },
      { path: 'notification', name: 'Notification', component: () => import('../views/notification/index.vue'), meta: { title: '消息通知' } },
      { path: 'ops', name: 'Ops', component: () => import('../views/ops/index.vue'), meta: { title: '运维面板' } }
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
    const redirect = typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/') ? to.query.redirect : '/dashboard'
    return redirect
  }
  return true
})

export default router
