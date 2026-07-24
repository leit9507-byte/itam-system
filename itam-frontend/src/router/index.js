import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '../store'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/login/index.vue'), meta: { public: true, title: '登录' } },
  { path: '/mobile', name: 'MobileWork', component: () => import('../views/mobile/index.vue'), meta: { public: true, title: '移动扫码作业', resource: 'asset' } },
  { path: '/403', name: 'Forbidden', component: () => import('../views/error/Forbidden.vue'), meta: { public: true, title: '无权访问' } },
  {
    path: '/',
    component: () => import('../layout/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'operation-log', name: 'OperationLog', component: () => import('../views/operation-log/index.vue'), meta: { title: '日志中心', resource: 'ops' } },
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/dashboard/index.vue'), meta: { title: '资产总览', resource: 'asset' } },
      { path: 'company', name: 'Company', component: () => import('../views/company/index.vue'), meta: { title: '公司管理', resource: 'asset' } },
      { path: 'company/detail', name: 'CompanyDetail', component: () => import('../views/company/detail.vue'), meta: { title: '公司详情', resource: 'asset' } },
      { path: 'department', name: 'Department', component: () => import('../views/department/index.vue'), meta: { title: '部门管理', resource: 'identity' } },
      { path: 'department/detail', name: 'DepartmentDetail', component: () => import('../views/department/detail.vue'), meta: { title: '部门详情', resource: 'identity' } },
      { path: 'asset/list', name: 'AssetList', component: () => import('../views/asset/list.vue'), meta: { title: '资产管理', resource: 'asset' } },
      { path: 'asset/detail/:id', name: 'AssetDetail', component: () => import('../views/asset/detail.vue'), meta: { title: '资产详情', resource: 'asset' } },
      { path: 'checkout', name: 'CheckoutHistory', component: () => import('../views/checkout/index.vue'), meta: { title: '借用中心', resource: 'asset' } },
      { path: 'inventory', name: 'AccessoryManagement', component: () => import('../views/inventory/index.vue'), meta: { title: '配件管理', inventoryMode: 'parts', resource: 'asset' } },
      { path: 'software-license', name: 'SoftwareLicense', component: () => import('../views/inventory/index.vue'), meta: { title: '软件许可', inventoryMode: 'license', resource: 'asset' } },
      { path: 'location', name: 'Location', component: () => import('../views/location/index.vue'), meta: { title: '位置管理', resource: 'asset' } },
      { path: 'location/detail', name: 'LocationDetail', component: () => import('../views/location/detail.vue'), meta: { title: '位置详情', resource: 'asset' } },
      { path: 'device-type', name: 'DeviceType', component: () => import('../views/device-type/index.vue'), meta: { title: '设备类型', resource: 'catalog' } },
      { path: 'product', name: 'ProductCatalog', component: () => import('../views/product/index.vue'), meta: { title: '产品档案', resource: 'catalog' } },
      { path: 'purchase', name: 'Purchase', component: () => import('../views/purchase/index.vue'), meta: { title: '采购管理', resource: 'purchase' } },
      { path: 'supplier', name: 'Supplier', component: () => import('../views/supplier/index.vue'), meta: { title: '供应商管理', resource: 'supplier' } },
      { path: 'supplier/detail', name: 'SupplierDetail', component: () => import('../views/supplier/detail.vue'), meta: { title: '供应商详情', resource: 'supplier' } },
      { path: 'stocktake', name: 'Stocktake', component: () => import('../views/stocktake/index.vue'), meta: { title: '资产盘点', resource: 'asset' } },
      { path: 'todo', name: 'TodoCenter', component: () => import('../views/todo/index.vue'), meta: { title: '待办中心', resource: 'asset' } },
      { path: 'repair', name: 'Repair', component: () => import('../views/repair/index.vue'), meta: { title: '维修管理', resource: 'repair' } },
      { path: 'audit', name: 'Audit', component: () => import('../views/audit/index.vue'), meta: { title: '审计中心', resource: 'audit' } },
      { path: 'risk', redirect: '/audit' },
      { path: 'lifecycle', name: 'Lifecycle', component: () => import('../views/lifecycle/index.vue'), meta: { title: '生命周期', resource: 'asset' } },
      { path: 'scrap', name: 'ScrapDisposal', component: () => import('../views/scrap/index.vue'), meta: { title: '报废处置登记', resource: 'asset' } },
      { path: 'report', name: 'Report', component: () => import('../views/report/index.vue'), meta: { title: '报告中心', resource: 'report' } },
      { path: 'permission', name: 'Permission', component: () => import('../views/permission/index.vue'), props: { mode: 'permission' }, meta: { title: '权限管理', resource: 'rbac' } },
      { path: 'personnel', name: 'Personnel', component: () => import('../views/permission/index.vue'), props: { mode: 'personnel' }, meta: { title: '人员管理', resource: 'identity' } },
      { path: 'notification', name: 'Notification', component: () => import('../views/notification/index.vue'), meta: { title: '消息通知', resource: 'identity' } },
      { path: 'residual-rule', name: 'ResidualRule', component: () => import('../views/residual-rule/index.vue'), meta: { title: '残值计算规则', resource: 'asset' } },
      { path: 'ops', name: 'Ops', component: () => import('../views/ops/index.vue'), meta: { title: '运维面板', resource: 'ops' } }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async to => {
  const store = useAppStore()
  store.syncSessionFromStorage()
  if (!to.meta.public && !store.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && store.isAuthenticated) {
    const redirect = typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/') ? to.query.redirect : '/dashboard'
    return redirect
  }
  if (!to.meta.public && to.meta.resource) {
    await store.loadPermissions()
    if (!store.canReadResource(to.meta.resource)) return { path: '/403' }
  }
  return true
})

export default router
