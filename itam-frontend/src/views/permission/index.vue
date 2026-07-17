<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ pageTitle }}</h2>
        <p class="page-subtitle">{{ pageSubtitle }}</p>
      </div>
      <div v-if="isPersonnelMode" class="header-actions">
        <el-button @click="openLocalUserDialog">新增本地账户</el-button>
        <el-button type="primary" @click="syncFromProvider">从身份源同步用户</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane v-if="isPersonnelMode" label="用户目录" name="users">
        <el-card shadow="never">
          <el-table :data="pagedUsers" border stripe>
            <el-table-column prop="display_name" label="姓名" min-width="130" />
            <el-table-column prop="username" label="账号" min-width="120" />
            <el-table-column prop="email" label="邮箱" min-width="180" />
            <el-table-column prop="dept_name" label="部门" min-width="140">
              <template #default="{ row }">{{ row.dept_name || row.dept_id || '-' }}</template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="100">
              <template #default="{ row }"><el-tag>{{ row.source }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="role" label="角色" width="120" />
            <el-table-column prop="failed_login_count" label="失败次数" width="100" />
            <el-table-column prop="locked_until" label="锁定至" min-width="160">
              <template #default="{ row }">{{ row.locked_until || '未锁定' }}</template>
            </el-table-column>
            <el-table-column prop="last_login_at" label="最后登录" min-width="160">
              <template #default="{ row }">{{ row.last_login_at || '-' }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }"><el-tag :type="userStatusType(row.status)">{{ userStatusLabel(row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="300" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openUserPermission(row)">配置权限</el-button>
                <el-button v-if="row.status === 'active'" link type="primary" @click="goAssetAssign(row)">资产分配</el-button>
                <el-button v-if="isInactiveUser(row.status)" link type="warning" @click="goAssetReclaim(row)">离职回收</el-button>
                <el-button link type="danger" :disabled="row.source !== 'local' || row.username === 'admin' || isInactiveUser(row.status)" @click="removeUser(row)">标记离职</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="userPagination.page"
              v-model:page-size="userPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="users.length"
              layout="total, sizes, prev, pager, next, jumper"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="isPersonnelMode" label="入职清单" name="onboarding">
        <el-card shadow="never">
          <el-table :data="pagedOnboardingUsers" border stripe empty-text="暂无入职人员">
            <el-table-column prop="display_name" label="姓名" min-width="130" />
            <el-table-column prop="username" label="账号" min-width="130" />
            <el-table-column prop="dept_name" label="部门" min-width="140">
              <template #default="{ row }">{{ row.dept_name || row.dept_id || '-' }}</template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="100">
              <template #default="{ row }"><el-tag>{{ row.source }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="created_at" label="入职/同步创建时间" min-width="180">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="last_synced_at" label="最近同步" min-width="180">
              <template #default="{ row }">{{ formatDateTime(row.last_synced_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="goAssetAssign(row)">资产分配</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="onboardingPagination.page"
              v-model:page-size="onboardingPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="onboardingUsers.length"
              layout="total, sizes, prev, pager, next, jumper"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="isPersonnelMode" label="离职清单" name="offboarding">
        <el-card shadow="never">
          <el-table :data="pagedOffboardingUsers" border stripe empty-text="暂无离职人员">
            <el-table-column prop="display_name" label="姓名" min-width="130" />
            <el-table-column prop="username" label="账号" min-width="130" />
            <el-table-column prop="dept_name" label="部门" min-width="140">
              <template #default="{ row }">{{ row.dept_name || row.dept_id || '-' }}</template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="100">
              <template #default="{ row }"><el-tag>{{ row.source }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }"><el-tag :type="userStatusType(row.status)">{{ userStatusLabel(row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="last_synced_at" label="离职/同步更新时间" min-width="180">
              <template #default="{ row }">{{ formatDateTime(row.last_synced_at || row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="warning" @click="goAssetReclaim(row)">离职回收</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="offboardingPagination.page"
              v-model:page-size="offboardingPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="offboardingUsers.length"
              layout="total, sizes, prev, pager, next, jumper"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="!isPersonnelMode" label="用户权限配置" name="user-permissions">
        <el-card shadow="never">
          <div class="user-permission-picker">
            <el-select
              v-model="selectedUserId"
              filterable
              placeholder="选择要配置权限的用户"
              class="user-select"
              @change="selectPermissionUser"
            >
              <el-option
                v-for="user in users"
                :key="user.user_id"
                :label="`${user.display_name || user.username} / ${user.username} / ${roleLabel(user.role)}`"
                :value="user.user_id"
              />
            </el-select>
            <el-button type="primary" :disabled="!selectedUserId" @click="openSelectedUserPermission">打开配置弹窗</el-button>
          </div>

          <el-empty v-if="!selectedPermissionUser" description="请选择一个用户后配置角色和权限" />

          <template v-else>
            <el-descriptions border :column="3" class="user-permission-summary">
              <el-descriptions-item label="用户">{{ selectedPermissionUser.display_name || selectedPermissionUser.username }}</el-descriptions-item>
              <el-descriptions-item label="账号">{{ selectedPermissionUser.username }}</el-descriptions-item>
              <el-descriptions-item label="当前角色">{{ roleLabel(selectedPermissionUser.role) }}</el-descriptions-item>
              <el-descriptions-item label="来源">{{ selectedPermissionUser.source }}</el-descriptions-item>
              <el-descriptions-item label="状态">{{ userStatusLabel(selectedPermissionUser.status) }}</el-descriptions-item>
              <el-descriptions-item label="部门">{{ selectedPermissionUser.dept_name || selectedPermissionUser.dept_id || '-' }}</el-descriptions-item>
            </el-descriptions>

            <el-form label-width="90px" class="user-permission-form">
              <el-form-item label="角色">
                <el-select v-model="selectedRole" filterable allow-create default-first-option style="width: 280px">
                  <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="状态">
                <el-select v-model="userPermissionDialog.status" style="width: 180px">
                  <el-option label="在职" value="active" />
                  <el-option label="停用" value="disabled" />
                  <el-option label="离职" value="resigned" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button @click="resetPermissionDraft">重置权限</el-button>
                <el-button type="primary" :loading="userPermissionDialog.saving" @click="saveUserPermissionConfig">保存用户权限</el-button>
              </el-form-item>
            </el-form>

            <el-alert
              v-if="selectedRole === 'admin'"
              class="rbac-alert"
              type="info"
              show-icon
              :closable="false"
              title="admin 角色拥有全部权限。切换为其他角色后，可以编辑该角色权限。"
            />

            <el-table :data="permissionMatrixRows" border stripe>
              <el-table-column prop="label" label="资源" min-width="160">
                <template #default="{ row }">
                  <strong>{{ row.label }}</strong>
                  <div class="resource-key">{{ row.resource }}</div>
                </template>
              </el-table-column>
              <el-table-column v-for="action in permissionActions" :key="action.value" :label="action.label" width="130" align="center">
                <template #default="{ row }">
                  <el-switch
                    :model-value="permissionAllowed(row.resource, action.value)"
                    :disabled="selectedRole === 'admin'"
                    @change="value => updatePermission(row.resource, action.value, value)"
                  />
                </template>
              </el-table-column>
            </el-table>
          </template>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="!isPersonnelMode" label="RBAC 权限" name="rbac">
        <div class="rbac-toolbar">
          <el-select v-model="selectedRole" filterable allow-create default-first-option placeholder="选择或输入角色" class="role-select">
            <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
          </el-select>
          <el-button @click="resetPermissionDraft">重置</el-button>
          <el-button type="primary" :loading="permissionSaving" :disabled="selectedRole === 'admin'" @click="saveSelectedRolePermissions">保存权限</el-button>
        </div>

        <el-alert
          v-if="selectedRole === 'admin'"
          class="rbac-alert"
          type="info"
          show-icon
          :closable="false"
          title="admin 为超级管理员角色，后端会直接放行所有资源，不需要配置权限。"
        />

        <el-card shadow="never">
          <el-table :data="permissionMatrixRows" border stripe>
            <el-table-column prop="label" label="资源" min-width="160">
              <template #default="{ row }">
                <strong>{{ row.label }}</strong>
                <div class="resource-key">{{ row.resource }}</div>
              </template>
            </el-table-column>
            <el-table-column v-for="action in permissionActions" :key="action.value" :label="action.label" width="130" align="center">
              <template #default="{ row }">
                <el-switch
                  :model-value="permissionAllowed(row.resource, action.value)"
                  :disabled="selectedRole === 'admin'"
                  @change="value => updatePermission(row.resource, action.value, value)"
                />
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never" class="permission-detail-card">
          <template #header>权限明细</template>
          <el-table :data="pagedPermissions" border stripe>
            <el-table-column prop="role" label="角色" width="130" />
            <el-table-column prop="resource" label="资源" width="150" />
            <el-table-column prop="action" label="动作" width="120" />
            <el-table-column prop="allowed" label="允许" width="100">
              <template #default="{ row }"><el-tag :type="row.allowed ? 'success' : 'danger'">{{ row.allowed ? '允许' : '拒绝' }}</el-tag></template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="permissionPagination.page"
              v-model:page-size="permissionPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="permissions.length"
              layout="total, sizes, prev, pager, next, jumper"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="!isPersonnelMode" label="身份源配置" name="providers">
        <div class="provider-grid">
          <el-card shadow="never">
            <template #header>新增/编辑身份源</template>
            <el-form :model="providerForm" label-width="110px">
              <el-alert
                class="config-help"
                type="info"
                show-icon
                :closable="false"
                title="按字段逐项填写即可。LDAP 用于账号登录和目录同步。"
              />
              <el-form-item label="名称"><el-input v-model="providerForm.name" placeholder="例如：公司 LDAP" /></el-form-item>
              <el-form-item label="类型">
                <el-select v-model="providerForm.provider_type" style="width: 100%">
                  <el-option label="LDAP / AD" value="ldap" />
                  <el-option label="飞书应用（仅 JSAPI）" value="feishu" />
                </el-select>
              </el-form-item>
              <el-form-item label="启用"><el-switch v-model="providerForm.enabled" /></el-form-item>

              <template v-if="providerForm.provider_type === 'ldap'">
                <el-divider content-position="left">连接信息</el-divider>
                <el-form-item label="服务器地址" required><el-input v-model="providerConfig.host" placeholder="ldap://ldap.example.com 或 ldaps://ldap.example.com" /></el-form-item>
                <el-form-item label="端口"><el-input v-model="providerConfig.port" placeholder="389 或 636；留空自动判断" /></el-form-item>
                <el-form-item label="绑定账号" required><el-input v-model="providerConfig.bind_dn" placeholder="cn=admin,dc=example,dc=com" /></el-form-item>
                <el-form-item label="绑定密码" required><el-input v-model="providerConfig.bind_password" type="password" show-password placeholder="服务账号密码" /></el-form-item>
                <el-form-item label="搜索根 DN" required><el-input v-model="providerConfig.base_dn" placeholder="ou=people,dc=example,dc=com" /></el-form-item>
                <el-form-item label="登录过滤器"><el-input v-model="providerConfig.user_filter" placeholder="(uid={username}) 或 (sAMAccountName={username})" /></el-form-item>
                <el-form-item label="同步过滤器"><el-input v-model="providerConfig.sync_filter" placeholder="(objectClass=person)" /></el-form-item>

                <el-divider content-position="left">字段映射</el-divider>
                <el-form-item label="账号字段"><el-input v-model="providerConfig.username_attr" placeholder="OpenLDAP: uid；AD: sAMAccountName" /></el-form-item>
                <el-form-item label="姓名字段"><el-input v-model="providerConfig.display_name_attr" placeholder="displayName 或 cn" /></el-form-item>
                <el-form-item label="邮箱字段"><el-input v-model="providerConfig.email_attr" placeholder="mail" /></el-form-item>
                <el-form-item label="部门编码字段"><el-input v-model="providerConfig.dept_id_attr" placeholder="departmentNumber，可留空" /></el-form-item>
                <el-form-item label="部门名称字段"><el-input v-model="providerConfig.dept_name_attr" placeholder="department 或 ou，可留空" /></el-form-item>

                <el-divider content-position="left">同步设置</el-divider>
                <el-form-item label="默认角色">
                  <el-select v-model="providerConfig.default_role" style="width: 100%">
                    <el-option label="普通用户" value="user" />
                    <el-option label="资产管理员" value="asset_manager" />
                    <el-option label="部门负责人" value="dept_manager" />
                    <el-option label="审计员" value="auditor" />
                  </el-select>
                </el-form-item>
                <el-form-item label="同步上限"><el-input v-model="providerConfig.sync_limit" placeholder="200" /></el-form-item>
                <el-form-item label="测试账号"><el-input v-model="providerConfig.test_username" placeholder="保存后测试时尝试解析这个账号，可留空" /></el-form-item>
                <el-alert
                  class="config-help"
                  type="info"
                  show-icon
                  :closable="false"
                  title="OpenLDAP 常用 uid/cn/mail/ou；AD 常用 sAMAccountName/displayName/mail/department。登录过滤器中的 {username} 会自动替换为登录账号。"
                />
              </template>

              <template v-else-if="providerForm.provider_type === 'feishu'">
                <el-divider content-position="left">JSAPI 鉴权</el-divider>
                <el-form-item label="App ID" required><el-input v-model="providerConfig.app_id" placeholder="cli_xxxxxxxxxxxxxxxx" /></el-form-item>
                <el-form-item label="App Secret" required><el-input v-model="providerConfig.app_secret" type="password" show-password placeholder="飞书应用 App Secret" /></el-form-item>
                <el-alert
                  class="config-help"
                  type="info"
                  show-icon
                  :closable="false"
                  title="此配置只用于生成飞书 JSAPI 签名和移动端扫码，不提供飞书登录，也不会发起飞书审批。"
                />
              </template>

              <el-form-item>
                <el-button @click="resetProviderForm">清空</el-button>
                <el-button type="primary" @click="saveProvider">保存配置</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>已配置身份源</template>
            <el-table :data="pagedProviders" border>
              <el-table-column prop="name" label="名称" />
              <el-table-column label="类型" width="110">
                <template #default="{ row }">{{ providerTypeLabel(row.provider_type) }}</template>
              </el-table-column>
              <el-table-column prop="enabled" label="启用" width="80">
                <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '是' : '否' }}</el-tag></template>
              </el-table-column>
              <el-table-column prop="last_test_status" label="测试状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="row.last_test_status === 'success' ? 'success' : row.last_test_status === 'failed' ? 'danger' : 'info'">{{ row.last_test_status || '-' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="last_test_message" label="测试信息" min-width="220" show-overflow-tooltip />
              <el-table-column label="操作" width="230">
                <template #default="{ row }">
                  <el-button link type="primary" @click="editProvider(row)">编辑</el-button>
                  <el-button link type="warning" @click="testProvider(row)">测试</el-button>
                  <el-button link type="success" @click="syncFromProvider(row)">同步</el-button>
                  <el-button link type="danger" @click="removeProvider(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-bar">
              <el-pagination
                v-model:current-page="providerPagination.page"
                v-model:page-size="providerPagination.pageSize"
                :page-sizes="[10, 20, 50, 100]"
                :total="supportedProviders.length"
                layout="total, sizes, prev, pager, next"
              />
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="!isPersonnelMode" label="移动端配置" name="mobile-config">
        <div class="mobile-config-grid">
          <el-card shadow="never">
            <template #header>访问入口</template>
            <el-descriptions border :column="1" class="mobile-config-desc">
              <el-descriptions-item label="移动端地址">
                <div class="copy-row">
                  <span>{{ mobileConfig.mobileUrl }}</span>
                  <el-button link type="primary" @click="copyText(mobileConfig.mobileUrl)">复制</el-button>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="飞书工作台地址">
                <div class="copy-row">
                  <span>{{ mobileConfig.mobileUrl }}</span>
                  <el-button link type="primary" @click="copyText(mobileConfig.mobileUrl)">复制</el-button>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="扫码内容示例">
                <div class="copy-row">
                  <span>{{ mobileConfig.scanExample }}</span>
                  <el-button link type="primary" @click="copyText(mobileConfig.scanExample)">复制</el-button>
                </div>
              </el-descriptions-item>
            </el-descriptions>

            <div class="mobile-checks">
              <div v-for="item in mobileConfigChecks" :key="item.label" class="mobile-check-item">
                <el-tag :type="item.ok ? 'success' : 'warning'">{{ item.ok ? '已就绪' : '需配置' }}</el-tag>
                <div>
                  <strong>{{ item.label }}</strong>
                  <span>{{ item.tip }}</span>
                </div>
              </div>
            </div>
          </el-card>

          <el-card shadow="never">
            <template #header>飞书应用配置</template>
            <el-steps direction="vertical" :active="5" finish-status="success" class="mobile-steps">
              <el-step title="应用能力" description="在飞书开放平台创建企业自建应用，网页应用或工作台入口指向移动端地址。" />
              <el-step title="安全域名" :description="mobileConfig.host ? `把 ${mobileConfig.host} 加入网页应用安全域名。` : '把当前系统域名加入网页应用安全域名。'" />
              <el-step title="JS SDK" description="需要原生扫码时启用飞书 JS SDK，并确保页面使用 HTTPS 或飞书客户端内访问。" />
              <el-step title="应用凭证" description="在身份源配置中新增“飞书应用（仅 JSAPI）”，填写 App ID 和 App Secret。" />
              <el-step title="发布应用" description="权限、域名、工作台入口变更后发布应用，移动端扫码才会按最新配置生效。" />
            </el-steps>
          </el-card>

          <el-card shadow="never">
            <template #header>前端环境变量</template>
            <el-table :data="mobileEnvRows" border stripe>
              <el-table-column prop="key" label="变量" width="220" />
              <el-table-column prop="value" label="当前值" min-width="220">
                <template #default="{ row }">{{ row.value || '未配置' }}</template>
              </el-table-column>
              <el-table-column prop="desc" label="说明" min-width="260" />
            </el-table>
            <el-input class="env-snippet" :model-value="mobileConfig.envSnippet" type="textarea" :rows="5" readonly />
            <el-button type="primary" @click="copyText(mobileConfig.envSnippet)">复制环境变量示例</el-button>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="!isPersonnelMode" label="登录测试" name="login">
        <el-card shadow="never" class="login-card">
          <el-form :model="loginForm" label-width="100px">
            <el-form-item label="登录方式">
              <el-radio-group v-model="loginForm.provider">
                <el-radio-button label="local">本地</el-radio-button>
                <el-radio-button label="ldap">LDAP</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="账号"><el-input v-model="loginForm.username" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="loginForm.password" type="password" show-password /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="submitLogin">账号登录</el-button>
            </el-form-item>
          </el-form>
          <el-descriptions v-if="loginResult" title="登录结果" border :column="1">
            <el-descriptions-item label="Token">{{ loginResult.access_token }}</el-descriptions-item>
            <el-descriptions-item label="有效期">{{ loginResult.expires_in }} 秒</el-descriptions-item>
            <el-descriptions-item label="用户">{{ loginResult.user.display_name }} / {{ loginResult.user.role }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ loginResult.user.source }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="accountDialog.visible" title="新增本地账户" width="560px">
      <el-form :model="accountDialog.form" label-width="90px">
        <el-form-item label="账号" required><el-input v-model="accountDialog.form.username" /></el-form-item>
        <el-form-item label="姓名" required><el-input v-model="accountDialog.form.display_name" /></el-form-item>
        <el-form-item label="密码" required><el-input v-model="accountDialog.form.password" type="password" show-password /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="accountDialog.form.email" /></el-form-item>
        <el-form-item label="部门编码"><el-input v-model="accountDialog.form.dept_id" /></el-form-item>
        <el-form-item label="部门名称"><el-input v-model="accountDialog.form.dept_name" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="accountDialog.form.role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="审计员" value="auditor" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="accountDialog.form.status" style="width: 100%">
            <el-option label="在职" value="active" />
            <el-option label="停用" value="disabled" />
            <el-option label="离职" value="resigned" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="accountDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitLocalUser">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="userPermissionDialog.visible" title="配置用户权限" width="900px">
      <el-descriptions v-if="userPermissionDialog.user" border :column="2" class="user-permission-summary">
        <el-descriptions-item label="用户">{{ userPermissionDialog.user.display_name || userPermissionDialog.user.username }}</el-descriptions-item>
        <el-descriptions-item label="账号">{{ userPermissionDialog.user.username }}</el-descriptions-item>
        <el-descriptions-item label="来源">{{ userPermissionDialog.user.source }}</el-descriptions-item>
        <el-descriptions-item label="部门">{{ userPermissionDialog.user.dept_name || userPermissionDialog.user.dept_id || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-form label-width="90px" class="user-permission-form">
        <el-form-item label="角色">
          <el-select v-model="selectedRole" filterable allow-create default-first-option style="width: 280px">
            <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="userPermissionDialog.status" style="width: 180px">
            <el-option label="在职" value="active" />
            <el-option label="停用" value="disabled" />
            <el-option label="离职" value="resigned" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="selectedRole === 'admin'"
        class="rbac-alert"
        type="info"
        show-icon
        :closable="false"
        title="admin 角色拥有全部权限。切换为其他角色后，可以在下方编辑该角色权限。"
      />

      <el-table :data="permissionMatrixRows" border stripe>
        <el-table-column prop="label" label="资源" min-width="160">
          <template #default="{ row }">
            <strong>{{ row.label }}</strong>
            <div class="resource-key">{{ row.resource }}</div>
          </template>
        </el-table-column>
        <el-table-column v-for="action in permissionActions" :key="action.value" :label="action.label" width="130" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="permissionAllowed(row.resource, action.value)"
              :disabled="selectedRole === 'admin'"
              @change="value => updatePermission(row.resource, action.value, value)"
            />
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <el-button @click="userPermissionDialog.visible = false">取消</el-button>
        <el-button @click="resetPermissionDraft">重置权限</el-button>
        <el-button type="primary" :loading="userPermissionDialog.saving" @click="saveUserPermissionConfig">保存用户权限</el-button>
      </template>
    </el-dialog>

    <TodoAssetActions ref="todoAssetActionsRef" @completed="loadUsers" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '../../store'
import TodoAssetActions from '../../components/TodoAssetActions.vue'
import {
  createIdentityProvider,
  deleteUser,
  deleteIdentityProvider,
  getIdentityProviders,
  getRolePermissions,
  getUsers,
  login,
  saveRolePermissions,
  saveUser,
  syncUsers,
  testIdentityProvider,
  updateIdentityProvider,
  updateUserPermissions
} from '../../api/user'

const props = defineProps({
  mode: { type: String, default: 'permission' }
})

const store = useAppStore()
const isPersonnelMode = computed(() => props.mode === 'personnel')
const pageTitle = computed(() => (isPersonnelMode.value ? '人员管理' : '权限管理'))
const pageSubtitle = computed(() =>
  isPersonnelMode.value
    ? '独立维护本地账号、身份源同步用户、账号状态和离职回收入口'
    : '统一管理用户权限、RBAC 角色、LDAP 身份源和登录测试'
)
const activeTab = ref(isPersonnelMode.value ? 'users' : 'user-permissions')
const users = ref([])
const providers = ref([])
const permissions = ref([])
const loginResult = ref(null)
const selectedUserId = ref('')
const selectedRole = ref('user')
const permissionSaving = ref(false)
const runtimeOrigin = typeof window !== 'undefined' ? window.location.origin : ''
const runtimeProtocol = typeof window !== 'undefined' ? window.location.protocol : ''
const runtimeHost = typeof window !== 'undefined' ? window.location.host : ''
const providerForm = reactive(defaultProviderForm())
const providerConfig = reactive(defaultConfig())
const loginForm = reactive({ provider: 'local', username: 'admin', password: 'admin' })
const accountDialog = reactive({ visible: false, form: defaultLocalUserForm() })
const userPermissionDialog = reactive({ visible: false, user: null, status: 'active', saving: false })
const permissionDraft = reactive({})
const userPagination = reactive({ page: 1, pageSize: 10 })
const onboardingPagination = reactive({ page: 1, pageSize: 10 })
const offboardingPagination = reactive({ page: 1, pageSize: 10 })
const permissionPagination = reactive({ page: 1, pageSize: 10 })
const providerPagination = reactive({ page: 1, pageSize: 10 })
const todoAssetActionsRef = ref(null)
const pagedUsers = computed(() => paginate(users.value, userPagination))
const onboardingUsers = computed(() => users.value.filter(user => user.status === 'active').sort((a, b) => dateValue(b.created_at) - dateValue(a.created_at)))
const offboardingUsers = computed(() => users.value.filter(user => isInactiveUser(user.status)).sort((a, b) => dateValue(b.last_synced_at || b.created_at) - dateValue(a.last_synced_at || a.created_at)))
const pagedOnboardingUsers = computed(() => paginate(onboardingUsers.value, onboardingPagination))
const pagedOffboardingUsers = computed(() => paginate(offboardingUsers.value, offboardingPagination))
const pagedPermissions = computed(() => paginate(permissions.value, permissionPagination))
const supportedProviders = computed(() => providers.value.filter(item => ['ldap', 'feishu'].includes(item.provider_type)))
const pagedProviders = computed(() => paginate(supportedProviders.value, providerPagination))
const selectedPermissionUser = computed(() => users.value.find(user => user.user_id === selectedUserId.value) || null)
const mobileConfig = computed(() => {
  const publicUrl = import.meta.env.VITE_MOBILE_PUBLIC_URL || `${runtimeOrigin}/mobile`
  return {
    mobileUrl: publicUrl,
    host: safeUrlHost(publicUrl) || runtimeHost,
    scanExample: `${runtimeOrigin || 'https://it.example.com'}/hardware/1982`,
    feishuSdkUrl: import.meta.env.VITE_FEISHU_SDK_URL || '',
    feishuSdkAutoLoad: import.meta.env.VITE_FEISHU_SDK_AUTO_LOAD || '',
    envSnippet: [
      `VITE_MOBILE_PUBLIC_URL=${publicUrl}`,
      'VITE_FEISHU_SDK_URL=https://lf1-cdn-tos.bytegoofy.com/goofy/lark/op/h5-js-sdk-1.5.30.js',
      'VITE_FEISHU_SDK_AUTO_LOAD=true'
    ].join('\n')
  }
})
const mobileConfigChecks = computed(() => [
  {
    label: '移动端访问地址',
    ok: Boolean(mobileConfig.value.mobileUrl),
    tip: '飞书工作台、二维码或企业微信内嵌入口都使用这个地址。'
  },
  {
    label: 'HTTPS 或本地调试',
    ok: runtimeProtocol === 'https:' || ['localhost', '127.0.0.1'].includes((runtimeHost.split(':')[0] || '').toLowerCase()),
    tip: '浏览器摄像头扫码通常要求 HTTPS；飞书客户端内扫码也建议使用 HTTPS。'
  },
  {
    label: '飞书 JS SDK',
    ok: Boolean(mobileConfig.value.feishuSdkUrl || mobileConfig.value.feishuSdkAutoLoad === 'true'),
    tip: '配置后移动端会优先调用飞书原生扫码，失败时再回退浏览器扫码。'
  }
])
const mobileEnvRows = computed(() => [
  { key: 'VITE_MOBILE_PUBLIC_URL', value: import.meta.env.VITE_MOBILE_PUBLIC_URL || '', desc: '移动端对外访问地址，用于飞书工作台和配置指引展示。' },
  { key: 'VITE_FEISHU_SDK_URL', value: import.meta.env.VITE_FEISHU_SDK_URL || '', desc: '飞书 JS SDK 地址；内网环境可换成企业可访问的镜像地址。' },
  { key: 'VITE_FEISHU_SDK_AUTO_LOAD', value: import.meta.env.VITE_FEISHU_SDK_AUTO_LOAD || '', desc: '设为 true 时非飞书客户端也尝试加载 SDK，便于调试。' }
])
const permissionActions = [
  { label: '读取', value: 'read' },
  { label: '写入', value: 'write' },
  { label: '删除', value: 'delete' }
]
const resourceOptions = [
  { label: '资产运营', resource: 'asset' },
  { label: '采购管理', resource: 'purchase' },
  { label: '维修管理', resource: 'repair' },
  { label: '供应商管理', resource: 'supplier' },
  { label: '产品目录', resource: 'catalog' },
  { label: '审计中心', resource: 'audit' },
  { label: '身份源/用户', resource: 'identity' },
  { label: 'RBAC 权限', resource: 'rbac' },
  { label: '运维面板', resource: 'ops' },
  { label: '附件文件', resource: 'file' },
  { label: '报告中心', resource: 'report' }
]
const permissionMatrixRows = computed(() => resourceOptions)
const roleOptions = computed(() => {
  const roleSet = new Set(['user', 'auditor', 'admin'])
  users.value.forEach(item => item.role && roleSet.add(item.role))
  permissions.value.forEach(item => item.role && roleSet.add(item.role))
  return Array.from(roleSet).map(role => ({ label: roleLabel(role), value: role }))
})

onMounted(async () => {
  await Promise.all([loadUsers(), loadProviders(), loadPermissions()])
  resetProviderForm()
})

watch(
  () => providerForm.provider_type,
  type => {
    if (!providerForm.id) {
      setProviderConfig(defaultConfig(type))
    }
  }
)

watch(
  () => props.mode,
  mode => {
    activeTab.value = mode === 'personnel' ? 'users' : 'user-permissions'
  }
)

async function loadUsers() {
  users.value = await getUsers()
  if (!selectedUserId.value && users.value.length) {
    selectedUserId.value = users.value[0].user_id
    selectPermissionUser(selectedUserId.value)
  }
}

async function loadProviders() {
  providers.value = await getIdentityProviders()
}

async function loadPermissions() {
  permissions.value = await getRolePermissions()
  resetPermissionDraft()
}

function roleLabel(role) {
  return {
    user: '普通用户',
    auditor: '审计员',
    admin: '管理员'
  }[role] || role
}

function permissionKey(role, resource, action) {
  return `${role}::${resource}::${action}`
}

function resetPermissionDraft() {
  Object.keys(permissionDraft).forEach(key => delete permissionDraft[key])
  permissions.value.forEach(item => {
    permissionDraft[permissionKey(item.role, item.resource, item.action)] = Boolean(item.allowed)
  })
}

function permissionAllowed(resource, action) {
  if (selectedRole.value === 'admin') return true
  return Boolean(permissionDraft[permissionKey(selectedRole.value, resource, action)])
}

function updatePermission(resource, action, allowed) {
  permissionDraft[permissionKey(selectedRole.value, resource, action)] = allowed
}

async function saveSelectedRolePermissions() {
  if (!selectedRole.value || selectedRole.value === 'admin') return
  permissionSaving.value = true
  try {
    const payload = resourceOptions.flatMap(resource =>
      permissionActions.map(action => ({
        role: selectedRole.value,
        resource: resource.resource,
        action: action.value,
        allowed: permissionAllowed(resource.resource, action.value)
      }))
    )
    permissions.value = await saveRolePermissions(payload)
    resetPermissionDraft()
    ElMessage.success(`${roleLabel(selectedRole.value)}权限已保存`)
  } finally {
    permissionSaving.value = false
  }
}

function defaultProviderForm() {
  return { id: null, name: '', provider_type: 'ldap', enabled: true }
}

function defaultLocalUserForm() {
  return {
    username: '',
    display_name: '',
    password: '',
    email: '',
    dept_id: '',
    dept_name: '',
    role: 'user',
    status: 'active'
  }
}

function openLocalUserDialog() {
  Object.assign(accountDialog.form, defaultLocalUserForm())
  accountDialog.visible = true
}

function openUserPermission(row) {
  selectedUserId.value = row.user_id
  userPermissionDialog.user = row
  userPermissionDialog.status = row.status || 'active'
  selectedRole.value = row.role || 'user'
  resetPermissionDraft()
  userPermissionDialog.visible = true
}

function selectPermissionUser(userId) {
  const user = users.value.find(item => item.user_id === userId)
  if (!user) return
  userPermissionDialog.user = user
  userPermissionDialog.status = user.status || 'active'
  selectedRole.value = user.role || 'user'
  resetPermissionDraft()
}

function openSelectedUserPermission() {
  const user = selectedPermissionUser.value
  if (!user) return
  openUserPermission(user)
}

async function saveUserPermissionConfig() {
  if (!userPermissionDialog.user?.user_id) return
  if (!selectedRole.value) {
    ElMessage.warning('请选择或输入角色')
    return
  }
  userPermissionDialog.saving = true
  try {
    if (selectedRole.value !== 'admin') {
      const payload = resourceOptions.flatMap(resource =>
        permissionActions.map(action => ({
          role: selectedRole.value,
          resource: resource.resource,
          action: action.value,
          allowed: permissionAllowed(resource.resource, action.value)
        }))
      )
      permissions.value = await saveRolePermissions(payload)
      resetPermissionDraft()
    }
    await updateUserPermissions(userPermissionDialog.user.user_id, {
      role: selectedRole.value,
      status: userPermissionDialog.status
    })
    userPermissionDialog.visible = false
    ElMessage.success('用户权限已保存')
    await Promise.all([loadUsers(), loadPermissions()])
  } finally {
    userPermissionDialog.saving = false
  }
}

async function submitLocalUser() {
  if (!accountDialog.form.username.trim() || !accountDialog.form.display_name.trim() || !accountDialog.form.password) {
    ElMessage.warning('请填写账号、姓名和密码')
    return
  }
  const createdUser = await saveUser(accountDialog.form)
  accountDialog.visible = false
  try {
    await ElMessageBox.confirm('入职账户已创建。是否现在进入资产管理，为该员工分配设备？', '入职提醒', {
      confirmButtonText: '去资产分配',
      cancelButtonText: '稍后处理',
      type: 'success'
    })
    goAssetAssign(createdUser || accountDialog.form)
  } catch {
    ElMessage.success('入职账户已创建，请后续在用户目录中执行资产分配')
  }
  await loadUsers()
}

function userStatusLabel(status) {
  return {
    active: '在职',
    disabled: '停用',
    resigned: '离职',
    inactive: '停用',
    locked: '锁定',
    left: '离职',
    offboarded: '离职'
  }[status] || status || '-'
}

function userStatusType(status) {
  if (status === 'active') return 'success'
  if (isInactiveUser(status)) return 'warning'
  return 'info'
}

function isInactiveUser(status) {
  return ['inactive', 'disabled', 'locked', 'resigned', 'left', 'offboarded', '离职', '停用', '禁用'].includes(String(status || '').toLowerCase())
}

async function goAssetAssign(row) {
  await todoAssetActionsRef.value?.handle({
    type: 'onboarding_assign',
    user_id: row.user_id,
    username: row.username || '',
    name: row.display_name || row.username || row.user_id,
    owner: row.display_name || row.username || row.user_id
  })
}

async function goAssetReclaim(row) {
  await todoAssetActionsRef.value?.handle({
    type: 'user_reclaim',
    user_id: row.user_id,
    username: row.username || '',
    name: row.display_name || row.username || row.user_id
  })
}

function dateValue(value) {
  const time = new Date(value || 0).getTime()
  return Number.isFinite(time) ? time : 0
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

async function removeUser(row) {
  if (row.source !== 'local') {
    ElMessage.warning('LDAP 同步账户不能手动删除，请通过身份源同步标记离职')
    return
  }
  if (row.username === 'admin') {
    ElMessage.warning('内置管理员账户不能删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确定将账户“${row.display_name || row.username}”标记为离职吗？该用户会保留在目录中，名下资产将在待办中心生成离职回收事项。`, '标记离职', {
      confirmButtonText: '标记离职',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteUser(row.user_id)
  ElMessage.success('账户已标记离职，名下资产会进入离职回收待办')
  await loadUsers()
}

function defaultConfig(type = 'ldap') {
  const samples = {
    ldap: {
      host: '',
      port: '',
      bind_dn: '',
      bind_password: '',
      base_dn: '',
      user_filter: '',
      sync_filter: '',
      username_attr: 'uid',
      display_name_attr: 'displayName',
      email_attr: 'mail',
      dept_id_attr: '',
      dept_name_attr: '',
      default_role: 'user',
      sync_limit: '200',
      test_username: ''
    },
    feishu: {
      app_id: '',
      app_secret: ''
    }
  }
  return { ...(samples[type] || samples.ldap) }
}

function resetProviderForm() {
  Object.assign(providerForm, defaultProviderForm())
  setProviderConfig(defaultConfig(providerForm.provider_type))
}

function editProvider(row) {
  Object.assign(providerForm, { id: row.id, name: row.name, provider_type: row.provider_type, enabled: row.enabled })
  setProviderConfig({ ...defaultConfig(row.provider_type), ...(row.config || {}) })
}

async function saveProvider() {
  if (!providerForm.name.trim()) {
    ElMessage.warning('请填写身份源名称')
    return
  }
  if (providerForm.provider_type === 'ldap' && (!providerConfig.host || !providerConfig.bind_dn || !providerConfig.base_dn)) {
    ElMessage.warning('请填写 LDAP 服务器地址、绑定账号和搜索根 DN')
    return
  }
  if (providerForm.provider_type === 'feishu' && (!providerConfig.app_id || !providerConfig.app_secret)) {
    ElMessage.warning('请填写飞书应用 App ID 和 App Secret')
    return
  }
  const payload = {
    name: providerForm.name.trim(),
    provider_type: providerForm.provider_type,
    enabled: providerForm.enabled,
    config: buildProviderConfig()
  }
  if (providerForm.id) await updateIdentityProvider(providerForm.id, payload)
  else await createIdentityProvider(payload)
  ElMessage.success('身份源配置已保存')
  await loadProviders()
}

function setProviderConfig(config) {
  Object.keys(providerConfig).forEach(key => delete providerConfig[key])
  Object.assign(providerConfig, config)
}

function buildProviderConfig() {
  const config = {}
  Object.entries(providerConfig).forEach(([key, value]) => {
    if (value === '' || value == null) return
    if (['port', 'sync_limit'].includes(key)) config[key] = Number(value)
    else config[key] = value
  })
  return config
}

function providerTypeLabel(type) {
  return { ldap: 'LDAP / AD', feishu: '飞书 JSAPI' }[type] || type
}

async function copyText(text) {
  if (!text) return
  await navigator.clipboard?.writeText(text).catch(() => null)
  ElMessage.success('已复制')
}

function safeUrlHost(url) {
  try {
    return new URL(url).host
  } catch {
    return ''
  }
}

async function testProvider(row) {
  const result = await testIdentityProvider(row.id)
  ElMessage[result.last_test_status === 'success' ? 'success' : 'warning'](result.last_test_message)
  await loadProviders()
}

async function removeProvider(row) {
  try {
    await ElMessageBox.confirm(`确认删除身份源“${row.name}”？删除后不会影响已同步用户。`, '删除身份源', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteIdentityProvider(row.id)
  if (providerForm.id === row.id) resetProviderForm()
  ElMessage.success('身份源已删除')
  await loadProviders()
}

async function syncFromProvider(row = null) {
  const provider = row?.id ? row : supportedProviders.value.find(item => item.enabled && item.provider_type === 'ldap')
  if (!provider) {
    ElMessage.warning('请先配置并启用一个身份源')
    return
  }
  if (provider.provider_type !== 'ldap') {
    ElMessage.warning('当前仅 LDAP 身份源支持从目录同步用户')
    return
  }
  const result = await syncUsers({ provider_id: provider?.id })
  ElMessage.success(`同步完成：新增 ${result.created} 人，更新 ${result.updated} 人，标记离职 ${result.offboarded || 0} 人`)
  await loadUsers()
}

async function submitLogin() {
  loginResult.value = await login(loginForm)
  store.setSession(loginResult.value)
  ElMessage.success('登录成功，JWT 已写入本地会话')
  await loadUsers()
}

function paginate(rows, pagination) {
  const start = (pagination.page - 1) * pagination.pageSize
  return rows.slice(start, start + pagination.pageSize)
}
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.provider-grid {
  display: grid;
  grid-template-columns: minmax(400px, 0.9fr) minmax(520px, 1.1fr);
  gap: 16px;
}

.mobile-config-grid {
  display: grid;
  grid-template-columns: minmax(360px, 0.9fr) minmax(420px, 1.1fr);
  gap: 16px;
}

.mobile-config-grid > .el-card:last-child {
  grid-column: 1 / -1;
}

.mobile-config-desc {
  margin-bottom: 16px;
}

.copy-row {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.copy-row span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.mobile-checks {
  display: grid;
  gap: 10px;
}

.mobile-check-item {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 10px 12px;
  border: 1px solid #dbe7f3;
  border-radius: 8px;
  background: #fff;
}

.mobile-check-item div {
  display: grid;
  gap: 4px;
}

.mobile-check-item span,
.mobile-steps :deep(.el-step__description) {
  color: #64748b;
  line-height: 1.6;
}

.env-snippet {
  margin: 12px 0;
}

.rbac-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.role-select {
  width: 240px;
}

.rbac-alert {
  margin-bottom: 12px;
}

.resource-key {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}

.permission-detail-card {
  margin-top: 16px;
}

.user-permission-summary {
  margin-bottom: 16px;
}

.user-permission-picker {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.user-select {
  width: min(520px, 100%);
}

.user-permission-form {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.user-permission-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.config-help {
  margin: -4px 0 16px;
}

.feishu-guide {
  margin-bottom: 16px;
  background: #f8fbff;
}

.guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 700;
}

.guide-list {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}

.guide-list div {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid #dbe7f3;
  border-radius: 8px;
  background: #fff;
}

.guide-list strong {
  color: var(--text);
  font-size: 13px;
}

.guide-list span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.login-card {
  max-width: 760px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 1100px) {
  .provider-grid,
  .mobile-config-grid {
    grid-template-columns: 1fr;
  }

  .mobile-config-grid > .el-card:last-child {
    grid-column: auto;
  }
}
</style>
